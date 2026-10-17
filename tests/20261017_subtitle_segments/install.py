from pathlib import Path
import ast,os,shutil,sys,time

PATCH=r'''# EMBYFLOW_SUBTITLE_SEGMENTS_TEST_20261017
# Official user-authenticated API: StartPositionTicks/EndPositionTicks/CopyTimestamps.
if '_efn4_start_before' in globals():
    _embyflow_srt_v2_start=_efn4_start_before
    _embyflow_srt_v2_stop=_efn4_stop_before
    EmbyFlowMoviePlayer.embyflow_close_subtitle_window=_efn4_close_before
if '_efsc_auto_before' in globals():
    EmbyFlowMoviePlayer.set_preferred_subtitle_track=_efsc_auto_before

def _efseg_eligible(self,stream):
    source=_efut2_source(self)
    videos=[s for s in (source.get('MediaStreams') or source.get('media_streams') or []) if str(s.get('Type') or s.get('type') or '').lower()=='video']
    try:is4k=any(int(s.get('Width') or 0)>=3840 or int(s.get('Height') or 0)>=2160 for s in videos)
    except (TypeError,ValueError):return False
    title=(str(stream.get('Title') or '')+' '+str(stream.get('DisplayTitle') or '')).lower()
    forced=str(stream.get('IsForced') or '').lower() in ('true','1') or 'forced' in title or 'erzw' in title
    return (is4k and str(stream.get('IsExternal')).lower() in ('false','0')
            and _efut2_german(stream) and forced and _embyflow_srt_v2_is_text_stream(stream))

def _efseg_log(**row):
    try:
        import json,time
        row['time']=time.strftime('%H:%M:%S')
        with open('/tmp/embyflow_subtitle_segments.jsonl','a') as handle:handle.write(json.dumps(row)+'\n')
    except Exception:pass

def _efseg_fetch(urls,token,start_ms,end_ms,cancel):
    from urllib.parse import urlsplit,urlunsplit
    candidates=[]
    for url in urls:
        parts=urlsplit(url);prefix,sep,rest=parts.path.rpartition('/Items/')
        path=prefix+'/Videos/'+rest if sep else parts.path
        if path.endswith('/stream.srt'):path=path[:-len('stream.srt')]+'Stream.srt'
        url=urlunsplit((parts.scheme,parts.netloc,path,parts.query,parts.fragment))
        if url not in candidates:candidates.append(url)
    for url in candidates:
        if cancel.is_set():return None
        _efseg_log(event='request',start_ms=start_ms,end_ms=end_ms)
        # Keep the existing guarded Requests client. No new login or admin key.
        with requests.get(url,params=dict(api_key=token,StartPositionTicks=start_ms*10000,
                EndPositionTicks=end_ms*10000,CopyTimestamps='true'),
                timeout=(5,30),verify=True,stream=True) as response:
            status=int(response.status_code or 0)
            if status in (404,405):continue
            if status!=200:raise RuntimeError('HTTP '+str(status))
            chunks=[];size=0
            for chunk in response.iter_content(16384):
                if cancel.is_set():return None
                if not chunk:continue
                size+=len(chunk)
                if size>1024*1024:raise RuntimeError('Untertitelabschnitt groesser als 1 MiB')
                chunks.append(chunk)
            raw=b''.join(chunks)
        if not raw.strip():
            _efseg_log(event='response',status=status,bytes=0,cues=0,start_ms=start_ms,end_ms=end_ms)
            return []  # Forced tracks can legitimately have silent intervals.
        decoded=None
        for encoding in ('utf-8-sig','utf-8','cp1252','latin-1'):
            try:decoded=raw.decode(encoding);break
            except UnicodeError:pass
        cues=_embyflow_srt_v2_parse(decoded or '')
        # Never guess an offset if the server ignores CopyTimestamps.
        if any(b<max(0,start_ms-5000) or a>end_ms+5000 for a,b,text in cues):
            raise RuntimeError('Server liefert keine begrenzten absoluten Untertitelzeiten')
        _efseg_log(event='response',status=status,bytes=size,cues=len(cues),start_ms=start_ms,end_ms=end_ms)
        return [cue for cue in cues if cue[1]>=start_ms and cue[0]<=end_ms]
    raise RuntimeError('Untertitelabschnitt-Endpunkt nicht verfuegbar')

def _efseg_next(windows,position):
    end=max((b for a,b in windows if a<=position<b),default=None)
    if end is None:
        start=max(0,(position//60000)*60000)
        return start,start+60000
    while True:
        extended=max([end]+[b for a,b in windows if a<=end<b])
        if extended==end:break
        end=extended
    return (end,end+60000) if end-position<15000 else None

def _efseg_cancel(self):
    state=getattr(self,'_efseg_state',None)
    if state is not None:state['cancel'].set()
    self._efseg_state=None
    timer=getattr(self,'_efseg_timer',None)
    if timer is not None:timer.stop()

_efseg_stop_before=_embyflow_srt_v2_stop
def _efseg_stop(self,invalidate=True):
    _efseg_cancel(self)
    return _efseg_stop_before(self,invalidate)

def _efseg_apply(self,state):
    cues=set(tuple(cue) for segment in state['segments'].values() for cue in segment)
    self.embyflow_srt_v2_cues=sorted(cues)
    self.embyflow_srt_v2_starts=[cue[0] for cue in self.embyflow_srt_v2_cues]
    self.embyflow_srt_v2_visible_index=None
    state['display_empty']=False

def _efseg_poll(self):
    import queue,threading
    state=getattr(self,'_efseg_state',None)
    if state is None or state['cancel'].is_set():return
    try:
        if (str(getattr(self,'item_id',''))!=state['item_id'] or
                str(getattr(self,'media_source_id',''))!=state['source_id']):
            _efseg_stop(self,True)
            self.embyflow_active_subtitle_index=None
            self.embyflow_active_subtitle_stream_index=None
            return
        position=max(0,int(self.embyflow_v10_content_position_ticks() or 0)//10000)
        try:result=state['results'].get_nowait()
        except queue.Empty:result=None
        if result is not None:
            state['busy']=False
            if result.get('error'):
                _efseg_log(event='error',kind=result['error'])
                _efseg_stop(self,True)
                self.embyflow_active_subtitle_index=None
                self.embyflow_active_subtitle_stream_index=None
                self['state_label'].setText('4K-Untertitelabschnitt konnte nicht geladen werden.')
                self.show_overlay()
                return
            a,b=result['window']
            # A completed old request must not draw stale text after a seek.
            useful=(a<=position<b or any(x<=position<y and a==y for x,y in state['windows']))
            if useful:
                state['segments']={w:c for w,c in state['segments'].items() if w[1]>=position-10000 and w[0]<=position+120000}
                state['segments'][(a,b)]=result['cues']
                keep=sorted(state['segments'],key=lambda w:(0 if w[0]<=position<w[1] else 1,abs(w[0]-position)))[:3]
                state['segments']={w:state['segments'][w] for w in keep}
                state['windows']=sorted(keep)
                _efseg_apply(self,state)
                self.embyflow_srt_v2_loading=False
                self.embyflow_active_subtitle_index=state['position']
                self.embyflow_active_subtitle_stream_index=state['index']
                _efut2_source(self)['DefaultSubtitleStreamIndex']=state['index']
                _embyflow_srt_v2_overlay(self,True)
                self.embyflow_srt_v2_render_timer.start(100,False)
                self['state_label'].setText('Untertitel: '+state['label']+' (Abschnitte)')
        covered=any(a<=position<b for a,b in state['windows'])
        if not covered:
            self.embyflow_srt_v2_cues=[];self.embyflow_srt_v2_starts=[]
            self.embyflow_srt_v2_visible_index=None
            _embyflow_srt_v2_hide_overlay(self)
            state['display_empty']=True
        elif state['display_empty']:
            _efseg_apply(self,state)
        window=_efseg_next(state['windows'],position)
        if window is not None and not state['busy']:
            state['busy']=True
            urls,token=state['urls'],state['token']
            def worker():
                try:
                    cues=_efseg_fetch(urls,token,window[0],window[1],state['cancel'])
                    result=dict(window=window,cues=cues or [])
                except Exception as error:
                    # Log class only: Requests exceptions can contain secrets in URLs.
                    result=dict(error=type(error).__name__)
                if not state['cancel'].is_set():state['results'].put_nowait(result)
            threading.Thread(target=worker,name='EmbyForcedSubtitleSegment',daemon=True).start()
    except Exception as error:
        _efseg_log(event='poll-error',kind=type(error).__name__)
        _efseg_stop(self,True)
        self.embyflow_active_subtitle_index=None
        self.embyflow_active_subtitle_stream_index=None

_efseg_start_before=_embyflow_srt_v2_start
def _efseg_start(self,stream,label,position,announce=True):
    import queue,threading
    if not _efseg_eligible(self,stream):return _efseg_start_before(self,stream,label,position,announce)
    urls,token,index=_embyflow_srt_v2_urls(self,stream)
    _efseg_stop(self,True)
    self.embyflow_active_subtitle_index=None;self.embyflow_active_subtitle_stream_index=None
    self.embyflow_srt_v2_loading=True
    self._efseg_state=dict(cancel=threading.Event(),results=queue.Queue(maxsize=1),
        busy=False,windows=[],segments={},display_empty=True,urls=urls,token=token,index=int(index),position=int(position),label=str(label),
        item_id=str(getattr(self,'item_id','')),source_id=str(getattr(self,'media_source_id','')))
    timer=eTimer();self._efseg_timer=timer
    if not _embyflow_srt_v2_connect_timer(self,timer,lambda:_efseg_poll(self),'_efseg_connection'):
        _efseg_stop(self,True)
        return _efseg_start_before(self,stream,label,position,announce)
    self['state_label'].setText('Deutsche Untertitel werden abschnittsweise geladen.')
    timer.start(250,False)
    _efseg_poll(self)

_embyflow_srt_v2_start=_efseg_start
_embyflow_srt_v2_stop=_efseg_stop
'''

def patched(source):
    if '# EMBYFLOW_SUBTITLE_SEGMENTS_TEST_20261017' in source:
        raise RuntimeError('Abschnittstest bereits installiert. Nichts geaendert.')
    if '# EMBYFLOW_SUBTITLE_EMPTY_DOWNLOAD_V3_20261017' not in source:
        raise RuntimeError('V3/Build 2026101703 fehlt. Nichts geaendert.')
    old="kwargs['timeout'] = (5, 15)"
    if source.count(old)>1:raise RuntimeError('Timeoutstelle nicht eindeutig.')
    if old in source:source=source.replace(old,"kwargs['timeout'] = (5, 120)",1)
    ast.parse(source)
    result=source+'\n'+PATCH
    compile(result,'plugin.py','exec');return result

def main():
    p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    result=patched(p.read_text());backup=p.with_name('plugin.py.vor-ut-abschnitten-'+time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(str(p),str(backup));temp=p.with_name('plugin.py.subtitle-segments.tmp')
    with temp.open('x') as handle:
        handle.write(result);handle.flush();os.fsync(handle.fileno())
    shutil.copystat(str(p),str(temp));os.replace(str(temp),str(p))
    print('Untertitel-Abschnittstest installiert. Sicherung:',backup)
    print('Kein Adminzugang und keine externe SRT erforderlich. Serverunterstuetzung wird getestet.')
    print('GUI neu starten und denselben 4K-Film erneut oeffnen; nichts manuell auswaehlen.')

if __name__=='__main__':main()

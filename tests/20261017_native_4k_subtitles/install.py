from pathlib import Path
import ast, os, shutil, sys, time

PATCH='''
# EMBYFLOW_NATIVE_4K_FORCED_TEST_20261017
def _efn4_eligible(self, stream):
    from urllib.parse import urlsplit, parse_qs
    source=_efut2_source(self)
    if str(stream.get('IsExternal')).lower() not in ('false','0'):
        return False
    if not _efut2_german(stream) or not _embyflow_srt_v2_is_text_stream(stream):
        return False
    if 'Erzw.' not in _embyflow_subtitle_flags_0629(stream):
        return False
    video=[s for s in source.get('MediaStreams',[]) if str(s.get('Type','')).lower()=='video']
    if not any(int(s.get('Width') or 0)>=3840 or int(s.get('Height') or 0)>=2160 for s in video):
        return False
    url=urlsplit(str(getattr(self,'stream_url','') or ''))
    query={k.lower():v for k,v in parse_qs(url.query).items()}
    return (url.scheme in ('http','https') and url.path.lower().endswith(('.mkv','.mp4','.ts'))
            and [str(v).lower() for v in query.get('static',[])]==['true'])

def _efn4_entry(self, stream):
    embedded=[s for s in _efut2_streams(self) if str(s.get('IsExternal')).lower() in ('false','0')]
    positions=[i for i,s in enumerate(embedded) if s.get('Index')==stream.get('Index')]
    if len(positions)!=1:return None
    service=self.session.nav.getCurrentService()
    interface=service and service.subtitle()
    entries=list(interface.getSubtitleList() or []) if interface else []
    # Native indices are not Emby stream indices. Require an exact inventory.
    if len(entries)!=len(embedded):return None
    entry=entries[positions[0]]
    if len(entry)<5:return None
    language=str(entry[4] or '').lower()
    if language not in ('','und','unknown') and not _efut2_german({'Language':language}):
        return None
    return interface,entry

def _efn4_cancel(self):
    self._efn4_generation=int(getattr(self,'_efn4_generation',0))+1
    timer=getattr(self,'_efn4_timer',None)
    if timer is not None:timer.stop()
    active=getattr(self,'_efn4_active',None)
    if active is not None:
        interface,widget=active
        try:interface.disableSubtitles(widget)
        except Exception:pass
        window=getattr(self,'embyflow_subtitle_window',None)
        if window is not None:window.hide()
    self._efn4_active=None

_efn4_stop_before=_embyflow_srt_v2_stop
def _efn4_stop(self,invalidate=True):
    _efn4_cancel(self)
    return _efn4_stop_before(self,invalidate)

_efn4_start_before=_embyflow_srt_v2_start
def _efn4_start(self,stream,label,position,announce=True):
    _efn4_cancel(self)
    try:eligible=_efn4_eligible(self,stream)
    except (TypeError,ValueError):eligible=False
    if not eligible:
        return _efn4_start_before(self,stream,label,position,announce)
    _efn4_stop_before(self,True)
    generation=self._efn4_generation
    self.embyflow_srt_v2_loading=True
    self.embyflow_active_subtitle_index=None
    self.embyflow_active_subtitle_stream_index=None
    self['state_label'].setText('Untertitel werden im Player vorbereitet: '+str(label))
    state={'attempt':0}
    timer=eTimer()
    self._efn4_timer=timer
    def attempt():
        if generation!=self._efn4_generation:return
        state['attempt']+=1
        try:
            match=_efn4_entry(self,stream)
            if match is not None:
                interface,entry=match
                window=self.embyflow_get_subtitle_window()
                widget=getattr(window,'instance',None)
                if widget is None:raise RuntimeError('Kein Untertitelfenster')
                result=interface.enableSubtitles(widget,entry)
                if result is False:raise RuntimeError('Native Untertitel abgelehnt')
                self._efn4_active=(interface,widget)
                window.show()
                self.embyflow_selected_subtitle=entry
                self.embyflow_srt_v2_loading=False
                self.embyflow_active_subtitle_index=int(position)
                self.embyflow_active_subtitle_stream_index=int(stream['Index'])
                _efut2_source(self)['DefaultSubtitleStreamIndex']=int(stream['Index'])
                self['state_label'].setText('Untertitel: '+str(label)+' (Player)')
                return
        except Exception:
            _efn4_cancel(self)
            return _efn4_start_before(self,stream,label,position,announce)
        if state['attempt']<8:
            timer.start(500,True)
        else:
            _efn4_cancel(self)
            return _efn4_start_before(self,stream,label,position,announce)
    if _embyflow_srt_v2_connect_timer(self,timer,attempt,'_efn4_connection') is False:
        _efn4_cancel(self)
        return _efn4_start_before(self,stream,label,position,announce)
    attempt()

_efn4_close_before=EmbyFlowMoviePlayer.embyflow_close_subtitle_window
def _efn4_close(self):
    _efn4_cancel(self)
    return _efn4_close_before(self)

_embyflow_srt_v2_start=_efn4_start
_embyflow_srt_v2_stop=_efn4_stop
EmbyFlowMoviePlayer.embyflow_close_subtitle_window=_efn4_close
'''

def patched(source):
    if '# EMBYFLOW_NATIVE_4K_FORCED_TEST_20261017' in source:raise RuntimeError('4K-Test bereits installiert.')
    if '# EMBYFLOW_FORCED_UT_ACTIVE_SOURCE_V2_20261017' not in source:raise RuntimeError('V2/V3 fehlt. Nichts geaendert.')
    result=source+'\n'+PATCH
    compile(result,'plugin.py','exec');return result

def main():
    p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    result=patched(p.read_text());backup=p.with_name('plugin.py.vor-native-4k-'+time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(str(p),str(backup));temp=p.with_name('plugin.py.native4k.tmp')
    with temp.open('x') as handle:
        handle.write(result);handle.flush();os.fsync(handle.fileno())
    shutil.copystat(str(p),str(temp));os.replace(str(temp),str(p))
    print('Direkter 4K-Untertiteltest installiert. Sicherung:',backup)
    print('GUI neu starten und 4K-Film erneut starten; nichts manuell waehlen.')

if __name__=='__main__':main()

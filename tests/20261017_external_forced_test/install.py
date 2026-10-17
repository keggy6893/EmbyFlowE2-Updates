"""Receiver test: prefer a server-provided external German forced SRT for 4K."""
from pathlib import Path
import ast, os, shutil, sys, time

PATCH='''
# EMBYFLOW_EXTERNAL_FORCED_SRT_TEST_20261017
# Retire the unsuccessful native test for this clean external-SRT test.
if '_efn4_start_before' in globals():
    _embyflow_srt_v2_start=_efn4_start_before
    _embyflow_srt_v2_stop=_efn4_stop_before
    EmbyFlowMoviePlayer.embyflow_close_subtitle_window=_efn4_close_before

def _efsc_forced(stream):
    title=(str(stream.get('Title') or '')+' '+str(stream.get('DisplayTitle') or '')).lower()
    return str(stream.get('IsForced') or '').lower() in ('true','1') or 'forced' in title or 'erzw' in title

def _efsc_record(result, source, index=None):
    try:
        import json,os,time
        row=dict(time=time.strftime('%H:%M:%S'),result=result,index=index,
            external_count=sum(str(s.get('IsExternal')).lower() in ('true','1') for s in (source.get('MediaStreams') or source.get('media_streams') or []) if str(s.get('Type') or s.get('type') or '').lower()=='subtitle'))
        path='/tmp/embyflow_external_forced_test.json'
        with open(path+'.tmp','w') as handle:json.dump(row,handle)
        os.replace(path+'.tmp',path)
    except Exception:
        pass

_efsc_auto_before=EmbyFlowMoviePlayer.set_preferred_subtitle_track
def _efsc_auto(self):
    if getattr(self,'_efut_manual',False):return
    if self.embyflow_srt_v2_loading or self.embyflow_active_subtitle_index is not None:return
    source=_efut2_source(self)
    video=[s for s in (source.get('MediaStreams') or source.get('media_streams') or []) if str(s.get('Type') or s.get('type') or '').lower()=='video']
    try:
        is4k=any(int(s.get('Width') or 0)>=3840 or int(s.get('Height') or 0)>=2160 for s in video)
    except (TypeError,ValueError):is4k=False
    if not is4k:return _efsc_auto_before(self)
    streams=_efut2_streams(self)
    try:desired=int(source.get('DefaultSubtitleStreamIndex',-1))
    except (TypeError,ValueError):desired=-1
    selected=next((s for s in streams if str(s.get('Index'))==str(desired)),None)
    # Respect a server-selected full/foreign track. Replace only German forced
    # defaults (or no default) with an equivalent external forced SRT.
    if selected is not None and not (_efut2_german(selected) and _efsc_forced(selected)):
        return _efsc_auto_before(self)
    candidates=[]
    for position,stream in enumerate(streams):
        if str(stream.get('IsExternal')).lower() not in ('true','1'):continue
        if not _efut2_german(stream) or not _efsc_forced(stream):continue
        if str(stream.get('Codec') or '').lower() not in ('srt','subrip'):continue
        try:index=int(stream.get('Index'))
        except (TypeError,ValueError):continue
        candidates.append((0 if index==desired else 1,position,stream,index))
    if not candidates:
        _efsc_record('missing_external_german_forced_srt',source)
        self['state_label'].setText('Test: Externe deutsche Forced-SRT fehlt auf dem Server.')
        self.show_overlay()
        return
    _,position,stream,index=min(candidates,key=lambda c:(c[0],c[1]))
    _efsc_record('loading_external_german_forced_srt',source,index)
    # Bypass the retired native experiment; activation still requires parsed SRT.
    _embyflow_srt_v2_start(self,stream,_embyflow_srt_v2_language(self,stream,position),position,False)

EmbyFlowMoviePlayer.set_preferred_subtitle_track=_efsc_auto
'''

def patched(source):
    if '# EMBYFLOW_EXTERNAL_FORCED_SRT_TEST_20261017' in source:
        raise RuntimeError('Externer-SRT-Test bereits installiert. Nichts geaendert.')
    if '# EMBYFLOW_SUBTITLE_EMPTY_DOWNLOAD_V3_20261017' not in source:
        raise RuntimeError('V3 fehlt. Nichts geaendert.')
    # Undo the too-short V4 read-timeout experiment while preserving its tracing.
    old="kwargs['timeout'] = (5, 15)"
    if source.count(old)>1:raise RuntimeError('Timeoutstelle nicht eindeutig. Nichts geaendert.')
    if old in source:source=source.replace(old,"kwargs['timeout'] = (5, 120)",1)
    ast.parse(source)
    result=source+'\n'+PATCH
    compile(result,'plugin.py','exec');return result

def main():
    p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    result=patched(p.read_text())
    backup=p.with_name('plugin.py.vor-externem-ut-test-'+time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(str(p),str(backup));temp=p.with_name('plugin.py.external-ut-test.tmp')
    with temp.open('x') as handle:
        handle.write(result);handle.flush();os.fsync(handle.fileno())
    shutil.copystat(str(p),str(temp));os.replace(str(temp),str(p))
    print('Externer Forced-SRT-Test installiert. Sicherung:',backup)
    print('Voraussetzung: Admin muss passende Filmname.de.forced.srt bereitstellen und Emby neu einlesen lassen.')
    print('GUI neu starten und Film neu oeffnen. Der Test erzeugt selbst keine Untertiteldatei.')

if __name__=='__main__':main()

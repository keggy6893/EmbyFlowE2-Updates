"""Observe actual receiver subtitle decisions; do not change selection or download."""
from pathlib import Path
import ast, os, shutil, sys, time

PATCH='''
# EMBYFLOW_SUBTITLE_RUNTIME_DIAG_20261017
def _efut_runtime_snapshot(self, event):
    try:
        import json, time
        item = getattr(self, 'item', None) or {}
        sources = item.get('MediaSources') or item.get('media_sources') or []
        wanted = str(getattr(self, 'media_source_id', '') or '')
        source = _efut2_source(self)
        inventory = _efut2_streams(self)
        menu = _embyflow_subtitle_streams_0629(self)
        def info(stream):
            return dict(index=stream.get('Index'),
                language=str(stream.get('Language') or '')[:24],
                display_language=str(stream.get('DisplayLanguage') or '')[:40],
                codec=str(stream.get('Codec') or '')[:24],
                forced=str(stream.get('IsForced') or '')[:8],
                forced_label='Erzw.' in _embyflow_subtitle_flags_0629(stream),
                german=_efut2_german(stream),
                text=_embyflow_srt_v2_is_text_stream(stream))
        row=dict(time=time.strftime('%H:%M:%S'),event=event,
            source_count=len(sources),wanted_present=bool(wanted),source_found=bool(source),
            default_index=source.get('DefaultSubtitleStreamIndex'),
            manual=bool(getattr(self,'_efut_manual',False)),
            loading=bool(getattr(self,'embyflow_srt_v2_loading',False)),
            active=getattr(self,'embyflow_active_subtitle_index',None),
            waits=getattr(self,'_efut2_waits',0),
            streams=[info(s) for s in inventory],menu_streams=[info(s) for s in menu])
        with open('/tmp/embyflow_ut_runtime.jsonl','a') as handle:
            handle.write(json.dumps(row,ensure_ascii=True)+'\\n')
    except Exception:
        pass

_efut_runtime_auto_before=EmbyFlowMoviePlayer.set_preferred_subtitle_track
def _efut_runtime_auto(self):
    _efut_runtime_snapshot(self,'auto-before')
    try:
        return _efut_runtime_auto_before(self)
    finally:
        _efut_runtime_snapshot(self,'auto-after')

_efut_runtime_menu_before=EmbyFlowMoviePlayer.open_subtitle_selection
def _efut_runtime_menu(self):
    _efut_runtime_snapshot(self,'menu')
    return _efut_runtime_menu_before(self)

EmbyFlowMoviePlayer.set_preferred_subtitle_track=_efut_runtime_auto
EmbyFlowMoviePlayer.open_subtitle_selection=_efut_runtime_menu
'''

def patched(source):
    if '# EMBYFLOW_SUBTITLE_RUNTIME_DIAG_20261017' in source:
        raise RuntimeError('Diagnose bereits installiert. Nichts geaendert.')
    if '# EMBYFLOW_FORCED_UT_ACTIVE_SOURCE_V2_20261017' not in source:
        raise RuntimeError('V2/V3 fehlt. Nichts geaendert.')
    ast.parse(source)
    result=source+'\n'+PATCH
    compile(result,'plugin.py','exec')
    return result

def main():
    target=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    result=patched(target.read_text())
    backup=target.with_name('plugin.py.vor-ut-diagnose-'+time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(str(target),str(backup))
    temp=target.with_name('plugin.py.ut-diag.tmp')
    with temp.open('x') as handle:
        handle.write(result);handle.flush();os.fsync(handle.fileno())
    shutil.copystat(str(target),str(temp));os.replace(str(temp),str(target))
    print('UT-Diagnose installiert. Auswahl/Wiedergabe unveraendert. Sicherung:',backup)
    print('GUI neu starten, 4K-Film starten, 10 Sekunden warten, Untertitelmenue oeffnen.')

if __name__=='__main__':main()

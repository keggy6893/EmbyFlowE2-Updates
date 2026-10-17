from pathlib import Path
import ast, os, shutil, sys, time

PATCH = '''
# EMBYFLOW_FORCED_UT_ACTIVE_SOURCE_V2_20261017
def _efut2_source(self):
    item = getattr(self, 'item', None) or {}
    sources = item.get('MediaSources') or item.get('media_sources') or []
    wanted = str(getattr(self, 'media_source_id', '') or '')
    if wanted:
        for source in sources:
            if str(source.get('Id') or source.get('id') or '') == wanted:
                return source
        return {}
    return sources[0] if sources else {}

def _efut2_streams(self):
    source = _efut2_source(self)
    return [s for s in (source.get('MediaStreams') or source.get('media_streams') or [])
            if str(s.get('Type') or s.get('type') or '').lower() == 'subtitle']

def _efut2_german(stream):
    import re
    for key in ('Language', 'DisplayLanguage'):
        value = str(stream.get(key) or '').strip().lower()
        if re.split(r'[-_]', value)[0] in ('de', 'ger', 'deu', 'german', 'deutsch'):
            return True
    if not stream.get('Language') and not stream.get('DisplayLanguage'):
        return bool(re.search(r'\\b(?:deutsch|german)\\b', str(stream.get('DisplayTitle') or '').lower()))
    return False

def _efut2_auto(self):
    if getattr(self, '_efut_manual', False):
        return
    if self.embyflow_srt_v2_loading or self.embyflow_active_subtitle_index is not None:
        return
    source = _efut2_source(self)
    streams = _efut2_streams(self)
    if not streams:
        tries = int(getattr(self, '_efut2_waits', 0))
        if tries < 4:
            self._efut2_waits = tries + 1
            self.subtitle_timer.start(1000, True)
        return
    try:
        desired = int(source.get('DefaultSubtitleStreamIndex', -1))
    except (TypeError, ValueError):
        desired = -1
    for position, stream in enumerate(streams):
        try:
            index = int(stream.get('Index'))
        except (TypeError, ValueError):
            continue
        if not _embyflow_srt_v2_is_text_stream(stream):
            continue
        if desired >= 0:
            chosen = index == desired
        else:
            title = (str(stream.get('Title') or '') + ' ' + str(stream.get('DisplayTitle') or '')).lower()
            forced = str(stream.get('IsForced') or '').lower() in ('true', '1') or 'forced' in title or 'erzw' in title
            chosen = _efut2_german(stream) and forced
        if chosen:
            _embyflow_srt_v2_start(self, stream, _embyflow_srt_v2_language(self, stream, position), position, False)
            return

_embyflow_srt_v2_streams = _efut2_streams
EmbyFlowMoviePlayer.set_preferred_subtitle_track = _efut2_auto
'''

def patched(source):
    if '# EMBYFLOW_FORCED_UT_ACTIVE_SOURCE_V2_20261017' in source:
        raise RuntimeError('V2 bereits installiert. Nichts geaendert.')
    if '# EMBYFLOW_FORCED_UT_FIX_20261017' not in source:
        raise RuntimeError('V1/Build 2026101701 fehlt. Nichts geaendert.')
    tree=ast.parse(source)
    names={'_embyflow_srt_v2_poll_download', '_embyflow_srt_v2_selection_finished'}
    nodes=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if len(nodes)!=2:
        raise RuntimeError('Abweichende Pluginversion. Nichts geaendert.')
    lines=source.splitlines(True)
    for node in sorted(nodes, key=lambda n:n.lineno, reverse=True):
        section=''.join(lines[node.lineno-1:node.end_lineno])
        old='sources[0]["DefaultSubtitleStreamIndex"]'
        if section.count(old)!=1:
            raise RuntimeError('Abweichende Untertitelzuordnung. Nichts geaendert.')
        section=section.replace(old,'_efut2_source(self)["DefaultSubtitleStreamIndex"]',1)
        lines[node.lineno-1:node.end_lineno]=[section]
    result=''.join(lines)+'\n'+PATCH
    compile(result,'plugin.py','exec')
    return result

def main():
    target=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    result=patched(target.read_text())
    backup=target.with_name('plugin.py.vor-ut-v2-'+time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(str(target),str(backup))
    temp=target.with_name('plugin.py.ut-v2.tmp')
    with temp.open('x') as handle:
        handle.write(result);handle.flush();os.fsync(handle.fileno())
    shutil.copystat(str(target),str(temp))
    os.replace(str(temp),str(target))
    print('UT-V2 installiert. Sicherung:',backup)
    print('GUI neu starten und betroffenen Film erneut oeffnen.')

if __name__=='__main__':main()

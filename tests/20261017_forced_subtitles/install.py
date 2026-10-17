from pathlib import Path
import ast, os, shutil, sys, time

PATCH = '''
# EMBYFLOW_FORCED_UT_FIX_20261017
def _efut_get(url, **kwargs):
    try:
        return embyflow_http_get(url, **kwargs)
    except requests.exceptions.SSLError:
        raise
    except requests.exceptions.ConnectionError:
        # Exactly one fresh connection after a disconnected pooled request.
        headers = dict(kwargs.get('headers') or {})
        headers['Connection'] = 'close'
        kwargs['headers'] = headers
        return requests.get(url, **kwargs)

_efut_auto_before = EmbyFlowMoviePlayer.set_preferred_subtitle_track
_efut_selection_before = EmbyFlowMoviePlayer.subtitle_selection_finished

def _efut_selection(self, result):
    if result and result[0] in ('subtitle_off', 'subtitle', 'subtitle_bitmap_info_0629'):
        self._efut_manual = True
    return _efut_selection_before(self, result)

def _efut_auto(self):
    if getattr(self, '_efut_manual', False):
        return
    if self.embyflow_srt_v2_loading or self.embyflow_active_subtitle_index is not None:
        return
    sources = self.item.get('MediaSources') or self.item.get('media_sources') or []
    if not sources:
        return
    source = sources[0]
    try:
        desired = int(source.get('DefaultSubtitleStreamIndex', -1))
    except (TypeError, ValueError):
        desired = -1
    if desired < 0:
        for position, stream in enumerate(_embyflow_srt_v2_streams(self)):
            language = str(stream.get('Language') or stream.get('DisplayLanguage') or '').strip().lower()
            title = (str(stream.get('Title') or '') + ' ' + str(stream.get('DisplayTitle') or '')).lower()
            forced = str(stream.get('IsForced') or '').lower() in ('true', '1') or 'forced' in title or 'erzw' in title
            if language in ('de', 'deu', 'ger', 'german', 'deutsch') and forced and _embyflow_srt_v2_is_text_stream(stream):
                _embyflow_srt_v2_start(self, stream, _embyflow_srt_v2_language(self, stream, position), position, False)
                return
    return _efut_auto_before(self)

EmbyFlowMoviePlayer.set_preferred_subtitle_track = _efut_auto
EmbyFlowMoviePlayer.subtitle_selection_finished = _efut_selection
'''

def patched(source):
    if '# EMBYFLOW_FORCED_UT_FIX_20261017' in source:
        raise RuntimeError('Fix bereits installiert. Nichts geaendert.')
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_embyflow_srt_v2_start']
    if len(nodes) != 1:
        raise RuntimeError('Abweichende Pluginversion. Nichts geaendert.')
    node = nodes[0]
    lines = source.splitlines(True)
    section = ''.join(lines[node.lineno-1:node.end_lineno])
    old = 'response = embyflow_http_get('
    if section.count(old) != 1:
        raise RuntimeError('Downloadstelle weicht ab. Nichts geaendert.')
    section = section.replace(old, 'response = _efut_get(', 1)
    result = ''.join(lines[:node.lineno-1]) + section + ''.join(lines[node.end_lineno:]) + '\n' + PATCH
    compile(result, 'plugin.py', 'exec')
    return result

def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    source = target.read_text()
    result = patched(source)
    backup = target.with_name('plugin.py.vor-ut-fix-' + time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():
        raise RuntimeError('Sicherung existiert bereits. Nichts geaendert.')
    shutil.copy2(str(target), str(backup))
    temp = target.with_name('plugin.py.ut-fix.tmp')
    with temp.open('x') as handle:
        handle.write(result)
        handle.flush()
        os.fsync(handle.fileno())
    shutil.copystat(str(target), str(temp))
    os.replace(str(temp), str(target))
    print('UT-Testfix installiert. Sicherung:', backup)
    print('Jetzt GUI ueber das Box-Menue neu starten.')

if __name__ == '__main__':
    main()

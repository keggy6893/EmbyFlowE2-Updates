from pathlib import Path
import ast, os, shutil, sys, time

GET = '''def _efut_get(url, **kwargs):
    # Subtitle files use isolated guarded Sessions, not metadata response caches.
    headers = dict(kwargs.get('headers') or {})
    headers.pop('Accept-Encoding', None)
    headers['Connection'] = 'close'
    kwargs['headers'] = headers
    for attempt in range(2):
        try:
            response = requests.get(url, **kwargs)
        except requests.exceptions.SSLError:
            raise
        except requests.exceptions.ConnectionError:
            _efut3_diag(attempt, 0, 0, 'connection')
            if attempt == 0:
                continue
            raise
        status = int(response.status_code or 0)
        size = len(response.content or b'')
        _efut3_diag(attempt, status, size, 'response')
        if status != 200 or size or attempt == 1:
            return response
        response.close()
    raise RuntimeError('Untertitel-Download ohne Ergebnis')
'''

PATCH = '''
# EMBYFLOW_SUBTITLE_EMPTY_DOWNLOAD_V3_20261017
def _efut3_diag(attempt, status, size, kind):
    # No URLs, hostnames, item IDs, subtitle text, tokens or credentials.
    try:
        import json, time
        with open('/tmp/embyflow_ut_v3.jsonl', 'a') as handle:
            handle.write(json.dumps(dict(time=time.strftime('%H:%M:%S'),
                attempt=attempt+1, status=status, bytes=size, kind=kind))+'\\n')
    except Exception:
        pass

_efut3_urls_before = _embyflow_srt_v2_urls
def _efut3_urls(self, stream):
    urls, token, index = _efut3_urls_before(self, stream)
    # Both API routes are already used by this repository's text renderers.
    extra = []
    for url in urls:
        from urllib.parse import urlsplit, urlunsplit
        parts = urlsplit(url)
        prefix, sep, rest = parts.path.rpartition('/Items/')
        if sep:
            path = prefix+'/Videos/'+rest
            if path.endswith('/stream.srt'):
                path = path[:-len('stream.srt')]+'Stream.srt'
            candidate = urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
            if candidate not in urls and candidate not in extra:
                extra.append(candidate)
    return urls+extra, token, index

_embyflow_srt_v2_urls = _efut3_urls
'''

def patched(source):
    if '# EMBYFLOW_SUBTITLE_EMPTY_DOWNLOAD_V3_20261017' in source:
        raise RuntimeError('V3 bereits installiert. Nichts geaendert.')
    if '# EMBYFLOW_FORCED_UT_ACTIVE_SOURCE_V2_20261017' not in source:
        raise RuntimeError('V2/Build 2026101702 fehlt. Nichts geaendert.')
    nodes=[n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name=='_efut_get']
    if len(nodes)!=1:raise RuntimeError('Abweichende Pluginversion. Nichts geaendert.')
    node=nodes[0];lines=source.splitlines(True)
    result=''.join(lines[:node.lineno-1])+GET+''.join(lines[node.end_lineno:])+'\n'+PATCH
    compile(result,'plugin.py','exec')
    return result

def main():
    target=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    result=patched(target.read_text())
    backup=target.with_name('plugin.py.vor-ut-v3-'+time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(str(target),str(backup))
    temp=target.with_name('plugin.py.ut-v3.tmp')
    with temp.open('x') as handle:
        handle.write(result);handle.flush();os.fsync(handle.fileno())
    shutil.copystat(str(target),str(temp))
    os.replace(str(temp),str(target))
    print('UT-V3-Test installiert. Sicherung:',backup)
    print('GUI neu starten, Film erneut oeffnen und betroffene Szene pruefen.')

if __name__=='__main__':main()

from pathlib import Path
import ast, os, shutil, sys, time

GET='''def _efut_get(url, **kwargs):
    # Match e2-emby-client subtitle GET: API-key query, standard Requests headers.
    # The guarded Requests wrapper still enforces TLS and server pauses.
    if not (kwargs.get('params') or {}).get('api_key'):
        raise RuntimeError('API-Schluessel fuer Untertitel fehlt')
    kwargs['headers'] = {}
    kwargs['timeout'] = (5, 15)
    kwargs['verify'] = True
    for attempt in range(2):
        _efut3_diag(attempt, 0, 0, 'v4-request-start')
        try:
            response = requests.get(url, **kwargs)
        except requests.exceptions.SSLError:
            _efut3_diag(attempt, 0, 0, 'v4-tls-error')
            raise
        except requests.exceptions.Timeout:
            _efut3_diag(attempt, 0, 0, 'v4-timeout')
            raise
        except requests.exceptions.ConnectionError:
            _efut3_diag(attempt, 0, 0, 'v4-connection')
            if attempt == 0:
                continue
            raise
        status = int(response.status_code or 0)
        size = len(response.content or b'')
        _efut3_diag(attempt, status, size, 'v4-response')
        if status != 200 or size or attempt == 1:
            return response
        response.close()
    raise RuntimeError('Untertitel-Download ohne Ergebnis')
'''
MARKER='# EMBYFLOW_SUBTITLE_MINIMAL_REQUEST_V4_20261017'

def patched(source):
    if MARKER in source:raise RuntimeError('V4 bereits installiert. Nichts geaendert.')
    if '# EMBYFLOW_SUBTITLE_EMPTY_DOWNLOAD_V3_20261017' not in source:
        raise RuntimeError('V3/Build 2026101703 fehlt. Nichts geaendert.')
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_efut_get']
    if len(nodes)!=1:raise RuntimeError('Abweichende Pluginversion. Nichts geaendert.')
    n=nodes[0];lines=source.splitlines(True)
    result=''.join(lines[:n.lineno-1])+GET+''.join(lines[n.end_lineno:])+'\n'+MARKER+'\n'
    compile(result,'plugin.py','exec')
    return result

def main():
    target=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    result=patched(target.read_text())
    backup=target.with_name('plugin.py.vor-ut-v4-'+time.strftime('%Y%m%d-%H%M%S'))
    if backup.exists():raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(str(target),str(backup))
    temp=target.with_name('plugin.py.ut-v4.tmp')
    with temp.open('x') as handle:
        handle.write(result);handle.flush();os.fsync(handle.fileno())
    shutil.copystat(str(target),str(temp));os.replace(str(temp),str(target))
    print('UT-V4-Anfragetest installiert. Sicherung:',backup)
    print('GUI neu starten, denselben 4K-Film erneut oeffnen, nichts manuell auswaehlen.')

if __name__=='__main__':main()

from pathlib import Path
import os
import shutil
import tempfile
import time


def patched(source, runtime):
    if '# EMBYFLOW_AUTOMATIC_THEME_HEARING_V1' in source:return source
    for required in ('def _efbg_music(', 'def _triso_code(', 'def _efserver_theme_url(', 'def _efbg_cancel('):
        if required not in source:raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
    result = source+'\n\n'+runtime
    compile(result,'plugin.py','exec')
    return result


def install(path, runtime):
    path=Path(path)
    if path.is_symlink():raise RuntimeError('Unerwarteter Pluginpfad.')
    source=path.read_text();result=patched(source,runtime)
    if source == result:
        print('Theme-Hoertest bereits installiert.',flush=True)
        return False
    backup=str(path)+'.vor-theme-hoertest-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    if os.path.exists(backup):raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path,backup)
    fd,name=tempfile.mkstemp(prefix='plugin.py.theme-',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w') as handle:
            handle.write(result);handle.flush();os.fsync(handle.fileno())
        shutil.copystat(path,name);os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
    print('Theme-Hoertest installiert. Sicherung:',backup,flush=True)
    return True

RUNTIME = "# EMBYFLOW_AUTOMATIC_THEME_HEARING_V1\n# Limited receiver test, using the existing detail-page lifecycle and settings.\nimport json as _efth_json\nimport os as _efth_os\nimport signal as _efth_signal\nimport subprocess as _efth_subprocess\nimport sys as _efth_sys\nfrom urllib.parse import quote as _efth_quote, urlparse as _efth_urlparse\n\n_EFTH_SERVER_MUSIC = _efbg_music\n_EFTH_SAMPLES = {'movies': {'37724', '157336'}, 'tv_shows': {'1399', '1396'}}\n\n\nclass _EFThemeProcess:\n    def __init__(self, code, payload):\n        self.process = _efth_subprocess.Popen(\n            [_efth_sys.executable, '-c', code, _efth_json.dumps(payload)],\n            stdout=_efth_subprocess.PIPE, stderr=_efth_subprocess.PIPE,\n            start_new_session=True)\n\n    @property\n    def returncode(self):\n        return self.process.returncode\n\n    def communicate(self, **kwargs):\n        return self.process.communicate(**kwargs)\n\n    def kill(self):\n        try:\n            _efth_os.killpg(self.process.pid, _efth_signal.SIGKILL)\n        except ProcessLookupError:\n            pass\n\n\ndef _efth_lookup(data, auth, cancel, state):\n    if cancel.is_set():return ''\n    providers = data.get('ProviderIds') or data.get('provider_ids') or {}\n    kind = str(data.get('Type') or data.get('type') or '').lower()\n    tmdb = next((str(v) for k,v in providers.items() if str(k).lower() == 'tmdb'), '')\n    item_id = str(data.get('Id') or data.get('id') or '')\n    if (not tmdb or kind not in ('movie','series')) and item_id and auth and len(auth) >= 3 and all(auth[:3]):\n        response = embyflow_http_get(\n            auth[0].rstrip('/')+'/Users/%s/Items/%s' %\n            (_efth_quote(str(auth[2]),safe=''),_efth_quote(item_id,safe='')),\n            headers={'X-Emby-Token':auth[1],'X-Emby-Authorization':AUTH_HEADER},\n            timeout=8,verify=True)\n        if response.status_code == 200:\n            item = response.json() or {}\n            providers = item.get('ProviderIds') or providers\n            tmdb = next((str(v) for k,v in providers.items() if str(k).lower() == 'tmdb'), '')\n            kind = str(item.get('Type') or kind).lower()\n    if cancel.is_set() or kind not in ('movie','series'):return ''\n    category = 'tv_shows' if kind == 'series' else 'movies'\n    if tmdb not in _EFTH_SAMPLES[category]:return ''\n    entry = _json('https://app.lizardbyte.dev/ThemerrDB/%s/themoviedb/%s.json' % (category,tmdb))\n    if not isinstance(entry,dict) or str(entry.get('id')) != tmdb or cancel.is_set():return ''\n    url = entry.get('youtube_theme_url') or ''\n    if not _eftr_youtube_url(url):return ''\n    process = _EFThemeProcess(_triso_code(),\n        {'url':url,'context':None,'format':'bestaudio[ext=m4a]/bestaudio'})\n    state['process'] = process\n    try:\n        if cancel.is_set():process.kill()\n        try:\n            stdout,stderr = process.communicate(timeout=55)\n        except _efth_subprocess.TimeoutExpired:\n            process.kill()\n            process.communicate()\n            return ''\n        if process.returncode or cancel.is_set():return ''\n        if len(stdout) > 2*1024*1024:return ''\n        result = _efth_json.loads(stdout.decode('utf-8'))\n        stream = result.get('url') or ''\n        parsed = _efth_urlparse(stream)\n        if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.googlevideo.com'):\n            return ''\n        return stream\n    finally:\n        if state.get('process') is process:state['process'] = None\n\n\ndef _efth_music(data, auth, cancel, state=None):\n    if cancel.is_set() or _efbg_mode() == 'off':return ''\n    try:\n        song = _EFTH_SERVER_MUSIC(data,auth,cancel,state)\n    except Exception:\n        song = ''\n    if cancel.is_set():return ''\n    if song:return song\n    try:\n        return _efth_lookup(data,auth,cancel,state if state is not None else {})\n    except Exception:\n        return ''\n\n\n_efbg_music = _efth_music\n"

if __name__ == '__main__':
    if install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py',RUNTIME):
        print('GUI startet neu. Detail-Hintergrund auf Musik + Fanart stellen, dann Testtitel oeffnen.',flush=True)
        os.system('init 4')
        time.sleep(3)
        os.system('init 3')

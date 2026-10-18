# EMBYFLOW_AUTOMATIC_THEME_HEARING_V1
# Limited receiver test, using the existing detail-page lifecycle and settings.
import json as _efth_json
import os as _efth_os
import signal as _efth_signal
import subprocess as _efth_subprocess
import sys as _efth_sys
from urllib.parse import quote as _efth_quote, urlparse as _efth_urlparse

_EFTH_SERVER_MUSIC = _efbg_music
_EFTH_SAMPLES = {'movies': {'37724', '157336'}, 'tv_shows': {'1399', '1396'}}


class _EFThemeProcess:
    def __init__(self, code, payload):
        self.process = _efth_subprocess.Popen(
            [_efth_sys.executable, '-c', code, _efth_json.dumps(payload)],
            stdout=_efth_subprocess.PIPE, stderr=_efth_subprocess.PIPE,
            start_new_session=True)

    @property
    def returncode(self):
        return self.process.returncode

    def communicate(self, **kwargs):
        return self.process.communicate(**kwargs)

    def kill(self):
        try:
            _efth_os.killpg(self.process.pid, _efth_signal.SIGKILL)
        except ProcessLookupError:
            pass


def _efth_lookup(data, auth, cancel, state):
    if cancel.is_set():return ''
    providers = data.get('ProviderIds') or data.get('provider_ids') or {}
    kind = str(data.get('Type') or data.get('type') or '').lower()
    tmdb = next((str(v) for k,v in providers.items() if str(k).lower() == 'tmdb'), '')
    item_id = str(data.get('Id') or data.get('id') or '')
    if (not tmdb or kind not in ('movie','series')) and item_id and auth and len(auth) >= 3 and all(auth[:3]):
        response = embyflow_http_get(
            auth[0].rstrip('/')+'/Users/%s/Items/%s' %
            (_efth_quote(str(auth[2]),safe=''),_efth_quote(item_id,safe='')),
            headers={'X-Emby-Token':auth[1],'X-Emby-Authorization':AUTH_HEADER},
            timeout=8,verify=True)
        if response.status_code == 200:
            item = response.json() or {}
            providers = item.get('ProviderIds') or providers
            tmdb = next((str(v) for k,v in providers.items() if str(k).lower() == 'tmdb'), '')
            kind = str(item.get('Type') or kind).lower()
    if cancel.is_set() or kind not in ('movie','series'):return ''
    category = 'tv_shows' if kind == 'series' else 'movies'
    if tmdb not in _EFTH_SAMPLES[category]:return ''
    entry = _json('https://app.lizardbyte.dev/ThemerrDB/%s/themoviedb/%s.json' % (category,tmdb))
    if not isinstance(entry,dict) or str(entry.get('id')) != tmdb or cancel.is_set():return ''
    url = entry.get('youtube_theme_url') or ''
    if not _eftr_youtube_url(url):return ''
    process = _EFThemeProcess(_triso_code(),
        {'url':url,'context':None,'format':'bestaudio[ext=m4a]/bestaudio'})
    state['process'] = process
    try:
        if cancel.is_set():process.kill()
        try:
            stdout,stderr = process.communicate(timeout=55)
        except _efth_subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            return ''
        if process.returncode or cancel.is_set():return ''
        if len(stdout) > 2*1024*1024:return ''
        result = _efth_json.loads(stdout.decode('utf-8'))
        stream = result.get('url') or ''
        parsed = _efth_urlparse(stream)
        if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.googlevideo.com'):
            return ''
        return stream
    finally:
        if state.get('process') is process:state['process'] = None


def _efth_music(data, auth, cancel, state=None):
    if cancel.is_set() or _efbg_mode() == 'off':return ''
    try:
        song = _EFTH_SERVER_MUSIC(data,auth,cancel,state)
    except Exception:
        song = ''
    if cancel.is_set():return ''
    if song:return song
    try:
        return _efth_lookup(data,auth,cancel,state if state is not None else {})
    except Exception:
        return ''


_efbg_music = _efth_music

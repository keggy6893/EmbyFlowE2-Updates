# EMBYFLOW_ISOLATED_RESOLVER_0403
_TRISO_ORIGINAL_POPEN = _trfast_popen

def _triso_popen(command, *args, **kwargs):
    if len(command) < 3 or command[1] != _EFTR_RESOLVER_PATH:
        return _TRISO_ORIGINAL_POPEN(command, *args, **kwargs)
    existing = _eftr_sys.modules.get('yt_dlp')
    conflict = existing is not None and not str(getattr(existing, '__file__', '')).startswith(command[1] + '/')
    if len(command) >= 3 and command[1] == _EFTR_RESOLVER_PATH and conflict:
        with _trall_lock:
            context = _trall_context.get(command[-1])
        payload = {'url': command[-1], 'context': context,
                   'format': command[command.index('-f') + 1]}
        _trcache_log('RESOLVER_ISOLIERT Kontext=%s' % bool(context))
        return _eftr_subprocess.Popen([command[0], '-c', _TRISO_CODE, command[1], _eftr_json.dumps(payload)], *args, **kwargs)
    return _TRISO_ORIGINAL_POPEN(command, *args, **kwargs)

_trfast_popen = _triso_popen

def _efbg_diagnose(data, status, stderr, kind):
    title = str(data.get('title') or data.get('Name') or '').replace('\n', ' ').replace('\r', ' ')
    message = stderr.decode('utf-8', errors='replace')[-12000:]
    try:
        with open('/tmp/embyflow_background_debug.log', 'a') as handle:
            handle.write('\n%s | %s | %s | Status=%s\n%s\n' % (time.strftime('%H:%M:%S'), title, kind, status, message))
    except OSError:
        pass

def _efbg_music(data, auth, cancel, state=None):
    if cancel.is_set():
        return ''
    item_id = str(data.get('id') or data.get('Id') or '')
    server, token, user_id = auth
    providers = data.get('ProviderIds') or data.get('provider_ids') or {}
    kind = data.get('Type') or data.get('type') or 'Movie'
    try:
        response = embyflow_http_get(server.rstrip('/') + '/Users/%s/Items/%s' % (user_id, item_id),
            headers={'X-Emby-Token': token, 'X-Emby-Authorization': AUTH_HEADER}, timeout=8, verify=True)
        if response.status_code == 200:
            item = response.json() or {}
            providers = item.get('ProviderIds') or providers
            kind = item.get('Type') or kind
    except Exception:
        pass
    tmdb = next((v for k, v in providers.items() if str(k).lower() == 'tmdb'), None)
    if not tmdb or not _trall_re.fullmatch(r'[0-9]+', str(tmdb)) or cancel.is_set():
        return ''
    category = 'tv_shows' if str(kind).lower() in ('series', 'season', 'episode') else 'movies'
    info = _json('%s/%s/themoviedb/%s.json' % (THEMERR_BASE, category, tmdb))
    url = (info or {}).get('youtube_theme_url') if isinstance(info, dict) else None
    if not url or not _eftr_youtube_url(url) or cancel.is_set():
        return ''
    resolver = _eftr_ensure_resolver(cancel)
    payload = {'url': url, 'context': None, 'format': 'bestaudio[ext=m4a]/bestaudio'}
    process = _eftr_subprocess.Popen([_eftr_sys.executable, '-c', _TRISO_CODE, resolver, _eftr_json.dumps(payload)],
        stdout=_eftr_subprocess.PIPE, stderr=_eftr_subprocess.PIPE)
    if state is not None:
        state['process'] = process
    try:
        if cancel.is_set():
            process.kill()
        try:
            stdout, stderr = process.communicate(timeout=40)
        except _eftr_subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        _efbg_diagnose(data, process.returncode, stderr, 'MUSIK')
        if process.returncode or cancel.is_set():
            return ''
        stream = _eftr_json.loads(stdout.decode('utf-8')).get('url') or ''
        return stream if stream.startswith(('https://', 'http://')) else ''
    finally:
        if state is not None and state.get('process') is process:
            state['process'] = None

# Warmup must not repeatedly retry an import known to belong to another plugin.
_TRISO_WARMUP = _trwarm_start

def _trwarm_start():
    existing = _eftr_sys.modules.get('yt_dlp')
    if existing is not None and not str(getattr(existing, '__file__', '')).startswith(_EFTR_RESOLVER_PATH + '/'):
        _trcache_log('VORLADEN uebersprungen: isolierter Resolver')
        return
    return _TRISO_WARMUP()

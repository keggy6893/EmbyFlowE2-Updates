# EMBYFLOW_LCD_ORIGINAL_FANART_0404
def _efimg4_backdrop(state, auth, image_ids):
    import tempfile
    path = ''
    try:
        if state['cancel'].is_set() or not auth or not auth[0] or not auth[1]:
            return
        server, token = auth[:2]
        for image_id in image_ids:
            if state['cancel'].is_set():
                return
            response = embyflow_http_get(
                server.rstrip('/') + '/Items/%s/Images/Backdrop/0' % image_id,
                headers={'X-Emby-Token': token, 'X-Emby-Authorization': AUTH_HEADER},
                params={'maxWidth': 1280, 'quality': 90}, timeout=8, verify=True)
            content = getattr(response, 'content', b'')
            if response.status_code != 200 or not content.startswith(b'\xff\xd8'):
                continue
            if len(content) > 16 * 1024 * 1024:
                continue
            fd, path = tempfile.mkstemp(prefix='embyflow-lcd-original-', suffix='.jpg')
            with os.fdopen(fd, 'wb') as handle:
                handle.write(content)
            if _efimg3_copy(state, path, 'Backdrop.jpg'):
                _efimg3_log('LCD ungedunkeltes Emby-Backdrop bereitgestellt')
            return
    except Exception as error:
        _efimg3_log('LCD Backdrop: ' + type(error).__name__)
    finally:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass

_efimg4_worker_before = _efimg3_worker
def _efimg3_worker(state, sources):
    # Independent requests: a slow backdrop must not delay the poster.
    auth = state.get('auth')
    if auth:
        thread = _efimg3_threading.Thread(target=_efimg4_backdrop,
            args=(state, auth, state['image_ids']), name='EmbyFlowOriginalFanart')
        thread.daemon = True
        thread.start()
    _efimg4_worker_before(state, {k: v for k, v in sources.items() if k != 'Backdrop.jpg'})

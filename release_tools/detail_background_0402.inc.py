# EMBYFLOW_DETAIL_BACKGROUND_0402
# Workers own immutable input and cancellation state, never a Screen.
if not hasattr(config.embyflow, 'detail_background'):
    config.embyflow.detail_background = ConfigSelection(default='video', choices=[
        ('video', 'Video, sonst Musik und Backdrop'),
        ('music', 'Musik und Backdrop'), ('off', 'Aus')])

def _efbg_mode():
    return config.embyflow.detail_background.value

def _embyflow_theme_schedule_v1(screen):
    return

def _embyflow_theme_begin_lookup_v1(screen):
    return

def _embyflow_theme_poll_lookup_v1(screen):
    return

def _efbg_music(data, auth, cancel):
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
    if not tmdb or cancel.is_set():
        return ''
    resolver = _eftr_ensure_resolver(cancel)
    module = _trfast_load(resolver)
    # ThemerrDB is a public file lookup by existing metadata ID; no API key.
    return ThemeMediaManager(module).theme_from_themerr(tmdb, kind) or ''

def _efbg_resolve_video(data, auth, state):
    cancel = state['cancel']
    url = _eftr_lookup(data, auth, cancel)
    resolver = _eftr_ensure_resolver(cancel)
    if cancel.is_set():
        return ''
    command = _trpref_command(resolver, url)
    key = tuple(command)
    job = {'owner': _trcache_threading.get_ident(), 'event': _trcache_threading.Event()}
    with _trpref_lock:
        owns_job = key not in _trpref_jobs
        if owns_job:
            _trpref_jobs[key] = job
    try:
        process = _eftr_cached_popen(command, stdout=_eftr_subprocess.PIPE, stderr=_eftr_subprocess.PIPE)
        state['process'] = process
        if cancel.is_set():
            process.kill()
        try:
            stdout, stderr = process.communicate(timeout=60)
        except _eftr_subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise RuntimeError('Hintergrundvideo Zeitlimit')
        if process.returncode or cancel.is_set():
            return ''
        path, playlist = _eftr_select_stream(_eftr_json.loads(stdout.decode('utf-8')))
        if playlist:
            with state['lock']:
                if cancel.is_set():
                    return ''
                directory = _eftr_tempfile.mkdtemp(prefix='embyflow-background-')
                state['directory'] = directory
                path = str(_eftr_Path(directory) / 'background.m3u8')
                _eftr_Path(path).write_text(playlist)
        return path
    finally:
        state['process'] = None
        if owns_job:
            job['event'].set()
            with _trpref_lock:
                if _trpref_jobs.get(key) is job:
                    del _trpref_jobs[key]

_EFBG_START_ORIGINAL = EmbyFlowDetailScreen._fallback_detail_start

def _efbg_start(self):
    if _efbg_mode() == 'off' or getattr(self, '_fallback_closed', False):
        return
    state = self._efbg_state
    if state['started']:
        return
    state['started'] = True
    data = dict(self.data)
    auth = get_emby_auth()
    mode = _efbg_mode()
    item_id = str(data.get('id') or data.get('Id') or '')
    cache_paths = tuple('%s/grid_backdrops/%s_%s_%sx%s.jpg' %
        (CACHE_DIR, prefix, item_id, int(SCREEN_W or 1920), int(SCREEN_H or 1080))
        for prefix in ('grid', 'step1'))
    self._fallback_poll_timer = eTimer()
    self._fallback_poll_timer.callback.append(lambda: _efbg_poll(self))
    self._fallback_poll_timer.start(200, True)
    def worker():
        result = {'backdrop': '', 'video': '', 'song': ''}
        cancel = state['cancel']
        try:
            result['backdrop'] = next((p for p in cache_paths if os.path.isfile(p)), '')
            if not result['backdrop'] and not cancel.is_set():
                response = embyflow_http_get(auth[0].rstrip('/') + '/Items/%s/Images/Backdrop/0' % item_id,
                    headers={'X-Emby-Token': auth[1]}, params={'maxWidth': 1920, 'quality': 85}, timeout=8, verify=True)
                if response.status_code == 200 and len(response.content) > 1000:
                    with state['lock']:
                        if not cancel.is_set():
                            directory = _eftr_tempfile.mkdtemp(prefix='embyflow-background-image-')
                            state['image_directory'] = directory
                            path = str(_eftr_Path(directory) / 'backdrop.jpg')
                            _eftr_Path(path).write_bytes(response.content)
                            result['backdrop'] = path
            # Display the image immediately while the video lookup runs.
            with state['lock']:
                if not cancel.is_set():
                    state['preview'] = dict(result)
            if mode == 'video' and not cancel.is_set():
                try:
                    result['video'] = _efbg_resolve_video(data, auth, state)
                except Exception as error:
                    _trcache_log('HINTERGRUND_VIDEO_FEHLER ' + type(error).__name__)
            if not result['video'] and not cancel.is_set():
                try:
                    result['song'] = _efbg_music(data, auth, cancel)
                except Exception as error:
                    _trcache_log('HINTERGRUND_MUSIK_FEHLER ' + type(error).__name__)
        except Exception as error:
            _trcache_log('HINTERGRUND_FEHLER ' + type(error).__name__)
        finally:
            with state['lock']:
                if not cancel.is_set():
                    state['result'] = result
    _eftr_threading.Thread(target=worker, daemon=True).start()

def _efbg_poll(self):
    state = self._efbg_state
    if state['cancel'].is_set() or self._fallback_closed:
        return
    with state['lock']:
        result = state.pop('result', None)
        preview = state.pop('preview', None)
    if preview and result is None:
        self._fallback_result = preview
        _fallback_detail_poll(self)
        if preview.get('backdrop'):
            self['detail_blue_background'].hide()
    if result is None:
        self._fallback_poll_timer.start(200, True)
        return
    self._fallback_result = result
    _fallback_detail_poll(self)
    if result.get('video') or result.get('backdrop'):
        self['detail_blue_background'].hide()
    _trcache_log('HINTERGRUND_DETAIL Video=%s Musik=%s Backdrop=%s' %
        (bool(result['video']), bool(result['song']), bool(result['backdrop'])))

def _efbg_cancel(self, kill=True):
    state = getattr(self, '_efbg_state', None)
    if not state:
        return
    with state['lock']:
        state['cancel'].set()
    timer = getattr(self, '_fallback_poll_timer', None)
    if timer:
        timer.stop()
    process = state.get('process')
    if process and kill:
        process.kill()

def _efbg_cleanup(self):
    _efbg_cancel(self)
    state = self._efbg_state
    with state['lock']:
        for key in ('directory', 'image_directory'):
            directory = state.pop(key, None)
            if directory:
                _eftr_shutil.rmtree(directory, ignore_errors=True)

_EFBG_INIT = EmbyFlowDetailScreen.__init__
_EFBG_PLAY = EmbyFlowDetailScreen.play_selected
_EFBG_TRAILER = EmbyFlowDetailScreen.trailer_begin
_EFBG_SILENCE = EmbyFlowDetailScreen._fallback_detail_silence_tv
_EFBG_PREFETCH = _trpref_start

def _efbg_init(self, session, data):
    self._efbg_state = {'cancel': _eftr_threading.Event(), 'lock': _eftr_threading.RLock(), 'started': False}
    _EFBG_INIT(self, session, data)
    self.onClose.append(lambda: _efbg_cleanup(self))

def _efbg_play(self, *args, **kwargs):
    _efbg_cancel(self)
    return _EFBG_PLAY(self, *args, **kwargs)

def _efbg_trailer(self):
    # Suspend application of background results while the trailer player owns nav.
    _efbg_cancel(self, kill=False)
    return _EFBG_TRAILER(self)

def _efbg_silence(self):
    if _efbg_mode() != 'off':
        return _EFBG_SILENCE(self)

def _trpref_start(self):
    if _efbg_mode() != 'video':
        return _EFBG_PREFETCH(self)

EmbyFlowDetailScreen.__init__ = _efbg_init
EmbyFlowDetailScreen.play_selected = _efbg_play
EmbyFlowDetailScreen.trailer_begin = _efbg_trailer
EmbyFlowDetailScreen._fallback_detail_start = _efbg_start
EmbyFlowDetailScreen._fallback_detail_silence_tv = _efbg_silence

_EFBG_SETTINGS_INIT = EmbyFlowThemeVolumeScreen.__init__
_EFBG_SETTINGS_CHANGE = EmbyFlowThemeVolumeScreen.change

def _efbg_settings_init(self, session):
    self.background_mode = _efbg_mode()
    _EFBG_SETTINGS_INIT(self, session)
    self['actions'] = ActionMap(['OkCancelActions', 'DirectionActions', 'ColorActions'],
        {'left': lambda: self.change(-5), 'right': lambda: self.change(5),
         'up': lambda: _efbg_settings_cycle(self, -1), 'down': lambda: _efbg_settings_cycle(self, 1),
         'ok': self.save_level, 'green': self.save_level, 'cancel': self.close, 'red': self.close}, -1)
    self.change(0)

def _efbg_settings_cycle(self, step):
    modes = ('video', 'music', 'off')
    self.background_mode = modes[(modes.index(self.background_mode) + step) % len(modes)]
    self.change(0)

def _efbg_settings_change(self, amount):
    _EFBG_SETTINGS_CHANGE(self, amount)
    labels = {'video': 'Video, sonst Musik + Backdrop', 'music': 'Musik + Backdrop', 'off': 'Aus'}
    self['help'].setText('HOCH / RUNTER: %s\nNur auf der Detailseite.\nLINKS / RECHTS: Lautstaerke' % labels[self.background_mode])

def _efbg_settings_save(self):
    volume, mode = config.embyflow.theme_volume, config.embyflow.detail_background
    before = (volume.value, mode.value)
    try:
        volume.value, mode.value = str(self.level), self.background_mode
        volume.save()
        mode.save()
        configfile.save()
    except Exception:
        volume.value, mode.value = before
        volume.save()
        mode.save()
        self['help'].setText('Speichern fehlgeschlagen.')
        return
    self.close(True)

EmbyFlowThemeVolumeScreen.__init__ = _efbg_settings_init
EmbyFlowThemeVolumeScreen.change = _efbg_settings_change
EmbyFlowThemeVolumeScreen.save_level = _efbg_settings_save

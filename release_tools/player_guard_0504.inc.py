# EMBYFLOW_PLAYER_GUARD_0504_START
# Securitycheck by Paul
# Native service HTTP status is unavailable here. This gates plugin-issued
# starts and stops the native service on known host blocks/reported failures.
_efstream_active = None
_efstream_timer = None
_efstream_timer_connection = None
_efstream_nav_callbacks = {}


def _efstream_url(reference):
    try:
        value = reference.getPath()
    except Exception:
        value = str(reference or '')
    from urllib.parse import unquote
    value = unquote(str(value or ''))
    return value if _efguard_urlsplit(value).scheme.lower() in ('http', 'https') else ''


def _efstream_ref_text(reference):
    try:
        return reference.toString()
    except Exception:
        return str(reference or '')


def _efstream_is_current(state):
    try:
        current = state['nav'].getCurrentlyPlayingServiceReference()
        return current is not None and _efstream_ref_text(current) == state['reference']
    except Exception:
        return False


def _efstream_abort(state, failure=False):
    global _efstream_active, _efguard_notice
    if _efstream_active is not state:
        return
    # Clear before stopService: its EOF must not become another failure.
    _efstream_active = None
    if _efstream_timer is not None:
        _efstream_timer.stop()
    if failure:
        with _efguard_lock:
            key = _efguard_key(state['url'])
            old = _efguard_servers.get(key, {})
            _efguard_servers[key] = dict(
                until=max(old.get('until', 0), _efguard_clock() + 300),
                status='Streamfehler', probe=False)
            _efguard_notice = ('Stream konnte nicht weiter abgespielt werden. '
                               'Anfragen an diesen Server pausieren fuer mindestens 5 Minuten. '
                               'Der native Player meldet hier keinen HTTP-Status. '
                               'Securitycheck by Paul')
    state['nav'].stopService()


def _efstream_poll():
    global _efstream_active
    state = _efstream_active
    if state is None:
        if _efstream_timer is not None:
            _efstream_timer.stop()
        return
    if not _efstream_is_current(state):
        _efstream_active = None
        _efstream_timer.stop()
        return
    try:
        _efguard_check(state['url'])
    except EmbyFlowServerPaused:
        _efstream_abort(state)


def _efstream_event(event):
    state = _efstream_active
    if state is None or not _efstream_is_current(state):
        return
    owner = state.get('owner')
    if getattr(owner, '_embyflow_stream_replacement_in_progress', False):
        return
    tune_failed = getattr(iPlayableService, 'evTuneFailed', None)
    if tune_failed is not None and event == tune_failed:
        _efstream_abort(state, failure=True)
        return
    if event == getattr(iPlayableService, 'evEOF', None):
        # A genuine end and unknown duration must never be labelled HTTP 403.
        try:
            duration = int(getattr(owner, 'duration_ticks', 0) or 0)
            position = int(owner.current_position_ticks() or 0)
        except Exception:
            return
        if duration > 0 and position * 100 < duration * 95:
            _efstream_abort(state, failure=True)


def _efguard_play_service(nav, reference, *args, **kwargs):
    global _efstream_active, _efstream_timer, _efstream_timer_connection
    url = _efstream_url(reference)
    if url:
        _efguard_check(url)
    # Intentional switches/restoration must not trip on the old stream's EOF.
    _efstream_active = None
    if _efstream_timer is not None:
        _efstream_timer.stop()
    if not url:
        return nav.playService(reference, *args, **kwargs)
    if id(nav) not in _efstream_nav_callbacks:
        events = getattr(nav, 'event', None)
        if isinstance(events, list):
            events.insert(0, _efstream_event)
            _efstream_nav_callbacks[id(nav)] = nav
    if _efstream_timer is None:
        _efstream_timer = eTimer()
        try:
            _efstream_timer.callback.append(_efstream_poll)
        except AttributeError:
            _efstream_timer_connection = _efstream_timer.timeout.connect(_efstream_poll)
    session = globals().get('_efguard_gui_session')
    state = dict(nav=nav, url=url, reference=_efstream_ref_text(reference),
                 owner=getattr(session, 'current_dialog', None))
    _efstream_active = state
    try:
        result = nav.playService(reference, *args, **kwargs)
    except Exception:
        _efstream_abort(state, failure=True)
        raise
    if type(result) is int and result != 0:
        _efstream_abort(state, failure=True)
        raise RuntimeError('Streamstart fehlgeschlagen. Server-Pause: 5 Minuten.')
    if _efstream_active is state:
        _efstream_timer.start(500, False)
    return result


_efstream_previous_player_init = EmbyFlowMoviePlayer.__init__


def _efstream_player_init(self, *args, **kwargs):
    _efstream_previous_player_init(self, *args, **kwargs)
    # Prestarted services were launched before the movie screen existed.
    state = _efstream_active
    if state is not None and state['nav'] is self.session.nav:
        state['owner'] = self


EmbyFlowMoviePlayer.__init__ = _efstream_player_init
# EMBYFLOW_PLAYER_GUARD_0504_END

# EMBYFLOW_SERVER_GUARD_UI_0502_START
_efguard_previous_auth = get_emby_auth


def _efguard_auth(force=False):
    server = str(EMBY_SERVER or '').rstrip('/')
    try:
        # Include cached-token users in the server pause.
        _efguard_check(server)
        with EMBYFLOW_V18_AUTH_LOCK:
            if _embyflow_v20_cached_auth_valid():
                force = False
            return _efguard_previous_auth(force)
    except EmbyFlowServerPaused:
        return server, None, None


get_emby_auth = _efguard_auth
_efguard_previous_main = main
_efguard_gui_timer = None
_efguard_gui_connection = None
_efguard_gui_session = None


def _efguard_gui_tick():
    global _efguard_notice, _efguard_gui_session
    session = _efguard_gui_session
    if session is None:
        return
    dialogs = [getattr(session, 'current_dialog', None)]
    for entry in getattr(session, 'dialog_stack', ()):
        dialogs.append(entry[0] if isinstance(entry, (tuple, list)) else entry)
    if not any(getattr(type(dialog), '__module__', '') == __name__ for dialog in dialogs if dialog):
        _efguard_gui_timer.stop()
        _efguard_gui_session = None
        return
    with _efguard_lock:
        notice = _efguard_notice
        _efguard_notice = None
    if notice:
        session.open(MessageBox, notice, MessageBox.TYPE_INFO, timeout=12)


def _efguard_main(session, **kwargs):
    global _efguard_gui_timer, _efguard_gui_connection, _efguard_gui_session
    _efguard_gui_session = session
    if _efguard_gui_timer is None:
        _efguard_gui_timer = eTimer()
        try:
            _efguard_gui_timer.callback.append(_efguard_gui_tick)
        except AttributeError:
            _efguard_gui_connection = _efguard_gui_timer.timeout.connect(_efguard_gui_tick)
    result = _efguard_previous_main(session, **kwargs)
    _efguard_gui_timer.start(1000, False)
    return result


main = _efguard_main
# EMBYFLOW_SERVER_GUARD_UI_0502_END

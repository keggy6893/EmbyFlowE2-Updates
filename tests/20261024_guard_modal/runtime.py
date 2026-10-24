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
    # StartEnigma rejects session.open while a modal screen is not executing.
    # Keep the pending notice through dialog/service transitions.
    if not bool(getattr(session, 'in_exec', False)):
        return
    with _efguard_lock:
        notice = _efguard_notice
        _efguard_notice = None
    if notice:
        try:
            session.open(MessageBox, notice, MessageBox.TYPE_INFO, timeout=12)
        except Exception:
            # Another transition may have begun between the check and open.
            # A background notification must never crash Enigma2. Retry later;
            # do not overwrite a newer notice generated while open was tried.
            with _efguard_lock:
                if _efguard_notice is None:
                    _efguard_notice = notice

# EMBYFLOW_TV_MUTE_LOCALTEST1
# Local only: mute TV on entry, unmute plugin media, restore entry mute state.
class _EmbyFlowLocalTvMute:
    def __init__(self, session):
        from enigma import eDVBVolumecontrol
        self.session = session
        self.control = eDVBVolumecontrol.getInstance()
        self.original_muted = bool(self.control.isMuted())
        self.finished = False
        self.timer = eTimer()
        try:
            self.timer.callback.append(self.check)
        except AttributeError:
            self.connection = self.timer.timeout.connect(self.check)
        self.control.volumeMute()

    def release_for_media(self):
        if not self.finished:
            self.control.volumeUnMute()

    def check(self):
        if self.finished:
            return
        dialogs = [getattr(self.session, 'current_dialog', None)]
        for entry in getattr(self.session, 'dialog_stack', []):
            dialogs.append(entry[0] if isinstance(entry, (tuple, list)) else entry)
        if any(dialog is not None and type(dialog).__module__ == __name__ for dialog in dialogs):
            self.timer.start(250, True)
        else:
            self.finish()

    def finish(self):
        if self.finished:
            return
        self.finished = True
        self.timer.stop()
        if self.original_muted:
            self.control.volumeMute()
        else:
            self.control.volumeUnMute()
        if getattr(self.session, '_embyflow_local_tv_mute', None) is self:
            self.session._embyflow_local_tv_mute = None

_LOCAL_TV_MUTE_MAIN = main
_LOCAL_TV_MUTE_THEME_PLAY = _embyflow_theme_volume_play
_LOCAL_TV_MUTE_OPEN_PLAYER = _open_embyflow_player_now

def _embyflow_local_tv_mute_main(session, **kwargs):
    previous = getattr(session, '_embyflow_local_tv_mute', None)
    if previous is not None and not previous.finished:
        return _LOCAL_TV_MUTE_MAIN(session, **kwargs)
    state = _EmbyFlowLocalTvMute(session)
    session._embyflow_local_tv_mute = state
    try:
        result = _LOCAL_TV_MUTE_MAIN(session, **kwargs)
    except Exception:
        state.finish()
        raise
    state.timer.start(250, True)
    return result

def _embyflow_local_tv_mute_theme_play(screen, reference):
    result = _LOCAL_TV_MUTE_THEME_PLAY(screen, reference)
    # Switch away from TV first, then unmute. Keep the theme volume cap intact.
    state = getattr(screen.session, '_embyflow_local_tv_mute', None)
    if state is not None:
        state.release_for_media()
    return result

def _embyflow_local_tv_mute_open_player(session, *args, **kwargs):
    result = _LOCAL_TV_MUTE_OPEN_PLAYER(session, *args, **kwargs)
    # The existing launcher stops TV before scheduling movie/audio playback.
    state = getattr(session, '_embyflow_local_tv_mute', None)
    if state is not None:
        state.release_for_media()
    return result

main = _embyflow_local_tv_mute_main
_embyflow_theme_volume_play = _embyflow_local_tv_mute_theme_play
_open_embyflow_player_now = _embyflow_local_tv_mute_open_player

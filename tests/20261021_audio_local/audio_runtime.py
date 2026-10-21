# EMBYFLOW_AUDIO_LOCAL_BACKEND_V1_BEGIN
# DirectPlay only: keep the server URL/session and recover the movie position.
# Receiver validation is still required; a track-index acknowledgement is not
# proof that the decoder is producing sound/pictures.
_EFA_OPEN = EmbyFlowMoviePlayer.open_audio_selection
_EFA_SELECT = EmbyFlowMoviePlayer.audio_selection_finished
_EFA_CONFIRM = EmbyFlowMoviePlayer.embyflow_confirm_audio_track


def _efa_position(player):
    try:
        value = int(player.current_position_ticks() or 0)
    except Exception:
        value = 0
    if value <= 0:
        value = int(getattr(player, '_efa_menu_position', 0) or 0)
    return max(0, value)


def _efa_error(player, message):
    player.session.open(MessageBox, message, MessageBox.TYPE_ERROR, timeout=7)


def _efa_close(player):
    player._efa_pending = None
    player._efa_restore_position = None
    timer = getattr(player, '_efa_timer', None)
    if timer is not None:
        timer.stop()


def _efa_timer(player):
    timer = getattr(player, '_efa_timer', None)
    if timer is None:
        timer = eTimer()
        callback = lambda: _efa_poll(player)
        try:
            timer.callback.append(callback)
        except AttributeError:
            player._efa_connection = timer.timeout.connect(callback)
        player._efa_timer = timer
        player.onClose.append(lambda: _efa_close(player))
    return timer


def _efa_open(player):
    if getattr(player, '_efa_pending', None) is not None:
        return
    player._efa_menu_position = 0
    player._efa_menu_position = _efa_position(player)
    return _EFA_OPEN(player)


def _efa_select(player, result):
    payload = player.embyflow_extract_audio_payload(result)
    if not payload:
        return
    if getattr(player, '_efa_pending', None) is not None:
        return
    player._efa_restore_position = None
    if not _embyflow_rcdev7_static_direct(player):
        return _EFA_SELECT(player, result)
    try:
        requested = int(payload['e2_index'])
        service = player.session.nav.getCurrentService()
        tracks = service and service.audioTracks()
        if not tracks or requested < 0 or requested >= int(tracks.getNumberOfTracks()):
            raise ValueError('Die gewaehlte Tonspur ist nicht mehr verfuegbar.')
        if requested == int(tracks.getCurrentTrack()):
            return
        reference = player.session.nav.getCurrentlyPlayingServiceReference()
        backend = int(reference.type)
        position = _efa_position(player)
        if backend != 4097:
            # Keep the working backend. Restore position after acknowledgement,
            # since some receivers reset their demux clock on a track switch.
            player._efa_restore_position = position
            return _EFA_SELECT(player, result)
        if not _embyflow_engine_v11_4_exteplayer3_available():
            raise ValueError('Sicherer Tonwechsel benoetigt ExtEplayer3 / ServiceApp. '
                             'Der laufende Film wurde nicht umgeschaltet.')
        if _embyflow_engine_v11_4_mode(player) == 'e2':
            raise ValueError('Bitte im Player-Menue den Wiedergabe-Engine-Modus '
                             'Automatisch oder ExtEplayer3 waehlen und erneut versuchen.')
        stream = getattr(player, 'embyflow_audio_track_map', {}).get(requested) or {}
        if stream.get('Index') is None:
            raise ValueError('Die Tonspur kann nicht eindeutig dem Film zugeordnet werden.')
        descriptor = player.embyflow_audio_track_descriptor(tracks, requested)
        if not descriptor.get('language_key'):
            raise ValueError('Die Sprache der gewaehlten Tonspur ist nicht eindeutig erkennbar.')
        # Retain the Emby stream identity, not the old backend's track number.
        pending = dict(index=int(stream['Index']), label=str(payload.get('label') or 'Tonspur'),
                       position=position, attempts=0, descriptor=descriptor)
        timer = _efa_timer(player)
        player.embyflow_stop_audio_confirm()
        player.embyflow_manual_audio_selected = True
        player.audio_timer.stop()
        player._efa_pending = pending
        if not _embyflow_rcdev7_switch_static_to_ext(player, position):
            player._efa_pending = None
            raise ValueError('Der lokale Player konnte nicht gestartet werden.')
        player['state_label'].setText('Tonwechsel: lokaler Player wird vorbereitet')
        timer.start(250, True)
    except Exception as error:
        player._efa_restore_position = None
        _efa_error(player, str(error))


def _efa_poll(player):
    pending = getattr(player, '_efa_pending', None)
    if pending is None:
        return
    pending['attempts'] += 1
    try:
        reference = player.session.nav.getCurrentlyPlayingServiceReference()
        if reference is None or int(reference.type) != 5002:
            raise ValueError('Lokaler Player noch nicht bereit')
        service = player.session.nav.getCurrentService()
        tracks = service and service.audioTracks()
        if not tracks or int(tracks.getNumberOfTracks()) <= 0:
            raise ValueError('Tonspuren noch nicht bereit')
        player.embyflow_audio_selection_entries(tracks, int(tracks.getNumberOfTracks()),
                                               int(tracks.getCurrentTrack()))
        matches = [index for index, stream in player.embyflow_audio_track_map.items()
                   if stream and stream.get('Index') == pending['index']]
        if len(matches) != 1:
            raise ValueError('Tonspur im lokalen Player nicht eindeutig zugeordnet')
        actual = player.embyflow_audio_track_descriptor(tracks, matches[0])
        for field in ('language_key', 'codec_key', 'channels'):
            expected = pending['descriptor'].get(field)
            if expected and actual.get(field) != expected:
                raise ValueError('Tonspurmerkmale stimmen nach dem Playerwechsel nicht ueberein')
        player._efa_pending = None
        player._efa_restore_position = pending['position']
        _EFA_SELECT(player, dict(action='audio', e2_index=matches[0], label=pending['label']))
        return
    except Exception:
        if pending['attempts'] < 24:
            player._efa_timer.start(250, True)
            return
    player._efa_pending = None
    player._efa_restore_position = None
    _efa_error(player, 'Tonwechsel konnte im lokalen Player nicht vorbereitet werden. '
                       'Bitte den Film beenden und erneut fortsetzen.')


def _efa_confirm(player):
    requested = getattr(player, 'embyflow_audio_confirm_requested', None)
    result = _EFA_CONFIRM(player)
    target = getattr(player, '_efa_restore_position', None)
    if target is None or requested is None:
        return result
    if getattr(player, 'embyflow_audio_confirm_requested', None) is None:
        player._efa_restore_position = None
        service = player.session.nav.getCurrentService()
        tracks = service and service.audioTracks()
        if tracks and int(tracks.getCurrentTrack()) == int(requested):
            _embyflow_qs_v2_schedule_resume(player, target)
    return result


EmbyFlowMoviePlayer.open_audio_selection = _efa_open
EmbyFlowMoviePlayer.audio_selection_finished = _efa_select
EmbyFlowMoviePlayer.embyflow_confirm_audio_track = _efa_confirm
# EMBYFLOW_AUDIO_LOCAL_BACKEND_V1_END

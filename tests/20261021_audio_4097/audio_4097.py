# EMBYFLOW_ANSKAR_AUDIO_4097_V2_BEGIN
# A receiver-test candidate: server-selected audio, no native selectTrack on 4097.
_EFA2_OPEN = EmbyFlowMoviePlayer.open_audio_selection
_EFA2_SELECT = EmbyFlowMoviePlayer.audio_selection_finished
_EFA2_REPORT = EmbyFlowMoviePlayer.emby_report_payload


def _efa2_report(player, position_ticks=0):
    payload = _EFA2_REPORT(player, position_ticks)
    if payload and getattr(player, '_efa2_server_session', None) == player.play_session_id:
        payload['PlayMethod'] = 'DirectStream'
        payload['AudioStreamIndex'] = player.item.get('embyflow_selected_audio_index')
    return payload


def _efa2_enabled(player):
    reference = player.session.nav.getCurrentlyPlayingServiceReference()
    return bool(reference is not None and int(reference.type) == 4097
                and (_embyflow_rcdev7_static_direct(player)
                     or (getattr(player, '_efa2_server_session', None) is not None
                         and player._efa2_server_session == player.play_session_id)))


def _efa2_streams(player):
    # Keep the complete source list: a remux may expose only one native track.
    sources = player.item.get('MediaSources') or player.item.get('media_sources') or []
    wanted = str(getattr(player, 'media_source_id', '') or '')
    for source in sources:
        if wanted and str(source.get('Id') or source.get('id') or '') == wanted:
            return [s for s in source.get('MediaStreams', [])
                    if str(s.get('Type', '')).lower() == 'audio' and s.get('Index') is not None]
    if wanted and sources:
        raise ValueError('Die laufende Filmversion ist in der Serverliste nicht mehr verfügbar.')
    return [s for s in player.embyflow_media_streams_by_type('Audio')
            if s.get('Index') is not None]


def _efa2_error(player, message):
    player.session.open(MessageBox, message, MessageBox.TYPE_ERROR, timeout=8)


def _efa2_open(player):
    if not _efa2_enabled(player):
        return _EFA2_OPEN(player)
    if getattr(player, '_efa2_pending', False):
        return
    try:
        streams = _efa2_streams(player)
        if not streams:
            raise ValueError('Der Server liefert keine eindeutig zugeordneten Tonspuren.')
        player._efa2_menu_position = max(0, int(player.current_position_ticks() or 0))
        selected = player.item.get('embyflow_selected_audio_index')
        if selected is None:
            selected = player.embyflow_v10_stream_context()[4]
        entries = []
        active = 0
        for n, stream in enumerate(streams):
            index = int(stream['Index'])
            language = player.embyflow_audio_language_label(
                player.embyflow_audio_language_key(str(stream.get('Language') or '')),
                str(stream.get('DisplayLanguage') or stream.get('Language') or 'Tonspur'))
            label = str(stream.get('DisplayTitle') or stream.get('Title') or language)
            if index == selected:
                active = n
            entries.append(dict(primary=language, secondary=label,
                                tertiary=str(stream.get('Codec') or '').upper(),
                                active=index == selected,
                                payload=dict(action='audio', emby_index=index, label=label)))
        player.session.openWithCallback(player.audio_selection_finished,
                                       EmbyFlowTrackSelectionScreen,
                                       title='Tonspur auswählen', entries=entries,
                                       active_index=active)
    except Exception as error:
        _efa2_error(player, 'Tonspurauswahl nicht verfügbar: %s' % error)


def _efa2_select(player, result):
    payload = player.embyflow_extract_audio_payload(result)
    if not payload:
        return
    if 'emby_index' not in payload:
        return _EFA2_SELECT(player, result)
    if getattr(player, '_efa2_pending', False):
        return
    try:
        if not _efa2_enabled(player):
            raise ValueError('Der laufende Player hat sich geändert. Bitte die Tonspurauswahl erneut öffnen.')
        requested = int(payload['emby_index'])
        matches = [s for s in _efa2_streams(player) if int(s['Index']) == requested]
        if len(matches) != 1:
            raise ValueError('Die gewählte Server-Tonspur ist nicht eindeutig verfügbar.')
        if requested == player.item.get('embyflow_selected_audio_index',
                                       player.embyflow_v10_stream_context()[4]):
            return
        position = max(0, int(player.current_position_ticks() or 0))
        if position == 0:
            position = int(getattr(player, '_efa2_menu_position', 0) or 0)
        # Remux with burned-in subtitles would re-encode video in the old helper.
        # Leave that separate path unchanged until it can be tested independently.
        if getattr(player, 'embyflow_server_subtitle_stream_index', None) is not None:
            raise ValueError('Für diesen Tonwechsel bitte eingebrannte Untertitel zuerst ausschalten.')
        player._efa2_pending = True
        old_manual = getattr(player, 'embyflow_manual_audio_selected', False)
        player._efa2_was_paused = bool(getattr(player, 'paused', False))
        player.embyflow_manual_audio_selected = True
        player.embyflow_stop_audio_confirm()
        player.audio_timer.stop()
        if not _efa2_restart_4097(player, position, audio_index_override=requested):
            player.embyflow_manual_audio_selected = old_manual
            raise ValueError('Der Stream konnte nicht neu gestartet werden. Bitte den Film beenden und fortsetzen.')
        player._efa2_server_session = player.play_session_id
        player.item['embyflow_selected_audio_index'] = requested
        player.embyflow_active_audio_override = dict(matches[0])
        # Do not carry native indexes from the original multi-track stream over.
        player.embyflow_audio_track_map = {}
        player['state_label'].setText('Tonspur wird serverseitig gestartet: %s' % payload.get('label', 'Tonspur'))
        player._efa2_timer = eTimer()
        callback = lambda: _efa2_ready(player)
        try:
            player._efa2_timer.callback.append(callback)
        except AttributeError:
            player._efa2_connection = player._efa2_timer.timeout.connect(callback)
        player._efa2_ready_attempts = 0
        player._efa2_last_native = None
        player._efa2_expected_language = player.embyflow_audio_language_key(str(matches[0].get('Language') or ''))
        player._efa2_timer.start(500, True)
        if not getattr(player, '_efa2_close_hook', False):
            player.onClose.append(lambda: _efa2_close(player))
            player._efa2_close_hook = True
    except Exception as error:
        player._efa2_pending = False
        _efa2_error(player, str(error))


def _efa2_close(player):
    player._efa2_pending = False
    timer = getattr(player, '_efa2_timer', None)
    if timer is not None:
        timer.stop()


def _efa2_ready(player):
    if not getattr(player, '_efa2_pending', False):
        return
    player._efa2_ready_attempts += 1
    try:
        service = player.session.nav.getCurrentService()
        tracks = service and service.audioTracks()
        native = player.native_position_ticks()
        last = player._efa2_last_native
        player._efa2_last_native = native
        moving = native is not None and last is not None and native > last
        language_ok = False
        if tracks and int(tracks.getNumberOfTracks()) == 1:
            descriptor = player.embyflow_audio_track_descriptor(tracks, int(tracks.getCurrentTrack()))
            language = descriptor.get('language_key')
            expected = player._efa2_expected_language
            language_ok = not expected or not language or language == expected
        if moving and language_ok:
            player._efa2_pending = False
            if getattr(player, '_efa2_was_paused', False):
                player.pause_playback()
            player['state_label'].setText('Tonspur: Stream läuft – Bild und Ton bitte prüfen')
            player.update_playback_overlay()
            return
    except Exception:
        pass
    if player._efa2_ready_attempts < 30:
        player._efa2_timer.start(500, True)
        return
    player._efa2_pending = False
    _efa2_error(player, 'Tonwechsel: Der neue Stream wurde nicht als laufend erkannt. Bitte den Film beenden und erneut fortsetzen.')


EmbyFlowMoviePlayer.open_audio_selection = _efa2_open
EmbyFlowMoviePlayer.audio_selection_finished = _efa2_select
EmbyFlowMoviePlayer.emby_report_payload = _efa2_report
# EMBYFLOW_ANSKAR_AUDIO_4097_V2_END

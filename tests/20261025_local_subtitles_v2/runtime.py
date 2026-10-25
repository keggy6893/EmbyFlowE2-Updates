# EMBYFLOW_LOCAL_NATIVE_SUBTITLES_V2_BEGIN
_EFLU_OPEN_BEFORE = EmbyFlowMoviePlayer.open_subtitle_selection
_EFLU_SELECT_BEFORE = EmbyFlowMoviePlayer.subtitle_selection_finished


def _eflu_local(player):
    return bool((getattr(player, 'playback_info', None) or {}).get('local_file'))


def _eflu_owned(player):
    current = player.session.nav.getCurrentlyPlayingServiceReference()
    own = getattr(player, 'ref', None)
    if current is None or own is None or current.toString() != own.toString():
        raise RuntimeError('Der laufende Film hat gewechselt.')
    return current.toString()


def _eflu_inventory(player):
    owner = _eflu_owned(player)
    service = player.session.nav.getCurrentService()
    interface = service and service.subtitle()
    raw = list(interface.getSubtitleList() or []) if interface else []
    rows = []
    for entry in raw:
        if not isinstance(entry, (tuple, list)) or len(entry) < 5:
            continue
        try:
            if int(entry[0]) not in (0, 1, 2, 3):
                continue
            int(entry[1]); int(entry[2]); int(entry[3])
        except (TypeError, ValueError):
            continue
        row = tuple(entry)
        if row not in rows:
            rows.append(row)
    return owner, interface, rows


def _eflu_log(event, **fields):
    try:
        import json, time, os
        path = '/tmp/embyflow_local_subtitles.jsonl'
        if os.path.exists(path) and os.path.getsize(path) > 65536:
            return
        fields.update(event=event, time=time.strftime('%H:%M:%S'))
        with open(path, 'a') as out:
            out.write(json.dumps(fields, ensure_ascii=True) + '\n')
    except Exception:
        pass


def _eflu_open(player):
    if not _eflu_local(player):
        return _EFLU_OPEN_BEFORE(player)
    try:
        owner, interface, native = _eflu_inventory(player)
        player._eflu_menu_owner = owner
        selected = getattr(player, 'embyflow_selected_subtitle', None)
        active = tuple(selected) if isinstance(selected, (tuple, list)) else None
        entries = [dict(primary='Untertitel aus', secondary='', tertiary='',
                        active=active not in native,
                        payload=('eflu_off', None, 'Aus', None))]
        for index, entry in enumerate(native):
            language = player.embyflow_track_language_name(str(entry[4] or ''), 'Untertitel %d' % (index+1))
            kind = int(entry[0])
            codec = {0: 'DVB', 1: 'Videotext', 3: 'PGS'}.get(kind)
            if kind == 2:
                codec = {1: 'Text', 2: 'SSA', 3: 'ASS', 4: 'SRT', 6: 'PGS', 7: 'VTT'}.get(int(entry[2]), 'Nativ')
            entries.append(dict(primary=language, secondary=codec or 'Nativ', tertiary='',
                                active=entry == active,
                                payload=('eflu_native', entry, language, index)))
        _eflu_log('inventory', tracks=len(native))
        if not native:
            player['state_label'].setText('Der Dateidienst meldet keine eingebetteten Untertitel.')
        active_index = next((i for i, row in enumerate(entries) if row['active']), 0)
        return player.session.openWithCallback(player.subtitle_selection_finished,
            EmbyFlowTrackSelectionScreen, title='Untertitel auswählen',
            entries=entries, active_index=active_index)
    except Exception as error:
        _eflu_log('menu-failed', kind=type(error).__name__)
        player['state_label'].setText('Untertitelauswahl derzeit nicht verfügbar.')
        player.show_overlay()


def _eflu_selection(player, result):
    if not result or not _eflu_local(player):
        return _EFLU_SELECT_BEFORE(player, result)
    action, entry, label, position = result
    if action not in ('eflu_off', 'eflu_native'):
        return _EFLU_SELECT_BEFORE(player, result)
    try:
        owner, interface, native = _eflu_inventory(player)
        if owner != getattr(player, '_eflu_menu_owner', None):
            raise RuntimeError('Untertitelmenue gehoert nicht zum laufenden Film.')
        if action == 'eflu_native' and (interface is None or tuple(entry) not in native):
            raise RuntimeError('Native Untertitelspur nicht mehr vorhanden.')
        player._efut_manual = True
        player.embyflow_manual_subtitle_selected = True
        player._efpd_done = True
        player.subtitle_timer.stop()
        _embyflow_srt_v2_stop(player, True)
        player.embyflow_active_subtitle_index = None
        player.embyflow_active_subtitle_stream_index = None
        player.embyflow_selected_subtitle = None
        player._eflu_active = None
        window = getattr(player, 'embyflow_subtitle_window', None)
        if action == 'eflu_native':
            window = player.embyflow_get_subtitle_window()
        widget = getattr(window, 'instance', None) if window is not None else None
        if action == 'eflu_native' and widget is None:
            raise RuntimeError('Untertitelfenster nicht bereit.')
        if interface is not None and widget is not None:
            interface.disableSubtitles(widget)
        if action == 'eflu_off':
            window = getattr(player, 'embyflow_subtitle_window', None)
            if window is not None:
                window.hide()
            player['state_label'].setText('Untertitel: Aus')
            _eflu_log('off')
        else:
            # Enigma2/EMC attaches eSubtitleWidget to SubtitleDisplay.instance.
            # Never use the movie screen as its parent. Keep only native keys;
            # an optional sixth display-title field is not an activation key.
            native_key = tuple(entry[:5])
            try:
                service = player.session.nav.getCurrentService()
                seek = service and service.seek()
                before_position = seek.getPlayPosition() if seek else None
            except Exception:
                before_position = None
            _eflu_log('enable-request', native=list(native_key),
                      paused=bool(getattr(player, 'paused', False)), position=before_position)
            try:
                accepted = interface.enableSubtitles(widget, native_key)
                if accepted not in (None, 0):
                    raise RuntimeError('Dateidienst hat die Untertitel abgelehnt.')
                window.show()
            except Exception:
                try:
                    interface.disableSubtitles(widget)
                    window.hide()
                except Exception:
                    pass
                raise
            # Reuse the established native subtitle shutdown path on off/close.
            player._efpg_active = (interface, widget, window)
            player._eflu_active = tuple(entry)
            player.embyflow_selected_subtitle = tuple(entry)
            player.embyflow_active_subtitle_index = int(position)
            player['state_label'].setText('Untertitel: ' + str(label))
            _eflu_log('active', native_type=int(entry[0]), pid=int(entry[1]), language=str(entry[4]),
                      page=int(entry[2]), magazine=int(entry[3]),
                      parent='SubtitleDisplay', paused=bool(getattr(player, 'paused', False)))
        player.show_overlay()
    except Exception as error:
        _eflu_log('selection-failed', kind=type(error).__name__)
        player['state_label'].setText('Untertitel konnten nicht aktiviert werden; Auswahl erneut öffnen.')
        player.show_overlay()


EmbyFlowMoviePlayer.open_subtitle_selection = _eflu_open
EmbyFlowMoviePlayer.subtitle_selection_finished = _eflu_selection
# EMBYFLOW_LOCAL_NATIVE_SUBTITLES_V2_END

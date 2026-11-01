# EMBYFLOW_LOCAL_TS_SHARED_SUBTITLES_V1_BEGIN
# Local TS uses the native DVB service and OpenATV's shared subtitle owner.
# The published EmbyFlowMoviePlayer skin, controls and audio code stay intact.
_EFTSH_OPEN = _open_embyflow_player_now
_EFTSH_MENU = EmbyFlowMoviePlayer.open_subtitle_selection
_EFTSH_SELECTION = EmbyFlowMoviePlayer.subtitle_selection_finished
_EFTSH_AUTO = EmbyFlowMoviePlayer.set_preferred_subtitle_track
_EFTSH_SET = EmbyFlowMoviePlayer.embyflow_set_embedded_subtitle
_EFTSH_CLOSE = EmbyFlowMoviePlayer.embyflow_close_subtitle_window
_EFTSH_INIT = EmbyFlowMoviePlayer.__init__


def _eftsh_log(event, **fields):
    try:
        import json, os, time
        path = '/tmp/embyflow-ts-native.jsonl'
        if os.path.exists(path) and os.path.getsize(path) >= 65536:
            return
        fields.update(event=event, time=time.strftime('%H:%M:%S'))
        with open(path, 'a') as handle:
            handle.write(json.dumps(fields, ensure_ascii=True) + '\n')
    except Exception:
        pass






def _eftsh_display(player, event):
    try:
        _eftsh_owned(player)
        bridge = getattr(player, '_eftsh_bridge', None)
        if bridge is None:
            return
        window = bridge.subtitle_window
        widget = window.instance
        fields = dict(shown=bool(getattr(window, 'shown', False)),
                      selected=list(bridge.selected_subtitle or ()))
        attributes = getattr(window, 'skinAttributes', None)
        if isinstance(attributes, (tuple, list)):
            fields['skin'] = [x for x in attributes
                              if isinstance(x, (tuple, list)) and len(x) == 2
                              and x[0] in ('zPosition', 'position', 'size')]
        for key, name in (('visible', 'isVisible'), ('layer', 'getZPosition')):
            method = getattr(widget, name, None)
            if callable(method):
                value = method()
                if isinstance(value, (int, bool)):
                    fields[key] = value
        size = widget.size()
        fields['size'] = [size.width(), size.height()]
        _eftsh_log(event, **fields)
    except Exception as error:
        _eftsh_log('display-check-failed', kind=type(error).__name__)


def _eftsh_layer(bridge, enabled):
    window = bridge.subtitle_window
    if enabled:
        if not hasattr(bridge, '_eftsh_original_layer'):
            attributes = getattr(window, 'skinAttributes', ())
            layer = next((int(value) for name, value in attributes
                          if name == 'zPosition'), None)
            if layer is None:
                getter = getattr(window.instance, 'getZPosition', None)
                layer = getter() if callable(getter) else None
            if not isinstance(layer, int):
                raise RuntimeError('Untertitelebene kann nicht gesichert werden.')
            bridge._eftsh_original_layer = layer
        # The receiver reports SubtitleDisplay at z=-1, below our movie window.
        # Lift only the borrowed native display, leaving the player skin intact.
        window.instance.setZPosition(10)
        window._eftsh_layer_owner = bridge
        _eftsh_log('display-layer', layer=10)
    elif getattr(window, '_eftsh_layer_owner', None) is bridge:
        window.instance.setZPosition(bridge._eftsh_original_layer)
        window._eftsh_layer_owner = None
        _eftsh_log('display-layer-restored', layer=bridge._eftsh_original_layer)


def _eftsh_hide_for_dialog(player):
    try:
        _eftsh_owned(player)
        bridge = getattr(player, '_eftsh_bridge', None)
        if bridge is not None and bridge.selected_subtitle:
            bridge.subtitle_window.hide()
    except Exception:
        pass


def _eftsh_restore_after_dialog(player):
    try:
        _eftsh_owned(player)
        bridge = getattr(player, '_eftsh_bridge', None)
        if bridge is not None and bridge.selected_subtitle:
            _eftsh_layer(bridge, True)
            bridge.subtitle_window.show()
    except Exception:
        pass


def _eftsh_path(info, path):
    import posixpath
    return bool((info or {}).get('local_file') and posixpath.isabs(path)
                and path.lower().endswith('.ts'))


def _eftsh_local(player):
    info = getattr(player, 'playback_info', None) or {}
    path = str(info.get('url') or getattr(player, 'stream_url', '') or '')
    return _eftsh_path(info, path)


def _eftsh_owned(player):
    current = player.session.nav.getCurrentlyPlayingServiceReference()
    own = getattr(player, 'ref', None)
    if (getattr(player, 'closed', False) or current is None or own is None
            or current.toString() != own.toString() or current.type != 1
            or not _eftsh_local(player)):
        raise RuntimeError('Der lokale TS-Dienst hat gewechselt.')
    return current.toString()


def _eftsh_launch(session, ref, title, stream_url, playback_info=None):
    path = str(stream_url or '')
    if _eftsh_path(playback_info, path):
        ref = eServiceReference(1, 0, path)
        ref.setName(title)
        playback_info = dict(playback_info, local_service_type=1,
                             local_extension='.ts')
    return _EFTSH_OPEN(session, ref, title, stream_url, playback_info)


def _eftsh_inventory(player):
    owner = _eftsh_owned(player)
    service = player.session.nav.getCurrentService()
    interface = service and service.subtitle()
    rows = []
    if interface is not None:
        for entry in interface.getSubtitleList() or []:
            # Use the receiver's original tuple (including page/magazine).
            # Never derive DVB/teletext identifiers from ffprobe stream indices.
            if not isinstance(entry, (tuple, list)) or len(entry) < 5:
                continue
            if not isinstance(entry[0], int) or entry[0] not in (0, 1):
                continue
            row = tuple(entry)
            if row not in rows:
                rows.append(row)
    return owner, rows


def _eftsh_bridge(player):
    bridge = getattr(player, '_eftsh_bridge', None)
    if bridge is not None:
        return bridge
    from Screens.InfoBar import InfoBar
    from Screens.InfoBarGenerics import InfoBarSubtitleSupport
    from Components.ServiceEventTracker import InfoBarBase
    infobar = InfoBar.instance
    window = getattr(infobar, 'subtitle_window', None)
    if window is None or getattr(window, 'instance', None) is None:
        raise RuntimeError('Das gemeinsame Untertitelfenster ist nicht bereit.')

    class SharedSubtitleOwner(InfoBarBase, InfoBarSubtitleSupport):
        # EMC initializes BOTH mixins. Merely borrowing enableSubtitle leaves
        # the TV InfoBar as the active receiver of native subtitle events.
        # The owner borrows our Screen; it never creates a visible player.
        def __init__(self):
            # Set the borrowed Screen state before initializing either mixin.
            pass

        def __getitem__(self, name):
            return self.actions[name]

        def __setitem__(self, name, value):
            self.actions[name] = value

        def __getattr__(self, name):
            return getattr(player, name)

        def enableSubtitle(self, selected):
            if selected is not None:
                _eftsh_layer(self, True)
            try:
                result = InfoBarSubtitleSupport.enableSubtitle(self, selected)
            except Exception:
                _eftsh_layer(self, False)
                raise
            if selected is None:
                _eftsh_layer(self, False)
            return result

        def getCurrentServiceSubtitle(self):
            try:
                _eftsh_owned(player)
            except RuntimeError:
                return None
            service = player.session.nav.getCurrentService()
            interface = service and service.subtitle()
            if interface is None:
                return None

            class CheckedInterface:
                def getCachedSubtitle(self):
                    return interface.getCachedSubtitle()

                def enableSubtitles(self, widget, entry):
                    _eftsh_log('native-enable-before', track=list(entry))
                    result = interface.enableSubtitles(widget, entry)
                    _eftsh_log('native-enable-after', result=result)
                    if result not in (None, 0):
                        raise RuntimeError('TS-Dienst lehnt Untertitel ab: %r' % (result,))
                    return result

                def disableSubtitles(self, widget):
                    return interface.disableSubtitles(widget)

            return CheckedInterface()

        def doCenterDVBSubs(self):
            center = getattr(infobar, 'doCenterDVBSubs', None)
            if callable(center):
                center()

    bridge = SharedSubtitleOwner()
    bridge.session = player.session
    bridge.onClose = []
    bridge.helpList = []
    bridge.actions = {}
    try:
        # The owner can also be attached after playback already started.
        InfoBarBase.__init__(bridge, steal_current_service=True)
        InfoBarSubtitleSupport.__init__(bridge)
        # Keep EmbyFlow's selection and key handling. The native initializer's
        # optional action map is never attached to or executed by our Screen.
        bridge.actions['SubtitleSelectionAction'].setEnabled(False)
    except Exception:
        for callback in list(bridge.onClose):
            try:
                callback()
            except Exception:
                pass
        raise
    player._eftsh_bridge = bridge
    player._eftsh_owner = player.ref.toString()
    if not getattr(player, '_eftsh_dialog_hooks', False):
        player.onHide.append(lambda: _eftsh_hide_for_dialog(player))
        player.onShow.append(lambda: _eftsh_restore_after_dialog(player))
        player._eftsh_dialog_hooks = True
    _eftsh_log('native-owner-initialized')
    return bridge


def _eftsh_init(player, *args, **kwargs):
    _EFTSH_INIT(player, *args, **kwargs)
    if _eftsh_local(player):
        try:
            _eftsh_bridge(player)
        except Exception as error:
            # Let playback start. The menu can retry native initialization.
            _eftsh_log('native-owner-init-failed', kind=type(error).__name__)


def _eftsh_prepare(player):
    # Cancel the legacy external renderer once, before native activation.
    # In particular, do not run its shutdown routine after enabling TS captions.
    player._efut_manual = True
    player.embyflow_manual_subtitle_selected = True
    player._efpd_done = True
    player.subtitle_timer.stop()
    _eftsh_log('external-stop-before')
    _embyflow_srt_v2_stop(player, True)
    _eftsh_log('external-stop-after')
    player.embyflow_active_subtitle_index = None
    player.embyflow_active_subtitle_stream_index = None


def _eftsh_set(player, entry):
    if not _eftsh_local(player):
        return _EFTSH_SET(player, entry)
    owner, rows = _eftsh_inventory(player)
    if entry is not None and tuple(entry) not in rows:
        raise RuntimeError('Die Untertitelspur ist nicht mehr vorhanden.')
    bridge = _eftsh_bridge(player)
    # OpenATV/EMC does not disable the decoder before each language switch.
    # Pass the untouched native tuple to the shared SubtitleDisplay instance.
    try:
        bridge.enableSubtitle(tuple(entry) if entry is not None else None)
    except Exception:
        bridge.selected_subtitle = None
        player.embyflow_selected_subtitle = None
        bridge.subtitle_window.hide()
        raise
    player._eftsh_owner = owner
    player.embyflow_selected_subtitle = tuple(entry) if entry is not None else None
    _eftsh_display(player, 'display-after-enable' if entry is not None else 'display-off')
    if entry is not None:
        try:
            timer = getattr(player, '_eftsh_trace_timer', None)
            if timer is None:
                timer = eTimer()
                timer.callback.append(lambda: _eftsh_display(player, 'display-delayed'))
                player._eftsh_trace_timer = timer
            timer.start(1500, True)
        except Exception:
            pass


def _eftsh_message(player, text):
    player['state_label'].setText(text)
    player.show_overlay()


def _eftsh_menu(player):
    if not _eftsh_local(player):
        return _EFTSH_MENU(player)
    if getattr(player, '_eftsh_menu_pending', False):
        return 1
    try:
        owner, rows = _eftsh_inventory(player)
        player._eftsh_menu_owner = owner
        bridge = getattr(player, '_eftsh_bridge', None)
        active = (bridge.selected_subtitle if bridge is not None
                  else getattr(player, 'embyflow_selected_subtitle', None))
        entries = [dict(primary='Untertitel aus', secondary='', tertiary='',
                        active=active not in rows,
                        payload=('eftsh_off', None, 'Aus', None))]
        for position, row in enumerate(rows):
            label = player.embyflow_track_language_name(
                str(row[4] or ''), 'Untertitel %d' % (position + 1))
            codec = 'Videotext' if row[0] == 1 else 'DVB'
            entries.append(dict(primary=label, secondary=codec, tertiary='',
                                active=row == active,
                                payload=('eftsh_native', row, label, position)))
        if not rows:
            _eftsh_message(player, 'Der TS-Dienst meldet noch keine DVB-/Videotext-Untertitel.')
        player._eftsh_menu_pending = True
        player.session.openWithCallback(
            player.subtitle_selection_finished, EmbyFlowTrackSelectionScreen,
            title='Untertitel auswählen', entries=entries,
            active_index=next((i for i, row in enumerate(entries) if row['active']), 0))
    except Exception:
        player._eftsh_menu_pending = False
        _eftsh_message(player, 'TS-Untertitelauswahl derzeit nicht verfügbar.')
    # ePython::call treats None and Screen objects as unhandled. Always consume
    # GELB, including failures, so the image's pause binding cannot run next.
    return 1


def _eftsh_selection(player, result):
    player._eftsh_menu_pending = False
    if not result or result[0] not in ('eftsh_native', 'eftsh_off'):
        return _EFTSH_SELECTION(player, result)
    try:
        owner, rows = _eftsh_inventory(player)
        if owner != getattr(player, '_eftsh_menu_owner', None):
            raise RuntimeError('Die Untertitelauswahl gehört zu einem anderen Dienst.')
        action, entry, label, position = result
        _eftsh_log('selection', action=action,
                   track=list(entry) if entry is not None else None)
        if action == 'eftsh_native' and tuple(entry) not in rows:
            raise RuntimeError('Die Untertitelspur ist nicht mehr vorhanden.')
        # Resolve the shared owner before canceling the external renderer.
        _eftsh_bridge(player)
        if not getattr(player, '_eftsh_prepared', False):
            _eftsh_prepare(player)
            player._eftsh_prepared = True
        _eftsh_set(player, entry if action == 'eftsh_native' else None)
        _eftsh_message(player, 'Untertitel angefordert: ' + str(label)
                       if action == 'eftsh_native' else 'Untertitel: Aus')
    except Exception as error:
        _eftsh_log('selection-failed', kind=type(error).__name__)
        _eftsh_message(player, 'TS-Untertitel konnten nicht aktiviert werden.')


def _eftsh_auto(player):
    if not _eftsh_local(player):
        return _EFTSH_AUTO(player)
    # A local native TS service must never enter the HTTP/SRT/PGS auto path.
    player.subtitle_timer.stop()


def _eftsh_close(player):
    timer = getattr(player, '_eftsh_trace_timer', None)
    if timer is not None:
        timer.stop()
    bridge = getattr(player, '_eftsh_bridge', None)
    if bridge is not None:
        try:
            current = player.session.nav.getCurrentlyPlayingServiceReference()
            if current is None:
                # The recording has ended and no replacement service owns the
                # display yet. Hide stale captions without calling the decoder.
                bridge.subtitle_window.hide()
            elif current.toString() == getattr(player, '_eftsh_owner', None):
                service = player.session.nav.getCurrentService()
                interface = service and service.subtitle()
                if interface is not None:
                    interface.disableSubtitles(bridge.subtitle_window.instance)
                bridge.selected_subtitle = None
                bridge.subtitle_window.hide()
        except Exception:
            # A failing native shutdown must not prevent the player closing.
            # Do not hide or disable a new service's shared display here.
            pass
        # The shared InfoBar window is borrowed. Never delete it; restore its
        # saved layer only if this player still owns the temporary elevation.
        try:
            _eftsh_layer(bridge, False)
        except Exception:
            _eftsh_log('display-layer-restore-failed')
        # Release InfoBarBase's ownership and the native event subscription.
        for callback in list(bridge.onClose):
            try:
                callback()
            except Exception:
                pass
        bridge.onClose[:] = []
        player._eftsh_bridge = None
        player._eftsh_owner = None
    return _EFTSH_CLOSE(player)


_open_embyflow_player_now = _eftsh_launch
EmbyFlowMoviePlayer.open_subtitle_selection = _eftsh_menu
EmbyFlowMoviePlayer.subtitle_selection_finished = _eftsh_selection
EmbyFlowMoviePlayer.set_preferred_subtitle_track = _eftsh_auto
EmbyFlowMoviePlayer.embyflow_set_embedded_subtitle = _eftsh_set
EmbyFlowMoviePlayer.embyflow_close_subtitle_window = _eftsh_close
EmbyFlowMoviePlayer.__init__ = _eftsh_init
# EMBYFLOW_LOCAL_TS_SHARED_SUBTITLES_V1_END


# EMBYFLOW_TS_OWN_SUBTITLE_WINDOW_FIX_BEGIN
# Dedicated native subtitle surface; private player skin remains untouched.
from Screens.SubtitleDisplay import SubtitleDisplay as _eftw_SubtitleDisplay

_eftw_previous_bridge = _eftsh_bridge
_eftw_previous_layer = _eftsh_layer
_eftw_previous_close = _eftsh_close


def _eftw_log(event, **fields):
    try:
        import json
        import time
        fields.update(event=event, clock=time.strftime('%H:%M:%S'))
        with open('/tmp/embyflow-ts-window-fix.jsonl', 'a') as handle:
            handle.write(json.dumps(fields) + '\n')
    except Exception:
        pass


class _eftw_Display(_eftw_SubtitleDisplay):
    def __init__(self, session):
        _eftw_SubtitleDisplay.__init__(self, session)
        self.skinName = 'SubtitleDisplay'

    def applySkin(self):
        # Screen.applySkin passes this value to eWindow's CONSTRUCTOR.
        # setZPosition on an already registered root does not reorder roots.
        self.skinAttributes = [(name, value) for name, value in self.skinAttributes
                               if name != 'zPosition'] + [('zPosition', '10')]
        result = _eftw_SubtitleDisplay.applySkin(self)
        # Only the dedicated subtitle surface is transparent. The player still
        # clips the TV InfoBar underneath it, preserving the private UI.
        self.instance.setTransparent(1)
        self.instance.child().setTransparent(1)
        _eftw_log('subtitle-window-created', constructor_layer=10,
                   transparent=[bool(self.instance.isTransparent()),
                                bool(self.instance.child().isTransparent())])
        return result


def _eftw_bridge(player):
    bridge = _eftw_previous_bridge(player)
    if getattr(bridge, '_eftw_window', None) is not None:
        return bridge
    try:
        window = player.session.instantiateDialog(_eftw_Display)
        window.hide()
        window.setAnimationMode(0)
    except Exception as error:
        if 'window' in locals():
            player.session.deleteDialog(window)
        _eftw_log('window-create-error', kind=type(error).__name__, detail=str(error))
        raise
    bridge._eftw_window = window
    bridge.subtitle_window = window
    _eftw_log('native-owner-uses-private-window')
    return bridge


def _eftw_layer(bridge, enabled):
    if getattr(bridge, '_eftw_window', None) is not None:
        # The constructor established the ordering. Never move borrowed roots.
        return
    return _eftw_previous_layer(bridge, enabled)


def _eftw_close(player):
    bridge = getattr(player, '_eftsh_bridge', None)
    window = getattr(bridge, '_eftw_window', None)
    result = _eftw_previous_close(player)  # Disable native renderer first.
    if window is not None:
        player.session.deleteDialog(window)
        bridge._eftw_window = None
        _eftw_log('private-subtitle-window-deleted')
    return result


_eftsh_bridge = _eftw_bridge
_eftsh_layer = _eftw_layer
_eftsh_close = _eftw_close
EmbyFlowMoviePlayer.embyflow_close_subtitle_window = _eftw_close
# EMBYFLOW_TS_OWN_SUBTITLE_WINDOW_FIX_END


# EMBYFLOW_TS_SUBTITLE_STATE_FIX_BEGIN
import types as _eftu_types
_eftu_previous_bridge = _eftsh_bridge
_eftu_previous_set = _eftsh_set


def _eftu_key(entry):
    # Native type, PID, page and magazine identify this track. Cache language
    # may be 'und'; the sixth inventory field is only a display title.
    return tuple(entry[:4]) if isinstance(entry, (tuple, list)) and len(entry) >= 4 else None


def _eftu_bridge(player):
    bridge = _eftu_previous_bridge(player)
    if not getattr(bridge, '_eftu_guard_installed', False):
        previous = bridge.enableSubtitle
        def guarded(owner, selected):
            if selected and getattr(player, '_eftu_explicit_off', False):
                _eftw_log('cached-auto-enable-blocked', track=list(selected[:5]))
                return None
            return previous(selected)
        bridge.enableSubtitle = _eftu_types.MethodType(guarded, bridge)
        bridge._eftu_guard_installed = True
    return bridge


def _eftu_set(player, entry):
    if not _eftsh_local(player):
        return _eftu_previous_set(player, entry)
    previous = getattr(player, '_eftu_explicit_off', False)
    player._eftu_explicit_off = entry is None
    try:
        result = _eftu_previous_set(player, entry)
    except Exception:
        player._eftu_explicit_off = previous
        raise
    _eftw_log('explicit-subtitle-selection', enabled=entry is not None,
              track=list(entry[:5]) if entry is not None else None)
    return result


def _eftu_menu(player):
    if not _eftsh_local(player):
        return _EFTSH_MENU(player)
    if getattr(player, '_eftsh_menu_pending', False):
        return 1
    try:
        owner, rows = _eftsh_inventory(player)
        player._eftsh_menu_owner = owner
        bridge = _eftu_bridge(player)
        active = getattr(bridge, 'selected_subtitle', None)
        off = bool(getattr(player, '_eftu_explicit_off', False)) or not active
        key = None if off else _eftu_key(active)
        entries = [dict(primary='Untertitel aus', secondary='', tertiary='',
                        active=off, payload=('eftsh_off', None, 'Aus', None))]
        matched = False
        for position, row in enumerate(rows):
            label = player.embyflow_track_language_name(str(row[4] or ''), 'Untertitel %d' % (position + 1))
            selected = not matched and key is not None and _eftu_key(row) == key
            matched = matched or selected
            entries.append(dict(primary=label, secondary='Videotext' if row[0] == 1 else 'DVB',
                                tertiary='', active=selected,
                                payload=('eftsh_native', row, label, position)))
        player._eftsh_menu_pending = True
        player.session.openWithCallback(player.subtitle_selection_finished,
            EmbyFlowTrackSelectionScreen, title='Untertitel auswaehlen', entries=entries,
            active_index=next((i for i, row in enumerate(entries) if row['active']), 0))
        _eftw_log('subtitle-menu-state', off=off, matched=matched,
                  track=list(active[:5]) if active else None)
    except Exception as error:
        player._eftsh_menu_pending = False
        _eftw_log('subtitle-menu-error', kind=type(error).__name__)
        _eftsh_message(player, 'TS-Untertitelauswahl derzeit nicht verfuegbar.')
    return 1


_eftsh_bridge = _eftu_bridge
_eftsh_set = _eftu_set
EmbyFlowMoviePlayer.embyflow_set_embedded_subtitle = _eftu_set
EmbyFlowMoviePlayer.open_subtitle_selection = _eftu_menu
# EMBYFLOW_TS_SUBTITLE_STATE_FIX_END



# EMBYFLOW_LOCAL_SEEK_V1_BEGIN
_EFLS_CHAPTER_BEFORE = EmbyFlowMoviePlayer.embyflow_seek_to_chapter
_EFLS_RESTART_BEFORE = EmbyFlowMoviePlayer.embyflow_v10_restart_stream
_EFLS_FALLBACK_BEFORE = EmbyFlowMoviePlayer.restart_stream_at_ticks


def _efls_is_local(player):
    return bool((getattr(player, 'playback_info', None) or {}).get('local_file'))


def _efls_native(player, target_ticks):
    # Local files must never enter an Emby HTTP restart or backend promotion.
    # Use the active file service, as standard Enigma2/EMC seeking does.
    try:
        import os
        if getattr(player, 'closed', False):
            return False
        current = player.session.nav.getCurrentlyPlayingServiceReference()
        own = getattr(player, 'ref', None)
        path = str(getattr(player, 'stream_url', '') or '')
        if (current is None or own is None or
                current.toString() != own.toString() or not os.path.isabs(path) or
                os.path.realpath(current.getPath()) != os.path.realpath(path)):
            return False
        service = player.session.nav.getCurrentService()
        seek = service and service.seek()
        if not seek:
            return False
        capability = getattr(seek, 'isCurrentlySeekable', None)
        if callable(capability) and not capability():
            return False
        target = max(0, int(target_ticks))
        # Prefer the active service length, not remote metadata for another cut.
        length = seek.getLength()
        if length and len(length) >= 2 and length[0] == 0 and int(length[1]) > 0:
            target = min(target, max(0, (int(length[1]) * 10000000 // 90000) - 10000000))
        target_pts = target * 90000 // 10000000
        accepted = seek.seekTo(target_pts) in (None, 0)
        # Do not replace real position with the requested position, reset audio,
        # unpause deliberately paused playback, or report a server session.
        if accepted:
            player.seek_has_been_used = True
        try:
            with embyflow_open_log('/tmp/embyflow_local_seek.log', 'a') as log:
                log.write('%s LOCAL_SEEK target_pts=%s accepted=%d service=%s\n' %
                          (time.strftime('%H:%M:%S'), target_pts, accepted, current.type))
        except Exception:
            pass
        try:
            player['state_label'].setText('Lokaler Sprung angefordert' if accepted else 'Lokaler Sprung nicht angenommen')
            player.show_overlay()
        except Exception:
            pass
        return accepted
    except Exception:
        return False


def _efls_chapter(player, target_ticks):
    if _efls_is_local(player):
        return _efls_native(player, target_ticks)
    return _EFLS_CHAPTER_BEFORE(player, target_ticks)


def _efls_restart(player, target_ticks, subtitle_stream_index=None, subtitle_label=None):
    if _efls_is_local(player):
        return _efls_native(player, target_ticks)
    return _EFLS_RESTART_BEFORE(player, target_ticks, subtitle_stream_index, subtitle_label)


def _efls_fallback(player, target_ticks):
    if _efls_is_local(player):
        return _efls_native(player, target_ticks)
    return _EFLS_FALLBACK_BEFORE(player, target_ticks)


EmbyFlowMoviePlayer.embyflow_seek_to_chapter = _efls_chapter
EmbyFlowMoviePlayer.embyflow_v10_restart_stream = _efls_restart
EmbyFlowMoviePlayer.restart_stream_at_ticks = _efls_fallback
# EMBYFLOW_LOCAL_SEEK_V1_END

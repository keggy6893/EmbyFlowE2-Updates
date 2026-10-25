# EMBYFLOW_ACTIVE_AUDIO_LANGUAGE_V1_BEGIN
_EFAL_STREAMS_BEFORE = EmbyFlowMoviePlayer.tester_osd_selected_streams
_EFAL_SHOW_BEFORE = EmbyFlowMoviePlayer.show_overlay
_EFAL_UPDATE_BEFORE = EmbyFlowMoviePlayer.update_playback_overlay


def _efal_streams(player):
    source, video, audio = _EFAL_STREAMS_BEFORE(player)
    try:
        if getattr(player, 'closed', False):
            return source, video, audio
        own = getattr(player, 'ref', None)
        current = player.session.nav.getCurrentlyPlayingServiceReference()
        if own is None or current is None or own.toString() != current.toString():
            return source, video, audio
        service = player.session.nav.getCurrentService()
        tracks = service and service.audioTracks()
        if not tracks:
            return source, video, audio
        index = int(tracks.getCurrentTrack())
        if not 0 <= index < int(tracks.getNumberOfTracks()):
            return source, video, audio
        descriptor = player.embyflow_audio_track_descriptor(tracks, index)
        language = descriptor.get('language_key')
        if language:
            # Native active-track identity wins over startup/default metadata.
            # Copy only display data: no stream selection, source mutation or seek.
            audio = dict(audio or {})
            audio['Language'] = language
            audio['DisplayLanguage'] = descriptor.get('language_label') or language
            player.overlay_language = audio['DisplayLanguage']
    except Exception:
        pass
    return source, video, audio


def _efal_refresh(player):
    if getattr(player, 'closed', False):
        return
    try:
        player['technical_badges'].setText(player.tester_osd_build_badges())
        try:
            player['chip_language'].setText(player.overlay_language)
        except Exception:
            pass
    except Exception:
        pass


def _efal_show(player, *args, **kwargs):
    result = _EFAL_SHOW_BEFORE(player, *args, **kwargs)
    _efal_refresh(player)
    return result


def _efal_update(player, *args, **kwargs):
    result = _EFAL_UPDATE_BEFORE(player, *args, **kwargs)
    # A native switch can complete after the menu callback. The existing OSD
    # update picks that up without adding a timer or changing its hide timeout.
    if getattr(player, 'overlay_visible', False):
        _efal_refresh(player)
    return result


EmbyFlowMoviePlayer.tester_osd_selected_streams = _efal_streams
EmbyFlowMoviePlayer.show_overlay = _efal_show
EmbyFlowMoviePlayer.update_playback_overlay = _efal_update
# EMBYFLOW_ACTIVE_AUDIO_LANGUAGE_V1_END

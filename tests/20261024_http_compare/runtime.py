# EMBYFLOW_HTTP_COMPARE_V1_BEGIN
# server implementation is inserted here by build.py

_EFHC_DETAIL_INIT = EmbyFlowLocalSkyfallDetail.__init__
_EFHC_DETAIL_RENDER = EmbyFlowLocalSkyfallDetail.render_local
_EFHC_PLAYER_INIT = EmbyFlowMoviePlayer.__init__
_EFHC_AUDIO = EmbyFlowMoviePlayer.audio_selection_finished
_EFHC_REPORT = EmbyFlowMoviePlayer.send_emby_playback_report
_EFHC_CANCEL_ENCODING = EmbyFlowMoviePlayer.cancel_active_encoding
_EFHC_NATIVE = _efls_native


def _efhc_log(event, **fields):
    try:
        import json, time, os
        path = '/tmp/embyflow_http_compare.jsonl'
        fields.update(event=event, time=time.strftime('%H:%M:%S'))
        if os.path.exists(path) and os.path.getsize(path) > 262144:
            return
        with open(path, 'a') as out:
            out.write(json.dumps(fields, ensure_ascii=True) + '\n')
    except Exception:
        pass


def _efhc_flag(player):
    return str((getattr(player, 'playback_info', None) or {}).get('http_compare_mode') or '')


def _efhc_detail_init(self, *args, **kwargs):
    _EFHC_DETAIL_INIT(self, *args, **kwargs)
    self._efhc_server = None
    self['actions_http_compare'] = ActionMap(['ColorActions'], {
        'yellow': lambda: _efhc_play(self, 'file4097'),
        'blue': lambda: _efhc_play(self, 'http4097'),
    }, -2)
    self['status'].setText('GRUEN: USB nativ · GELB: USB GStreamer · BLAU: HTTP GStreamer (nur Box)')
    self.onClose.append(lambda: _efhc_close(self))


def _efhc_render(self):
    result = _EFHC_DETAIL_RENDER(self)
    if self.local_status == 'Originaldatei auf USB · Wiedergabe lokal':
        self['status'].setText('GRUEN: USB nativ · GELB: USB GStreamer · BLAU: HTTP GStreamer (nur Box)')
    return result


def _efhc_close(detail):
    server = getattr(detail, '_efhc_server', None)
    if server is not None:
        server.close()
        detail._efhc_server = None


def _efhc_play(detail, mode):
    try:
        import os
        from uuid import uuid4
        if not os.path.isfile(_ELS_PATH):
            raise ValueError('Originaldatei fehlt')
        if mode not in ('file4097', 'http4097'):
            raise ValueError('Testmodus ungueltig')
        probe = _embyflow_v21b_probe_local_file(_ELS_PATH) or {}
        url = _ELS_PATH
        if mode == 'http4097':
            if detail._efhc_server is None:
                detail._efhc_server = _EFHCServer(_ELS_PATH, _efhc_log)
            url = detail._efhc_server.url
        source = dict(Id='local-compare-' + mode, Path=url,
                      MediaStreams=list(probe.get('media_streams') or []),
                      DefaultSubtitleStreamIndex=-1)
        if probe.get('default_audio_index') is not None:
            source['DefaultAudioStreamIndex'] = probe['default_audio_index']
        item = dict(Id='local-compare-' + mode, Type='Movie', Name='Skyfall · ' + mode,
                    RunTimeTicks=int(probe.get('runtime_ticks') or 0), MediaSources=[source])
        info = dict(url=url, item=item, local_file=True, local_probe=probe,
                    local_service_type=4097, service_type=4097, engine_mode='e2',
                    local_extension='.ts', play_session_id='local-' + uuid4().hex,
                    http_compare_mode=mode)
        ref = eServiceReference(4097, 0, url)
        ref.setName(item['Name'])
        _efhc_log('START', mode=mode, service=4097, file_size=os.stat(_ELS_PATH).st_size)
        _open_embyflow_player_now(detail.session, ref, item['Name'], url, info)
    except Exception as error:
        detail.local_status = 'Vergleich konnte nicht starten: ' + str(error)
        detail.render_local()


def _efhc_report(player, *args, **kwargs):
    if not _efhc_flag(player):
        return _EFHC_REPORT(player, *args, **kwargs)


def _efhc_cancel_encoding(player, *args, **kwargs):
    if not _efhc_flag(player):
        return _EFHC_CANCEL_ENCODING(player, *args, **kwargs)


def _efhc_player_init(self, *args, **kwargs):
    _EFHC_PLAYER_INIT(self, *args, **kwargs)
    if not _efhc_flag(self):
        return
    self._efhc_samples = 0
    self._efhc_timer = eTimer()
    callback = lambda: _efhc_sample(self)
    self._efhc_callback = callback
    try:
        self._efhc_timer.callback.append(callback)
    except AttributeError:
        self._efhc_connection = self._efhc_timer.timeout.connect(callback)
    self.onClose.append(lambda: self._efhc_timer.stop())
    self._efhc_timer.start(1000, False)


def _efhc_sample(player):
    if getattr(player, 'closed', False) or player._efhc_samples >= 600:
        player._efhc_timer.stop()
        return
    player._efhc_samples += 1
    try:
        service = player.session.nav.getCurrentService()
        seek = service and service.seek()
        tracks = service and service.audioTracks()
        reference = player.session.nav.getCurrentlyPlayingServiceReference()
        _efhc_log('SAMPLE', mode=_efhc_flag(player),
                  service_type=getattr(reference, 'type', None),
                  position=seek.getPlayPosition() if seek else None,
                  length=seek.getLength() if seek else None,
                  audio=tracks.getCurrentTrack() if tracks else None,
                  paused=bool(getattr(player, 'paused', False)))
    except Exception as error:
        _efhc_log('SAMPLE_ERROR', error=type(error).__name__)


def _efhc_audio(player, result):
    if _efhc_flag(player):
        payload = player.embyflow_extract_audio_payload(result)
        if payload:
            _efhc_log('AUDIO_REQUEST', mode=_efhc_flag(player), index=payload.get('e2_index'))
    return _EFHC_AUDIO(player, result)


def _efhc_native(player, target_ticks):
    if _efhc_flag(player) != 'http4097':
        return _EFHC_NATIVE(player, target_ticks)
    # Isolate native HTTP seeking; never invoke provider remux or auto-5002.
    try:
        from urllib.parse import urlsplit
        if getattr(player, 'closed', False):
            return False
        url = str(getattr(player, 'stream_url', '') or '')
        parsed = urlsplit(url)
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1':
            return False
        current = player.session.nav.getCurrentlyPlayingServiceReference()
        if current is None or current.toString() != player.ref.toString() or current.getPath() != url:
            return False
        service = player.session.nav.getCurrentService()
        seek = service and service.seek()
        if not seek:
            return False
        capability = getattr(seek, 'isCurrentlySeekable', None)
        if callable(capability) and not capability():
            _efhc_log('SEEK_UNAVAILABLE', mode=_efhc_flag(player))
            return False
        target = max(0, int(target_ticks))
        length = seek.getLength()
        if length and len(length) >= 2 and length[0] == 0 and int(length[1]) > 0:
            target = min(target, max(0, int(length[1]) * 10000000 // 90000 - 10000000))
        result = seek.seekTo(target * 90000 // 10000000)
        accepted = result in (0, None)
        _efhc_log('SEEK_REQUEST', mode=_efhc_flag(player), target_ticks=target, result=result, accepted=accepted)
        return accepted
    except Exception as error:
        _efhc_log('SEEK_ERROR', error=type(error).__name__)
        return False


EmbyFlowLocalSkyfallDetail.__init__ = _efhc_detail_init
EmbyFlowLocalSkyfallDetail.render_local = _efhc_render
EmbyFlowMoviePlayer.__init__ = _efhc_player_init
EmbyFlowMoviePlayer.audio_selection_finished = _efhc_audio
EmbyFlowMoviePlayer.send_emby_playback_report = _efhc_report
EmbyFlowMoviePlayer.cancel_active_encoding = _efhc_cancel_encoding
_efls_native = _efhc_native
# EMBYFLOW_HTTP_COMPARE_V1_END

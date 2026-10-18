"""Unpublished PGS test: native 4097 only, no video restart/transcoding."""
# EMBYFLOW_PGS_NATIVE_LOCAL_V1
# EMBYFLOW_PGS_PARENT_LOCAL_V2
def _efpg_codec(stream):
    return str(stream.get('Codec') or '').strip().lower()


def _efpg_lang(value):
    import re
    value = re.split('[-_]', str(value or '').strip().lower())[0]
    return {'ger': 'de', 'deu': 'de', 'deutsch': 'de', 'german': 'de',
            'eng': 'en', 'english': 'en', 'englisch': 'en'}.get(value, value)


def _efpg_match(self, stream):
    from urllib.parse import urlsplit, parse_qs
    ref = self.session.nav.getCurrentlyPlayingServiceReference()
    if ref is None or getattr(ref, 'type', None) != 4097:
        raise RuntimeError('Der PGS-Test benoetigt den aktiven Player 4097.')
    url = urlsplit(str(getattr(self, 'stream_url', '') or ''))
    query = {k.lower(): [v.lower() for v in values]
             for k, values in parse_qs(url.query).items()}
    if (url.scheme not in ('http', 'https') or
            not url.path.lower().endswith(('.mkv', '.mp4', '.ts')) or
            query.get('static') != ['true']):
        raise RuntimeError('PGS-Test nur fuer eingebettete Spuren im Originalstream.')
    streams = _efut2_streams(self)
    # External/unknown streams cannot be mapped to embedded stream ordinals.
    embedded = [s for s in streams if str(s.get('IsExternal')).lower() in ('false', '0')]
    embedded = sorted(embedded, key=lambda s: int(s['Index']))
    indices = [int(s['Index']) for s in embedded]
    if len(set(indices)) != len(indices):
        raise RuntimeError('Mehrdeutige Emby-Untertitelindizes.')
    matches = [i for i, s in enumerate(embedded)
               if int(s['Index']) == int(stream['Index']) and s == stream]
    if len(matches) != 1 or _efpg_codec(stream) not in ('pgs', 'pgssub', 'hdmv_pgs_subtitle'):
        raise RuntimeError('Keine eingebettete PGS-Spur der aktiven Filmversion.')
    service = self.session.nav.getCurrentService()
    interface = service and service.subtitle()
    native = list(interface.getSubtitleList() or []) if interface else []
    # The backend exposes subtitle ordinals, not Emby video/audio stream IDs.
    # Reject partial/mixed/unknown inventories instead of guessing a language.
    if len(native) != len(embedded):
        raise RuntimeError('4097 bietet keine eindeutig zuordenbare PGS-Spurliste an.')
    types = {'pgs': (6,), 'pgssub': (6,), 'hdmv_pgs_subtitle': (6,),
             'subrip': (4,), 'srt': (4,), 'ssa': (2,), 'ass': (3,),
             'text': (1,), 'webvtt': (7,), 'vtt': (7,)}
    by_pid = {}
    for entry in native:
        if not isinstance(entry, (tuple, list)) or len(entry) < 5:
            raise RuntimeError('Unbekanntes natives Untertitelformat.')
        pid = int(entry[1])
        if pid in by_pid or not 0 <= pid < len(embedded):
            raise RuntimeError('Mehrdeutige native Untertitelindizes.')
        expected = embedded[pid]
        subtype = int(entry[2])
        if subtype not in types.get(_efpg_codec(expected), ()):
            raise RuntimeError('Untertitelcodecs von Emby und 4097 passen nicht zusammen.')
        expected_type = (2, 3) if subtype == 6 else (2,)
        if int(entry[0]) not in expected_type:
            raise RuntimeError('PGS wird von diesem 4097-Backend nicht angeboten.')
        left, right = _efpg_lang(expected.get('Language')), _efpg_lang(entry[4])
        if not left or left in ('und', 'unknown') or left != right:
            raise RuntimeError('Untertitelsprachen sind nicht eindeutig zuordenbar.')
        by_pid[pid] = entry
    return interface, by_pid[matches[0]]


_efpg_stop_before = _embyflow_srt_v2_stop
def _efpg_stop(self, invalidate=True):
    active = getattr(self, '_efpg_active', None)
    self._efpg_active = None
    if active is not None:
        interface, widget, window = active
        try:
            interface.disableSubtitles(widget)
        except Exception:
            pass
        try:
            window.hide()
        except Exception:
            pass
        self.embyflow_selected_subtitle = None
        self.embyflow_active_subtitle_index = None
        self.embyflow_active_subtitle_stream_index = None
    return _efpg_stop_before(self, invalidate)


def _efpg_start(self, stream, label, position):
    interface, entry = _efpg_match(self, stream)
    window = self.embyflow_get_subtitle_window()
    # Attach native eSubtitleWidget to the visible EmbyFlow movie screen.
    # Its parent determines both size and compositor layer. The separate
    # standard SubtitleDisplay can live below modal plugin screens.
    widget = getattr(self, 'instance', None)
    if widget is None:
        raise RuntimeError('Kein natives Untertitelfenster verfuegbar.')
    _efpg_stop(self, True)
    self.embyflow_active_subtitle_index = None
    self.embyflow_active_subtitle_stream_index = None
    try:
        # Cached selections may return 0 without attaching a new display owner.
        interface.disableSubtitles(widget)
        result = interface.enableSubtitles(widget, entry)
        if result not in (None, 0):
            raise RuntimeError('4097 hat die PGS-Aktivierung abgelehnt.')
        window.show()
    except Exception:
        try:
            interface.disableSubtitles(widget)
            window.hide()
        except Exception:
            pass
        raise
    self._efpg_active = (interface, widget, window)
    self.embyflow_selected_subtitle = entry
    self.embyflow_active_subtitle_index = int(position)
    self.embyflow_active_subtitle_stream_index = int(stream['Index'])
    _efut2_source(self)['DefaultSubtitleStreamIndex'] = int(stream['Index'])
    self['state_label'].setText('Untertitel: ' + str(label) + ' (PGS)')
    self.show_overlay()


_efpg_selection_before = EmbyFlowMoviePlayer.subtitle_selection_finished
def _efpg_selection(self, result):
    if not result:
        return _efpg_selection_before(self, result)
    action, stream, label, position = result
    if action == 'subtitle_bitmap_info_0629' and _efpg_codec(stream or {}) in ('pgs', 'pgssub', 'hdmv_pgs_subtitle'):
        self._efut_manual = True
        try:
            _efpg_start(self, stream, label, position)
        except Exception as error:
            self.session.open(MessageBox, str(error), MessageBox.TYPE_INFO, timeout=8)
        return
    # Cancel native display even when a non-PGS start fails before SRT stop.
    if action in ('subtitle', 'subtitle_off'):
        _efpg_stop(self, True)
    return _efpg_selection_before(self, result)


_efpg_close_before = EmbyFlowMoviePlayer.embyflow_close_subtitle_window
def _efpg_close(self):
    _efpg_stop(self, True)
    return _efpg_close_before(self)


_embyflow_srt_v2_stop = _efpg_stop
EmbyFlowMoviePlayer.subtitle_selection_finished = _efpg_selection
EmbyFlowMoviePlayer.embyflow_close_subtitle_window = _efpg_close

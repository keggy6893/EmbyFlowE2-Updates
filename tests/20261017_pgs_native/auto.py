"""PGS automatic selection on the already receiver-tested native display path."""
# EMBYFLOW_PGS_AUTO_LOCAL_V3
def _efpga_forced(stream):
    title = (str(stream.get('Title') or '') + ' ' + str(stream.get('DisplayTitle') or '')).lower()
    return str(stream.get('IsForced')).strip().lower() in ('true', '1') or 'forced' in title or 'erzw' in title


def _efpga_candidate(self):
    source = _efut2_source(self)
    streams = _efut2_streams(self)
    try:
        desired = int(source.get('DefaultSubtitleStreamIndex', -1))
    except (TypeError, ValueError):
        desired = -1
    if desired >= 0:
        # A user/server-selected text, full, or foreign-language track wins.
        for position, stream in enumerate(streams):
            try:
                if int(stream.get('Index')) != desired:
                    continue
            except (TypeError, ValueError):
                continue
            if _efpg_codec(stream) in ('pgs', 'pgssub', 'hdmv_pgs_subtitle'):
                return position, stream
            return None
        return None
    # Preserve the proven SRT/4K-segment choice when forced text is available.
    if any(_efut2_german(s) and _efpga_forced(s) and _embyflow_srt_v2_is_text_stream(s) for s in streams):
        return None
    for position, stream in enumerate(streams):
        if (_efpg_codec(stream) in ('pgs', 'pgssub', 'hdmv_pgs_subtitle') and
                _efut2_german(stream) and _efpga_forced(stream)):
            return position, stream
    return None


_efpga_auto_before = EmbyFlowMoviePlayer.set_preferred_subtitle_track
def _efpga_auto(self):
    if (getattr(self, '_efut_manual', False) or
            getattr(self, 'embyflow_manual_subtitle_selected', False) or
            getattr(self, 'closed', False)):
        return
    if (getattr(self, 'embyflow_srt_v2_loading', False) or
            getattr(self, 'embyflow_active_subtitle_index', None) is not None):
        return
    try:
        candidate = _efpga_candidate(self)
        if candidate is None:
            return _efpga_auto_before(self)
        position, stream = candidate
        key = (str(getattr(self, 'item_id', '')),
               str(getattr(self, 'media_source_id', '')), int(stream['Index']))
        if getattr(self, '_efpga_key', None) != key:
            self._efpga_key = key
            self._efpga_tries = 0
        if self._efpga_tries >= 8:
            return
        self._efpga_tries += 1
        try:
            _efpg_start(self, stream, _embyflow_srt_v2_language(self, stream, position), position)
        except Exception:
            # The native list/window can still be incomplete at initial startup.
            # Use the existing GUI timer; never block or restart the movie.
            if self._efpga_tries < 8:
                self.subtitle_timer.start(750, True)
            else:
                self['state_label'].setText('PGS-Untertitel konnten nicht automatisch aktiviert werden.')
    except Exception:
        # Do not expose URLs/tokens or raise a popup during automatic startup.
        return


EmbyFlowMoviePlayer.set_preferred_subtitle_track = _efpga_auto

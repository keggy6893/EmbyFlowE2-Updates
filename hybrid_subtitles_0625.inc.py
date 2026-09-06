# EMBYFLOW_HYBRID_SUBTITLES_0625_START
# Hybrid engine under EmbyFlow's existing custom subtitle UI.
# Text subtitle tracks use the existing direct Emby SRT renderer;
# bitmap/native tracks use Enigma2 service.subtitle().


def _embyflow_hybrid_0625_streams(self):
    try:
        return list(_embyflow_srt_v2_streams(self) or [])
    except Exception:
        try:
            return list(self.embyflow_text_subtitle_streams() or [])
        except Exception:
            return []


def _embyflow_hybrid_0625_is_text(self, stream):
    try:
        return bool(_embyflow_srt_v2_is_text_stream(stream))
    except Exception:
        try:
            return bool(self.embyflow_text_subtitle_is_text(stream))
        except Exception:
            return False


def _embyflow_hybrid_0625_lang_tokens(value):
    raw = str(value or "").strip().lower().replace("_", "-").split("-", 1)[0]
    aliases = {
        "de": ("de", "deu", "ger", "german", "deutsch"),
        "deu": ("de", "deu", "ger", "german", "deutsch"),
        "ger": ("de", "deu", "ger", "german", "deutsch"),
        "german": ("de", "deu", "ger", "german", "deutsch"),
        "deutsch": ("de", "deu", "ger", "german", "deutsch"),
        "en": ("en", "eng", "english"),
        "eng": ("en", "eng", "english"),
        "english": ("en", "eng", "english"),
        "fr": ("fr", "fra", "fre", "french", "français", "francais"),
        "fra": ("fr", "fra", "fre", "french", "français", "francais"),
        "fre": ("fr", "fra", "fre", "french", "français", "francais"),
        "es": ("es", "spa", "spanish", "español", "espanol"),
        "spa": ("es", "spa", "spanish", "español", "espanol"),
        "it": ("it", "ita", "italian", "italiano"),
        "ita": ("it", "ita", "italian", "italiano"),
    }
    return set(aliases.get(raw, (raw,))) if raw else set()


def _embyflow_hybrid_0625_native_entry_tokens(entry):
    values = list(entry) if isinstance(entry, (tuple, list)) else [entry]
    tokens = set()
    for value in values:
        if isinstance(value, str):
            tokens.update(_embyflow_hybrid_0625_lang_tokens(value))
    return tokens


def _embyflow_hybrid_0625_native_list(self):
    try:
        service = self.session.nav.getCurrentService()
        subtitle = service and service.subtitle()
        if not subtitle:
            return []
        return list(subtitle.getSubtitleList() or [])
    except Exception:
        return []


def _embyflow_hybrid_0625_native_map(self, streams, native_list):
    streams = list(streams or [])
    native_list = list(native_list or [])
    mapping = {}
    bitmap_positions = [
        pos for pos, stream in enumerate(streams)
        if not _embyflow_hybrid_0625_is_text(self, stream)
    ]
    if not bitmap_positions or not native_list:
        return mapping

    if len(native_list) == len(streams):
        for pos in bitmap_positions:
            if pos < len(native_list):
                mapping[pos] = native_list[pos]
        return mapping

    if len(native_list) == len(bitmap_positions):
        for pos, native in zip(bitmap_positions, native_list):
            mapping[pos] = native
        return mapping

    used = set()
    for pos in bitmap_positions:
        stream = streams[pos]
        wanted = _embyflow_hybrid_0625_lang_tokens(
            stream.get("Language") or stream.get("DisplayLanguage") or ""
        )
        chosen = None

        if pos < len(native_list) and pos not in used:
            tokens = _embyflow_hybrid_0625_native_entry_tokens(native_list[pos])
            if not wanted or wanted.intersection(tokens):
                chosen = pos

        if chosen is None and wanted:
            for idx, native in enumerate(native_list):
                if idx in used:
                    continue
                if wanted.intersection(_embyflow_hybrid_0625_native_entry_tokens(native)):
                    chosen = idx
                    break

        if chosen is None:
            for idx in range(len(native_list)):
                if idx not in used:
                    chosen = idx
                    break

        if chosen is not None:
            used.add(chosen)
            mapping[pos] = native_list[chosen]

    return mapping


def _embyflow_hybrid_0625_set_native(self, selected_subtitle):
    service = self.session.nav.getCurrentService()
    subtitle = service and service.subtitle()
    if not subtitle:
        raise RuntimeError("service.subtitle() ist nicht verfügbar")

    window = getattr(self, "embyflow_subtitle_window", None)

    if selected_subtitle is None:
        if window is not None:
            widget = getattr(window, "instance", None)
            if widget is not None:
                try:
                    subtitle.disableSubtitles(widget)
                except Exception:
                    pass
            try:
                window.hide()
            except Exception:
                pass
        self.embyflow_selected_subtitle = None
        return

    if window is None or getattr(window, "instance", None) is None:
        if SubtitleDisplay is None:
            raise RuntimeError("Screens.SubtitleDisplay ist nicht verfügbar")
        window = self.session.instantiateDialog(SubtitleDisplay)
        try:
            window.setAnimationMode(0)
        except Exception:
            pass
        try:
            window.hide()
        except Exception:
            pass
        self.embyflow_subtitle_window = window

    widget = getattr(window, "instance", None)
    if widget is None:
        raise RuntimeError("SubtitleDisplay besitzt keine eWidget-Instanz")

    subtitle.enableSubtitles(widget, selected_subtitle)
    self.embyflow_selected_subtitle = selected_subtitle
    window.show()


def _embyflow_hybrid_0625_set_default(self, stream_index):
    try:
        sources = self.item.get("MediaSources") or self.item.get("media_sources") or []
        wanted = str(getattr(self, "media_source_id", "") or "")
        source = None
        for candidate in sources:
            if wanted and str(candidate.get("Id") or candidate.get("id") or "") == wanted:
                source = candidate
                break
        if source is None and sources:
            source = sources[0]
        if source is not None:
            source["DefaultSubtitleStreamIndex"] = int(stream_index)
    except Exception:
        pass


def _embyflow_hybrid_0625_open(self):
    try:
        streams = _embyflow_hybrid_0625_streams(self)
        native_list = _embyflow_hybrid_0625_native_list(self)
        native_map = _embyflow_hybrid_0625_native_map(self, streams, native_list)

        entries = [{
            "primary": "Untertitel aus",
            "secondary": "",
            "tertiary": "",
            "active": self.embyflow_active_subtitle_index is None,
            "payload": ("hybrid_off_0625", None, "Aus", None),
        }]

        for position, stream in enumerate(streams):
            fallback = "Untertitel %d" % (position + 1)
            language_value = stream.get("Language") or stream.get("DisplayLanguage") or fallback
            try:
                language = self.embyflow_track_language_name(language_value, fallback)
            except Exception:
                language = str(language_value or fallback)
            try:
                codec = self.embyflow_track_codec_name(stream.get("Codec"))
            except Exception:
                codec = str(stream.get("Codec") or "").upper()

            flags = []
            title_text = " ".join((
                str(stream.get("Title") or ""),
                str(stream.get("DisplayTitle") or ""),
            )).lower()
            if stream.get("IsForced") or "forced" in title_text or "erzw" in title_text:
                flags.append("Erzw.")
            if stream.get("IsHearingImpaired") or "sdh" in title_text or "hearing" in title_text:
                flags.append("SDH")

            if _embyflow_hybrid_0625_is_text(self, stream):
                action = "hybrid_text_0625"
                value = stream
            elif position in native_map:
                action = "hybrid_native_0625"
                value = native_map[position]
            else:
                action = "hybrid_unsupported_0625"
                value = stream

            entries.append({
                "primary": language,
                "secondary": codec,
                "tertiary": "/".join(flags),
                "active": self.embyflow_active_subtitle_index == position,
                "payload": (action, value, language, position),
            })

        if len(entries) <= 1:
            raise RuntimeError("Keine Untertitelspuren gefunden")

        active_index = 0
        for index, entry in enumerate(entries):
            if entry.get("active"):
                active_index = index
                break

        self.session.openWithCallback(
            self.subtitle_selection_finished,
            EmbyFlowTrackSelectionScreen,
            title="Untertitel auswählen",
            entries=entries,
            active_index=active_index,
        )
    except Exception as error:
        self.session.open(
            MessageBox,
            "Untertitelauswahl nicht verfügbar: %s" % str(error),
            MessageBox.TYPE_INFO,
            timeout=4,
        )


def _embyflow_hybrid_0625_finished(self, result):
    if not result:
        return
    try:
        action, value, label, position = result

        if action == "hybrid_off_0625":
            self.embyflow_manual_subtitle_selected = True
            try:
                _embyflow_srt_v2_stop(self, True)
            except Exception:
                pass
            try:
                self.embyflow_text_subtitle_stop(keep_manual=True)
            except Exception:
                pass
            try:
                _embyflow_hybrid_0625_set_native(self, None)
            except Exception:
                pass
            self.embyflow_active_subtitle_index = None
            self.embyflow_active_subtitle_stream_index = None
            self.embyflow_server_subtitle_stream_index = None
            _embyflow_hybrid_0625_set_default(self, -1)
            try:
                self["state_label"].setText("Untertitel: Aus")
                self.show_overlay()
            except Exception:
                pass
            return

        if action == "hybrid_text_0625":
            self.embyflow_manual_subtitle_selected = True
            try:
                _embyflow_hybrid_0625_set_native(self, None)
            except Exception:
                pass
            stream_index = int(value.get("Index"))
            self.embyflow_server_subtitle_stream_index = stream_index
            _embyflow_hybrid_0625_set_default(self, stream_index)
            _embyflow_srt_v2_start(self, value, label, int(position), True)
            return

        if action == "hybrid_native_0625":
            self.embyflow_manual_subtitle_selected = True
            try:
                _embyflow_srt_v2_stop(self, True)
            except Exception:
                pass
            try:
                self.embyflow_text_subtitle_stop(keep_manual=True)
            except Exception:
                pass
            _embyflow_hybrid_0625_set_native(self, value)
            streams = _embyflow_hybrid_0625_streams(self)
            stream = streams[int(position)] if 0 <= int(position) < len(streams) else {}
            stream_index = int(stream.get("Index")) if stream.get("Index") is not None else int(position)
            self.embyflow_active_subtitle_index = int(position)
            self.embyflow_active_subtitle_stream_index = stream_index
            self.embyflow_server_subtitle_stream_index = stream_index
            _embyflow_hybrid_0625_set_default(self, stream_index)
            try:
                self["state_label"].setText("Untertitel: %s" % str(label))
                self.show_overlay()
            except Exception:
                pass
            return

        if action == "hybrid_unsupported_0625":
            self.session.open(
                MessageBox,
                "Diese Bitmap-Untertitelspur wird vom aktuellen Enigma2-Dienst nicht als native Spur angeboten.",
                MessageBox.TYPE_INFO,
                timeout=5,
            )
            return
    except Exception as error:
        self.session.open(
            MessageBox,
            "Untertitel konnten nicht gewechselt werden: %s" % str(error),
            MessageBox.TYPE_ERROR,
            timeout=5,
        )


def _embyflow_hybrid_0625_auto(self):
    if getattr(self, "embyflow_manual_subtitle_selected", False):
        return
    try:
        streams = _embyflow_hybrid_0625_streams(self)
        sources = self.item.get("MediaSources") or self.item.get("media_sources") or []
        wanted_source = str(getattr(self, "media_source_id", "") or "")
        source = None
        for candidate in sources:
            if wanted_source and str(candidate.get("Id") or candidate.get("id") or "") == wanted_source:
                source = candidate
                break
        if source is None and sources:
            source = sources[0]
        if source is None:
            return

        desired = int(
            source.get("DefaultSubtitleStreamIndex")
            if source.get("DefaultSubtitleStreamIndex") is not None
            else -1
        )
        if desired < 0:
            return

        selected_position = None
        selected_stream = None
        for position, stream in enumerate(streams):
            try:
                if int(stream.get("Index")) == desired:
                    selected_position = position
                    selected_stream = stream
                    break
            except Exception:
                continue
        if selected_stream is None:
            return

        language_value = selected_stream.get("Language") or selected_stream.get("DisplayLanguage") or "Untertitel"
        try:
            label = self.embyflow_track_language_name(language_value, "Untertitel")
        except Exception:
            label = str(language_value or "Untertitel")

        if _embyflow_hybrid_0625_is_text(self, selected_stream):
            if getattr(self, "embyflow_srt_v2_loading", False):
                return
            if int(getattr(self, "embyflow_active_subtitle_stream_index", -999) or -999) == desired:
                return
            _embyflow_srt_v2_start(self, selected_stream, label, int(selected_position), False)
            return

        native_list = _embyflow_hybrid_0625_native_list(self)
        native_map = _embyflow_hybrid_0625_native_map(self, streams, native_list)
        native_entry = native_map.get(int(selected_position))
        if native_entry is None:
            self.subtitle_retry_count = int(getattr(self, "subtitle_retry_count", 0) or 0) + 1
            if self.subtitle_retry_count < 8:
                try:
                    self.subtitle_timer.start(1000, True)
                except Exception:
                    pass
            return

        _embyflow_hybrid_0625_set_native(self, native_entry)
        self.embyflow_active_subtitle_index = int(selected_position)
        self.embyflow_active_subtitle_stream_index = desired
        self.embyflow_server_subtitle_stream_index = desired
        self.subtitle_retry_count = 0
    except Exception:
        pass


def _embyflow_hybrid_0625_close(self):
    try:
        _embyflow_srt_v2_stop(self, True)
    except Exception:
        pass
    try:
        self.embyflow_text_subtitle_stop(keep_manual=True)
    except Exception:
        pass
    try:
        _embyflow_hybrid_0625_set_native(self, None)
    except Exception:
        pass

    window = getattr(self, "embyflow_subtitle_window", None)
    if window is not None:
        try:
            self.session.deleteDialog(window)
        except Exception:
            try:
                window.close()
            except Exception:
                pass
        self.embyflow_subtitle_window = None
    self.embyflow_selected_subtitle = None


EmbyFlowMoviePlayer.open_subtitle_selection = _embyflow_hybrid_0625_open
EmbyFlowMoviePlayer.subtitle_selection_finished = _embyflow_hybrid_0625_finished
EmbyFlowMoviePlayer.embyflow_set_embedded_subtitle = _embyflow_hybrid_0625_set_native
EmbyFlowMoviePlayer.set_preferred_subtitle_track = _embyflow_hybrid_0625_auto
EmbyFlowMoviePlayer.embyflow_close_subtitle_window = _embyflow_hybrid_0625_close
# EMBYFLOW_HYBRID_SUBTITLES_0625_RELEASE
# EMBYFLOW_HYBRID_SUBTITLES_0625_END

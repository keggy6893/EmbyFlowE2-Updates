# EMBYFLOW_BITMAP_EXTEPLAYER3_0626_START
# Bitmap subtitle fallback for ServiceApp / ExtEplayer3.
# Important safety properties:
# - only the receiver-local service backend is changed 4097 -> 5002;
# - the existing Static=true URL and PlaySessionId are reused;
# - no PlaybackInfo call, no Static=false URL and no server transcode is created;
# - EmbyFlow's existing custom subtitle menu remains the only selection UI.

_EMBYFLOW_HYBRID_0625_FINISHED_FOR_0626 = EmbyFlowMoviePlayer.subtitle_selection_finished
_EMBYFLOW_HYBRID_0625_CLOSE_FOR_0626 = EmbyFlowMoviePlayer.embyflow_close_subtitle_window


def _embyflow_bitmap_0626_cancel_pending(self):
    try:
        timer = getattr(self, "embyflow_bitmap_0626_timer", None)
        if timer is not None:
            timer.stop()
    except Exception:
        pass
    self.embyflow_bitmap_0626_pending = None
    self.embyflow_bitmap_0626_attempts = 0


def _embyflow_bitmap_0626_position_ticks(self):
    try:
        return max(0, int(self.current_position_ticks() or 0))
    except Exception:
        pass
    try:
        return max(0, int(self.embyflow_v10_content_position_ticks() or 0))
    except Exception:
        return 0


def _embyflow_bitmap_0626_timer_get(self):
    timer = getattr(self, "embyflow_bitmap_0626_timer", None)
    if timer is not None:
        return timer
    timer = eTimer()
    try:
        timer.callback.append(lambda: _embyflow_bitmap_0626_retry(self))
    except Exception:
        try:
            timer.timeout.connect(lambda: _embyflow_bitmap_0626_retry(self))
        except Exception:
            pass
    self.embyflow_bitmap_0626_timer = timer
    return timer


def _embyflow_bitmap_0626_finish_native(self, pending, native_entry):
    _embyflow_hybrid_0625_set_native(self, native_entry)

    position = int(pending.get("position", 0) or 0)
    stream = dict(pending.get("stream") or {})
    try:
        stream_index = int(stream.get("Index"))
    except Exception:
        stream_index = position

    self.embyflow_active_subtitle_index = position
    self.embyflow_active_subtitle_stream_index = stream_index
    self.embyflow_server_subtitle_stream_index = stream_index
    _embyflow_hybrid_0625_set_default(self, stream_index)

    try:
        self["state_label"].setText(
            "Untertitel: %s" % str(pending.get("label") or "Bitmap")
        )
        self.show_overlay()
    except Exception:
        pass

    _embyflow_bitmap_0626_cancel_pending(self)


def _embyflow_bitmap_0626_retry(self):
    pending = getattr(self, "embyflow_bitmap_0626_pending", None)
    if not isinstance(pending, dict):
        return

    try:
        streams = _embyflow_hybrid_0625_streams(self)
        native_list = _embyflow_hybrid_0625_native_list(self)
        native_map = _embyflow_hybrid_0625_native_map(self, streams, native_list)
        position = int(pending.get("position", -1))
        native_entry = native_map.get(position)
        if native_entry is not None:
            _embyflow_bitmap_0626_finish_native(self, pending, native_entry)
            return
    except Exception:
        pass

    attempts = int(getattr(self, "embyflow_bitmap_0626_attempts", 0) or 0) + 1
    self.embyflow_bitmap_0626_attempts = attempts

    # ExtEplayer3 and ServiceApp can need a few seconds before subtitle()
    # publishes the embedded bitmap list. Keep this receiver-local and bounded.
    if attempts >= 16:
        _embyflow_bitmap_0626_cancel_pending(self)
        try:
            self.session.open(
                MessageBox,
                "Die Bitmap-Untertitelspur wurde auch von ExtEplayer3 nicht als native Spur bereitgestellt.",
                MessageBox.TYPE_INFO,
                timeout=5,
            )
        except Exception:
            pass
        return

    try:
        _embyflow_bitmap_0626_timer_get(self).start(500, True)
    except Exception:
        pass


def _embyflow_bitmap_0626_start(self, stream, label, position):
    _embyflow_bitmap_0626_cancel_pending(self)

    if not _embyflow_engine_v11_4_exteplayer3_available():
        try:
            self.session.open(
                MessageBox,
                "ExtEplayer3 / ServiceApp ist für diese Bitmap-Untertitelspur nicht verfügbar.",
                MessageBox.TYPE_INFO,
                timeout=5,
            )
        except Exception:
            pass
        return

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

    self.embyflow_bitmap_0626_pending = {
        "stream": dict(stream or {}),
        "label": str(label or "Bitmap"),
        "position": int(position),
    }
    self.embyflow_bitmap_0626_attempts = 0

    current_type = int(
        getattr(self, "embyflow_engine_service_type_v11_4", STREAM_SERVICE_TYPE)
        or STREAM_SERVICE_TYPE
    )

    if current_type != 5002:
        target_ticks = _embyflow_bitmap_0626_position_ticks(self)
        # Existing SERVERSAFE helper: same Static=true URL + same PlaySessionId,
        # only local service type 4097 -> 5002, then local seek back to position.
        if not _embyflow_rcdev7_switch_static_to_ext(self, target_ticks):
            _embyflow_bitmap_0626_cancel_pending(self)
            try:
                self.session.open(
                    MessageBox,
                    "Diese Bitmap-Untertitelspur benötigt ExtEplayer3. Der aktuelle Stream kann ohne Server-Transcode nicht sicher auf 5002 umgestellt werden.",
                    MessageBox.TYPE_INFO,
                    timeout=6,
                )
            except Exception:
                pass
            return

    try:
        self["state_label"].setText(
            "Untertitel: %s · ExtEplayer3 wird vorbereitet" % str(label or "Bitmap")
        )
        self.show_overlay()
    except Exception:
        pass

    try:
        _embyflow_bitmap_0626_timer_get(self).start(700, True)
    except Exception:
        _embyflow_bitmap_0626_retry(self)


def _embyflow_bitmap_0626_finished(self, result):
    if not result:
        return

    try:
        action, value, label, position = result
    except Exception:
        return _EMBYFLOW_HYBRID_0625_FINISHED_FOR_0626(self, result)

    # Any new user choice supersedes a pending bitmap activation.
    if action != "hybrid_unsupported_0625":
        _embyflow_bitmap_0626_cancel_pending(self)
        return _EMBYFLOW_HYBRID_0625_FINISHED_FOR_0626(self, result)

    return _embyflow_bitmap_0626_start(
        self,
        value,
        label,
        int(position),
    )


def _embyflow_bitmap_0626_close(self):
    _embyflow_bitmap_0626_cancel_pending(self)
    return _EMBYFLOW_HYBRID_0625_CLOSE_FOR_0626(self)


EmbyFlowMoviePlayer.subtitle_selection_finished = _embyflow_bitmap_0626_finished
EmbyFlowMoviePlayer.embyflow_close_subtitle_window = _embyflow_bitmap_0626_close
# EMBYFLOW_BITMAP_EXTEPLAYER3_0626_RELEASE
# EMBYFLOW_BITMAP_EXTEPLAYER3_0626_END

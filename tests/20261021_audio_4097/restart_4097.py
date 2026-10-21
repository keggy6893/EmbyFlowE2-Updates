def _efa2_restart_4097(
    self,
    target_ticks,
    subtitle_stream_index=None,
    subtitle_label=None,
    audio_index_override=None,
):
    try:
        target_ticks = max(0, int(target_ticks or 0))
    except Exception:
        target_ticks = 0

    try:
        duration = int(getattr(self, "duration_ticks", 0) or 0)
        if duration > 10000000:
            target_ticks = min(target_ticks, duration - 10000000)
    except Exception:
        pass

    try:
        (
            server,
            token,
            item_id,
            media_source_id,
            audio_index,
        ) = self.embyflow_v10_stream_context()
        if audio_index_override is not None:
            audio_index = int(audio_index_override)

        if not server or not token or not item_id:
            raise RuntimeError("Emby-Wiedergabekontext unvollständig")

        try:
            from urllib.parse import urlencode
        except Exception:
            from urllib import urlencode

        active_subtitle = None
        if subtitle_stream_index is not None:
            try:
                active_subtitle = int(subtitle_stream_index)
                if active_subtitle < 0:
                    active_subtitle = None
            except Exception:
                active_subtitle = None

        old_play_session_id = str(getattr(self, "play_session_id", "") or "")
        new_session_id = uuid4().hex
        params = [
            ("Static", "false"),
            ("StartTimeTicks", str(int(target_ticks))),
            ("PlaySessionId", new_session_id),
            ("DeviceId", "embyflowe2"),
        ]
        if media_source_id:
            params.append(("MediaSourceId", media_source_id))
        if audio_index is not None:
            params.append(("AudioStreamIndex", str(int(audio_index))))

        if active_subtitle is None:
            params.extend([
                ("VideoCodec", "copy"),
                ("AudioCodec", "copy"),
            ])
            endpoint = "stream.mkv"
        else:
            params.extend([
                ("VideoCodec", "h264"),
                ("AudioCodec", "aac"),
                ("VideoBitRate", "20000000"),
                ("AudioBitRate", "384000"),
                ("MaxAudioChannels", "6"),
                ("SubtitleStreamIndex", str(active_subtitle)),
                ("SubtitleMethod", "Encode"),
                ("CopyTimestamps", "true"),
            ])
            endpoint = "stream.mkv"

        params.append(("api_key", token))
        new_url = "%s/Videos/%s/%s?%s" % (
            server,
            item_id,
            endpoint,
            urlencode(params),
        )

        new_ref = eServiceReference(
            4097,
            0,
            new_url,
        )
        new_ref.setName(self.title_text)

        self.play_session_id = new_session_id
        self.stream_url = new_url
        self.ref = new_ref
        self.embyflow_v10_stream_base_ticks = int(target_ticks)
        self.embyflow_v10_stream_started_monotonic = None
        self.embyflow_v10_stream_confirmed_playing = False
        self.embyflow_v10_stream_time_mode = None
        self.embyflow_v10_clock_wait_logged = False
        try:
            self.embyflow_v10_stream_restart_issued_monotonic = time.monotonic()
        except Exception:
            self.embyflow_v10_stream_restart_issued_monotonic = None

        try:
            with embyflow_open_log(
                "/tmp/embyflow_chapter_clock_v16_1.log",
                "a",
                encoding="utf-8",
            ) as log:
                log.write(
                    "%s RESTART target=%s\n"
                    % (
                        time.strftime("%Y-%m-%d %H:%M:%S"),
                        int(target_ticks),
                    )
                )
        except Exception:
            pass

        self.embyflow_server_subtitle_stream_index = active_subtitle
        if subtitle_label is not None:
            self.embyflow_server_subtitle_label = str(subtitle_label or "Untertitel")

        self.pending_seek_started_ticks = None
        self.pending_seek_target_ticks = None
        self.initial_big_seek_target_ticks = None
        self.seek_has_been_used = True
        try:
            self.seek_fallback_timer.stop()
        except Exception:
            pass
        try:
            self.initial_big_seek_timer.stop()
        except Exception:
            pass

        generation = int(
            getattr(self, "_embyflow_seek_async_generation_v17_5_6", 0)
            or 0
        ) + 1
        self._embyflow_seek_async_generation_v17_5_6 = generation

        # Snapshot report payloads while the new session is current.  Workers
        # receive plain Python data only; they never inspect Enigma2 services.
        self.embyflow_playback_mode = 'directstream'
        self.playback_info.update(url=new_url, play_session_id=new_session_id,
                                  playback_mode='directstream', service_type=4097)
        playing_payload = self.emby_report_payload(target_ticks)
        playing_payload["AudioStreamIndex"] = audio_index
        playing_payload["PlayMethod"] = 'DirectStream'
        progress_payload = dict(playing_payload or {})
        progress_payload["EventName"] = "TimeUpdate"

        main_started = time.time()
        _embyflow_seek_async_v17_5_6_log(
            "RESTART_BEGIN generation=%s item=%s target=%s old_session=%s new_session=%s"
            % (
                generation,
                item_id,
                target_ticks,
                old_play_session_id or "-",
                new_session_id,
            )
        )

        # Start old-session cleanup without blocking Enigma2's ActionMap/eTimer
        # processing.  Brief overlap is preferable to serial UI-thread waits;
        # cleanup is still mandatory and logged.
        try:
            import threading
            cancel_thread = threading.Thread(
                target=_embyflow_seek_async_v17_5_6_cancel_worker,
                args=(self, old_play_session_id, str(item_id), generation),
                name="EmbyFlowSeekCancelV17_5_6",
            )
            cancel_thread.daemon = True
            cancel_thread.start()
        except Exception as error:
            # Thread creation failure: keep cleanup correctness over latency.
            _embyflow_seek_async_v17_5_6_log(
                "CANCEL_THREAD_ERROR generation=%s type=%s message=%s fallback=sync"
                % (
                    generation,
                    type(error).__name__,
                    str(error).replace("\n", " ")[:200],
                )
            )
            self.cancel_active_encoding(old_play_session_id)

        self._embyflow_stream_replacement_in_progress = True
        try:
            _efguard_play_service(self.session.nav, self.ref)
        finally:
            self._embyflow_stream_replacement_in_progress = False

        self.synthetic_position_ticks = int(target_ticks)
        self.paused = False
        try:
            self.play_started_ts = int(time.time()) - int(target_ticks // 10000000)
        except Exception:
            pass

        try:
            self.audio_retry_count = 0
            self.audio_timer.start(1200, True)
        except Exception:
            pass

        self.show_overlay()
        self.update_playback_overlay()

        # One Playing + one Progress, asynchronously and guarded.  This also
        # removes the duplicate synchronous Playing report that existed in the
        # older restart body.
        try:
            import threading
            report_thread = threading.Thread(
                target=_embyflow_seek_async_v17_5_6_report_worker,
                args=(
                    self,
                    generation,
                    new_session_id,
                    str(server),
                    str(token),
                    dict(playing_payload or {}),
                    dict(progress_payload or {}),
                    str(item_id),
                ),
                name="EmbyFlowSeekReportV17_5_6",
            )
            report_thread.daemon = True
            report_thread.start()
        except Exception as error:
            # Report failure must not turn a successful service replacement
            # into a second seek/restart.  Log it; normal periodic Progress
            # reporting remains active as a recovery path.
            _embyflow_seek_async_v17_5_6_log(
                "REPORT_THREAD_ERROR generation=%s type=%s message=%s"
                % (
                    generation,
                    type(error).__name__,
                    str(error).replace("\n", " ")[:200],
                )
            )

        main_ms = int((time.time() - main_started) * 1000)
        _embyflow_seek_async_v17_5_6_log(
            "RESTART_RETURN generation=%s item=%s target=%s main_ms=%s"
            % (generation, item_id, target_ticks, main_ms)
        )
        return True

    except Exception as error:
        _embyflow_seek_async_v17_5_6_log(
            "RESTART_ERROR target=%s subtitle=%s type=%s message=%s"
            % (
                int(target_ticks or 0),
                str(subtitle_stream_index),
                type(error).__name__,
                str(error).replace("\n", " ")[:300],
            )
        )
        return False


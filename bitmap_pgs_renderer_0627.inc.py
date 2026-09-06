# EMBYFLOW_BITMAP_PGS_RENDERER_0627_START
# Receiver-local graphic subtitle path for PGS/DVB/XSUB.
#
# Why this exists:
# ServiceApp/5002 can start ExtEplayer3, but its public option map does not pass
# ExtEplayer3's -G/-W/-H graphic-subtitle output options. Without -G,
# ExtEplayer3 deliberately omits PGS/DVB/XSUB from the usable subtitle path.
#
# 0627 inserts a tiny receiver-local wrapper only for the lifetime of the
# EmbyFlow player. The wrapper adds -G/-W/-H to the *same* Static=true URL,
# intercepts ExtEplayer3 graphic subtitle JSON before older ServiceApp builds
# try to parse it as text, and lets EmbyFlow render the generated PNG rectangles.
# No PlaybackInfo call, no Static=false URL, no HLS/remux, no video transcode.

_EMBYFLOW_BITMAP_0626_FINISHED_FOR_0627 = EmbyFlowMoviePlayer.subtitle_selection_finished
_EMBYFLOW_BITMAP_0626_CLOSE_FOR_0627 = EmbyFlowMoviePlayer.embyflow_close_subtitle_window

_EMBYFLOW_PGS_0627_WRAPPER_DIR = "/tmp/embyflow_ext3_wrapper"
_EMBYFLOW_PGS_0627_WRAPPER_PATH = _EMBYFLOW_PGS_0627_WRAPPER_DIR + "/exteplayer3"
_EMBYFLOW_PGS_0627_REAL_EXT3 = "/usr/bin/exteplayer3"

_EMBYFLOW_PGS_0627_WRAPPER = r'''#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import sys

real = os.environ.get("EMBYFLOW_EXT3_REAL", "/usr/bin/exteplayer3")
args = [real] + list(sys.argv[1:])
enabled = os.environ.get("EMBYFLOW_PGS_ENABLE", "") == "1"
pgs_dir = os.environ.get("EMBYFLOW_PGS_DIR", "")
event_file = os.environ.get("EMBYFLOW_PGS_EVENT_FILE", "")
width = os.environ.get("EMBYFLOW_PGS_WIDTH", "1920")
height = os.environ.get("EMBYFLOW_PGS_HEIGHT", "1080")

if enabled and pgs_dir:
    try:
        os.makedirs(pgs_dir, exist_ok=True)
    except Exception:
        pass
    # ServiceApp does not expose these ExtEplayer3 graphic subtitle switches.
    if "-G" not in args:
        args.extend(["-G", pgs_dir])
    if "-W" not in args:
        args.extend(["-W", str(width)])
    if "-H" not in args:
        args.extend(["-H", str(height)])

child = None

def forward_signal(signum, _frame):
    global child
    try:
        if child is not None and child.poll() is None:
            child.send_signal(signum)
    except Exception:
        pass

for sig in (signal.SIGINT, signal.SIGTERM):
    try:
        signal.signal(sig, forward_signal)
    except Exception:
        pass

try:
    child = subprocess.Popen(
        args,
        stdin=None,
        stdout=None,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
except Exception as error:
    sys.stderr.write("EmbyFlow ExtEplayer3 wrapper start failed: %s\n" % error)
    sys.stderr.flush()
    sys.exit(127)

events = None
if enabled and event_file:
    try:
        events = open(event_file, "a", encoding="utf-8", buffering=1)
    except Exception:
        events = None

try:
    for line in child.stderr:
        intercepted = False
        stripped = line.strip()
        if enabled and stripped.startswith("{") and '"s_a"' in stripped:
            try:
                data = json.loads(stripped)
                payload = data.get("s_a") if isinstance(data, dict) else None
                # Graphic ExtEplayer3 events contain rectangle array "r".
                # Older ServiceApp sources expect text key "t" here, so do not
                # forward graphic events to ServiceApp; EmbyFlow consumes them.
                if isinstance(payload, dict) and isinstance(payload.get("r"), list):
                    if events is not None:
                        events.write(json.dumps(data, separators=(",", ":")) + "\n")
                    intercepted = True
            except Exception:
                intercepted = False
        if not intercepted:
            sys.stderr.write(line)
            sys.stderr.flush()
finally:
    try:
        if events is not None:
            events.close()
    except Exception:
        pass

sys.exit(child.wait())
'''


class EmbyFlowBitmapSubtitleOverlay0627(Screen):
    skin = scale_skin(
        '''
        <screen name="EmbyFlowBitmapSubtitleOverlay0627"
                position="0,0"
                size="1920,1080"
                flags="wfNoBorder"
                backgroundColor="transparent">
            <widget name="pgs0" position="0,0" size="1,1" transparent="1" alphatest="blend" zPosition="40" />
            <widget name="pgs1" position="0,0" size="1,1" transparent="1" alphatest="blend" zPosition="41" />
            <widget name="pgs2" position="0,0" size="1,1" transparent="1" alphatest="blend" zPosition="42" />
            <widget name="pgs3" position="0,0" size="1,1" transparent="1" alphatest="blend" zPosition="43" />
        </screen>
        '''
    )

    def __init__(self, session):
        Screen.__init__(self, session)
        for idx in range(4):
            self["pgs%d" % idx] = Pixmap()
        self.onShown.append(self.clear)

    def clear(self):
        for idx in range(4):
            try:
                self["pgs%d" % idx].hide()
            except Exception:
                pass

    def show_rectangles(self, base_dir, rectangles):
        rectangles = list(rectangles or [])[:4]
        for idx in range(4):
            widget = self["pgs%d" % idx]
            if idx >= len(rectangles):
                try:
                    widget.hide()
                except Exception:
                    pass
                continue

            rect = rectangles[idx] if isinstance(rectangles[idx], dict) else {}
            filename = os.path.basename(str(rect.get("f") or ""))
            path = os.path.join(str(base_dir or ""), filename)
            try:
                x = max(0, int(rect.get("x") or 0))
                y = max(0, int(rect.get("y") or 0))
                w = max(1, int(rect.get("w") or 1))
                h = max(1, int(rect.get("h") or 1))
            except Exception:
                continue

            if not filename or not os.path.isfile(path):
                try:
                    widget.hide()
                except Exception:
                    pass
                continue

            try:
                pixmap = LoadPixmap(path)
                instance = getattr(widget, "instance", None)
                if instance is None or pixmap is None:
                    widget.hide()
                    continue
                instance.move(ePoint(x, y))
                instance.resize(eSize(w, h))
                instance.setPixmap(pixmap)
                try:
                    instance.setScale(0)
                except Exception:
                    pass
                widget.show()
                instance.show()
                instance.invalidate()
            except Exception:
                try:
                    widget.hide()
                except Exception:
                    pass


def _embyflow_pgs_0627_status(self, text):
    try:
        self["state_label"].setText(str(text or ""))
        self.show_overlay()
    except Exception:
        pass


def _embyflow_pgs_0627_cancel_0626(self):
    try:
        _embyflow_bitmap_0626_cancel_pending(self)
    except Exception:
        pass


def _embyflow_pgs_0627_screen_size():
    try:
        profile = embyflow_get_runtime_profile() or {}
        width = max(320, int(profile.get("width") or 1920))
        height = max(240, int(profile.get("height") or 1080))
        return width, height
    except Exception:
        return 1920, 1080


def _embyflow_pgs_0627_install_wrapper(self):
    if not os.path.isfile(_EMBYFLOW_PGS_0627_REAL_EXT3):
        return False
    try:
        if not os.path.isdir(_EMBYFLOW_PGS_0627_WRAPPER_DIR):
            os.makedirs(_EMBYFLOW_PGS_0627_WRAPPER_DIR)
        current = ""
        try:
            with io.open(_EMBYFLOW_PGS_0627_WRAPPER_PATH, "r", encoding="utf-8") as handle:
                current = handle.read()
        except Exception:
            current = ""
        if current != _EMBYFLOW_PGS_0627_WRAPPER:
            with io.open(_EMBYFLOW_PGS_0627_WRAPPER_PATH, "w", encoding="utf-8") as handle:
                handle.write(_EMBYFLOW_PGS_0627_WRAPPER)
        os.chmod(_EMBYFLOW_PGS_0627_WRAPPER_PATH, 0o755)
        return True
    except Exception:
        return False


def _embyflow_pgs_0627_remove_tree(path):
    path = str(path or "")
    if not path or not path.startswith("/tmp/embyflow_pgs_"):
        return
    try:
        for name in os.listdir(path):
            candidate = os.path.join(path, name)
            try:
                if os.path.isfile(candidate) or os.path.islink(candidate):
                    os.remove(candidate)
            except Exception:
                pass
        os.rmdir(path)
    except Exception:
        pass


def _embyflow_pgs_0627_prepare_environment(self):
    if not _embyflow_pgs_0627_install_wrapper(self):
        return False

    if not isinstance(getattr(self, "embyflow_pgs_0627_env_backup", None), dict):
        keys = (
            "PATH",
            "EMBYFLOW_PGS_ENABLE",
            "EMBYFLOW_PGS_DIR",
            "EMBYFLOW_PGS_EVENT_FILE",
            "EMBYFLOW_PGS_WIDTH",
            "EMBYFLOW_PGS_HEIGHT",
            "EMBYFLOW_EXT3_REAL",
        )
        self.embyflow_pgs_0627_env_backup = {
            key: os.environ.get(key) for key in keys
        }

    old_dir = str(getattr(self, "embyflow_pgs_0627_dir", "") or "")
    if not old_dir:
        token = str(uuid4()).replace("-", "")[:12]
        session_dir = "/tmp/embyflow_pgs_%s" % token
        os.makedirs(session_dir)
        self.embyflow_pgs_0627_dir = session_dir
        self.embyflow_pgs_0627_event_file = os.path.join(session_dir, "events.jsonl")
    else:
        session_dir = old_dir

    event_file = str(getattr(self, "embyflow_pgs_0627_event_file", "") or "")
    try:
        with io.open(event_file, "w", encoding="utf-8"):
            pass
    except Exception:
        return False

    for name in os.listdir(session_dir):
        if name == os.path.basename(event_file):
            continue
        candidate = os.path.join(session_dir, name)
        try:
            if os.path.isfile(candidate):
                os.remove(candidate)
        except Exception:
            pass

    width, height = _embyflow_pgs_0627_screen_size()
    current_path = str(os.environ.get("PATH") or "")
    parts = [part for part in current_path.split(os.pathsep) if part]
    if _EMBYFLOW_PGS_0627_WRAPPER_DIR not in parts:
        current_path = _EMBYFLOW_PGS_0627_WRAPPER_DIR + os.pathsep + current_path

    os.environ["PATH"] = current_path
    os.environ["EMBYFLOW_PGS_ENABLE"] = "1"
    os.environ["EMBYFLOW_PGS_DIR"] = session_dir
    os.environ["EMBYFLOW_PGS_EVENT_FILE"] = event_file
    os.environ["EMBYFLOW_PGS_WIDTH"] = str(width)
    os.environ["EMBYFLOW_PGS_HEIGHT"] = str(height)
    os.environ["EMBYFLOW_EXT3_REAL"] = _EMBYFLOW_PGS_0627_REAL_EXT3

    self.embyflow_pgs_0627_event_offset = 0
    self.embyflow_pgs_0627_events = []
    self.embyflow_pgs_0627_last_end_ms = None
    return True


def _embyflow_pgs_0627_restore_environment(self):
    backup = getattr(self, "embyflow_pgs_0627_env_backup", None)
    if isinstance(backup, dict):
        for key, value in backup.items():
            try:
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = str(value)
            except Exception:
                pass
    self.embyflow_pgs_0627_env_backup = None


def _embyflow_pgs_0627_overlay(self):
    overlay = getattr(self, "embyflow_pgs_0627_overlay", None)
    if overlay is not None:
        return overlay
    try:
        overlay = self.session.instantiateDialog(EmbyFlowBitmapSubtitleOverlay0627)
        try:
            overlay.setAnimationMode(0)
        except Exception:
            pass
        overlay.show()
        overlay.clear()
        self.embyflow_pgs_0627_overlay = overlay
        return overlay
    except Exception:
        return None


def _embyflow_pgs_0627_event_timer(self):
    timer = getattr(self, "embyflow_pgs_0627_event_timer", None)
    if timer is not None:
        return timer
    timer = eTimer()
    try:
        timer.callback.append(lambda: _embyflow_pgs_0627_event_tick(self))
    except Exception:
        try:
            timer.timeout.connect(lambda: _embyflow_pgs_0627_event_tick(self))
        except Exception:
            pass
    self.embyflow_pgs_0627_event_timer = timer
    return timer


def _embyflow_pgs_0627_retry_timer(self):
    timer = getattr(self, "embyflow_pgs_0627_retry_timer", None)
    if timer is not None:
        return timer
    timer = eTimer()
    try:
        timer.callback.append(lambda: _embyflow_pgs_0627_retry(self))
    except Exception:
        try:
            timer.timeout.connect(lambda: _embyflow_pgs_0627_retry(self))
        except Exception:
            pass
    self.embyflow_pgs_0627_retry_timer = timer
    return timer


def _embyflow_pgs_0627_stop_render(self, keep_wrapper=True):
    for name in ("embyflow_pgs_0627_event_timer", "embyflow_pgs_0627_retry_timer"):
        try:
            timer = getattr(self, name, None)
            if timer is not None:
                timer.stop()
        except Exception:
            pass
    self.embyflow_pgs_0627_pending = None
    self.embyflow_pgs_0627_attempts = 0
    self.embyflow_pgs_0627_events = []
    self.embyflow_pgs_0627_last_end_ms = None
    try:
        overlay = getattr(self, "embyflow_pgs_0627_overlay", None)
        if overlay is not None:
            overlay.clear()
    except Exception:
        pass
    if not keep_wrapper:
        _embyflow_pgs_0627_restore_environment(self)


def _embyflow_pgs_0627_read_new_events(self):
    event_file = str(getattr(self, "embyflow_pgs_0627_event_file", "") or "")
    if not event_file or not os.path.isfile(event_file):
        return []
    try:
        size = os.path.getsize(event_file)
        offset = int(getattr(self, "embyflow_pgs_0627_event_offset", 0) or 0)
        if size < offset:
            offset = 0
        result = []
        with io.open(event_file, "r", encoding="utf-8", errors="replace") as handle:
            handle.seek(offset)
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    payload = data.get("s_a") if isinstance(data, dict) else None
                    if isinstance(payload, dict) and isinstance(payload.get("r"), list):
                        result.append(payload)
                except Exception:
                    continue
            self.embyflow_pgs_0627_event_offset = handle.tell()
        return result
    except Exception:
        return []


def _embyflow_pgs_0627_position_ms(self):
    try:
        ticks = max(0, int(self.current_position_ticks() or 0))
        return int(ticks // 10000)
    except Exception:
        return 0


def _embyflow_pgs_0627_event_tick(self):
    if not getattr(self, "embyflow_pgs_0627_rendering", False):
        return

    new_events = _embyflow_pgs_0627_read_new_events(self)
    queue = list(getattr(self, "embyflow_pgs_0627_events", []) or [])
    for payload in new_events:
        try:
            start_ms = max(0, int(payload.get("s") or 0))
        except Exception:
            start_ms = 0
        queue.append((start_ms, payload))
    queue.sort(key=lambda item: item[0])
    if len(queue) > 96:
        queue = queue[-96:]

    now_ms = _embyflow_pgs_0627_position_ms(self)
    latest = None
    while queue and queue[0][0] <= now_ms + 120:
        latest = queue.pop(0)[1]

    overlay = _embyflow_pgs_0627_overlay(self)
    if latest is not None and overlay is not None:
        rectangles = list(latest.get("r") or [])
        if rectangles:
            overlay.show_rectangles(
                getattr(self, "embyflow_pgs_0627_dir", ""),
                rectangles,
            )
        else:
            overlay.clear()
        end_value = latest.get("e")
        try:
            self.embyflow_pgs_0627_last_end_ms = (
                int(end_value) if end_value is not None else None
            )
        except Exception:
            self.embyflow_pgs_0627_last_end_ms = None

    end_ms = getattr(self, "embyflow_pgs_0627_last_end_ms", None)
    if end_ms is not None and now_ms >= int(end_ms):
        try:
            if overlay is not None:
                overlay.clear()
        except Exception:
            pass
        self.embyflow_pgs_0627_last_end_ms = None

    self.embyflow_pgs_0627_events = queue
    try:
        _embyflow_pgs_0627_event_timer(self).start(100, True)
    except Exception:
        pass


def _embyflow_pgs_0627_restart_5002(self, target_ticks):
    current_url = str(getattr(self, "stream_url", "") or "")
    if not current_url or not embyflow_is_static_stream_url(current_url):
        return False
    if not _embyflow_engine_v11_4_exteplayer3_available():
        return False

    new_ref = eServiceReference(5002, 0, current_url)
    try:
        new_ref.setName(str(getattr(self, "title_text", "") or ""))
    except Exception:
        pass

    self.embyflow_engine_mode_v11_4 = "ext"
    self.embyflow_engine_service_type_v11_4 = 5002
    self.ref = new_ref
    try:
        self.playback_info["engine_mode"] = "ext"
        self.playback_info["service_type"] = 5002
        self.playback_info["url"] = current_url
    except Exception:
        pass

    self.embyflow_v10_stream_base_ticks = None
    self.embyflow_v10_stream_started_monotonic = None
    self.embyflow_v10_stream_confirmed_playing = False
    self.embyflow_v10_stream_time_mode = None
    self.embyflow_v10_clock_wait_logged = False

    self._embyflow_stream_replacement_in_progress = True
    try:
        self.session.nav.playService(new_ref)
    finally:
        self._embyflow_stream_replacement_in_progress = False

    try:
        self.audio_retry_count = 0
        self.audio_timer.start(1200, True)
    except Exception:
        pass

    try:
        _embyflow_qs_v2_schedule_resume(self, max(0, int(target_ticks or 0)))
    except Exception:
        pass

    self.embyflow_pgs_0627_wrapper_launched = True
    return True


def _embyflow_pgs_0627_finish(self, pending, native_entry):
    try:
        _embyflow_hybrid_0625_set_native(self, native_entry)
    except Exception:
        return False

    position = int(pending.get("position", 0) or 0)
    stream = dict(pending.get("stream") or {})
    try:
        stream_index = int(stream.get("Index"))
    except Exception:
        stream_index = position

    self.embyflow_active_subtitle_index = position
    self.embyflow_active_subtitle_stream_index = stream_index
    self.embyflow_server_subtitle_stream_index = stream_index
    try:
        _embyflow_hybrid_0625_set_default(self, stream_index)
    except Exception:
        pass

    self.embyflow_pgs_0627_pending = None
    self.embyflow_pgs_0627_attempts = 0
    self.embyflow_pgs_0627_rendering = True
    _embyflow_pgs_0627_overlay(self)
    _embyflow_pgs_0627_status(
        self,
        "Untertitel: %s · Bitmap lokal" % str(pending.get("label") or "PGS"),
    )
    try:
        _embyflow_pgs_0627_event_timer(self).start(100, True)
    except Exception:
        pass
    return True


def _embyflow_pgs_0627_retry(self):
    pending = getattr(self, "embyflow_pgs_0627_pending", None)
    if not isinstance(pending, dict):
        return

    try:
        streams = _embyflow_hybrid_0625_streams(self)
        native_list = _embyflow_hybrid_0625_native_list(self)
        native_map = _embyflow_hybrid_0625_native_map(self, streams, native_list)
        native_entry = native_map.get(int(pending.get("position", -1)))
        if native_entry is not None:
            if _embyflow_pgs_0627_finish(self, pending, native_entry):
                return
    except Exception:
        pass

    attempts = int(getattr(self, "embyflow_pgs_0627_attempts", 0) or 0) + 1
    self.embyflow_pgs_0627_attempts = attempts
    if attempts >= 20:
        self.embyflow_pgs_0627_pending = None
        _embyflow_pgs_0627_status(
            self,
            "Bitmap-Untertitel: ExtEplayer3 hat die Spur nicht bereitgestellt",
        )
        return
    try:
        _embyflow_pgs_0627_retry_timer(self).start(500, True)
    except Exception:
        pass


def _embyflow_pgs_0627_start(self, stream, label, position):
    _embyflow_pgs_0627_cancel_0626(self)
    _embyflow_pgs_0627_stop_render(self, keep_wrapper=True)

    if not _embyflow_engine_v11_4_exteplayer3_available():
        _embyflow_pgs_0627_status(self, "Bitmap-Untertitel: ExtEplayer3 nicht verfügbar")
        return

    current_url = str(getattr(self, "stream_url", "") or "")
    if not current_url or not embyflow_is_static_stream_url(current_url):
        _embyflow_pgs_0627_status(
            self,
            "Bitmap-Untertitel benötigen sicheren Static Direct Play · kein Server-Transcode gestartet",
        )
        return

    if not _embyflow_pgs_0627_prepare_environment(self):
        _embyflow_pgs_0627_status(self, "Bitmap-Untertitel: lokaler Renderer konnte nicht vorbereitet werden")
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

    self.embyflow_pgs_0627_pending = {
        "stream": dict(stream or {}),
        "label": str(label or "Bitmap"),
        "position": int(position),
    }
    self.embyflow_pgs_0627_attempts = 0
    self.embyflow_pgs_0627_rendering = False

    target_ticks = 0
    try:
        target_ticks = max(0, int(self.current_position_ticks() or 0))
    except Exception:
        pass

    current_type = int(
        getattr(self, "embyflow_engine_service_type_v11_4", STREAM_SERVICE_TYPE)
        or STREAM_SERVICE_TYPE
    )
    wrapper_launched = bool(getattr(self, "embyflow_pgs_0627_wrapper_launched", False))

    switched = True
    if current_type != 5002:
        switched = bool(_embyflow_rcdev7_switch_static_to_ext(self, target_ticks))
        if switched:
            self.embyflow_pgs_0627_wrapper_launched = True
    elif not wrapper_launched:
        switched = bool(_embyflow_pgs_0627_restart_5002(self, target_ticks))

    if not switched:
        self.embyflow_pgs_0627_pending = None
        _embyflow_pgs_0627_status(
            self,
            "Bitmap-Untertitel: lokaler 5002-Start fehlgeschlagen · kein Server-Transcode gestartet",
        )
        return

    _embyflow_pgs_0627_status(
        self,
        "Untertitel: %s · Bitmap-Renderer startet" % str(label or "Bitmap"),
    )
    try:
        _embyflow_pgs_0627_retry_timer(self).start(800, True)
    except Exception:
        _embyflow_pgs_0627_retry(self)


def _embyflow_pgs_0627_finished(self, result):
    if not result:
        return
    try:
        action, value, label, position = result
    except Exception:
        return _EMBYFLOW_BITMAP_0626_FINISHED_FOR_0627(self, result)

    if action == "hybrid_unsupported_0625":
        return _embyflow_pgs_0627_start(
            self,
            value,
            label,
            int(position),
        )

    # Switching to Off/text/native immediately removes our bitmap overlay.
    _embyflow_pgs_0627_stop_render(self, keep_wrapper=True)
    return _EMBYFLOW_BITMAP_0626_FINISHED_FOR_0627(self, result)


def _embyflow_pgs_0627_close(self):
    _embyflow_pgs_0627_stop_render(self, keep_wrapper=False)
    overlay = getattr(self, "embyflow_pgs_0627_overlay", None)
    if overlay is not None:
        try:
            self.session.deleteDialog(overlay)
        except Exception:
            try:
                overlay.close()
            except Exception:
                pass
        self.embyflow_pgs_0627_overlay = None

    session_dir = str(getattr(self, "embyflow_pgs_0627_dir", "") or "")
    _embyflow_pgs_0627_remove_tree(session_dir)
    self.embyflow_pgs_0627_dir = ""
    self.embyflow_pgs_0627_event_file = ""
    self.embyflow_pgs_0627_wrapper_launched = False
    return _EMBYFLOW_BITMAP_0626_CLOSE_FOR_0627(self)


EmbyFlowMoviePlayer.subtitle_selection_finished = _embyflow_pgs_0627_finished
EmbyFlowMoviePlayer.embyflow_close_subtitle_window = _embyflow_pgs_0627_close
# EMBYFLOW_BITMAP_PGS_RENDERER_0627_RELEASE
# EMBYFLOW_BITMAP_PGS_RENDERER_0627_END

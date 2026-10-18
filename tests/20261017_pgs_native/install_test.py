"""Single-file installer template; build_test.py embeds the tested patches."""
from pathlib import Path
import os
import shutil
import tempfile
import time

NATIVE_MARKER = '# EMBYFLOW_PGS_NATIVE_LOCAL_V1'
PARENT_MARKER = '# EMBYFLOW_PGS_PARENT_LOCAL_V2'
AUTO_MARKER = '# EMBYFLOW_PGS_AUTO_LOCAL_V3'


def patched(source, native_patch, auto_patch):
    for required in ('def _efut2_streams(', 'def _embyflow_subtitle_finished_0629(',
                     'def _embyflow_srt_v2_stop('):
        if required not in source:
            raise RuntimeError('Basis mit aktivem MediaSource-UT-Fix fehlt. Bitte zuerst EmbyFlow aktualisieren.')
    result = source
    if NATIVE_MARKER not in result:
        if PARENT_MARKER in result or AUTO_MARKER in result:
            raise RuntimeError('Unvollstaendige PGS-Installation. Nichts geaendert.')
        result += '\n\n' + native_patch
    elif PARENT_MARKER not in result:
        before, sep, tail = result.partition(NATIVE_MARKER)
        old = "    widget = getattr(window, 'instance', None)"
        if tail.count(old) != 1:
            raise RuntimeError('PGS-V1-Einbaustelle abweichend. Nichts geaendert.')
        result = before + sep + '\n' + PARENT_MARKER + tail.replace(
            old, "    widget = getattr(self, 'instance', None)", 1)
    if AUTO_MARKER not in result:
        result += '\n\n' + auto_patch
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, native_patch, auto_patch):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Pluginpfad ist ein Symlink. Nichts geaendert.')
    source = path.read_text()
    result = patched(source, native_patch, auto_patch)
    if source == result:
        print('PGS-Test mit Automatik bereits installiert. Nichts geaendert.')
        return
    backup = str(path) + '.vor-pgs-test-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path, backup)
    fd, name = tempfile.mkstemp(prefix='plugin.py.pgs-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(result)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copystat(path, name)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print('PGS-Test mit Automatik installiert. Sicherung:', backup)
    print('GUI neu starten. Film frisch oeffnen und keine Untertitel manuell waehlen.')


NATIVE_PATCH = '"""Unpublished PGS test: native 4097 only, no video restart/transcoding."""\n# EMBYFLOW_PGS_NATIVE_LOCAL_V1\n# EMBYFLOW_PGS_PARENT_LOCAL_V2\ndef _efpg_codec(stream):\n    return str(stream.get(\'Codec\') or \'\').strip().lower()\n\n\ndef _efpg_lang(value):\n    import re\n    value = re.split(\'[-_]\', str(value or \'\').strip().lower())[0]\n    return {\'ger\': \'de\', \'deu\': \'de\', \'deutsch\': \'de\', \'german\': \'de\',\n            \'eng\': \'en\', \'english\': \'en\', \'englisch\': \'en\'}.get(value, value)\n\n\ndef _efpg_match(self, stream):\n    from urllib.parse import urlsplit, parse_qs\n    ref = self.session.nav.getCurrentlyPlayingServiceReference()\n    if ref is None or getattr(ref, \'type\', None) != 4097:\n        raise RuntimeError(\'Der PGS-Test benoetigt den aktiven Player 4097.\')\n    url = urlsplit(str(getattr(self, \'stream_url\', \'\') or \'\'))\n    query = {k.lower(): [v.lower() for v in values]\n             for k, values in parse_qs(url.query).items()}\n    if (url.scheme not in (\'http\', \'https\') or\n            not url.path.lower().endswith((\'.mkv\', \'.mp4\', \'.ts\')) or\n            query.get(\'static\') != [\'true\']):\n        raise RuntimeError(\'PGS-Test nur fuer eingebettete Spuren im Originalstream.\')\n    streams = _efut2_streams(self)\n    # External/unknown streams cannot be mapped to embedded stream ordinals.\n    embedded = [s for s in streams if str(s.get(\'IsExternal\')).lower() in (\'false\', \'0\')]\n    embedded = sorted(embedded, key=lambda s: int(s[\'Index\']))\n    indices = [int(s[\'Index\']) for s in embedded]\n    if len(set(indices)) != len(indices):\n        raise RuntimeError(\'Mehrdeutige Emby-Untertitelindizes.\')\n    matches = [i for i, s in enumerate(embedded)\n               if int(s[\'Index\']) == int(stream[\'Index\']) and s == stream]\n    if len(matches) != 1 or _efpg_codec(stream) not in (\'pgs\', \'pgssub\', \'hdmv_pgs_subtitle\'):\n        raise RuntimeError(\'Keine eingebettete PGS-Spur der aktiven Filmversion.\')\n    service = self.session.nav.getCurrentService()\n    interface = service and service.subtitle()\n    native = list(interface.getSubtitleList() or []) if interface else []\n    # The backend exposes subtitle ordinals, not Emby video/audio stream IDs.\n    # Reject partial/mixed/unknown inventories instead of guessing a language.\n    if len(native) != len(embedded):\n        raise RuntimeError(\'4097 bietet keine eindeutig zuordenbare PGS-Spurliste an.\')\n    types = {\'pgs\': (6,), \'pgssub\': (6,), \'hdmv_pgs_subtitle\': (6,),\n             \'subrip\': (4,), \'srt\': (4,), \'ssa\': (2,), \'ass\': (3,),\n             \'text\': (1,), \'webvtt\': (7,), \'vtt\': (7,)}\n    by_pid = {}\n    for entry in native:\n        if not isinstance(entry, (tuple, list)) or len(entry) < 5:\n            raise RuntimeError(\'Unbekanntes natives Untertitelformat.\')\n        pid = int(entry[1])\n        if pid in by_pid or not 0 <= pid < len(embedded):\n            raise RuntimeError(\'Mehrdeutige native Untertitelindizes.\')\n        expected = embedded[pid]\n        subtype = int(entry[2])\n        if subtype not in types.get(_efpg_codec(expected), ()):\n            raise RuntimeError(\'Untertitelcodecs von Emby und 4097 passen nicht zusammen.\')\n        expected_type = (2, 3) if subtype == 6 else (2,)\n        if int(entry[0]) not in expected_type:\n            raise RuntimeError(\'PGS wird von diesem 4097-Backend nicht angeboten.\')\n        left, right = _efpg_lang(expected.get(\'Language\')), _efpg_lang(entry[4])\n        if not left or left in (\'und\', \'unknown\') or left != right:\n            raise RuntimeError(\'Untertitelsprachen sind nicht eindeutig zuordenbar.\')\n        by_pid[pid] = entry\n    return interface, by_pid[matches[0]]\n\n\n_efpg_stop_before = _embyflow_srt_v2_stop\ndef _efpg_stop(self, invalidate=True):\n    active = getattr(self, \'_efpg_active\', None)\n    self._efpg_active = None\n    if active is not None:\n        interface, widget, window = active\n        try:\n            interface.disableSubtitles(widget)\n        except Exception:\n            pass\n        try:\n            window.hide()\n        except Exception:\n            pass\n        self.embyflow_selected_subtitle = None\n        self.embyflow_active_subtitle_index = None\n        self.embyflow_active_subtitle_stream_index = None\n    return _efpg_stop_before(self, invalidate)\n\n\ndef _efpg_start(self, stream, label, position):\n    interface, entry = _efpg_match(self, stream)\n    window = self.embyflow_get_subtitle_window()\n    # Attach native eSubtitleWidget to the visible EmbyFlow movie screen.\n    # Its parent determines both size and compositor layer. The separate\n    # standard SubtitleDisplay can live below modal plugin screens.\n    widget = getattr(self, \'instance\', None)\n    if widget is None:\n        raise RuntimeError(\'Kein natives Untertitelfenster verfuegbar.\')\n    _efpg_stop(self, True)\n    self.embyflow_active_subtitle_index = None\n    self.embyflow_active_subtitle_stream_index = None\n    try:\n        # Cached selections may return 0 without attaching a new display owner.\n        interface.disableSubtitles(widget)\n        result = interface.enableSubtitles(widget, entry)\n        if result not in (None, 0):\n            raise RuntimeError(\'4097 hat die PGS-Aktivierung abgelehnt.\')\n        window.show()\n    except Exception:\n        try:\n            interface.disableSubtitles(widget)\n            window.hide()\n        except Exception:\n            pass\n        raise\n    self._efpg_active = (interface, widget, window)\n    self.embyflow_selected_subtitle = entry\n    self.embyflow_active_subtitle_index = int(position)\n    self.embyflow_active_subtitle_stream_index = int(stream[\'Index\'])\n    _efut2_source(self)[\'DefaultSubtitleStreamIndex\'] = int(stream[\'Index\'])\n    self[\'state_label\'].setText(\'Untertitel: \' + str(label) + \' (PGS)\')\n    self.show_overlay()\n\n\n_efpg_selection_before = EmbyFlowMoviePlayer.subtitle_selection_finished\ndef _efpg_selection(self, result):\n    if not result:\n        return _efpg_selection_before(self, result)\n    action, stream, label, position = result\n    if action == \'subtitle_bitmap_info_0629\' and _efpg_codec(stream or {}) in (\'pgs\', \'pgssub\', \'hdmv_pgs_subtitle\'):\n        self._efut_manual = True\n        try:\n            _efpg_start(self, stream, label, position)\n        except Exception as error:\n            self.session.open(MessageBox, str(error), MessageBox.TYPE_INFO, timeout=8)\n        return\n    # Cancel native display even when a non-PGS start fails before SRT stop.\n    if action in (\'subtitle\', \'subtitle_off\'):\n        _efpg_stop(self, True)\n    return _efpg_selection_before(self, result)\n\n\n_efpg_close_before = EmbyFlowMoviePlayer.embyflow_close_subtitle_window\ndef _efpg_close(self):\n    _efpg_stop(self, True)\n    return _efpg_close_before(self)\n\n\n_embyflow_srt_v2_stop = _efpg_stop\nEmbyFlowMoviePlayer.subtitle_selection_finished = _efpg_selection\nEmbyFlowMoviePlayer.embyflow_close_subtitle_window = _efpg_close\n'
AUTO_PATCH = '"""PGS automatic selection on the already receiver-tested native display path."""\n# EMBYFLOW_PGS_AUTO_LOCAL_V3\ndef _efpga_forced(stream):\n    title = (str(stream.get(\'Title\') or \'\') + \' \' + str(stream.get(\'DisplayTitle\') or \'\')).lower()\n    return str(stream.get(\'IsForced\')).strip().lower() in (\'true\', \'1\') or \'forced\' in title or \'erzw\' in title\n\n\ndef _efpga_candidate(self):\n    source = _efut2_source(self)\n    streams = _efut2_streams(self)\n    try:\n        desired = int(source.get(\'DefaultSubtitleStreamIndex\', -1))\n    except (TypeError, ValueError):\n        desired = -1\n    if desired >= 0:\n        # A user/server-selected text, full, or foreign-language track wins.\n        for position, stream in enumerate(streams):\n            try:\n                if int(stream.get(\'Index\')) != desired:\n                    continue\n            except (TypeError, ValueError):\n                continue\n            if _efpg_codec(stream) in (\'pgs\', \'pgssub\', \'hdmv_pgs_subtitle\'):\n                return position, stream\n            return None\n        return None\n    # Preserve the proven SRT/4K-segment choice when forced text is available.\n    if any(_efut2_german(s) and _efpga_forced(s) and _embyflow_srt_v2_is_text_stream(s) for s in streams):\n        return None\n    for position, stream in enumerate(streams):\n        if (_efpg_codec(stream) in (\'pgs\', \'pgssub\', \'hdmv_pgs_subtitle\') and\n                _efut2_german(stream) and _efpga_forced(stream)):\n            return position, stream\n    return None\n\n\n_efpga_auto_before = EmbyFlowMoviePlayer.set_preferred_subtitle_track\ndef _efpga_auto(self):\n    if (getattr(self, \'_efut_manual\', False) or\n            getattr(self, \'embyflow_manual_subtitle_selected\', False) or\n            getattr(self, \'closed\', False)):\n        return\n    if (getattr(self, \'embyflow_srt_v2_loading\', False) or\n            getattr(self, \'embyflow_active_subtitle_index\', None) is not None):\n        return\n    try:\n        candidate = _efpga_candidate(self)\n        if candidate is None:\n            return _efpga_auto_before(self)\n        position, stream = candidate\n        key = (str(getattr(self, \'item_id\', \'\')),\n               str(getattr(self, \'media_source_id\', \'\')), int(stream[\'Index\']))\n        if getattr(self, \'_efpga_key\', None) != key:\n            self._efpga_key = key\n            self._efpga_tries = 0\n        if self._efpga_tries >= 8:\n            return\n        self._efpga_tries += 1\n        try:\n            _efpg_start(self, stream, _embyflow_srt_v2_language(self, stream, position), position)\n        except Exception:\n            # The native list/window can still be incomplete at initial startup.\n            # Use the existing GUI timer; never block or restart the movie.\n            if self._efpga_tries < 8:\n                self.subtitle_timer.start(750, True)\n            else:\n                self[\'state_label\'].setText(\'PGS-Untertitel konnten nicht automatisch aktiviert werden.\')\n    except Exception:\n        # Do not expose URLs/tokens or raise a popup during automatic startup.\n        return\n\n\nEmbyFlowMoviePlayer.set_preferred_subtitle_track = _efpga_auto\n'

if __name__ == '__main__':
    install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py', NATIVE_PATCH, AUTO_PATCH)

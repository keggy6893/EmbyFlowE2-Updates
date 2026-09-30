"""Build the theme volume update from the verified 2026093002 payload."""
import ast
import hashlib
import json
import pathlib
import sys

BASE_SHA256 = "abaa53a3ef40a072f14440545d65dcd1a463513db61d925ab70b81e73b1b7b10"
OUTPUT = "EmbyFlowE2_ThemeVolume_20260930_3003.py"


def build(base, layer):
    if hashlib.sha256(base).hexdigest() != BASE_SHA256:
        raise ValueError("Base payload differs from the reviewed build 2026093002")
    text = base.decode("utf-8")

    def replace(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError("Patch anchor is not unique: " + old[:100])
        text = text.replace(old, new, 1)

    replace('PLUGIN_VERSION = "2026-RCDEV-FTP-ACCOUNTS10-20260930"',
            'PLUGIN_VERSION = "2026-RCDEV-THEMEVOLUME-20260930"')
    replace('PLUGIN_UPDATE_BUILD = 2026093002', 'PLUGIN_UPDATE_BUILD = 2026093003')
    old_changelog = next(line for line in text.splitlines() if line.startswith('PLUGIN_UPDATE_CHANGELOG = '))
    replace(old_changelog, 'PLUGIN_UPDATE_CHANGELOG = ' + repr(
        'Hintergrundmusik und ThemeVideos: Lautstärkeobergrenze, Vorgabe 20 %|'
        'Erweiterte Einstellungen: BLAU Musik|Normale Lautstärke bei Filmstart und TV wiederhergestellt'))
    # Add to the legacy config list as well as the advanced settings dialog.
    replace('getConfigListEntry("Poster-Cache", config.embyflow.cache_enabled),',
            'getConfigListEntry("Hintergrundmusik (max. %)", config.embyflow.theme_volume),\n'
            '            getConfigListEntry("Poster-Cache", config.embyflow.cache_enabled),')
    replace('        screen.session.nav.playService(reference)\n'
            '        _embyflow_theme_log_v1(',
            '        screen._theme_service_ref_v1 = reference\n'
            '        _embyflow_theme_volume_play(screen, reference)\n'
            '        _embyflow_theme_log_v1(')

    start = text.index('def _embyflow_theme_stop_v1(screen, restore=True):')
    end = text.index('\ndef _embyflow_theme_schedule_v1(screen):', start)
    text = text[:start] + '''def _embyflow_theme_stop_v1(screen, restore=True):
    timer = getattr(screen, "_theme_delay_timer_v1", None)
    if timer is not None:
        timer.stop()
    was_playing = bool(getattr(screen, "_theme_playing_v1", False))
    screen._theme_playing_v1 = False
    screen._theme_playing_id_v1 = ""
    previous = getattr(screen, "_theme_previous_service_v1", None)
    screen._theme_previous_service_v1 = None
    try:
        if not was_playing:
            return
        current = screen.session.nav.getCurrentlyPlayingServiceReference()
        own = getattr(screen, "_theme_service_ref_v1", None)
        if current is None or own is None or current.toString() != own.toString():
            return
        screen.session.nav.stopService()
        _embyflow_theme_volume_release(screen)
        if restore and previous is not None:
            screen.session.nav.playService(previous)
    except Exception as error:
        _embyflow_theme_log_v1("STOP_ERROR %s" % error)
    finally:
        _embyflow_theme_volume_release(screen)

''' + text[end:]
    # Release before restoring TV, including early returns and failed stops.
    for name, next_name, owner in (
            ('_skyfall_local_theme_stop', '_skyfall_local_theme_start', 'self'),
            ('_fallback_detail_stop', '_fallback_detail_close', 'self')):
        start = text.index('def %s(' % name)
        end = text.index('\ndef %s(' % next_name, start)
        part = text[start:end]
        anchor = '        self.session.nav.stopService()\n'
        if part.count(anchor) != 1:
            raise ValueError("Stop anchor mismatch: " + name)
        part = part.replace(anchor, anchor + '        _embyflow_theme_volume_release(self)\n')
        part = part.rstrip() + '\n    finally:\n        _embyflow_theme_volume_release(self)\n\n'
        text = text[:start] + part + text[end:]

    replace('        self.session.nav.playService(self._skyfall_local_theme_ref)',
            '        _embyflow_theme_volume_play(self, self._skyfall_local_theme_ref)')
    replace('            self.session.nav.playService(self._fallback_theme_ref)',
            '            _embyflow_theme_volume_play(self, self._fallback_theme_ref)')
    # Definitions are available before any screen can be opened.
    text += '\n\n' + layer + '\n'
    ast.parse(text)
    return text.encode("utf-8")


if __name__ == "__main__":
    base_path, layer_path, outdir = map(pathlib.Path, sys.argv[1:])
    data = build(base_path.read_bytes(), layer_path.read_text(encoding="utf-8"))
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / OUTPUT).write_bytes(data)
    manifest = dict(version="2026-RCDEV-THEMEVOLUME-20260930", build=2026093003,
                    channel="rcdev", target="plugin.py", artifact_type="plugin_py",
                    download="https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/" + OUTPUT,
                    sha256=hashlib.sha256(data).hexdigest(),
                    changelog=["Hintergrundmusik und ThemeVideos: einstellbare Lautstärkeobergrenze, Vorgabe 20 %",
                               "Erweiterte Einstellungen: BLAU Musik; 0-100 % in 5-%-Schritten",
                               "Normale Lautstärke bei Filmstart und Rückkehr zum TV wiederhergestellt",
                               "10 FTP-Accounts und ThemeVideos Test8 weiterhin enthalten"])
    (outdir / "update.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(file=OUTPUT, sha256=manifest["sha256"], size=len(data))))

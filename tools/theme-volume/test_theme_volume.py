import ast
import importlib.util
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("builder", ROOT / "build_theme_volume.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Timer:
    def __init__(self):
        self.callback = []
        self.running = False

    def start(self, *args):
        self.running = True

    def stop(self):
        self.running = False


class Control:
    def __init__(self):
        self.volume = 65

    def getVolume(self):
        return self.volume

    def setVolume(self, left, right):
        self.volume = left


class Ref:
    def __init__(self, value):
        self.value = value

    def toString(self):
        return self.value


class Nav:
    def __init__(self):
        self.current = Ref("tv")
        self.fail = False
        self.stops = 0

    def getCurrentlyPlayingServiceReference(self):
        return self.current

    def playService(self, ref):
        if self.fail:
            raise RuntimeError("decoder failed")
        self.current = ref
        return 0

    def stopService(self):
        self.current = None
        self.stops += 1


class VolumeTests(unittest.TestCase):
    def setUp(self):
        self.control = Control()
        sys.modules["enigma"] = types.SimpleNamespace(
            eDVBVolumecontrol=types.SimpleNamespace(getInstance=lambda: self.control))
        self.nav = Nav()
        self.session = types.SimpleNamespace(nav=self.nav)
        self.screen = types.SimpleNamespace(session=self.session)
        self.setting = types.SimpleNamespace(value="20")
        self.ns = dict(eTimer=Timer, config=types.SimpleNamespace(
            embyflow=types.SimpleNamespace(theme_volume=self.setting)),
            _EMBYFLOW_THEME_VOLUME_STATE=None,
            _embyflow_theme_log_v1=lambda msg: None)
        layer = ast.parse((ROOT / "theme_volume_layer.py").read_text())
        functions = [node for node in layer.body if isinstance(node, ast.FunctionDef)]
        exec(compile(ast.Module(body=functions, type_ignores=[]), "layer", "exec"), self.ns)

    def play(self, owner=None, ref="theme"):
        self.ns["_embyflow_theme_volume_play"](owner or self.screen, Ref(ref))

    def release(self, owner=None):
        self.ns["_embyflow_theme_volume_release"](owner or self.screen)

    def tick(self):
        self.ns["_EMBYFLOW_THEME_VOLUME_STATE"]["timer"].callback[0]()

    def test_cap_restore_and_repeated_navigation(self):
        for _ in range(10):
            self.play()
            self.assertEqual(self.control.volume, 20)
            self.control.volume = 95  # Simulated external automatic volume change.
            self.tick()
            self.assertEqual(self.control.volume, 20)
            self.release()
            self.assertEqual(self.control.volume, 65)

    def test_lower_manual_volume_is_not_raised(self):
        self.control.volume = 8
        self.play()
        self.tick()
        self.assertEqual(self.control.volume, 8)
        self.control.volume = 3
        self.tick()
        self.assertEqual(self.control.volume, 3)
        self.release()
        self.assertEqual(self.control.volume, 8)

    def test_owner_transfer_preserves_original_volume(self):
        self.play()
        old_timer = self.ns["_EMBYFLOW_THEME_VOLUME_STATE"]["timer"]
        other = types.SimpleNamespace(session=self.session)
        self.play(other, "detail-theme")
        self.release()  # Closing an old grid must not restore over a new theme.
        self.assertEqual(self.control.volume, 20)
        self.assertFalse(old_timer.running)
        self.release(other)
        self.assertEqual(self.control.volume, 65)

    def test_failed_start_restores_volume(self):
        self.nav.fail = True
        with self.assertRaises(RuntimeError):
            self.play()
        self.assertEqual(self.control.volume, 65)
        self.assertIsNone(self.ns["_EMBYFLOW_THEME_VOLUME_STATE"])

    def test_external_service_change_releases_guard(self):
        self.play()
        self.nav.current = Ref("movie")
        self.tick()
        self.assertEqual(self.control.volume, 65)
        self.assertEqual(self.nav.current.toString(), "movie")
        self.assertIsNone(self.ns["_EMBYFLOW_THEME_VOLUME_STATE"])

    def test_zero_mutes_and_bounds_are_checked(self):
        self.setting.value = "0"
        self.play()
        self.assertEqual(self.control.volume, 0)
        self.release()
        self.assertEqual(self.control.volume, 65)
        for text, expected in (("n/a", 20), ("-5", 0), ("120", 100)):
            self.setting.value = text
            self.assertEqual(self.ns["_embyflow_theme_volume_limit"](), expected)

    def test_all_three_stop_paths_restore_and_do_not_stop_movies(self):
        data = builder.build((ROOT / "base.py").read_bytes(),
                             (ROOT / "theme_volume_layer.py").read_text())
        names = {"_embyflow_theme_stop_v1", "_skyfall_local_theme_stop", "_fallback_detail_stop"}
        functions = [n for n in ast.parse(data).body if isinstance(n, ast.FunctionDef) and n.name in names]
        exec(compile(ast.Module(body=functions, type_ignores=[]), "stop", "exec"), self.ns)
        for name, active, own, previous in (
                ("_embyflow_theme_stop_v1", "_theme_playing_v1", "_theme_service_ref_v1", "_theme_previous_service_v1"),
                ("_skyfall_local_theme_stop", "_skyfall_local_theme_active", "_skyfall_local_theme_ref", "_skyfall_local_previous_ref"),
                ("_fallback_detail_stop", "_fallback_theme_active", "_fallback_theme_ref", "_fallback_previous_ref")):
            self.play()
            setattr(self.screen, active, True)
            setattr(self.screen, own, Ref("theme"))
            setattr(self.screen, previous, Ref("tv"))
            self.ns[name](self.screen)
            self.assertEqual(self.nav.current.toString(), "tv", name)
            self.assertEqual(self.control.volume, 65, name)
            self.play()
            setattr(self.screen, active, True)
            self.nav.current = Ref("movie")
            stops = self.nav.stops
            self.ns[name](self.screen)
            self.assertEqual(self.nav.stops, stops, name)
            self.assertEqual(self.nav.current.toString(), "movie", name)
            self.assertEqual(self.control.volume, 65, name)


if __name__ == "__main__":
    unittest.main()

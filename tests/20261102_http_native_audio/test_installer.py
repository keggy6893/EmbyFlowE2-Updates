"""Run with python3 -m unittest discover -s tests/20261102_http_native_audio."""
import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('http_installer', HERE / 'installer.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
ORIGINAL = (HERE / 'original_predicate.py').read_text(encoding='utf-8')


class NativeAudioTests(unittest.TestCase):
    def setUp(self):
        self.state = dict(native=True, count=2, machine='vuduo4kse', compat=False, enabled=True)
        self.events = []
        self.env = dict(_efua_native=lambda p: self.state['native'],
                        _efa2_enabled=lambda p: self.state['enabled'],
                        _efa3_audio_compat_codec=lambda p: self.state['compat'],
                        _efua_log=lambda event, **kw: self.events.append(event))
        exec(compile(installer.transform(ORIGINAL), 'patched', 'exec'), self.env)
        self.tracks = types.SimpleNamespace(getNumberOfTracks=lambda: self.state['count'])
        self.nav = types.SimpleNamespace(
            getCurrentlyPlayingServiceReference=lambda: types.SimpleNamespace(type=4097),
            getCurrentService=lambda: types.SimpleNamespace(audioTracks=lambda: self.tracks))
        self.player = types.SimpleNamespace(playback_info={}, item={}, stream_url='https://example.invalid/video',
                                            session=types.SimpleNamespace(nav=self.nav))
        module = types.ModuleType('Components.SystemInfo')
        module.BoxInfo = types.SimpleNamespace(getItem=lambda k: self.state['machine'])
        self.modules = patch.dict(sys.modules, {'Components.SystemInfo': module})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def route(self):
        return self.env['_efua_vu_remote_audio_trial'](self.player)

    def test_native_two_tracks(self):
        self.assertFalse(self.route())
        self.assertEqual(self.events, ['http-native-first'])

    def test_single_or_no_track_keeps_fallback(self):
        for count in (0, 1):
            self.state['count'] = count
            self.assertTrue(self.route())

    def test_non_native_session_keeps_fallback(self):
        self.state['native'] = False
        self.assertTrue(self.route())

    def test_other_box_unchanged(self):
        self.state['machine'] = 'dreamone'
        self.assertFalse(self.route())
        self.assertEqual(self.events, [])

    def test_local_nas_unchanged(self):
        self.player.playback_info = {'local_file': True}
        self.assertFalse(self.route())
        self.assertEqual(self.events, [])

    def test_native_service_type_unchanged(self):
        self.nav.getCurrentlyPlayingServiceReference = lambda: types.SimpleNamespace(type=1)
        self.assertFalse(self.route())
        self.assertEqual(self.events, [])

    def test_non_http_unchanged(self):
        self.player.stream_url = '/media/movie/test.ts'
        self.assertFalse(self.route())

    def test_track_error_keeps_fallback(self):
        self.tracks.getNumberOfTracks = lambda: int('invalid')
        self.assertTrue(self.route())

    def test_compat_fallback_unchanged(self):
        self.state.update(native=False, compat=True)
        self.assertFalse(self.route())

    def test_scope_and_full_syntax(self):
        source = 'def untouched():\n    return 123\n\n' + ORIGINAL
        changed = installer.transform(source)
        compile(changed, 'plugin.py', 'exec')
        before, after = ast.parse(source), ast.parse(changed)
        self.assertEqual(ast.dump(before.body[0]), ast.dump(after.body[0]))
        self.assertEqual(len(before.body), len(after.body))

    def test_reinstall_refuses(self):
        with self.assertRaises(ValueError):
            installer.transform(installer.transform(ORIGINAL))

    def test_unknown_or_ambiguous_basis_refuses(self):
        for source in ('pass\n', ORIGINAL + ORIGINAL, ORIGINAL.replace('return bool(', 'return str(')):
            with self.assertRaises(ValueError):
                installer.transform(source)

    def test_shell_contains_exact_installer(self):
        shell = (HERE / 'install.sh').read_text(encoding='utf-8')
        body = shell.split("python3 - <<'EMBYFLOW_HTTP_AUDIO_PY'\n", 1)[1].rsplit('EMBYFLOW_HTTP_AUDIO_PY', 1)[0]
        self.assertEqual(body.rstrip(), (HERE / 'installer.py').read_text(encoding='utf-8').rstrip())


if __name__ == '__main__':
    unittest.main()

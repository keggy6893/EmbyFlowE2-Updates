import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
RUNTIME = (HERE / 'runtime.py').read_text()
spec = importlib.util.spec_from_file_location('hearing_install', HERE / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Hearing(unittest.TestCase):
    def setUp(self):
        self.cancel = threading.Event()
        self.state = {}
        self.data = {'Type': 'Movie', 'ProviderIds': {'Tmdb': '37724'}}
        self.server = Mock(return_value='')
        self.lookup = Mock(return_value={'id': 37724, 'youtube_theme_url': 'https://www.youtube.com/watch?v=example'})
        self.ns = {'_efbg_music': self.server, '_efbg_mode': lambda: 'music',
                   '_json': self.lookup, '_triso_code': lambda: 'worker',
                   '_eftr_youtube_url': lambda url: url.startswith('https://www.youtube.com/watch?v='),
                   'embyflow_http_get': Mock(), 'AUTH_HEADER': 'local-client'}
        exec(compile(RUNTIME, 'runtime.py', 'exec'), self.ns)
        self.process = Mock(returncode=0)
        self.process.communicate.return_value = (json.dumps({'url': 'https://r1.googlevideo.com/audio'}).encode(), b'')
        self.factory = Mock(return_value=self.process)
        self.ns['_EFThemeProcess'] = self.factory

    def play(self):
        return self.ns['_efbg_music'](self.data, ('https://emby.example', 'private-token', 'user'), self.cancel, self.state)

    def test_reachable_audio_returned_and_process_cleared(self):
        self.assertEqual(self.play(), 'https://r1.googlevideo.com/audio')
        self.assertIsNone(self.state['process'])
        self.assertEqual(self.factory.call_args.args[1]['format'], 'bestaudio[ext=m4a]/bestaudio')

    def test_server_theme_has_priority(self):
        self.server.return_value = 'https://emby.example/theme'
        self.assertEqual(self.play(), self.server.return_value)
        self.lookup.assert_not_called()

    def test_disabled_and_already_closed_skip_requests(self):
        self.ns['_efbg_mode'] = lambda: 'off'
        self.assertEqual(self.play(), '')
        self.server.assert_not_called()
        self.ns['_efbg_mode'] = lambda: 'music'
        self.cancel.set()
        self.assertEqual(self.play(), '')
        self.lookup.assert_not_called()

    def test_unknown_titles_and_episodes_not_resolved(self):
        for kind, tmdb in [('Movie', '99999'), ('Episode', '37724'), ('Movie', '1399')]:
            self.data = {'Type': kind, 'ProviderIds': {'Tmdb': tmdb}}
            self.assertEqual(self.play(), '')
        self.lookup.assert_not_called()

    def test_series_endpoint_and_no_external_credentials(self):
        self.data = {'Type': 'Series', 'ProviderIds': {'tmdb': '1399'}}
        self.lookup.return_value['id'] = 1399
        self.play()
        self.lookup.assert_called_once_with('https://app.lizardbyte.dev/ThemerrDB/tv_shows/themoviedb/1399.json')
        self.assertNotIn('private-token', str(self.factory.call_args))

    def test_missing_metadata_requested_only_from_emby(self):
        self.data = {'id': 'item'}
        response = self.ns['embyflow_http_get'].return_value
        response.status_code = 200
        response.json.return_value = {'Type': 'Movie', 'ProviderIds': {'Tmdb': '37724'}}
        self.assertTrue(self.play())
        call = self.ns['embyflow_http_get'].call_args
        self.assertEqual(call.args[0], 'https://emby.example/Users/user/Items/item')
        self.assertTrue(call.kwargs['verify'])

    def test_wrong_entry_and_non_youtube_source_rejected(self):
        self.lookup.return_value['id'] = 123
        self.assertEqual(self.play(), '')
        self.lookup.return_value = {'id': 37724, 'youtube_theme_url': 'https://other.example/track'}
        self.assertEqual(self.play(), '')
        self.factory.assert_not_called()

    def test_stream_origin_and_worker_failure_rejected(self):
        for url in ['http://r1.googlevideo.com/a', 'https://googlevideo.com.evil.example/a', 'file:///etc/passwd']:
            self.process.communicate.return_value = (json.dumps({'url': url}).encode(), b'')
            self.assertEqual(self.play(), '')
        self.process.returncode = 1
        self.assertEqual(self.play(), '')

    def test_timeout_kills_and_reaps(self):
        self.process.communicate.side_effect = [subprocess.TimeoutExpired('worker', 55), (b'', b'')]
        self.assertEqual(self.play(), '')
        self.process.kill.assert_called_once()
        self.assertEqual(self.process.communicate.call_count, 2)
        self.assertIsNone(self.state['process'])

    def test_close_during_resolution_prevents_late_audio(self):
        def result(**kwargs):
            self.cancel.set()
            return b'{"url":"https://r1.googlevideo.com/audio"}', b''
        self.process.communicate.side_effect = result
        self.assertEqual(self.play(), '')
        self.assertIsNone(self.state['process'])

    def test_close_during_server_lookup_prevents_late_audio(self):
        def result(*args):
            self.cancel.set()
            return 'https://emby.example/theme'
        self.server.side_effect = result
        self.assertEqual(self.play(), '')
        self.lookup.assert_not_called()

    def test_process_isolation_and_group_cleanup(self):
        ns = dict(self.ns)
        exec(RUNTIME, ns)
        with patch.object(ns['_efth_subprocess'], 'Popen') as popen, patch.object(ns['_efth_os'], 'killpg') as kill:
            popen.return_value.pid = 123456
            process = ns['_EFThemeProcess']('pass', {})
            self.assertTrue(popen.call_args.kwargs['start_new_session'])
            process.kill()
            kill.assert_called_once_with(123456, ns['_efth_signal'].SIGKILL)


class Installation(unittest.TestCase):
    def test_real_release_preserved_backup_and_repeat_install(self):
        release = HERE.parents[1] / 'EmbyFlowE2_2026101802.py'
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'plugin.py'
            target.write_bytes(release.read_bytes())
            target.chmod(0o644)
            original = target.read_bytes()
            self.assertTrue(installer.install(target, RUNTIME))
            self.assertTrue(target.read_bytes().startswith(original))
            self.assertEqual(next(target.parent.glob('plugin.py.vor-*')).read_bytes(), original)
            self.assertEqual(target.stat().st_mode & 0o777, 0o644)
            self.assertFalse(installer.install(target, RUNTIME))
            self.assertEqual(len(list(target.parent.glob('plugin.py.vor-*'))), 1)

    def test_unexpected_source_and_syntax_error_leave_original(self):
        with self.assertRaises(RuntimeError):
            installer.patched('pass', RUNTIME)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'plugin.py'
            target.write_text('def _efbg_music():pass\ndef _triso_code():pass\ndef _efserver_theme_url():pass\ndef _efbg_cancel():pass\n')
            original = target.read_bytes()
            with self.assertRaises(SyntaxError):
                installer.install(target, 'broken (')
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(list(target.parent.glob('plugin.py.vor-*')), [])


if __name__ == '__main__':
    unittest.main()

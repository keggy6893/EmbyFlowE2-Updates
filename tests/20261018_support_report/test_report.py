import importlib.util
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = load('support_core', HERE / 'report.py')
builder = load('support_builder', HERE / 'build.py')


class Report(unittest.TestCase):
    def test_private_messages_never_exported_but_errors_preserved(self):
        text = '''TypeError: password=super-secret user=private-person
Authorization: Bearer hidden-bearer
https://private-server.example/stream?api_key=secret-api-key
File "/home/private-person/plugin.py", line 12345, in login
HTTP Error 403: server rejected super-secret
status_code=500
ConnectionError: http://user:password@private-server.example
'''
        summary = report._efsr_summary(text)
        self.assertIn('TypeError: 1', summary)
        self.assertIn('ConnectionError: 1', summary)
        self.assertIn('HTTP 403: 1', summary)
        self.assertIn('HTTP 500: 1', summary)
        self.assertIn('plugin.py Zeilen: 12345', summary)
        for secret in ('super-secret', 'private-person', 'hidden-bearer', 'private-server', 'secret-api-key', 'password'):
            self.assertNotIn(secret, summary)

    def test_snapshot_only_reads_fixed_metadata_and_allowlisted_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'etc').mkdir()
            (root / 'proc/stb/info').mkdir(parents=True)
            (root / 'proc/stb/info/model').write_text('dreamone\n')
            (root / 'etc/image-version').write_text('distro=openatv\nversion=7.6.0\nfeedsurl=https://secret.example\ncreator=private\n')
            logs = root / 'logs'
            logs.mkdir()
            (logs / 'embyflow_login.log').write_text('NameError: hidden-password\n')
            (logs / 'unknown.log').write_text('TypeError: unrelated')
            text = report._efsr_collect('2026-RCDEV-TEST', 2026101803, {'LCD-Zeitfix': False}, root, logs)
            for expected in ('dreamone', 'openatv', '7.6.0', 'NameError: 1', 'LCD-Zeitfix: aus'):
                self.assertIn(expected, text)
            for forbidden in ('hidden-password', 'secret.example', 'creator=', 'unknown.log', 'TypeError: 1'):
                self.assertNotIn(forbidden, text)
            self.assertLess(len(text), 16000)

    def test_tail_bounded_and_symlinks_and_fifos_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'large.log'
            path.write_text('A' * 200000 + 'END')
            text = report._efsr_read(path)
            self.assertEqual(len(text), 65536)
            self.assertTrue(text.endswith('END'))
            link = root / 'link'
            link.symlink_to(path)
            fifo = root / 'fifo'
            os.mkfifo(fifo)
            for unsafe in (link, fifo):
                with self.assertRaises(OSError):
                    report._efsr_read(unsafe)

    def test_atomic_private_report_replaces_symlink_without_touching_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'original'
            original.write_text('must survive')
            target = root / 'report.txt'
            target.symlink_to(original)
            report._efsr_write(target, 'report\n')
            self.assertEqual(original.read_text(), 'must survive')
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_text(), 'report\n')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(root.glob('.embyflow-support-*')), [])

    def test_no_errors_and_no_logs_not_reported_as_success(self):
        self.assertIn('Keine erkannten Fehlerarten', report._efsr_summary('secret arbitrary text'))
        with tempfile.TemporaryDirectory() as directory:
            text = report._efsr_collect('test', 1, {}, directory, directory)
            self.assertIn('nicht vorhanden', text)
            self.assertIn('bedeuten nicht Fehlerfreiheit', text)


class UI(unittest.TestCase):
    def setUp(self):
        class Settings(dict):
            skin = '<screen name="Settings" size="1920,1080"><eLabel text="MUSIK"/></screen>'
            def __init__(self, session):
                self.session = session
                self['actions'] = {'blue': self.show_help, 'green': 'save', 'yellow': 'connection'}
            def show_help(self):
                self.session.open('existing music screen')
        self.settings = Settings
        self.ns = {'EmbyFlowAdvancedSettingsNeon': Settings, 'sx': int, 'sy': int, 'sf': int,
                   'ActionMap': lambda contexts, actions, priority: (contexts, actions, priority),
                   'config': types.SimpleNamespace(embyflow=types.SimpleNamespace()),
                   'PLUGIN_VERSION': 'test', 'PLUGIN_UPDATE_BUILD': 1,
                   '_efsr_collect': Mock(return_value='safe report'), '_efsr_write': Mock(),
                   'MessageBox': types.SimpleNamespace(TYPE_INFO=1, TYPE_ERROR=2),
                   'ChoiceBox': 'existing choice box'}
        exec((HERE / 'ui.py').read_text(), self.ns)
        self.session = Mock()
        self.screen = Settings(self.session)

    def test_blue_extras_keeps_other_actions_and_creates_report(self):
        self.assertEqual(self.screen['actions']['green'], 'save')
        self.assertEqual(self.screen['actions']['yellow'], 'connection')
        self.screen['actions']['blue']()
        call = self.session.openWithCallback.call_args
        self.assertEqual(call.kwargs['list'], [('Musik', 'music'), ('Supportbericht erstellen', 'support')])
        call.args[0](('Supportbericht erstellen', 'support'))
        self.ns['_efsr_write'].assert_called_once_with('/etc/enigma2/embyflow_support.txt', 'safe report')
        self.assertEqual(self.session.open.call_args.kwargs['type'], 1)
        self.assertEqual(ET.fromstring(self.settings.skin).find('eLabel').get('text'), 'EXTRAS')

    def test_music_and_cancel_choices(self):
        self.screen['actions']['blue']()
        callback = self.session.openWithCallback.call_args.args[0]
        callback(None)
        self.session.open.assert_not_called()
        self.ns['_efsr_write'].assert_not_called()
        callback(('Musik', 'music'))
        self.session.open.assert_called_once_with('existing music screen')

    def test_save_error_shows_failure_without_raw_exception(self):
        self.ns['_efsr_write'].side_effect = OSError('private-password')
        self.ns['_efsr_create'](self.screen)
        self.assertEqual(self.session.open.call_args.kwargs['type'], 2)
        self.assertNotIn('private-password', str(self.session.open.call_args))


class Installation(unittest.TestCase):
    def test_packaged_install_preserves_release_backup_and_local_changes(self):
        builder.build()
        ns = {'__name__': 'test_package'}
        exec((ROOT / 'install-support-report.py').read_text(), ns)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plugin.py'
            original = (ROOT / 'EmbyFlowE2_2026101803.py').read_text() + '\n# local LCD fix retained\n'
            path.write_text(original)
            path.chmod(0o644)
            self.assertTrue(ns['install'](path))
            self.assertTrue(path.read_text().startswith(original))
            self.assertEqual(next(path.parent.glob('plugin.py.vor-support-*')).read_text(), original)
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
            self.assertFalse(ns['install'](path))
            compile(path.read_text(), 'installed-plugin', 'exec')

    def test_incompatible_source_rejected_before_install(self):
        with self.assertRaises(RuntimeError):
            builder.patched('pass')

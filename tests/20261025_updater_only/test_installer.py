"""Exercise the shipped repair script; never control a real Enigma2 session."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'updater_only_installer', ROOT / 'tools/repair-updater-only-20261025.py')
REPAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPAIR)


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / 'EmbyFlowE2_BOOTSTRAP_V2_20260919.py').read_bytes()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.plugin = self.folder / 'plugin.py'
        self.plugin.write_bytes(self.original)
        self.lock = self.folder / 'repair.lock'
        self.output = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.output))
        self.run = self.enterContext(patch.object(REPAIR.subprocess, 'run'))
        self.enterContext(patch.object(REPAIR.time, 'sleep'))

    def install(self):
        REPAIR.main(str(self.plugin), str(self.lock))

    def assert_restart_attempted(self):
        self.assertEqual([call.args[0] for call in self.run.call_args_list],
                         [['init', '4'], ['init', '3']])

    def test_success_backup_and_idempotence(self):
        self.install()
        self.assert_restart_attempted()
        backups = list(self.folder.glob('plugin.py.vor-updater-only-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.original)
        self.assertEqual(self.plugin.read_text(), REPAIR.patched(self.original.decode()))
        self.assertFalse(list(self.folder.glob('.updater-only-*')))
        self.run.reset_mock()
        self.install()
        self.run.assert_not_called()

    def test_stop_failure_still_attempts_restart(self):
        self.run.side_effect = [subprocess.CalledProcessError(1, ['init', '4']), None]
        with self.assertRaises(subprocess.CalledProcessError):
            self.install()
        self.assert_restart_attempted()
        self.assertEqual(self.plugin.read_bytes(), self.original)
        self.assertNotIn('FERTIG.', self.output.getvalue())

    def test_replace_failure_and_cleanup_failure_still_restart(self):
        with patch.object(REPAIR.os, 'replace', side_effect=OSError('replace failed')), \
             patch.object(REPAIR.os, 'unlink', side_effect=PermissionError('cleanup failed')):
            with self.assertRaisesRegex(OSError, 'replace failed'):
                self.install()
        self.assert_restart_attempted()
        self.assertEqual(self.plugin.read_bytes(), self.original)
        self.assertIn('cleanup failed', self.output.getvalue())
        self.assertNotIn('FERTIG.', self.output.getvalue())

    def test_backup_failure_never_stops_gui(self):
        with patch.object(REPAIR.os, 'fsync', side_effect=OSError('backup failed')):
            with self.assertRaisesRegex(OSError, 'backup failed'):
                self.install()
        self.run.assert_not_called()
        self.assertEqual(self.plugin.read_bytes(), self.original)

    def test_package_install_changes_only_updater_without_controlling_gui(self):
        settings = self.folder / 'embyflow-login.ini'
        settings.write_bytes(b'private-settings-unchanged')
        REPAIR.main(str(self.plugin), str(self.lock), restart_gui=False)
        self.run.assert_not_called()
        self.assertEqual(settings.read_bytes(), b'private-settings-unchanged')
        self.assertEqual(self.plugin.read_text(), REPAIR.patched(self.original.decode()))
        self.assertIn('manuell neu starten', self.output.getvalue())

    def test_restart_failure_is_not_reported_as_success(self):
        self.run.side_effect = [None, subprocess.CalledProcessError(1, ['init', '3'])]
        with self.assertRaises(subprocess.CalledProcessError):
            self.install()
        self.assert_restart_attempted()
        self.assertNotIn('FERTIG.', self.output.getvalue())


if __name__ == '__main__':
    unittest.main()

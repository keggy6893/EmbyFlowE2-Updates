import ast
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('restore_skyfall', ROOT / 'tools/restore-local-skyfall-20261026.py')
RESTORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESTORE)


class RestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'EmbyFlowE2_2026102502.py').read_bytes()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.plugin = self.folder / 'plugin.py'
        self.plugin.write_bytes(self.source)
        self.movie = self.folder / 'James Bond 007 - Skyfall (2012).ts'
        self.movie.write_bytes(b'original-movie-retained')
        self.settings = self.folder / 'embyflow_local_sources.json'
        self.settings.write_bytes(b'{"sources":[{"path":"/media/net/nas"}]}')
        self.output = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.output))
        self.run = self.enterContext(patch.object(RESTORE.subprocess, 'run'))
        self.enterContext(patch.object(RESTORE.time, 'sleep'))

    def install(self, restart=True):
        return RESTORE.main(str(self.plugin), str(self.folder / 'lock'),
                            restart_gui=restart, movie_path=str(self.movie))

    def test_restores_detail_preserves_player_and_settings(self):
        self.install()
        self.assertEqual([c.args[0] for c in self.run.call_args_list], [['init', '4'], ['init', '3']])
        installed = self.plugin.read_text()
        before = ast.parse(self.source)
        after = ast.parse(installed.split(RESTORE.BEGIN)[0])
        self.assertEqual(ast.dump(before), ast.dump(after))
        self.assertEqual(self.movie.read_bytes(), b'original-movie-retained')
        self.assertEqual(self.settings.read_bytes(), b'{"sources":[{"path":"/media/net/nas"}]}')
        self.assertEqual(next(self.folder.glob('plugin.py.vor-skyfall-lokal-*')).read_bytes(), self.source)
        self.assertIn('EMBYFLOW_ACTIVE_AUDIO_LANGUAGE_V1_BEGIN', installed)
        self.assertIn('EMBYFLOW_LOCAL_SEEK_V1_BEGIN', installed)

    def test_exact_runtime_and_idempotent_patch(self):
        self.assertEqual(RESTORE.RUNTIME, (Path(__file__).parent / 'runtime.py').read_text())
        result = RESTORE.patched(self.source.decode())
        self.assertEqual(RESTORE.patched(result), result)
        ast.parse(result, feature_version=(3, 8))

    def test_previous_direct_skyfall_patch_upgrades_only_known_block(self):
        dashboard = "if 0<=index<len(rows) and rows[index][1].get('_direct_action_ref12')=='local_usb':return self.open_local_media_menu()"
        direct = "if 0<=index<len(rows) and rows[index][1].get('_direct_action_ref12')=='local_usb':return self.session.open(EmbyFlowLocalSkyfallDetail, {'path': _ELS_PATH})"
        previous = self.source.decode().rstrip() + '\n\n' + RESTORE.RUNTIME.replace(dashboard, direct, 1)
        self.plugin.write_text(previous)
        self.install()
        expected = RESTORE.patched(self.source.decode())
        self.assertEqual(self.plugin.read_text(), expected)
        self.assertEqual(next(self.folder.glob('plugin.py.vor-skyfall-lokal-*')).read_text(), previous)

    def test_unknown_existing_skyfall_block_is_not_overwritten(self):
        broken = RESTORE.patched(self.source.decode()).replace("self.open_local_media_menu()", "self.other_local_menu()")
        with self.assertRaisesRegex(RuntimeError, 'Abweichender'):
            RESTORE.patched(broken)

    def test_repeated_install_does_not_restart(self):
        self.install()
        self.run.reset_mock()
        self.install()
        self.run.assert_not_called()
        self.assertEqual(len(list(self.folder.glob('plugin.py.vor-skyfall-lokal-*'))), 1)

    def test_missing_movie_never_changes_plugin_or_stops_gui(self):
        self.movie.unlink()
        with self.assertRaisesRegex(RuntimeError, 'Skyfall-Originaldatei'):
            self.install()
        self.run.assert_not_called()
        self.assertEqual(self.plugin.read_bytes(), self.source)

    def test_unknown_plugin_is_rejected(self):
        self.plugin.write_bytes(b'UNKNOWN = True\n')
        with self.assertRaises(RuntimeError):
            self.install()
        self.run.assert_not_called()

    def test_stop_failure_still_restarts_and_preserves_plugin(self):
        self.run.side_effect = [subprocess.CalledProcessError(1, ['init', '4']), None]
        with self.assertRaises(subprocess.CalledProcessError):
            self.install()
        self.assertEqual([c.args[0] for c in self.run.call_args_list], [['init', '4'], ['init', '3']])
        self.assertEqual(self.plugin.read_bytes(), self.source)

    def test_replace_and_cleanup_failure_still_restart(self):
        with patch.object(RESTORE.os, 'replace', side_effect=OSError('replace failed')), \
             patch.object(RESTORE.os, 'unlink', side_effect=PermissionError('cleanup failed')):
            with self.assertRaisesRegex(OSError, 'replace failed'):
                self.install()
        self.assertEqual([c.args[0] for c in self.run.call_args_list], [['init', '4'], ['init', '3']])
        self.assertEqual(self.plugin.read_bytes(), self.source)

    def test_repair_can_avoid_automatic_restart(self):
        self.install(restart=False)
        self.run.assert_not_called()
        self.assertIn('manuell neu starten', self.output.getvalue())


if __name__ == '__main__':
    unittest.main()

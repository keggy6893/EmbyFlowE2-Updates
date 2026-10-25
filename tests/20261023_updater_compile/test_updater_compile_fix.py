import ast
import builtins
import hashlib
import json
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from updater_compile_fix import repair

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / 'EmbyFlowE2_2026102201.py').read_text(encoding='utf-8')
MANIFEST = json.loads((ROOT / 'update.json').read_text(encoding='utf-8'))
ARTIFACT = ROOT / MANIFEST['download'].rsplit('/', 1)[-1]
FIXED = ARTIFACT.read_text(encoding='utf-8')


class UpdaterCompileTests(unittest.TestCase):
    def test_advertised_artifact_matches_manifest_checksum(self):
        self.assertEqual(hashlib.sha256(ARTIFACT.read_bytes()).hexdigest(),
                         MANIFEST['sha256'].lower())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parent))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.live = self.root / 'plugin.py'
        self.old = b'ORIGINAL = True\n'
        self.new = b'UPDATED = True\n'
        self.live.write_bytes(self.old)
        self.downloads = []
        self.record = []

    def load(self, source, fail_mark=False):
        tree = ast.parse(source)
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('_embyflow_update_install_plugin', '_embyflow_update_check_python_source')]
        # Use the actual updater with isolated temporary stage/backup paths.
        for n in nodes:
            for child in ast.walk(n):
                if isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value.startswith('/tmp/embyflow_update_'):
                    child.value = str(self.root / Path(child.value).name)
        def read(*args):
            self.downloads.append(True)
            return self.new
        def mark(*args):
            if fail_mark:
                raise RuntimeError('Simulated metadata write failure')
            self.record.append(args)
        ns = dict(os=os, PLUGIN_PATH=str(self.root), _embyflow_update_read_url=read,
                  EMBYFLOW_UPDATE_ARTIFACT_MAX_BYTES=10000, EMBYFLOW_UPDATE_ALLOWED_INITIAL_HOSTS=(),
                  _embyflow_update_payload_identity_ok=lambda data: True,
                  _embyflow_update_mark_installed=mark)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'updater-regression', 'exec'), ns)
        return ns['_embyflow_update_install_plugin']

    def manifest(self, digest=None):
        return dict(download='https://example.invalid/update.py', installable=True,
                    sha256=digest or hashlib.sha256(self.new).hexdigest(),
                    version='test', build=1)

    def without_py_compile(self):
        original = builtins.__import__
        def blocked(name, *args, **kwargs):
            if name == 'py_compile':
                raise ModuleNotFoundError("No module named 'py_compile'")
            return original(name, *args, **kwargs)
        return patch('builtins.__import__', blocked)

    def test_old_updater_fails_before_download_and_leaves_live_file_untouched(self):
        install = self.load(SOURCE)
        with self.without_py_compile(), self.assertRaises(ModuleNotFoundError):
            install(self.manifest())
        self.assertFalse(self.downloads)
        self.assertEqual(self.live.read_bytes(), self.old)

    def test_repaired_updater_installs_without_optional_module(self):
        install = self.load(FIXED)
        with self.without_py_compile():
            result = install(self.manifest())
        self.assertTrue(result['ok'])
        self.assertEqual(self.live.read_bytes(), self.new)
        self.assertEqual(Path(result['backup']).read_bytes(), self.old)
        self.assertTrue(self.record)

    def test_bootstrap_repair_enables_old_updater_without_optional_module(self):
        spec = importlib.util.spec_from_file_location(
            'updater_only_repair', ROOT / 'tools/repair-updater-only-20261025.py')
        repair_script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(repair_script)
        old_source = (ROOT / 'EmbyFlowE2_BOOTSTRAP_V2_20260919.py').read_text()
        install = self.load(repair_script.patched(old_source))
        with self.without_py_compile():
            result = install(self.manifest())
        self.assertTrue(result['ok'])
        self.assertEqual(self.live.read_bytes(), self.new)
        self.assertEqual(Path(result['backup']).read_bytes(), self.old)

    def test_syntax_validation_does_not_execute_downloaded_code(self):
        self.new = b"raise RuntimeError('must not execute during validation')\n"
        install = self.load(FIXED)
        with self.without_py_compile():
            self.assertTrue(install(self.manifest())['ok'])

    def test_invalid_syntax_never_replaces_live_plugin(self):
        self.new = b'def broken(:\n'
        install = self.load(FIXED)
        with self.without_py_compile(), self.assertRaises(RuntimeError):
            install(self.manifest())
        self.assertEqual(self.live.read_bytes(), self.old)
        self.assertFalse(self.record)

    def test_checksum_failure_never_replaces_live_plugin(self):
        install = self.load(FIXED)
        with self.without_py_compile(), self.assertRaises(RuntimeError):
            install(self.manifest('0' * 64))
        self.assertEqual(self.live.read_bytes(), self.old)

    def test_later_failure_restores_previous_plugin_without_optional_module(self):
        install = self.load(FIXED, fail_mark=True)
        with self.without_py_compile(), self.assertRaisesRegex(RuntimeError, 'wiederhergestellt'):
            install(self.manifest())
        self.assertEqual(self.live.read_bytes(), self.old)

    def test_all_five_single_file_and_bundle_checks_remain_present(self):
        self.assertEqual(FIXED.count('_embyflow_update_check_python_source('), 6)
        ast.parse(FIXED, feature_version=(3, 8))


if __name__ == '__main__':
    unittest.main(verbosity=2)

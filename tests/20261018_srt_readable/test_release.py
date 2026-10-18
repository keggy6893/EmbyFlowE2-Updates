"""Exercise the actual installed updater with the new default SRT release."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SrtRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load('srt_release_builder', ROOT / '.github/build_srt_2026101803.py')
        cls.data = (ROOT / cls.builder.ARTIFACT).read_bytes()
        cls.manifest = (ROOT / 'update.json').read_bytes()

    def updater(self, directory):
        old = load('download_release_checks', ROOT / 'tests/20261017_movie_download/test_release.py')
        check = old.DownloadReleaseTests()
        check.data = self.data
        check.base_tree = ast.parse((ROOT / 'EmbyFlowE2_2026101802.py').read_bytes())
        return check, check.namespace(directory)

    def test_reproducible_release_hash_identity_and_default(self):
        manifest = json.loads(self.manifest)
        self.assertEqual(self.builder.build_source().encode(), self.data)
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), manifest['sha256'])
        self.assertEqual(manifest['build'], 2026101803)
        assignments = {node.targets[0].id: ast.literal_eval(node.value)
                       for node in ast.parse(self.data).body
                       if isinstance(node, ast.Assign) and len(node.targets) == 1
                       and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id in ('PLUGIN_VERSION', 'PLUGIN_UPDATE_BUILD')}
        self.assertEqual(assignments['PLUGIN_VERSION'], manifest['version'])
        self.assertEqual(assignments['PLUGIN_UPDATE_BUILD'], manifest['build'])
        self.assertIn('font="Regular;58"', self.data.decode())

    def test_only_confirmed_srt_layout_and_release_identity_changed(self):
        def normalize(source):
            return '\n'.join(line for line in source.splitlines()
                             if not line.startswith(('PLUGIN_VERSION = ', 'PLUGIN_UPDATE_BUILD = ', 'PLUGIN_UPDATE_CHANGELOG = ')))
        helper = load('srt_installer', ROOT / 'install-srt-readable.py')
        expected = helper.patched((ROOT / 'EmbyFlowE2_2026101802.py').read_text())
        self.assertEqual(normalize(self.data.decode()), normalize(expected))
        self.assertNotIn(b'EMBYFLOW_AUTOMATIC_THEME_HEARING_V1', self.data)

    def test_current_updater_installs_new_default_with_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            check, ns = self.updater(directory)
            manifest = ns['_embyflow_update_normalize_manifest'](self.manifest)
            self.assertTrue(manifest['installable'])
            self.assertTrue(ns['_embyflow_update_payload_identity_ok'](self.data))
            path = Path(directory) / 'plugin.py'
            old = (ROOT / 'EmbyFlowE2_2026101802.py').read_bytes()
            path.write_bytes(old)
            path.chmod(0o640)
            result = ns['_embyflow_update_install_plugin'](manifest)
            self.assertTrue(result['ok'])
            self.assertEqual(path.read_bytes(), self.data)
            self.assertEqual(Path(result['backup']).read_bytes(), old)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual(check.marked, [(manifest['version'], 2026101803)])

    def test_invalid_hash_cannot_replace_installed_plugin(self):
        with tempfile.TemporaryDirectory() as directory:
            check, ns = self.updater(directory)
            manifest = ns['_embyflow_update_normalize_manifest'](self.manifest)
            manifest['sha256'] = '0' * 64
            path = Path(directory) / 'plugin.py'
            path.write_bytes(b'# existing receiver plugin\n')
            with self.assertRaises(RuntimeError):
                ns['_embyflow_update_install_plugin'](manifest)
            self.assertEqual(path.read_bytes(), b'# existing receiver plugin\n')
            self.assertEqual(check.marked, [])

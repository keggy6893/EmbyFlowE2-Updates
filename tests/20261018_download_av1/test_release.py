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


class Release(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load('av1_release_builder', ROOT / '.github/build_av1_download_2026101805.py')
        cls.data = (ROOT / cls.builder.ARTIFACT).read_bytes()
        cls.manifest = (ROOT / 'update.json').read_bytes()

    def updater(self, directory):
        module = load('download_release_checks', ROOT / 'tests/20261017_movie_download/test_release.py')
        check = module.DownloadReleaseTests()
        check.data = self.data
        check.base_tree = ast.parse((ROOT / 'EmbyFlowE2_2026101804.py').read_bytes())
        return check, check.namespace(directory)

    def test_reproducible_payload_and_matching_identity_hash(self):
        manifest = json.loads(self.manifest)
        self.assertEqual(self.builder.build_source().encode(), self.data)
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), manifest['sha256'])
        self.assertEqual(manifest['build'], 2026101805)
        assignments = {node.targets[0].id: ast.literal_eval(node.value)
                       for node in ast.parse(self.data).body
                       if isinstance(node, ast.Assign) and len(node.targets) == 1
                       and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id in ('PLUGIN_VERSION', 'PLUGIN_UPDATE_BUILD')}
        self.assertEqual(assignments['PLUGIN_VERSION'], manifest['version'])
        self.assertEqual(assignments['PLUGIN_UPDATE_BUILD'], manifest['build'])

    def test_exact_receiver_test_runtime_and_unchanged_previous_playback_code(self):
        previous = (ROOT / 'EmbyFlowE2_2026101804.py').read_text()
        runtime = Path(__file__).with_name('runtime.py').read_text()
        def normalize(source):
            return '\n'.join(line for line in source.splitlines()
                             if not line.startswith(('PLUGIN_VERSION = ', 'PLUGIN_UPDATE_BUILD = ', 'PLUGIN_UPDATE_CHANGELOG = ')))
        self.assertEqual(normalize(self.data.decode()), normalize(previous + '\n\n' + runtime))
        self.assertEqual(self.data.decode().count('# EMBYFLOW_DOWNLOAD_AV1_LOCAL_TEST_V1'), 1)
        self.assertNotIn(b'EMBYFLOW_AUTOMATIC_THEME_HEARING_V1', self.data)
        self.assertNotIn(b'EMBYFLOW_SUPPORT_REPORT_V1', self.data)

    def test_previous_updater_installs_with_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            check, ns = self.updater(directory)
            manifest = ns['_embyflow_update_normalize_manifest'](self.manifest)
            self.assertTrue(manifest['installable'])
            self.assertTrue(ns['_embyflow_update_payload_identity_ok'](self.data))
            target = Path(directory) / 'plugin.py'
            previous = (ROOT / 'EmbyFlowE2_2026101804.py').read_bytes()
            target.write_bytes(previous)
            target.chmod(0o640)
            result = ns['_embyflow_update_install_plugin'](manifest)
            self.assertTrue(result['ok'])
            self.assertEqual(target.read_bytes(), self.data)
            self.assertEqual(Path(result['backup']).read_bytes(), previous)
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
            self.assertEqual(check.marked, [(manifest['version'], 2026101805)])

    def test_checksum_error_cannot_replace_receiver_plugin(self):
        with tempfile.TemporaryDirectory() as directory:
            check, ns = self.updater(directory)
            manifest = ns['_embyflow_update_normalize_manifest'](self.manifest)
            manifest['sha256'] = '0' * 64
            target = Path(directory) / 'plugin.py'
            target.write_bytes(b'# existing plugin\n')
            with self.assertRaises(RuntimeError):
                ns['_embyflow_update_install_plugin'](manifest)
            self.assertEqual(target.read_bytes(), b'# existing plugin\n')
            self.assertEqual(check.marked, [])

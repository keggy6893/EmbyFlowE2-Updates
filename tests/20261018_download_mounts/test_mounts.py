import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Mounts(unittest.TestCase):
    def setUp(self):
        self.ns = {'_efdl_choice_text': lambda entry: ('unchanged', '', '')}
        exec(Path(__file__).with_name('runtime.py').read_text(), self.ns)
        self.os = self.ns['_efmount_os']
        self.devices = {'/': 1, '/media/hdd': 2, '/media/hdd2': 3, '/media/usb': 4}
        self.patches = [
            patch.object(self.os, 'listdir', return_value=['usb', 'hdd2', 'hdd', 'net', 'hdd3']),
            patch.object(self.os.path, 'realpath', side_effect=lambda path: path),
            patch.object(self.os.path, 'ismount', side_effect=lambda path: path in self.devices),
            patch.object(self.os, 'stat', side_effect=lambda path: SimpleNamespace(st_dev=self.devices[path])),
            patch.object(self.os, 'statvfs', return_value=SimpleNamespace(f_flag=0)),
            patch.object(self.os, 'access', return_value=True),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_screenshot_layout_hdd2_is_listed_beside_both_sticks(self):
        self.assertEqual(self.ns['_efdl_targets'](), [(p, p) for p in ('/media/hdd', '/media/hdd2', '/media/usb')])
        self.assertEqual(self.ns['_efdl_choice_text'](('/media/hdd2', '/media/hdd2')),
                         ('Speicher · hdd2', '/media/hdd2', '/media/hdd2/movie/EmbyFlow'))

    def test_readonly_not_offered_for_download_but_still_readable_in_library(self):
        with patch.object(self.os, 'statvfs', return_value=SimpleNamespace(f_flag=self.os.ST_RDONLY)):
            self.assertEqual(self.ns['_efdl_targets'](), [])
            with patch.object(self.os.path, 'isdir', return_value=True):
                self.assertIn(('/media/hdd2/movie/EmbyFlow', 'hdd2'), self.ns['_eflib_roots']())

    def test_flash_and_duplicate_filesystems_and_unmounted_directories_excluded(self):
        self.devices['/media/hdd'] = 1
        self.devices['/media/usb'] = 3
        self.assertEqual(self.ns['_efdl_targets'](), [('/media/hdd2', '/media/hdd2')])

    def test_disappearing_disk_does_not_hide_others(self):
        def info(path):
            if path == '/media/hdd2': raise OSError('removed')
            return SimpleNamespace(st_dev=self.devices[path])
        with patch.object(self.os, 'stat', side_effect=info):
            self.assertEqual(len(self.ns['_efdl_targets']()), 2)

    def test_library_rejects_symlinked_download_directory(self):
        with patch.object(self.os.path, 'isdir', return_value=True):
            with patch.object(self.os.path, 'realpath', side_effect=lambda path: '/elsewhere' if path.endswith('/EmbyFlow') else path):
                self.assertEqual(self.ns['_eflib_roots'](), [])


class Release(unittest.TestCase):
    def test_reproducible_and_current_manifest_and_updater_install(self):
        module = load('mount_builder', ROOT / '.github/build_mounts_2026101804.py')
        data = (ROOT / module.ARTIFACT).read_bytes()
        manifest_bytes = Path(__file__).with_name('update_2026101804.json').read_bytes()
        manifest = json.loads(manifest_bytes)
        self.assertEqual(data, module.build_source().encode())
        self.assertEqual(hashlib.sha256(data).hexdigest(), manifest['sha256'])
        self.assertEqual(manifest['build'], 2026101804)
        old_checks = load('previous_release', ROOT / 'tests/20261017_movie_download/test_release.py')
        check = old_checks.DownloadReleaseTests()
        check.data = data
        check.base_tree = ast.parse((ROOT / 'EmbyFlowE2_2026101803.py').read_bytes())
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            ns = check.namespace(directory)
            normalized = ns['_embyflow_update_normalize_manifest'](manifest_bytes)
            self.assertTrue(normalized['installable'])
            target = Path(directory) / 'plugin.py'
            previous = (ROOT / 'EmbyFlowE2_2026101803.py').read_bytes()
            target.write_bytes(previous)
            result = ns['_embyflow_update_install_plugin'](normalized)
            self.assertTrue(result['ok'])
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(Path(result['backup']).read_bytes(), previous)
            self.assertEqual(check.marked, [(manifest['version'], 2026101804)])

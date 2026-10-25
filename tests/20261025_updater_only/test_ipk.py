"""Inspect and execute the distributed package in a private fake filesystem."""
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('repair_package', ROOT / 'ipk/build_updater_repair.py')
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


def members(ipk, part):
    raw = subprocess.check_output(['ar', 'p', str(ipk), part + '.tar.gz'])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        return {m.name.lstrip('./'): (m, archive.extractfile(m).read()) for m in archive}


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ipk = PACKAGE.DIRECTORY / (PACKAGE.PACKAGE + '_' + PACKAGE.VERSION + '_all.ipk')
        cls.data = members(cls.ipk, 'data')
        cls.control = members(cls.ipk, 'control')

    def test_manifest_and_exact_shipped_source(self):
        manifest = json.loads((PACKAGE.DIRECTORY / 'release.json').read_text())
        self.assertEqual(hashlib.sha256(self.ipk.read_bytes()).hexdigest(), manifest['sha256'])
        source = self.data[PACKAGE.INSTALL_DIR + 'repair.py'][1]
        self.assertEqual(source, (ROOT / 'tools/repair-updater-only-20261025.py').read_bytes())
        self.assertEqual(hashlib.sha256(source).hexdigest(), manifest['source_sha256'])
        ast.parse(source, feature_version=(3, 8))

    def test_no_live_plugin_settings_bytecode_or_remove_scripts(self):
        self.assertEqual(set(self.data), {PACKAGE.INSTALL_DIR + 'repair.py', PACKAGE.INSTALL_DIR + 'README.md'})
        self.assertEqual(set(self.control), {'control', 'postinst'})
        for name, (member, _) in {**self.data, **self.control}.items():
            self.assertTrue(member.isfile())
            self.assertEqual(member.uid, 0)
            self.assertEqual(member.mode, 0o755 if name == 'postinst' else 0o644)
        control = self.control['control'][1].decode()
        self.assertIn('Depends: enigma2, python3-core\n', control)
        self.assertNotIn('python3-compile', control)

    def run_postinst(self, source, offline=None):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            plugin = folder / 'plugin.py'
            plugin.write_bytes(source)
            settings = folder / 'settings.ini'
            settings.write_bytes(b'credentials-and-settings-retained')
            repair = folder / 'repair.py'
            payload = self.data[PACKAGE.INSTALL_DIR + 'repair.py'][1].decode()
            payload = payload.replace('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py', str(plugin))
            payload = payload.replace('/etc/enigma2/embyflow-download-quota.json.lock', str(folder / 'lock'))
            repair.write_text(payload)
            postinst = self.control['postinst'][1].decode().replace(
                '/usr/share/embyflow-updater-repair/repair.py', str(repair))
            env = dict(os.environ)
            env.pop('D', None)
            env.pop('IPKG_INSTROOT', None)
            if offline:
                env[offline] = tmp
            result = subprocess.run(['sh', '-c', postinst], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(settings.read_bytes(), b'credentials-and-settings-retained')
            backups = [p.read_bytes() for p in folder.glob('plugin.py.vor-updater-only-*')]
            return result, plugin.read_bytes(), backups

    def test_real_postinst_repairs_old_plugin_without_gui_commands(self):
        original = (ROOT / 'EmbyFlowE2_BOOTSTRAP_V2_20260919.py').read_bytes()
        result, actual, backups = self.run_postinst(original)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('manuell neu starten', result.stdout)
        self.assertNotEqual(actual, original)
        self.assertEqual(backups, [original])
        before, after = ast.parse(original), ast.parse(actual)
        for tree in (before, after):
            tree.body = [n for n in tree.body if getattr(n, 'name', None) != '_embyflow_update_install_plugin']
        self.assertEqual(ast.dump(before), ast.dump(after))

    def test_already_fixed_release_is_preserved(self):
        original = (ROOT / 'EmbyFlowE2_2026102402.py').read_bytes()
        result, actual, backups = self.run_postinst(original)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(actual, original)
        self.assertEqual(backups, [])

    def test_unknown_plugin_fails_without_success_message(self):
        original = b'UNKNOWN = True\n'
        result, actual, backups = self.run_postinst(original)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('STOPP:', result.stdout)
        self.assertNotIn('Updater geprueft/repariert.', result.stdout)
        self.assertEqual(actual, original)
        self.assertEqual(backups, [])

    def test_offline_root_never_modifies_host(self):
        for variable in ('D', 'IPKG_INSTROOT'):
            with self.subTest(variable=variable):
                original = b'UNKNOWN = True\n'
                result, actual, backups = self.run_postinst(original, offline=variable)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(actual, original)
                self.assertEqual(backups, [])

    def test_rebuild_is_reproducible(self):
        original = self.ipk.read_bytes()
        PACKAGE.build()
        self.assertEqual(self.ipk.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()

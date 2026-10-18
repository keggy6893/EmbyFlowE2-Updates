from pathlib import Path
import tempfile
import unittest

import install_test
from test_pgs import ROOT, PATCH
from test_auto import AUTO


class CompleteInstallerTests(unittest.TestCase):
    def setUp(self):
        self.base = (ROOT / 'EmbyFlowE2_2026101704.py').read_text()

    def test_embedded_code_matches_tested_sources(self):
        self.assertEqual(install_test.NATIVE_PATCH, PATCH)
        self.assertEqual(install_test.AUTO_PATCH, AUTO)

    def test_base_and_local_additions_get_complete_test(self):
        for original in (self.base, self.base + '\n# local receiver feature\nLOCAL_FEATURE=True\n'):
            output = install_test.patched(original, PATCH, AUTO)
            self.assertTrue(output.startswith(original))
            self.assertEqual(output.count(install_test.NATIVE_MARKER), 1)
            self.assertEqual(output.count(install_test.AUTO_MARKER), 1)
            self.assertEqual(install_test.patched(output, PATCH, AUTO), output)

    def test_v1_and_v2_upgrade_preserve_existing_code(self):
        v1 = PATCH.replace(install_test.PARENT_MARKER + '\n', '', 1).replace(
            "    widget = getattr(self, 'instance', None)",
            "    widget = getattr(window, 'instance', None)", 1)
        for patch in (v1, PATCH):
            result = install_test.patched(self.base + '\n' + patch, PATCH, AUTO)
            self.assertTrue(result.startswith(self.base))
            self.assertIn(install_test.PARENT_MARKER, result)
            self.assertIn("widget = getattr(self, 'instance', None)", result.partition(install_test.NATIVE_MARKER)[2])
            self.assertEqual(result.count(install_test.AUTO_MARKER), 1)

    def test_wrong_base_and_malformed_v1_do_not_install(self):
        for source in ('', self.base + '\n' + install_test.NATIVE_MARKER):
            with self.assertRaises(RuntimeError): install_test.patched(source, PATCH, AUTO)

    def test_real_install_backup_permissions_and_repeat_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'plugin.py'
            path.write_text(self.base)
            path.chmod(0o640)
            install_test.install(path, PATCH, AUTO)
            backup = next(path.parent.glob('*.vor-pgs-test-*'))
            self.assertEqual(backup.read_text(), self.base)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            expected = path.read_bytes()
            install_test.install(path, PATCH, AUTO)
            self.assertEqual(path.read_bytes(), expected)
            self.assertEqual(len(list(path.parent.glob('*.vor-pgs-test-*'))), 1)

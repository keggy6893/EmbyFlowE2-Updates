"""Offline migration tests; must never touch any real Enigma2 installation."""
import hashlib
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from install_bootstrap_stage1 import stage1_preflight, install_stage1_in_offline_package, BootstrapInstallError


class StageOneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name) / "Plugins" / "Extensions" / "EmbyFlowE2"
        self.root.mkdir(parents=True)
        for path in (self.root.parent.parent / "__init__.py", self.root.parent / "__init__.py"):
            path.write_bytes(b"")
        (self.root / "__init__.py").write_bytes(b'"""Preserved initializer."""\nKEEP = True\n')
        (self.root / "plugin.py").write_bytes(b"VERSION = 1\n")

    def test_guard_first_and_original_plugin_untouched(self):
        before = (self.root / "plugin.py").read_bytes()
        _, files, expected = stage1_preflight(self.root)
        result = install_stage1_in_offline_package(self.root, expected_initializer_sha256=expected)
        self.assertTrue(result["guard_installed"])
        self.assertEqual((self.root / "plugin.py").read_bytes(), before)
        self.assertEqual((self.root / "__init__.py.embyflow-stage1-backup").read_bytes(),
                         b'"""Preserved initializer."""\nKEEP = True\n')
        self.assertEqual((self.root / "startup_recovery_guard.py").read_bytes(), files["startup_recovery_guard.py"])
        probe = subprocess.run([sys.executable, "-c",
                                "from Plugins.Extensions.EmbyFlowE2 import plugin\n"
                                "from Plugins.Extensions import EmbyFlowE2\n"
                                "assert plugin.VERSION == 1\n"
                                "assert EmbyFlowE2.KEEP\n"],
                               env={"PYTHONPATH": str(self.root.parents[2])}, capture_output=True, text=True)
        self.assertEqual(probe.returncode, 0, probe.stderr)

    def test_reject_modified_initializer(self):
        _, _, expected = stage1_preflight(self.root)
        (self.root / "__init__.py").write_bytes(b"changed = True\n")
        with self.assertRaisesRegex(BootstrapInstallError, "changed since"):
            install_stage1_in_offline_package(self.root, expected_initializer_sha256=expected)
        self.assertFalse((self.root / "startup_recovery_guard.py").exists())

    def test_second_install_is_rejected(self):
        _, _, digest = stage1_preflight(self.root)
        install_stage1_in_offline_package(self.root, expected_initializer_sha256=digest)
        with self.assertRaisesRegex(BootstrapInstallError, "already present"):
            stage1_preflight(self.root)

    def test_reject_symlinked_initializer(self):
        original = self.root / "__init__.py"
        original.unlink()
        original.symlink_to(self.root / "plugin.py")
        with self.assertRaisesRegex(BootstrapInstallError, "initializer"):
            stage1_preflight(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Crash recovery tests using the real multi-file transaction journal."""
import hashlib
import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from startup_recovery_guard import recover_before_plugin_import, StartupRecoveryError
from update_coordinator import apply_release

def manifest(files):
    return {"schema": 2, "artifact_type": "python_bundle", "version": "dev",
            "build": 2026111610,
            "files": [{"path": name, "sha256": hashlib.sha256(content).hexdigest()}
                      for name, content in files.items()]}


class StartupGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / "plugin.py").write_bytes(b"old = True\n")

    def test_clean_start_does_not_touch_plugin(self):
        self.assertEqual(recover_before_plugin_import(self.root), 0)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"old = True\n")

    def test_aborted_install_recovered_before_plugin_import(self):
        candidate = {"plugin.py": b"from .new_module import function\n",
                     "new_module.py": b"def function(): return True\n"}
        with self.assertRaises(SystemExit):
            apply_release(self.root, manifest(candidate), candidate, crash_after=1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), candidate["plugin.py"])
        self.assertEqual(recover_before_plugin_import(self.root), 1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"old = True\n")
        self.assertFalse((self.root / "new_module.py").exists())

    def test_multiple_unmodified_helper_modules_are_not_needed_for_recovery(self):
        candidate = {
            "plugin.py": b"broken = 1\n",
            "refactor_modules/update_coordinator.py": b"bad new code\n",
            "refactor_modules/transactional_bundle.py": b"bad new code\n",
        }
        with self.assertRaises(Exception):
            # Syntax validation must prevent install before any replacement.
            apply_release(self.root, manifest(candidate), candidate)
        self.assertEqual(recover_before_plugin_import(self.root), 0)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"old = True\n")

    def test_startup_guard_refuses_corrupt_backup(self):
        candidate = {"plugin.py": b"new = True\n"}
        with self.assertRaises(SystemExit):
            apply_release(self.root, manifest(candidate), candidate, crash_after=1)
        stage = next(self.root.glob(".embyflow-txn-*"))
        (stage / "old" / "plugin.py").write_bytes(b"wrong\n")
        with self.assertRaisesRegex(StartupRecoveryError, "backup"):
            recover_before_plugin_import(self.root)
        self.assertTrue(stage.exists())

    def test_committed_install_is_kept(self):
        candidate = {"plugin.py": b"new = True\n"}
        apply_release(self.root, manifest(candidate), candidate)
        self.assertEqual(recover_before_plugin_import(self.root), 0)
        self.assertEqual((self.root / "plugin.py").read_bytes(), candidate["plugin.py"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

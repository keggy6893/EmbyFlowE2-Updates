"""Demonstrate stage-one crash states using an isolated synthetic package."""
import hashlib
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_stable_bootstrap import bootstrap_files
from install_bootstrap_stage1 import _atomic_bytes
from reconcile_bootstrap_stage1 import (
    Stage1RecoveryError, inspect_stage1, resume_stage1_offline,
)


class StageOneCrashTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.old_init = b'"""Original initializer."""\nMARKER = "original"\n'
        self.old_plugin = b"VERSION = 1\n"
        (self.root / "__init__.py").write_bytes(self.old_init)
        (self.root / "plugin.py").write_bytes(self.old_plugin)
        self.expected = bootstrap_files(self.old_init.decode())
        self.init_hash = hashlib.sha256(self.old_init).hexdigest()
        self.plugin_hash = hashlib.sha256(self.old_plugin).hexdigest()

    def _inject(self, stage):
        if stage >= 1:
            _atomic_bytes(self.root / "__init__.py.embyflow-stage1-backup", self.old_init)
        if stage >= 2:
            _atomic_bytes(self.root / "startup_recovery_guard.py", self.expected["startup_recovery_guard.py"])
        if stage >= 3:
            _atomic_bytes(self.root / "__init__.py", self.expected["__init__.py"])

    def _resume(self):
        return resume_stage1_offline(
            self.root,
            original_sha256=self.init_hash,
            plugin_sha256=self.plugin_hash,
            atomic_writer=_atomic_bytes,
        )

    def test_before_backup_is_unchanged(self):
        self.assertEqual(inspect_stage1(self.root)["state"], "not_started")
        self.assertEqual((self.root / "__init__.py").read_bytes(), self.old_init)

    def test_after_backup_recovers_to_activated(self):
        self._inject(1)
        self.assertEqual(inspect_stage1(self.root)["state"], "backup_only")
        self.assertTrue(self._resume()["changed"])
        self.assertEqual(inspect_stage1(self.root)["state"], "activated")
        self.assertEqual((self.root / "__init__.py").stat().st_mode & 0o777, 0o644)
        self.assertEqual((self.root / "plugin.py").read_bytes(), self.old_plugin)

    def test_after_guard_recovers_to_activated(self):
        self._inject(2)
        self.assertEqual(inspect_stage1(self.root)["state"], "guard_ready")
        self.assertTrue(self._resume()["changed"])
        self.assertEqual(inspect_stage1(self.root)["state"], "activated")

    def test_after_initializer_replacement_is_idempotent(self):
        self._inject(3)
        self.assertEqual(inspect_stage1(self.root)["state"], "activated")
        self.assertFalse(self._resume()["changed"])
        self.assertEqual((self.root / "plugin.py").read_bytes(), self.old_plugin)

    def test_reject_corrupt_guard(self):
        self._inject(2)
        (self.root / "startup_recovery_guard.py").write_bytes(b"untrusted\n")
        with self.assertRaisesRegex(Stage1RecoveryError, "digest mismatch"):
            inspect_stage1(self.root)

    def test_reject_changed_initializer(self):
        self._inject(2)
        (self.root / "__init__.py").write_bytes(b"something_else = True\n")
        with self.assertRaisesRegex(Stage1RecoveryError, "Initializer changed"):
            self._resume()

    def test_reject_changed_plugin(self):
        self._inject(2)
        (self.root / "plugin.py").write_bytes(b"VERSION = 2\n")
        with self.assertRaisesRegex(Stage1RecoveryError, "Plugin differs"):
            self._resume()

    def test_reject_activated_without_guard(self):
        self._inject(3)
        (self.root / "startup_recovery_guard.py").unlink()
        with self.assertRaisesRegex(Stage1RecoveryError, "active without guard"):
            inspect_stage1(self.root)

    def test_reject_symlinked_backup(self):
        self._inject(1)
        backup = self.root / "__init__.py.embyflow-stage1-backup"
        backup.unlink()
        backup.symlink_to(self.root / "plugin.py")
        with self.assertRaisesRegex(Stage1RecoveryError, "Unsafe"):
            inspect_stage1(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)

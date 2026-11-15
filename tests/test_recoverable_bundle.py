"""Crash recovery tests for experimental EmbyFlowE2 multi-file installer."""
import hashlib
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from recoverable_bundle import install_recoverable, recover_pending, BundleError


def digests(files):
    return {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}


class RecoverableTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = pathlib.Path(td.name)
        (self.root / "plugin.py").write_bytes(b"old_plugin = True\n")
        (self.root / "other.txt").write_text("USER DATA")
        self.files = {
            "plugin.py": b"new_plugin = True\n",
            "refactor_modules/local_media_utils.py": b"def title(x): return x\n",
        }

    def test_normal_install(self):
        self.assertEqual(install_recoverable(self.root, self.files, digests(self.files)), 2)
        self.assertEqual((self.root / "plugin.py").read_bytes(), self.files["plugin.py"])
        self.assertEqual((self.root / "refactor_modules/local_media_utils.py").read_bytes(), self.files["refactor_modules/local_media_utils.py"])
        self.assertEqual((self.root / "other.txt").read_text(), "USER DATA")
        self.assertEqual(recover_pending(self.root), 0)
        self.assertEqual(list(self.root.glob(".embyflow-txn-*")), [])

    def test_crash_after_first_replace_and_recover(self):
        with self.assertRaises(SystemExit):
            install_recoverable(self.root, self.files, digests(self.files), crash_after=1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), self.files["plugin.py"])
        self.assertEqual(len(list(self.root.glob(".embyflow-txn-*"))), 1)
        self.assertEqual(recover_pending(self.root), 1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"old_plugin = True\n")
        self.assertFalse((self.root / "refactor_modules/local_media_utils.py").exists())
        self.assertEqual((self.root / "other.txt").read_text(), "USER DATA")
        self.assertEqual(recover_pending(self.root), 0)

    def test_crash_after_all_replacements_and_recover(self):
        with self.assertRaises(SystemExit):
            install_recoverable(self.root, self.files, digests(self.files), crash_after=2)
        self.assertTrue((self.root / "refactor_modules/local_media_utils.py").exists())
        self.assertEqual(recover_pending(self.root), 1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"old_plugin = True\n")
        self.assertFalse((self.root / "refactor_modules/local_media_utils.py").exists())

    def test_block_second_update_while_recovery_pending(self):
        with self.assertRaises(SystemExit):
            install_recoverable(self.root, self.files, digests(self.files), crash_after=1)
        with self.assertRaises(BundleError):
            install_recoverable(self.root, self.files, digests(self.files))
        recover_pending(self.root)
        self.assertEqual(install_recoverable(self.root, self.files, digests(self.files)), 2)

    def test_tampered_backup_fails_closed(self):
        with self.assertRaises(SystemExit):
            install_recoverable(self.root, self.files, digests(self.files), crash_after=1)
        stage = next(self.root.glob(".embyflow-txn-*"))
        (stage / "old" / "plugin.py").write_bytes(b"CORRUPTED")
        with self.assertRaises(BundleError):
            recover_pending(self.root)
        self.assertTrue(stage.exists(), "Do not erase the only recovery record")

    def test_recovery_rejects_symlink_target(self):
        with self.assertRaises(SystemExit):
            install_recoverable(self.root, self.files, digests(self.files), crash_after=1)
        (self.root / "plugin.py").unlink()
        outside = self.root.parent / (self.root.name + "-outside.py")
        outside.write_bytes(b"never touch\n")
        self.addCleanup(outside.unlink, missing_ok=True)
        (self.root / "plugin.py").symlink_to(outside)
        with self.assertRaises(BundleError):
            recover_pending(self.root)
        self.assertEqual(outside.read_bytes(), b"never touch\n")

    def test_sha_and_syntax_error_no_change(self):
        with self.assertRaises(BundleError):
            install_recoverable(self.root, self.files, {k: "0"*64 for k in self.files})
        bad = {"plugin.py": b"def broken(\n"}
        with self.assertRaises(BundleError):
            install_recoverable(self.root, bad, digests(bad))
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"old_plugin = True\n")
        self.assertEqual(list(self.root.glob(".embyflow-txn-*")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

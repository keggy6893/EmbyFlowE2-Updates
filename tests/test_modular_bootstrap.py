"""Bootstrap-before-import regression tests for modular Enigma2 design."""
import hashlib
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from modular_bootstrap import startup_preflight, load_synthetic_plugin, BundleError
from update_coordinator import apply_release

def digests(files):
    return {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}

def manifest(files):
    return {"schema": 2, "artifact_type": "python_bundle", "version": "dev", "build": 1,
            "files": [{"path": name, "sha256": digest} for name, digest in digests(files).items()]}

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)
        (self.root / "plugin.py").write_bytes(b"VALUE = 'original'\n")
        self.new = {"plugin.py": b"VALUE = 'updated'\n", "lib/helper.py": b"NEW = True\n"}

    def test_original_plugin_loads(self):
        result = startup_preflight(self.root)
        self.assertEqual(result["restored_transactions"], 0)
        loaded = load_synthetic_plugin(self.root)
        self.assertEqual(loaded.VALUE, "original")

    def test_aborted_install_recovers_before_import(self):
        with self.assertRaises(SystemExit):
            apply_release(self.root, manifest(self.new), self.new, crash_after=1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"VALUE = 'updated'\n")
        loaded = load_synthetic_plugin(self.root)
        self.assertEqual(loaded.VALUE, "original")
        self.assertFalse((self.root / "lib/helper.py").exists())

    def test_committed_install_does_not_rollback(self):
        apply_release(self.root, manifest(self.new), self.new)
        loaded = load_synthetic_plugin(self.root)
        self.assertEqual(loaded.VALUE, "updated")
        self.assertTrue((self.root / "lib/helper.py").is_file())

    def test_preflight_fails_missing_module(self):
        with self.assertRaisesRegex(BundleError, "Required module"):
            startup_preflight(self.root, {"plugin.py": None, "missing.py": None})

    def test_preflight_fails_checksum_mismatch(self):
        with self.assertRaisesRegex(BundleError, "digest differs"):
            startup_preflight(self.root, {"plugin.py": "0"*64})

    def test_preflight_rejects_corrupt_syntax(self):
        (self.root / "plugin.py").write_bytes(b"def bad(\n")
        with self.assertRaisesRegex(BundleError, "Invalid startup module"):
            startup_preflight(self.root)

    def test_missing_recovery_backup_aborts_before_import(self):
        with self.assertRaises(SystemExit):
            apply_release(self.root, manifest(self.new), self.new, crash_after=1)
        stage = next(self.root.glob(".embyflow-txn-*"))
        (stage/"old"/"plugin.py").unlink()
        with self.assertRaises(BundleError):
            load_synthetic_plugin(self.root)

if __name__ == "__main__":
    unittest.main(verbosity=2)

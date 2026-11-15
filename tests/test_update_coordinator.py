"""Contract tests for the development-only modular update coordinator."""
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from update_coordinator import apply_release, parse_manifest, update_lock, recover_on_start, BundleError


def digest(data):
    return hashlib.sha256(data).hexdigest()


def make_manifest(files):
    return {
        "schema": 2,
        "artifact_type": "python_bundle",
        "version": "2026-RC26.10-dev",
        "build": 2026111601,
        "files": [{"path": key, "sha256": digest(val)} for key, val in files.items()],
    }


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = pathlib.Path(folder.name)
        (self.root / "plugin.py").write_bytes(b"previous = 1\n")
        self.files = {
            "plugin.py": b"new_version = 1\n",
            "refactor_modules/local_media_utils.py": b"x = 1\n",
        }
        self.manifest = make_manifest(self.files)

    def test_manifest_and_success(self):
        self.assertEqual(set(parse_manifest(self.manifest)), set(self.files))
        result = apply_release(self.root, self.manifest, self.files)
        self.assertEqual(result, {"restored_transactions": 0, "installed_files": 2})
        self.assertEqual((self.root / "plugin.py").read_bytes(), self.files["plugin.py"])

    def test_manifest_rejects_legacy_without_modifying_files(self):
        legacy = {"artifact_type": "plugin_py", "build": 2026111523, "target": "plugin.py"}
        with self.assertRaises(BundleError):
            apply_release(self.root, legacy, self.files)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"previous = 1\n")

    def test_reject_duplicate_and_unsafe_paths(self):
        for bad in ("../escape.py", "test//bad.py", "/tmp/bad.py"):
            with self.subTest(path=bad):
                m = make_manifest(self.files)
                m["files"][1]["path"] = bad
                with self.assertRaises(BundleError):
                    parse_manifest(m)
        m = make_manifest(self.files)
        m["files"][1]["path"] = "plugin.py"
        with self.assertRaises(BundleError):
            parse_manifest(m)

    def test_reject_invalid_digest_before_install(self):
        m = make_manifest(self.files)
        m["files"][1]["sha256"] = "x" * 64
        with self.assertRaises(BundleError):
            apply_release(self.root, m, self.files)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"previous = 1\n")

    def test_reject_mismatched_payload(self):
        with self.assertRaises(BundleError):
            apply_release(self.root, self.manifest, {"plugin.py": self.files["plugin.py"]})
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"previous = 1\n")

    def test_lock_prevents_second_installer(self):
        with update_lock(self.root):
            with self.assertRaisesRegex(BundleError, "Another EmbyFlowE2"):
                apply_release(self.root, self.manifest, self.files)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"previous = 1\n")

    def test_crash_recovery_before_next_update(self):
        with self.assertRaises(SystemExit):
            apply_release(self.root, self.manifest, self.files, crash_after=1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), self.files["plugin.py"])
        self.assertEqual(recover_on_start(self.root), 1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"previous = 1\n")
        self.assertEqual(apply_release(self.root, self.manifest, self.files)["installed_files"], 2)

    def test_recover_then_install_with_one_lock(self):
        with self.assertRaises(SystemExit):
            apply_release(self.root, self.manifest, self.files, crash_after=1)
        result = apply_release(self.root, self.manifest, self.files)
        self.assertEqual(result, {"restored_transactions": 1, "installed_files": 2})


if __name__ == "__main__":
    unittest.main(verbosity=2)

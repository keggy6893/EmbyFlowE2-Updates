"""Verify the real RC26.9 package and its compatibility with the new updater.

Tests run in a temporary directory. They DO NOT replace the live Enigma2 plugin.
"""
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_receiver_bundle import make_bundle
from update_coordinator import apply_release, parse_manifest, recover_on_start


class RealModularBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dist, cls.manifest = make_bundle()
        cls.files = {item["path"]: (cls.dist / item["path"]).read_bytes()
                     for item in cls.manifest["files"]}

    def test_receiver_ready_relative_import(self):
        candidate = self.files["plugin.py"]
        self.assertEqual(candidate.count(b"from .refactor_modules.local_media_utils import "), 2)
        self.assertNotIn(b"from refactor_modules.local_media_utils import ", candidate)
        compile(candidate, "plugin.py", "exec")
        self.assertEqual(self.files["refactor_modules/__init__.py"], b"")

    def test_v2_manifest_exact_digest(self):
        self.assertEqual(parse_manifest(self.manifest), {
            item["path"]: item["sha256"] for item in self.manifest["files"]
        })
        for item in self.manifest["files"]:
            self.assertEqual(hashlib.sha256(self.files[item["path"]]).hexdigest(), item["sha256"])

    def test_experimental_installer_with_real_code(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "plugin.py").write_bytes(b"previous = 1\n")
            result = apply_release(root, self.manifest, self.files)
            self.assertEqual(result["installed_files"], len(self.files))
            self.assertEqual((root / "plugin.py").read_bytes(), self.files["plugin.py"])
            self.assertEqual(recover_on_start(root), 0)
            self.assertTrue((root / "refactor_modules/local_media_utils.py").exists())

    def test_interruption_rollback_with_real_code(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            previous = b"previous = 1\n"
            (root / "plugin.py").write_bytes(previous)
            with self.assertRaises(SystemExit):
                apply_release(root, self.manifest, self.files, crash_after=2)
            self.assertEqual(recover_on_start(root), 1)
            self.assertEqual((root / "plugin.py").read_bytes(), previous)
            self.assertFalse((root / "refactor_modules/__init__.py").exists())

    def test_official_manifest_stays_legacy(self):
        official = json.loads((ROOT / "update.json").read_text())
        self.assertEqual(official["version"], "2026-RC26.9")
        self.assertEqual(official["artifact_type"], "plugin_py")
        self.assertNotIn("files", official)
        self.assertEqual(official["sha256"],
                         "b7bcf3dc4bbefd4c938b7747258eb8bcbc061be0d303aa0b19c11ec31d7cdbb9")


if __name__ == "__main__":
    unittest.main(verbosity=2)

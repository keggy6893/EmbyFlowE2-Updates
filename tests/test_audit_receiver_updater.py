"""Guard integration assumptions about the real legacy updater."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_receiver_updater import inspect_updater, UpdaterAuditError

class AuditTests(unittest.TestCase):
    def test_real_official_rc269_update_menu_is_legacy(self):
        data = inspect_updater(ROOT / "plugin_2026111523.py")
        self.assertTrue(data["syntax_ok"])
        self.assertTrue(data["gui_installer_wired"])
        self.assertTrue(data["legacy_plugin_py_supported"])
        self.assertTrue(data["existing_tar_gz_supported"])
        self.assertTrue(data["existing_tar_explicit_png_assets"])
        self.assertFalse(data["modular_v2_manifest_supported"])

    def test_reject_unrelated_python(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "plugin.py"
            path.write_text("def nothing(): pass\n", encoding="utf-8")
            with self.assertRaisesRegex(UpdaterAuditError, "Missing updater function"):
                inspect_updater(path)

if __name__ == "__main__":
    unittest.main(verbosity=2)

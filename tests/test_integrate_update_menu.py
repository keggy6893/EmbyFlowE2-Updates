"""Ensure a modular update is a separate path, not a regression for legacy GUI."""
import ast
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from integrate_update_menu import patch_source, MARKER


def isolated_normalizer(code, context):
    module = ast.parse(code)
    node = next(n for n in module.body if isinstance(n, ast.FunctionDef)
                and n.name == "_embyflow_update_normalize_manifest")
    block = ast.Module(body=[node], type_ignores=[])
    exec(compile(block, "<isolated_normalizer>", "exec"), context)
    return context[node.name]


class UpdateMenuBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = (ROOT / "plugin_2026111523.py").read_text(encoding="utf-8")
        cls.after = patch_source(cls.before)
        cls.func = isolated_normalizer(
            cls.after,
            {"json": json, "re": __import__("re"),
             "EMBYFLOW_UPDATE_CHANNEL": "rcdev",
             "EMBYFLOW_UPDATE_ALLOWED_INITIAL_HOSTS": ("raw.githubusercontent.com",),
             "_embyflow_update_https_url": lambda url, hosts: url.startswith("https://raw.githubusercontent.com/")}
        )

    def test_syntax_and_exactly_one_install_path(self):
        self.assertEqual(self.after.count(MARKER), 1)
        self.assertEqual(self.after.count("def _embyflow_update_install_plugin("), 1)
        compile(self.after, "plugin.py", "exec")

    def test_real_legacy_manifest_unchanged(self):
        legacy = json.loads((ROOT / "update.json").read_text())
        m = self.func(json.dumps(legacy).encode())
        self.assertTrue(m["installable"])
        self.assertFalse(m["modular_bundle"])
        self.assertFalse(m["bundle_tar_gz"])
        self.assertIsNone(m["files"])
        self.assertEqual(m["download"], legacy["download"])

    def test_existing_png_tar_bundle_still_supported(self):
        manifest = {
            "version": "RC26.10", "build": 2026111602, "channel": "rcdev",
            "target": "EmbyFlowE2", "artifact_type": "bundle_tar_gz",
            "download": "https://raw.githubusercontent.com/x/y/a.tar.gz",
            "sha256": "a" * 64,
        }
        m = self.func(json.dumps(manifest).encode())
        self.assertTrue(m["installable"])
        self.assertTrue(m["bundle_tar_gz"])
        self.assertFalse(m["modular_bundle"])

    def test_explicit_new_modular_bundle(self):
        manifest = {
            "schema": 2, "version": "RC26.10", "build": 2026111602,
            "channel": "rcdev", "target": "bundle",
            "artifact_type": "python_bundle",
            "files": [{"path": "plugin.py", "sha256": "b" * 64}],
            "download": "https://raw.githubusercontent.com/x/y/pinned.tar.gz",
            "sha256": "a" * 64,
        }
        m = self.func(json.dumps(manifest).encode())
        self.assertTrue(m["installable"])
        self.assertTrue(m["modular_bundle"])
        self.assertFalse(m["bundle_tar_gz"])
        self.assertEqual(m["files"], manifest["files"])

    def test_old_or_unknown_manifest_not_installable(self):
        manifest = {
            "version": "RC26.10", "build": 2026111602,
            "channel": "rcdev", "target": "bundle",
            "artifact_type": "unknown",
            "download": "https://raw.githubusercontent.com/x/y/a.tar.gz",
            "sha256": "a" * 64,
        }
        self.assertFalse(self.func(json.dumps(manifest).encode())["installable"])

    def test_does_not_double_patch(self):
        with self.assertRaisesRegex(ValueError, "already applied"):
            patch_source(self.after)

if __name__ == "__main__":
    unittest.main(verbosity=2)

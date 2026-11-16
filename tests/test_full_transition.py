"""End-to-end offline transition: legacy package -> stable boot -> modular update.

No production receiver interaction, no Enigma2 imports and no official release.
The synthetic plugin models the package-import order and recovery after crash.
"""
import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_updater_sidecars import staged_sidecars
from install_bootstrap_stage1 import install_stage1_in_offline_package, stage1_preflight
from reconcile_bootstrap_stage1 import inspect_stage1
from update_coordinator import apply_release
from modular_tar_bridge import pack_archive, unpack_verified_archive


def make_manifest(files, build=2026111611):
    return {"schema": 2, "artifact_type": "python_bundle", "version": "RC26.9-modular-dev",
            "build": build, "files": [
                {"path": name, "sha256": hashlib.sha256(payload).hexdigest()}
                for name, payload in files.items()
            ]}


class FullMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.root = self.base / "Plugins" / "Extensions" / "EmbyFlowE2"
        self.root.mkdir(parents=True)
        for file in (self.base / "Plugins" / "__init__.py",
                     self.base / "Plugins" / "Extensions" / "__init__.py"):
            file.write_bytes(b"")
        (self.root / "__init__.py").write_text(
            '"""Old extension package."""\nfrom __future__ import absolute_import\nSETTING = "preserved"\n',
            encoding="utf-8"
        )
        (self.root / "plugin.py").write_bytes(b"VERSION = 'legacy-working'\n")

    def _start(self, expected):
        code = (
            "from Plugins.Extensions.EmbyFlowE2 import plugin\n"
            "from Plugins.Extensions import EmbyFlowE2\n"
            "assert EmbyFlowE2.SETTING == 'preserved'\n"
            "assert plugin.VERSION == %r, plugin.VERSION\n" % expected
        )
        environment = dict(os.environ, PYTHONPATH=str(self.base))
        return subprocess.run([sys.executable, "-c", code], capture_output=True,
                              text=True, env=environment)

    def _bootstrap(self):
        _, _, init_hash = stage1_preflight(self.root)
        old = (self.root / "plugin.py").read_bytes()
        result = install_stage1_in_offline_package(self.root, expected_initializer_sha256=init_hash)
        self.assertTrue(result["plugin_untouched"])
        self.assertEqual(inspect_stage1(self.root)["state"], "activated")
        self.assertEqual((self.root / "plugin.py").read_bytes(), old)
        self.assertEqual(self._start("legacy-working").returncode, 0)
        return (self.root / "startup_recovery_guard.py").read_bytes()

    def _bundle(self):
        files = {
            "plugin.py":
                b"from .refactor_modules.local_media_utils import answer\n"
                b"VERSION = 'modular-working' if answer() == 42 else 'wrong'\n",
            "refactor_modules/local_media_utils.py": b"def answer(): return 42\n",
        }
        files.update(staged_sidecars())
        m = make_manifest(files)
        blob = pack_archive(m, files)
        self.assertEqual(unpack_verified_archive(blob, m, hashlib.sha256(blob).hexdigest()), files)
        return m, files

    def test_successful_two_stage_install(self):
        guard = self._bootstrap()
        manifest, files = self._bundle()
        result = apply_release(self.root, manifest, files)
        self.assertEqual(result["installed_files"], len(files))
        self.assertEqual(self._start("modular-working").returncode, 0)
        self.assertEqual((self.root / "startup_recovery_guard.py").read_bytes(), guard)
        self.assertEqual(inspect_stage1(self.root)["state"], "activated")

    def test_crash_after_main_plugin_replace_restores_legacy_on_next_start(self):
        guard = self._bootstrap()
        manifest, files = self._bundle()
        with self.assertRaises(SystemExit):
            apply_release(self.root, manifest, files, crash_after=1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), files["plugin.py"])
        # Parent package imports stable guard FIRST and rolls back broken plugin.
        launched = self._start("legacy-working")
        self.assertEqual(launched.returncode, 0, launched.stderr)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"VERSION = 'legacy-working'\n")
        self.assertEqual((self.root / "startup_recovery_guard.py").read_bytes(), guard)

    def test_crash_after_multiple_replacements_restores_legacy_on_next_start(self):
        self._bootstrap()
        manifest, files = self._bundle()
        with self.assertRaises(SystemExit):
            apply_release(self.root, manifest, files, crash_after=4)
        launched = self._start("legacy-working")
        self.assertEqual(launched.returncode, 0, launched.stderr)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"VERSION = 'legacy-working'\n")

    def test_stable_guard_never_in_update_manifest(self):
        self._bootstrap()
        manifest, _ = self._bundle()
        self.assertNotIn("startup_recovery_guard.py", {f["path"] for f in manifest["files"]})
        self.assertNotIn("__init__.py", {f["path"] for f in manifest["files"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)

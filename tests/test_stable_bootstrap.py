"""Exercise stable pre-import recovery in a synthetic Enigma2 package."""
import hashlib
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_stable_bootstrap import bootstrap_files, patch_initializer
from update_coordinator import apply_release


def manifest(files):
    return {"schema": 2, "artifact_type": "python_bundle", "version": "dev",
            "build": 2026111607,
            "files": [{"path": name, "sha256": hashlib.sha256(data).hexdigest()}
                      for name, data in files.items()]}


class StableBootstrapTests(unittest.TestCase):
    def test_import_order_and_restore_before_plugin_load(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            package = base / "Plugins" / "Extensions" / "EmbyFlowE2"
            package.mkdir(parents=True)
            for init in (base / "Plugins" / "__init__.py", base / "Plugins" / "Extensions" / "__init__.py"):
                init.parent.mkdir(parents=True, exist_ok=True)
                init.write_bytes(b"")
            existing = '"""Old package initializer."""\nfrom __future__ import absolute_import\nSENTINEL = "preserved"\n'
            for name, contents in bootstrap_files(existing).items():
                (package / name).write_bytes(contents)
            (package / "plugin.py").write_bytes(b"old_version = 'good'\n")
            changed = {"plugin.py": b"raise RuntimeError('BROKEN_NEW_PLUGIN_LOADED')\n",
                       "refactor_modules/local_media_utils.py": b"helper = 1\n"}
            with self.assertRaises(SystemExit):
                apply_release(package, manifest(changed), changed, crash_after=1)
            completed = subprocess.run(
                [sys.executable, "-c",
                 "from Plugins.Extensions.EmbyFlowE2 import plugin\n"
                 "from Plugins.Extensions import EmbyFlowE2\n"
                 "assert EmbyFlowE2.SENTINEL == 'preserved'\n"
                 "assert plugin.old_version == 'good'\n"
                 "print('PREIMPORT_RECOVERY_OK')\n"],
                env={"PYTHONPATH": str(base)}, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PREIMPORT_RECOVERY_OK", completed.stdout)
            self.assertEqual((package / "plugin.py").read_bytes(), b"old_version = 'good'\n")

    def test_preserve_future_import_and_docstring(self):
        result = patch_initializer('"""Doc"""\nfrom __future__ import print_function\nx = 1\n')
        compile(result, "__init__.py", "exec")
        self.assertLess(result.index("from __future__ import print_function"), result.index("EMBYFLOW_STABLE"))
        self.assertLess(result.index("EMBYFLOW_STABLE"), result.index("x = 1"))

    def test_double_install_refused(self):
        with self.assertRaises(ValueError):
            patch_initializer(patch_initializer("x = 1\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

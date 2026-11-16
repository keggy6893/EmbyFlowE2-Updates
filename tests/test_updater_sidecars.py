"""Check receiver sidecars import as an Enigma2 extension package."""
import hashlib
import importlib
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_updater_sidecars import staged_sidecars

class PackageImportTests(unittest.TestCase):
    def test_all_sibling_imports_resolve_inside_extension(self):
        contents = staged_sidecars()
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            package = base / "Plugins" / "Extensions" / "EmbyFlowE2"
            package.mkdir(parents=True)
            for parent in (base / "Plugins", base / "Plugins" / "Extensions", package):
                (parent / "__init__.py").write_bytes(b"")
            for path, data in contents.items():
                dest = package / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            sys.path.insert(0, str(base))
            names = ["Plugins", "Plugins.Extensions", "Plugins.Extensions.EmbyFlowE2"]
            try:
                for module in ("transactional_bundle", "recoverable_bundle", "update_coordinator", "modular_tar_bridge"):
                    fqname = "Plugins.Extensions.EmbyFlowE2.refactor_modules." + module
                    loaded = importlib.import_module(fqname)
                    names.append(fqname)
                    self.assertTrue(loaded.__file__.startswith(str(base)))
                bridge = importlib.import_module("Plugins.Extensions.EmbyFlowE2.refactor_modules.modular_tar_bridge")
                files = {"plugin.py": b"foo = 7\n"}
                manifest = {"schema": 2, "artifact_type": "python_bundle", "version": "dev",
                            "build": 2026111605,
                            "files": [{"path": "plugin.py", "sha256": hashlib.sha256(files["plugin.py"]).hexdigest()}]}
                blob = bridge.pack_archive(manifest, files)
                self.assertEqual(bridge.unpack_verified_archive(blob, manifest), files)
            finally:
                sys.path.remove(str(base))
                for name in list(sys.modules):
                    if name == "Plugins" or name.startswith("Plugins."):
                        sys.modules.pop(name, None)

if __name__ == "__main__":
    unittest.main(verbosity=2)

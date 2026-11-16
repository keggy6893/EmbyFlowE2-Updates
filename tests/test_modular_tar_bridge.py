"""Offline security and compatibility checks for modular tar.gz bundles."""
import hashlib
import io
import pathlib
import sys
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from modular_tar_bridge import pack_archive, unpack_verified_archive, install_modular_archive
from update_coordinator import BundleError

FILES = {
    "plugin.py": b"from .refactor_modules.local_media_utils import f\n",
    "refactor_modules/__init__.py": b"",
    "refactor_modules/local_media_utils.py": b"def f(): return 1\n",
}
MANIFEST = {
    "schema": 2,
    "artifact_type": "python_bundle",
    "version": "RC26.9-modular-dev",
    "build": 2026111602,
    "files": [
        {"path": name, "sha256": hashlib.sha256(payload).hexdigest()}
        for name, payload in FILES.items()
    ],
}


def make_raw(items):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, data, kind in items:
            item = tarfile.TarInfo(name)
            item.size = len(data) if kind == "file" else 0
            if kind == "symlink":
                item.type = tarfile.SYMTYPE
                item.linkname = "/etc/passwd"
            archive.addfile(item, io.BytesIO(data) if kind == "file" else None)
    return output.getvalue()


class ModularArchiveTests(unittest.TestCase):
    def test_valid_round_trip_and_install(self):
        blob = pack_archive(MANIFEST, FILES)
        self.assertEqual(unpack_verified_archive(blob, MANIFEST, hashlib.sha256(blob).hexdigest()), FILES)
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "plugin.py").write_bytes(b"old_version = True\n")
            result = install_modular_archive(root, blob, MANIFEST, archive_sha256=hashlib.sha256(blob).hexdigest())
            self.assertEqual(result["installed_files"], 3)
            self.assertEqual((root / "plugin.py").read_bytes(), FILES["plugin.py"])

    def test_reject_wrong_archive_hash(self):
        with self.assertRaisesRegex(BundleError, "Archive SHA256 mismatch"):
            unpack_verified_archive(pack_archive(MANIFEST, FILES), MANIFEST, "0" * 64)

    def test_reject_extra_file_and_path_escape(self):
        for path in ("EmbyFlowE2/../bad.py", "EmbyFlowE2/extra.py"):
            with self.subTest(path=path):
                blob = make_raw([("EmbyFlowE2/" + n, p, "file") for n, p in FILES.items()] +
                                [(path, b"x = 1\n", "file")])
                with self.assertRaisesRegex(BundleError, "Unknown or repeated"):
                    unpack_verified_archive(blob, MANIFEST)

    def test_reject_symlink(self):
        blob = make_raw([("EmbyFlowE2/" + n, p, "file") for n, p in FILES.items()] +
                        [("EmbyFlowE2/evil.py", b"", "symlink")])
        with self.assertRaisesRegex(BundleError, "Unexpected archive member"):
            unpack_verified_archive(blob, MANIFEST)

    def test_reject_missing_file(self):
        blob = make_raw([("EmbyFlowE2/plugin.py", FILES["plugin.py"], "file")])
        with self.assertRaisesRegex(BundleError, "missing required"):
            unpack_verified_archive(blob, MANIFEST)

    def test_reject_digest_mismatch_and_keep_original(self):
        blob = make_raw([("EmbyFlowE2/" + n, (b"bad\n" if n == "plugin.py" else p), "file")
                         for n, p in FILES.items()])
        with tempfile.TemporaryDirectory() as directory:
            original = pathlib.Path(directory) / "plugin.py"
            original.write_bytes(b"old\n")
            with self.assertRaisesRegex(BundleError, "file SHA256 mismatch"):
                install_modular_archive(directory, blob, MANIFEST)
            self.assertEqual(original.read_bytes(), b"old\n")

    def test_reject_duplicate(self):
        blob = make_raw([("EmbyFlowE2/" + n, p, "file") for n, p in FILES.items()] +
                        [("EmbyFlowE2/plugin.py", FILES["plugin.py"], "file")])
        with self.assertRaisesRegex(BundleError, "repeated"):
            unpack_verified_archive(blob, MANIFEST)


if __name__ == "__main__":
    unittest.main(verbosity=2)

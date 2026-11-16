"""Tests for verified pinned GitHub downloads without network access."""
import hashlib
import io
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from bundle_transport import download_bundle, install_downloaded_bundle
from update_coordinator import BundleError

COMMIT = "1234567890abcdef1234567890abcdef12345678"
REPO = "keggy6893/EmbyFlowE2-Updates"
FILES = {
    "plugin.py": b"version = 2\n",
    "refactor_modules/__init__.py": b"",
    "refactor_modules/local_media_utils.py": b"def func(): return 1\n",
}
MANIFEST = {
    "schema": 2,
    "artifact_type": "python_bundle",
    "version": "RC26.9-dev",
    "build": 2026111523,
    "files": [
        {"path": n, "sha256": hashlib.sha256(b).hexdigest()}
        for n, b in FILES.items()
    ],
}


class FakeResponse(io.BytesIO):
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class FakeOpener:
    def __init__(self, payloads):
        self.payloads = payloads
        self.urls = []
    def open(self, url, timeout):
        self.urls.append(url)
        return FakeResponse(self.payloads[url.rsplit("/", 1)[-1]])


class DownloadTests(unittest.TestCase):
    def test_download_validates_and_is_pinned(self):
        opener = FakeOpener({
            "plugin.py": FILES["plugin.py"],
            "__init__.py": b"",
            "local_media_utils.py": FILES["refactor_modules/local_media_utils.py"],
        })
        downloaded = download_bundle(MANIFEST, repository=REPO, commit=COMMIT, opener=opener)
        self.assertEqual(downloaded, FILES)
        self.assertTrue(all(url.startswith("https://raw.githubusercontent.com/" + REPO + "/" + COMMIT + "/")
                            for url in opener.urls))

    def test_hash_mismatch_blocks_all_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root / "plugin.py").write_bytes(b"old\n")
            opener = FakeOpener({
                "plugin.py": b"bad\n",
                "__init__.py": b"",
                "local_media_utils.py": FILES["refactor_modules/local_media_utils.py"],
            })
            with self.assertRaisesRegex(BundleError, "SHA256 mismatch"):
                install_downloaded_bundle(root, MANIFEST, repository=REPO, commit=COMMIT, opener=opener)
            self.assertEqual((root / "plugin.py").read_bytes(), b"old\n")

    def test_full_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root / "plugin.py").write_bytes(b"old\n")
            opener = FakeOpener({
                "plugin.py": FILES["plugin.py"],
                "__init__.py": b"",
                "local_media_utils.py": FILES["refactor_modules/local_media_utils.py"],
            })
            self.assertEqual(
                install_downloaded_bundle(root, MANIFEST, repository=REPO, commit=COMMIT, opener=opener)["installed_files"],
                3,
            )
            self.assertEqual((root / "plugin.py").read_bytes(), FILES["plugin.py"])

    def test_reject_branch_instead_of_commit(self):
        with self.assertRaisesRegex(BundleError, "commit SHA"):
            download_bundle(MANIFEST, repository=REPO, commit="main", opener=FakeOpener({}))

    def test_reject_manifest_without_plugin(self):
        manifest = dict(MANIFEST, files=[MANIFEST["files"][2]])
        with self.assertRaisesRegex(BundleError, "plugin.py"):
            download_bundle(manifest, repository=REPO, commit=COMMIT, opener=FakeOpener({}))


if __name__ == "__main__":
    unittest.main(verbosity=2)

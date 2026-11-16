"""Update routing contracts: existing RC26.9 works unchanged, v2 is opt-in."""
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from update_router import classify_update, route_update, _canonical_manifest
from update_coordinator import BundleError

COMMIT = "1234567890abcdef1234567890abcdef12345678"
PAYLOAD = b"modular = True\n"
BUNDLE = {
    "schema": 2,
    "artifact_type": "python_bundle",
    "version": "dev",
    "build": 2026111602,
    "files": [{"path": "plugin.py", "sha256": hashlib.sha256(PAYLOAD).hexdigest()}],
}
MANIFEST_DIGEST = hashlib.sha256(_canonical_manifest(BUNDLE)).hexdigest()


class FakeResponse(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class FakeOpener:
    def open(self, url, timeout):
        return FakeResponse(PAYLOAD)


class CompatibilityTests(unittest.TestCase):
    def test_official_manifest_routes_to_existing_updater(self):
        official = json.loads((ROOT / "update.json").read_text(encoding="utf-8"))
        self.assertEqual(classify_update(official), "legacy")
        received = []
        result = route_update(None, official, legacy_installer=lambda manifest: received.append(manifest) or "OK")
        self.assertEqual(result, {"kind": "legacy", "result": "OK"})
        self.assertEqual(received, [official])

    def test_bundle_disabled_by_default(self):
        with self.assertRaisesRegex(BundleError, "not been enabled"):
            route_update(None, BUNDLE)

    def test_bundle_rejects_missing_trust(self):
        with self.assertRaisesRegex(BundleError, "digest required"):
            route_update(None, BUNDLE, enable_bundle=True)

    def test_bundle_rejects_untrusted_manifest(self):
        with self.assertRaisesRegex(BundleError, "trust anchor mismatch"):
            route_update(None, BUNDLE, enable_bundle=True, trusted_manifest_sha256="0" * 64)

    def test_bundle_accepts_explicitly_pinned_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "plugin.py").write_bytes(b"old\n")
            result = route_update(root, BUNDLE, enable_bundle=True,
                                  repository="keggy6893/EmbyFlowE2-Updates",
                                  commit=COMMIT,
                                  trusted_manifest_sha256=MANIFEST_DIGEST,
                                  opener=FakeOpener())
            self.assertEqual(result["kind"], "bundle")
            self.assertEqual((root / "plugin.py").read_bytes(), PAYLOAD)

    def test_legacy_requires_callback_and_rejects_non_plugin_target(self):
        official = json.loads((ROOT / "update.json").read_text())
        with self.assertRaisesRegex(BundleError, "callback missing"):
            route_update(None, official)
        with self.assertRaisesRegex(BundleError, "legacy target"):
            classify_update(dict(official, target="../../evil.py"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

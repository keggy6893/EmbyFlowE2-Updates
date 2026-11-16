"""Development-only compatibility dispatcher for legacy and modular EmbyFlowE2 updates.

Do not wire into the live GUI until the old updater integration is reviewed.
Legacy update.json is delegated without modification; experimental v2 releases
require explicit enablement, a pinned commit and independent manifest digest.
"""
import hashlib
import json
from bundle_transport import install_downloaded_bundle
from update_coordinator import BundleError, parse_manifest

LEGACY_TYPE = "plugin_py"
BUNDLE_TYPE = "python_bundle"
MAX_MANIFEST_BYTES = 64 * 1024


def classify_update(manifest):
    """Return a stable choice; never silently convert legacy releases to v2."""
    if isinstance(manifest, dict) and manifest.get("artifact_type") == LEGACY_TYPE:
        if manifest.get("target") != "plugin.py":
            raise BundleError("Unexpected legacy target")
        if type(manifest.get("build")) is not int:
            raise BundleError("Invalid legacy build")
        digest = manifest.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise BundleError("Invalid legacy digest")
        return "legacy"
    parse_manifest(manifest)
    return "bundle"


def _canonical_manifest(manifest):
    if not isinstance(manifest, dict):
        raise BundleError("Manifest must be decoded JSON object")
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def route_update(root, manifest, *, legacy_installer=None, enable_bundle=False,
                 repository=None, commit=None, trusted_manifest_sha256=None, opener=None):
    """Dispatch a release.

    The legacy callback is the existing install path (not reimplemented here).
    A v2 bundle must be independently trusted; downloading a manifest and
    blindly trusting its self-declared hashes would not ensure authenticity.
    """
    kind = classify_update(manifest)
    if kind == "legacy":
        if not callable(legacy_installer):
            raise BundleError("Legacy updater callback missing")
        return {"kind": "legacy", "result": legacy_installer(manifest)}
    if not enable_bundle:
        raise BundleError("Modular updater has not been enabled")
    if not isinstance(trusted_manifest_sha256, str) or len(trusted_manifest_sha256) != 64:
        raise BundleError("Pinned manifest digest required")
    try:
        int(trusted_manifest_sha256, 16)
    except ValueError as exc:
        raise BundleError("Invalid pinned manifest digest") from exc
    raw = _canonical_manifest(manifest)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise BundleError("Manifest exceeds size limit")
    if hashlib.sha256(raw).hexdigest() != trusted_manifest_sha256.lower():
        raise BundleError("Manifest trust anchor mismatch")
    result = install_downloaded_bundle(
        root, manifest, repository=repository, commit=commit, opener=opener
    )
    return {"kind": "bundle", "result": result}

"""Development-only verified transport for EmbyFlowE2 multi-file releases.

This module does not touch the plugin on import, does not replace the existing
single-file updater, and requires an independently trusted manifest.
Only download files from an explicitly pinned raw.githubusercontent.com commit.
"""
import hashlib
import re
import urllib.parse
import urllib.request

from update_coordinator import (
    BundleError, MAX_PAYLOAD_BYTES, apply_release, parse_manifest,
)

RAW_HOST = "raw.githubusercontent.com"
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
DEFAULT_TIMEOUT = 20
MAX_MANIFEST_BYTES = 64 * 1024


def _pinned_url(repository, commit, name):
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise BundleError("Invalid GitHub repository name")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        raise BundleError("A full 40-character commit SHA is required")
    # Path safety follows the v2 manifest validation in parse_manifest.
    parts = name.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise BundleError("Invalid download path")
    safe_name = "/".join(urllib.parse.quote(part, safe="") for part in parts)
    return "https://%s/%s/%s/%s" % (RAW_HOST, repository, commit, safe_name)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BundleError("Redirects are not allowed for update payloads")


def _fetch_verified(url, max_bytes, opener, timeout):
    try:
        with opener.open(url, timeout=timeout) as response:
            if getattr(response, "status", 200) != 200:
                raise BundleError("Unexpected download HTTP status")
            data = response.read(max_bytes + 1)
    except BundleError:
        raise
    except (OSError, ValueError) as exc:
        raise BundleError("Failed downloading update payload") from exc
    if len(data) > max_bytes:
        raise BundleError("Update download exceeds allowed size")
    return data


def download_bundle(manifest, *, repository, commit, opener=None, timeout=DEFAULT_TIMEOUT):
    """Fetch all files, fail closed, verify all digests before returning bytes.

    Manifest must be supplied by a trusted caller. A self-declared hash from an
    untrusted manifest is NOT an authenticity guarantee.
    """
    expected = parse_manifest(manifest)
    if opener is None:
        opener = urllib.request.build_opener(_NoRedirect)
    downloaded = {}
    remaining = MAX_PAYLOAD_BYTES
    for name, expected_digest in expected.items():
        url = _pinned_url(repository, commit, name)
        data = _fetch_verified(url, remaining, opener, timeout)
        if hashlib.sha256(data).hexdigest() != expected_digest:
            raise BundleError("SHA256 mismatch: " + name)
        downloaded[name] = data
        remaining -= len(data)
    return downloaded


def install_downloaded_bundle(root, manifest, *, repository, commit, opener=None):
    """Install only after every payload has been downloaded and verified."""
    files = download_bundle(manifest, repository=repository, commit=commit, opener=opener)
    return apply_release(root, manifest, files)

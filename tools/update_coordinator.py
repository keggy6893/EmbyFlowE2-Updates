"""Experimental update coordinator for EmbyFlowE2 modular releases.

NOT wired into the production plugin.py updater. The caller must download
the listed file payloads over a trusted transport before invoking apply_release.

This coordinates the crash-recovery prototype and rejects parallel installs.
It deliberately does not import Enigma2, require py_compile, or alter update.json.
"""
import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path

from recoverable_bundle import BundleError, install_recoverable, recover_pending
from transactional_bundle import _relative_name

LOCK_NAME = ".embyflow-update.lock"
MAX_FILES = 128
MAX_PAYLOAD_BYTES = 32 * 1024 * 1024


def parse_manifest(value):
    """Validate a proposed v2 multi-file manifest (no legacy conversion)."""
    if isinstance(value, (bytes, str)):
        try:
            value = json.loads(value)
        except (ValueError, UnicodeError) as exc:
            raise BundleError("Invalid JSON manifest") from exc
    if not isinstance(value, dict) or value.get("schema") != 2:
        raise BundleError("Not a v2 bundle manifest")
    if value.get("artifact_type") != "python_bundle":
        raise BundleError("Unsupported artifact type")
    if not isinstance(value.get("version"), str) or not value["version"].strip():
        raise BundleError("Invalid bundle version")
    build = value.get("build")
    if type(build) is not int or build < 1:
        raise BundleError("Invalid build")
    entries = value.get("files")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_FILES:
        raise BundleError("Invalid file list")
    expected = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise BundleError("Unexpected file entry")
        name = _relative_name(entry["path"])
        sha = entry["sha256"]
        if name in expected:
            raise BundleError("Duplicate file")
        if not isinstance(sha, str) or len(sha) != 64 or any(x not in "0123456789abcdefABCDEF" for x in sha):
            raise BundleError("Invalid SHA256")
        expected[name] = sha.lower()
    if "plugin.py" not in expected:
        raise BundleError("Bundle must contain plugin.py")
    return expected


@contextmanager
def update_lock(root):
    """Hold an OS advisory lock across recovery and installation."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise BundleError("Plugin directory missing")
    lock_path = root / LOCK_NAME
    if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
        raise BundleError("Unsafe update lock")
    flags = os.O_CREAT | os.O_RDWR
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(lock_path), flags, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            raise BundleError("Another EmbyFlowE2 update is active") from exc
        try:
            yield root
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def apply_release(root, manifest, downloaded_files, *, crash_after=None):
    """Install v2 bundle or raise, preserving the existing production updater.

    All bytes must already be downloaded. Checks are performed before any live
    file replacement. Under the lock, incomplete previous updates are rolled
    back before a new installation begins.
    """
    expected = parse_manifest(manifest)
    if not isinstance(downloaded_files, dict) or set(downloaded_files) != set(expected):
        raise BundleError("Downloaded file set mismatch")
    if sum(len(data) for data in downloaded_files.values() if isinstance(data, bytes)) > MAX_PAYLOAD_BYTES:
        raise BundleError("Bundle exceeds size limit")
    with update_lock(root) as directory:
        recovered = recover_pending(directory)
        installed = install_recoverable(directory, downloaded_files, expected, crash_after=crash_after)
        return {"restored_transactions": recovered, "installed_files": installed}


def recover_on_start(root):
    """Recovery entry point for eventual bootstrap integration (not yet used)."""
    with update_lock(root) as directory:
        return recover_pending(directory)

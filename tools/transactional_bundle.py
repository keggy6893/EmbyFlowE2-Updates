"""Staged, transactional multi-file update primitive for future EmbyFlowE2 releases.

Development-only: this module is NOT wired into the production updater.
The caller must provide an already downloaded, locally validated bundle.
Does not require py_compile or Enigma2 imports.
"""
import hashlib
import os
import shutil
import tempfile
from pathlib import Path


class BundleError(Exception):
    pass


def _relative_name(name):
    if not isinstance(name, str) or not name or name.startswith(("/", "\\")):
        raise BundleError("Invalid bundle path")
    normalized = name.replace("\\", "/")
    parts = normalized.split("/")
    if any(x in ("", ".", "..") for x in parts) or ":" in normalized or "\x00" in normalized:
        raise BundleError("Unsafe bundle path")
    if not all(part.replace("_", "").replace("-", "").replace(".", "").isalnum() for part in parts):
        raise BundleError("Unsupported bundle path characters")
    if not normalized.endswith(".py"):
        raise BundleError("Only Python source files are supported")
    return normalized


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def validate_bundle(files, expected_sha256):
    """Validate all entries before touching a live plugin directory."""
    if not files or set(files) != set(expected_sha256):
        raise BundleError("Bundle manifest does not match file set")
    output = {}
    for name, data in files.items():
        path = _relative_name(name)
        if path in output or not isinstance(data, bytes):
            raise BundleError("Duplicate path or invalid payload")
        digest = expected_sha256[name]
        if not isinstance(digest, str) or len(digest) != 64 or _sha256(data) != digest.lower():
            raise BundleError("SHA256 mismatch: " + path)
        try:
            compile(data, path, "exec", dont_inherit=True)
        except (SyntaxError, ValueError, TypeError) as exc:
            raise BundleError("Python syntax error: " + path) from exc
        output[path] = data
    return output


def install_bundle(target_dir, files, expected_sha256, fail_after=None):
    """Install a validated file set with rollback on ordinary I/O failures.

    This is NOT a power-loss-safe multi-file transaction: a sudden process
    crash or power cut between replacements requires boot-time recovery.
    Production integration additionally needs startup recovery and updater
    compatibility for multi-file manifests.
    """
    files = validate_bundle(files, expected_sha256)
    root = Path(target_dir).resolve(strict=True)
    if not root.is_dir():
        raise BundleError("Plugin path is not a directory")

    # No user-controlled symlinks are followed within the plugin installation.
    for name in files:
        target = root.joinpath(*name.split("/"))
        current = root
        for component in name.split("/")[:-1]:
            current /= component
            if current.is_symlink():
                raise BundleError("Symlink in destination parent")
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise BundleError("Unsafe destination file: " + name)

    # Keep staging on the same filesystem as the live plugin.
    stage = Path(tempfile.mkdtemp(prefix=".embyflow-stage-", dir=str(root)))
    originals = {}
    written = []
    try:
        for name, data in files.items():
            prepared = stage / "new" / name
            prepared.parent.mkdir(parents=True, exist_ok=True)
            prepared.write_bytes(data)
            if _sha256(prepared.read_bytes()) != expected_sha256[name].lower():
                raise BundleError("Staging integrity check failed")
            target = root.joinpath(*name.split("/"))
            if target.exists():
                old = target.read_bytes()
                original = stage / "old" / name
                original.parent.mkdir(parents=True, exist_ok=True)
                original.write_bytes(old)
                originals[name] = original
            else:
                originals[name] = None

        for index, name in enumerate(files):
            target = root.joinpath(*name.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            replacement = stage / "new" / name
            os.replace(str(replacement), str(target))
            written.append(name)
            if fail_after is not None and index + 1 == fail_after:
                raise OSError("Injected failure for rollback test")
        return len(written)
    except Exception:
        for name in reversed(written):
            target = root.joinpath(*name.split("/"))
            saved = originals[name]
            if saved is None:
                target.unlink(missing_ok=True)
            else:
                os.replace(str(saved), str(target))
        raise
    finally:
        shutil.rmtree(str(stage), ignore_errors=True)

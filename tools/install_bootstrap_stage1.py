"""Conservative *offline* stage-one bootstrap installer for an Enigma2 package.

For a future, explicitly authorized first-time migration. NEVER run on an
active receiver or automatically from the legacy updater. It installs only
the stable recovery guard and patched __init__.py, preserving plugin.py.
Must be followed by an Enigma2 restart and on-box verification before v2.
"""
import hashlib
import os
from pathlib import Path

from build_stable_bootstrap import GUARD_MARKER, bootstrap_files


class BootstrapInstallError(RuntimeError):
    pass


def _atomic_bytes(path, payload, mode=0o644):
    temp = path.with_name("." + path.name + ".embyflow-stage1.tmp")
    if temp.is_symlink() or temp.exists():
        raise BootstrapInstallError("Unsafe pending bootstrap temporary path")
    try:
        with open(temp, "xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(str(temp), str(path))
        fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temp.exists():
            temp.unlink()


def stage1_preflight(root):
    """Read-only check: never overwrite unknown versions or existing guards."""
    root = Path(root).resolve(strict=True)
    init_file = root / "__init__.py"
    guard_file = root / "startup_recovery_guard.py"
    plugin_file = root / "plugin.py"
    if not root.is_dir() or not plugin_file.is_file() or plugin_file.is_symlink():
        raise BootstrapInstallError("Not an EmbyFlowE2 package")
    if not init_file.is_file() or init_file.is_symlink():
        raise BootstrapInstallError("Existing package initializer must be inspected")
    if guard_file.exists() or guard_file.is_symlink():
        raise BootstrapInstallError("Recovery guard already present: review manually")
    existing = init_file.read_bytes()
    if len(existing) > 128 * 1024:
        raise BootstrapInstallError("Unexpected initializer size")
    source = existing.decode("utf-8")
    if GUARD_MARKER in source:
        raise BootstrapInstallError("Recovery bootstrap already installed")
    contents = bootstrap_files(source)
    for name, data in contents.items():
        compile(data, name, "exec", dont_inherit=True)
    return root, contents, hashlib.sha256(existing).hexdigest()


def install_stage1_in_offline_package(root, *, expected_initializer_sha256):
    """Install guard first; initializer last. Non-overwriting, fail-closed API.

    This API is intended for a stopped Enigma2 service and an offline staged
    copy during development. A full production migration must still cover
    power loss DURING stage-one itself and compare service state atomically.
    """
    root, files, digest = stage1_preflight(root)
    if digest != expected_initializer_sha256:
        raise BootstrapInstallError("Initializer changed since preflight")
    init_file = root / "__init__.py"
    guard_file = root / "startup_recovery_guard.py"
    if guard_file.exists() or guard_file.is_symlink():
        raise BootstrapInstallError("Guard destination already exists")
    # Preserve a durable copy before altering the entrypoint.
    backup = root / "__init__.py.embyflow-stage1-backup"
    if backup.exists() or backup.is_symlink():
        raise BootstrapInstallError("Existing bootstrap backup requires review")
    original = init_file.read_bytes()
    init_mode = init_file.stat().st_mode & 0o777
    try:
        _atomic_bytes(backup, original, mode=0o600)
        _atomic_bytes(guard_file, files["startup_recovery_guard.py"])
        if hashlib.sha256(guard_file.read_bytes()).digest() != hashlib.sha256(files["startup_recovery_guard.py"]).digest():
            raise BootstrapInstallError("Guard staging digest mismatch")
        _atomic_bytes(init_file, files["__init__.py"], mode=init_mode)
        return {"guard_installed": True, "initializer_patched": True, "plugin_untouched": True}
    except Exception:
        # We can undo ordinary exceptions. After power loss a durable backup
        # remains for recovery by a separately installed stage-one supervisor.
        if backup.is_file():
            _atomic_bytes(init_file, original, mode=init_mode)
        raise

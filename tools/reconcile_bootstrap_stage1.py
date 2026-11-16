"""Read-only stage-one power-loss assessment and conservative offline resume.

Stage one writes (1) durable original initializer backup, (2) stable guard,
then (3) switches __init__.py. Any crash before (3) leaves old plugin startup
untouched. A crash during (3) produces either old or new initializer because
os.replace is atomic on the same filesystem. This module recognizes those
on-disk states and allows explicit resume only when hashes match.

Never invoked automatically on a live receiver. The remote operator must stop
Enigma2 and verify the package path before considering installation or resume.
"""
import hashlib
from pathlib import Path

from build_stable_bootstrap import GUARD_MARKER, bootstrap_files

BACKUP_NAME = "__init__.py.embyflow-stage1-backup"
GUARD_NAME = "startup_recovery_guard.py"


class Stage1RecoveryError(RuntimeError):
    pass


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect_stage1(root):
    """Return a named recoverable state without ever modifying the package."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise Stage1RecoveryError("Not an Enigma2 plugin directory")
    plugin = root / "plugin.py"
    init = root / "__init__.py"
    guard = root / GUARD_NAME
    backup = root / BACKUP_NAME
    for path in (plugin, init):
        if path.is_symlink() or not path.is_file():
            raise Stage1RecoveryError("Missing or unsafe plugin / initializer")
    for path in (guard, backup):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise Stage1RecoveryError("Unsafe guard or backup path")
    if not guard.exists() and not backup.exists():
        if GUARD_MARKER in init.read_text(encoding="utf-8"):
            raise Stage1RecoveryError("Activated bootstrap without guard or backup")
        return {"state": "not_started", "can_resume": False}
    if not backup.exists():
        raise Stage1RecoveryError("Guard present but original initializer backup missing")

    original = backup.read_bytes()
    if not original or len(original) > 128 * 1024:
        # Empty __init__.py is valid; do not reject on that basis.
        if len(original) > 128 * 1024:
            raise Stage1RecoveryError("Backup initializer too large")
    if GUARD_MARKER in original.decode("utf-8"):
        raise Stage1RecoveryError("Backup already contains bootstrap marker")
    expected = bootstrap_files(original.decode("utf-8"))
    active = init.read_bytes()
    if active not in (original, expected["__init__.py"]):
        raise Stage1RecoveryError("Initializer changed since stage-one began")
    if guard.exists() and _sha(guard.read_bytes()) != _sha(expected[GUARD_NAME]):
        raise Stage1RecoveryError("Guard digest mismatch")
    if active == expected["__init__.py"] and not guard.exists():
        raise Stage1RecoveryError("Bootstrap active without guard")
    if active == expected["__init__.py"]:
        state = "activated"
    elif guard.exists():
        state = "guard_ready"
    else:
        state = "backup_only"
    return {
        "state": state,
        "can_resume": state != "activated",
        "original_initializer_sha256": _sha(original),
        "guard_sha256": _sha(expected[GUARD_NAME]),
        "plugin_sha256": _sha(plugin.read_bytes()),
    }


def resume_stage1_offline(root, *, original_sha256, plugin_sha256, atomic_writer):
    """Resume a previously interrupted installation on an offline package copy.

    Caller supplies the same tested atomic writer used by stage-one installer.
    Refuses to replace arbitrary modifications and requires a pinned SHA256
    of both the original initializer and unchanged installed plugin.
    """
    root = Path(root).resolve(strict=True)
    status = inspect_stage1(root)
    if status["state"] == "not_started":
        raise Stage1RecoveryError("No interrupted stage-one transaction")
    if status.get("original_initializer_sha256") != original_sha256:
        raise Stage1RecoveryError("Original initializer differs from approved version")
    if status.get("plugin_sha256") != plugin_sha256:
        raise Stage1RecoveryError("Plugin differs from approved version")
    if status["state"] == "activated":
        return {"state": "activated", "changed": False}

    backup = root / BACKUP_NAME
    expected = bootstrap_files(backup.read_text(encoding="utf-8"))
    guard = root / GUARD_NAME
    initializer = root / "__init__.py"
    if not guard.exists():
        atomic_writer(guard, expected[GUARD_NAME])
    # Independent digest verification before changing the entrypoint.
    if _sha(guard.read_bytes()) != status["guard_sha256"]:
        raise Stage1RecoveryError("Guard verification failed")
    # Stage-one backups are deliberately stored with 0600 permissions.
    # Never copy that restricted backup mode onto the importable initializer.
    # Use readable source-file permissions; a later production migration may
    # persist and restore exact original mode in a durable journal.
    atomic_writer(initializer, expected["__init__.py"], mode=0o644)
    after = inspect_stage1(root)
    if after["state"] != "activated":
        raise Stage1RecoveryError("Stage-one activation was not durable")
    return {"state": "activated", "changed": True}

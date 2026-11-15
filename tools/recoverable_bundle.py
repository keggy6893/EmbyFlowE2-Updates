"""Crash-recoverable experimental installer for EmbyFlowE2 multi-file updates.

Development only. NOT connected to the installed EmbyFlowE2 updater.
Run recover_pending(root) before a new install, and at process startup before
importing changed modules. This implementation targets a single local POSIX
filesystem. It does not implement cross-process locking or secure handling of
a malicious process that can mutate files as the same OS user.
"""
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from transactional_bundle import BundleError, validate_bundle, _relative_name

PREFIX = ".embyflow-txn-"
JOURNAL = "journal.json"


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _sync_dir(directory):
    fd = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_synced(path, data):
    with open(path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    _sync_dir(path.parent)


def _atomic_write(path, data):
    temp = path.with_name(path.name + ".tmp")
    _write_synced(temp, data)
    os.replace(str(temp), str(path))
    _sync_dir(path.parent)


def _validate_target(root, name):
    normalized = _relative_name(name)
    target = root.joinpath(*normalized.split("/"))
    cursor = root
    for part in normalized.split("/")[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise BundleError("Symlink in destination parent: " + name)
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise BundleError("Unsafe destination: " + name)
    return target


def _journal_path(stage):
    return stage / JOURNAL


def _read_journal(stage):
    try:
        data = json.loads(_journal_path(stage).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError("Broken transaction journal: " + stage.name) from exc
    if not isinstance(data, dict) or data.get("format") != 1 or data.get("state") not in ("prepared", "committed"):
        raise BundleError("Invalid transaction journal")
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise BundleError("Empty transaction journal")
    seen = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise BundleError("Invalid journal entry")
        name = _relative_name(entry.get("path"))
        if name in seen or type(entry.get("existed")) is not bool:
            raise BundleError("Duplicate/invalid journal path")
        seen.add(name)
        for key in ("before", "after"):
            value = entry.get(key)
            if value is not None and (not isinstance(value, str) or len(value) != 64):
                raise BundleError("Invalid journal digest")
    return data


def _replace_restore(root, stage, entry):
    name = entry["path"]
    target = _validate_target(root, name)
    if entry["existed"]:
        backup = stage / "old" / name
        if not backup.is_file() or backup.is_symlink():
            raise BundleError("Missing recovery backup: " + name)
        original = backup.read_bytes()
        if _digest(original) != entry["before"]:
            raise BundleError("Corrupt recovery backup: " + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".embyflow-restore-temp")
        _write_synced(temp, original)
        os.replace(str(temp), str(target))
        _sync_dir(target.parent)
    elif target.exists():
        target.unlink()
        _sync_dir(target.parent)


def recover_pending(target_dir):
    """Restore all prepared transactions or finish committed cleanup.

    Conservative recovery: a prepared transaction always rolls back, even if
    every replacement occurred before the power failure.
    """
    root = Path(target_dir).resolve(strict=True)
    if not root.is_dir():
        raise BundleError("Plugin directory missing")
    recovered = 0
    for stage in sorted(root.glob(PREFIX + "*")):
        if not stage.is_dir() or stage.is_symlink():
            raise BundleError("Unexpected transaction path")
        journal = _journal_path(stage)
        if not journal.exists():
            # The installer creates this journal only after staging all backups.
            # No live path is touched before the journal is durable.
            shutil.rmtree(str(stage))
            _sync_dir(root)
            continue
        data = _read_journal(stage)
        if data["state"] == "prepared":
            for entry in reversed(data["files"]):
                _replace_restore(root, stage, entry)
            recovered += 1
        else:
            # Never silently accept external modifications to committed files.
            for entry in data["files"]:
                target = _validate_target(root, entry["path"])
                if not target.is_file() or _digest(target.read_bytes()) != entry["after"]:
                    raise BundleError("Committed transaction integrity mismatch")
        shutil.rmtree(str(stage))
        _sync_dir(root)
    return recovered


def install_recoverable(target_dir, files, expected_sha256, crash_after=None):
    """Validate and replace sources; recover_pending() handles interrupted runs.

    crash_after is a test-only injected SystemExit occurring after N replaces.
    """
    content = validate_bundle(files, expected_sha256)
    root = Path(target_dir).resolve(strict=True)
    if not root.is_dir():
        raise BundleError("Plugin directory missing")
    if list(root.glob(PREFIX + "*")):
        raise BundleError("Pending update: run recover_pending first")

    for name in content:
        _validate_target(root, name)
    stage = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(root)))
    journal_ready = False
    try:
        entries = []
        for name, payload in content.items():
            target = _validate_target(root, name)
            original = target.read_bytes() if target.exists() else None
            entry = {"path": name, "existed": original is not None,
                     "before": _digest(original) if original is not None else None,
                     "after": _digest(payload)}
            entries.append(entry)
            new_path = stage / "new" / name
            new_path.parent.mkdir(parents=True, exist_ok=True)
            _write_synced(new_path, payload)
            if original is not None:
                old_path = stage / "old" / name
                old_path.parent.mkdir(parents=True, exist_ok=True)
                _write_synced(old_path, original)
        _sync_dir(stage)
        record = {"format": 1, "state": "prepared", "files": entries}
        _atomic_write(_journal_path(stage), json.dumps(record, sort_keys=True).encode("utf-8"))
        _sync_dir(root)
        journal_ready = True
        for count, entry in enumerate(entries, 1):
            name = entry["path"]
            target = _validate_target(root, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            replacement = stage / "new" / name
            os.replace(str(replacement), str(target))
            _sync_dir(target.parent)
            if crash_after == count:
                raise SystemExit("SIMULATED_PROCESS_CRASH")
        record["state"] = "committed"
        _atomic_write(_journal_path(stage), json.dumps(record, sort_keys=True).encode("utf-8"))
        shutil.rmtree(str(stage))
        _sync_dir(root)
        return len(entries)
    except Exception:
        if journal_ready:
            recover_pending(root)
        else:
            shutil.rmtree(str(stage), ignore_errors=True)
        raise

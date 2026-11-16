"""Stable, standalone crash-recovery preflight for EmbyFlowE2.

This module must be installed in a *separate initial transition* and must NOT
be included in replaceable modular update bundles. Import it from the
extension package __init__.py BEFORE importing plugin.py.

Intentionally relies only on stdlib and the existing on-disk journal protocol.
No imports from mutable refactor_modules. It never modifies the official repo.
"""
import fcntl
import hashlib
import json
import os
import shutil
from pathlib import Path

PREFIX = ".embyflow-txn-"
LOCK_NAME = ".embyflow-update.lock"
MAX_FILES = 128


class StartupRecoveryError(RuntimeError):
    pass


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _sync_dir(path):
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _safe_path(root, name):
    if not isinstance(name, str) or not name or name.startswith(("/", "\\")):
        raise StartupRecoveryError("Unsafe recovery path")
    pieces = name.split("/")
    if any(piece in ("", ".", "..") for piece in pieces) or "\\" in name or "\x00" in name or ":" in name:
        raise StartupRecoveryError("Unsafe recovery filename")
    if not name.endswith(".py"):
        raise StartupRecoveryError("Non-Python recovery path")
    target = root
    for piece in pieces[:-1]:
        target = target / piece
        if target.is_symlink():
            raise StartupRecoveryError("Symlinked recovery parent")
    target = target / pieces[-1]
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise StartupRecoveryError("Unsafe recovery target")
    return target


def _journal(stage):
    path = stage / "journal.json"
    if path.is_symlink():
        raise StartupRecoveryError("Symlinked update journal")
    try:
        journal = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StartupRecoveryError("Invalid update journal") from exc
    if not isinstance(journal, dict) or journal.get("format") != 1 or journal.get("state") not in ("prepared", "committed"):
        raise StartupRecoveryError("Invalid journal format")
    entries = journal.get("files")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_FILES:
        raise StartupRecoveryError("Invalid recovery entries")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("existed"), bool):
            raise StartupRecoveryError("Invalid recovery entry")
        name = entry.get("path")
        if not isinstance(name, str) or name in seen:
            raise StartupRecoveryError("Duplicate recovery path")
        seen.add(name)
        for digest_key in ("before", "after"):
            value = entry.get(digest_key)
            if value is not None and (not isinstance(value, str) or len(value) != 64 or
                                      any(char not in "0123456789abcdefABCDEF" for char in value)):
                raise StartupRecoveryError("Malformed recovery digest")
        if not isinstance(entry.get("after"), str):
            raise StartupRecoveryError("Missing after digest")
        if entry["existed"] and not isinstance(entry.get("before"), str):
            raise StartupRecoveryError("Missing before digest")
        if not entry["existed"] and entry.get("before") is not None:
            raise StartupRecoveryError("Unexpected before digest")
    return journal


def _restore_entry(root, stage, entry):
    target = _safe_path(root, entry["path"])
    if entry["existed"]:
        old_path = stage / "old" / entry["path"]
        if old_path.is_symlink() or not old_path.is_file():
            raise StartupRecoveryError("Missing recovery backup")
        original = old_path.read_bytes()
        if _digest(original) != entry["before"].lower():
            raise StartupRecoveryError("Recovery backup hash mismatch")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".embyflow-restore-temp")
        if temp.is_symlink() or (temp.exists() and not temp.is_file()):
            raise StartupRecoveryError("Unsafe recovery temporary file")
        with open(temp, "wb") as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temp), str(target))
        _sync_dir(target.parent)
    elif target.exists():
        target.unlink()
        _sync_dir(target.parent)


def recover_before_plugin_import(plugin_dir):
    """Undo incomplete installs before any mutable plugin modules load.

    If recovery cannot complete, fail closed instead of importing possibly
    inconsistent code. Returns number of reverted incomplete transactions.
    """
    root = Path(plugin_dir).resolve(strict=True)
    if not root.is_dir():
        raise StartupRecoveryError("Missing EmbyFlowE2 directory")
    lock = root / LOCK_NAME
    if lock.is_symlink() or (lock.exists() and not lock.is_file()):
        raise StartupRecoveryError("Unsafe update lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(lock), flags, 0o600)
    recovered = 0
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        for stage in sorted(root.glob(PREFIX + "*")):
            if stage.is_symlink() or not stage.is_dir():
                raise StartupRecoveryError("Unexpected transaction directory")
            journal_path = stage / "journal.json"
            if not journal_path.exists():
                # The installer writes a durable journal BEFORE touching live files.
                shutil.rmtree(str(stage))
                _sync_dir(root)
                continue
            record = _journal(stage)
            entries = record["files"]
            if record["state"] == "prepared":
                # Check every backup before changing any live file.
                for entry in entries:
                    _safe_path(root, entry["path"])
                    if entry["existed"]:
                        old = stage / "old" / entry["path"]
                        if old.is_symlink() or not old.is_file() or _digest(old.read_bytes()) != entry["before"].lower():
                            raise StartupRecoveryError("Corrupt transaction backup")
                for entry in reversed(entries):
                    _restore_entry(root, stage, entry)
                recovered += 1
            else:
                for entry in entries:
                    current = _safe_path(root, entry["path"])
                    if not current.is_file() or _digest(current.read_bytes()) != entry["after"].lower():
                        raise StartupRecoveryError("Committed update checksum mismatch")
            shutil.rmtree(str(stage))
            _sync_dir(root)
        return recovered
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

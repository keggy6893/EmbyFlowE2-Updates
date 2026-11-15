"""Development-only bootstrap for a future modular EmbyFlowE2 package.

IMPORTANT: this loader is deliberately NOT wired into production RC26.9.
A real receiver must call preflight BEFORE importing plugin.py or any modules
that could have been updated. The loader does not auto-install releases.
"""
import hashlib
import importlib.util
import sys
from pathlib import Path

from update_coordinator import recover_on_start, BundleError


def startup_preflight(plugin_dir, required_files=None):
    """Rollback interrupted updates and verify required module sources.

    A startup preflight must live in a stable entrypoint outside the set of
    replaceable files; otherwise a crash might prevent recovery from running.
    """
    root = Path(plugin_dir).resolve(strict=True)
    if not root.is_dir():
        raise BundleError("Plugin directory missing")
    recovered = recover_on_start(root)
    required = required_files or {"plugin.py": None}
    if not isinstance(required, dict) or not required:
        raise BundleError("Invalid expected module list")

    for name, expected in required.items():
        if not isinstance(name, str) or "/" in name or "\\" in name or name in ("", ".", ".."):
            raise BundleError("Invalid required filename")
        if not name.endswith(".py"):
            raise BundleError("Non-Python startup dependency")
        file = root / name
        if file.is_symlink() or not file.is_file():
            raise BundleError("Required module not installed: " + name)
        data = file.read_bytes()
        if expected is not None:
            if not isinstance(expected, str) or hashlib.sha256(data).hexdigest() != expected.lower():
                raise BundleError("Required module digest differs: " + name)
        try:
            compile(data, str(file), "exec", dont_inherit=True)
        except (SyntaxError, ValueError, TypeError) as exc:
            raise BundleError("Invalid startup module: " + name) from exc
    return {"restored_transactions": recovered, "required_files": len(required)}


def load_synthetic_plugin(plugin_dir, module_name="_embyflow_bootstrap_test"):
    """Test helper only, NOT an Enigma2 launcher.

    Imports a synthetic plugin after recovery to prove startup ordering.
    Never use this as a replacement for Enigma2's official Plugins import.
    """
    directory = Path(plugin_dir).resolve(strict=True)
    startup_preflight(directory)
    plugin = directory / "plugin.py"
    spec = importlib.util.spec_from_file_location(module_name, plugin)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module

"""Build a stable package initializer for the first *separate* bootstrap install.

The stable guard is deliberately NOT part of subsequent modular update bundles.
A future IPK/installer must first place startup_recovery_guard.py and this
initializer, verify both, and then enable multi-file updates. Do not replace
a user's existing __init__.py without reviewing its contents.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD_MARKER = "# EMBYFLOW_STABLE_RECOVERY_BOOTSTRAP_V1"
BOOTSTRAP_HEADER = '''%s
# This must run before the Enigma2 plugin.py or any mutable update modules load.
from .startup_recovery_guard import recover_before_plugin_import as _embyflow_recover_before_import
_embyflow_recover_before_import(__path__[0])
del _embyflow_recover_before_import

''' % GUARD_MARKER


def patch_initializer(existing):
    if GUARD_MARKER in existing:
        raise ValueError("Bootstrap already installed")
    # Preserve encoding declarations, comments, module docstrings and __future__
    # imports. Insert recovery before all ordinary imports or side effects.
    tree = ast.parse(existing)
    lines = existing.splitlines(keepends=True)
    insert_line = 0
    if lines and lines[0].startswith("#!"):
        insert_line = 1
    for index in range(min(2, len(lines))):
        if "coding:" in lines[index] or "coding=" in lines[index]:
            insert_line = max(insert_line, index + 1)
    body = tree.body
    pos = 0
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(getattr(body[0].value, "value", None), str):
        insert_line = max(insert_line, body[0].end_lineno)
        pos = 1
    while pos < len(body) and isinstance(body[pos], ast.ImportFrom) and body[pos].module == "__future__":
        insert_line = max(insert_line, body[pos].end_lineno)
        pos += 1
    lines.insert(insert_line, BOOTSTRAP_HEADER)
    result = "".join(lines)
    compile(result, "__init__.py", "exec")
    return result


def bootstrap_files(existing_initializer):
    return {
        "__init__.py": patch_initializer(existing_initializer).encode("utf-8"),
        "startup_recovery_guard.py": (ROOT / "tools" / "startup_recovery_guard.py").read_bytes(),
    }

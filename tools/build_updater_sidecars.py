#!/usr/bin/env python3
"""Stage the updater's Python sidecars with valid Enigma2 package imports.

The developer tools/ folder uses top-level imports for standalone tests. On a
receiver, they live below Plugins.Extensions.EmbyFlowE2.refactor_modules and
must import one another relatively. This builder makes that explicit.
Do not publish a release directly from this standalone utility.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools"
SIDECAR_MODULES = (
    "transactional_bundle",
    "recoverable_bundle",
    "update_coordinator",
    "modular_tar_bridge",
)
CONVERSION = {
    "transactional_bundle": ".transactional_bundle",
    "recoverable_bundle": ".recoverable_bundle",
    "update_coordinator": ".update_coordinator",
}

def _repackage(source, module):
    tree = ast.parse(source)
    edits = []
    # Source-range replacement keeps original formatting and line numbers.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module in CONVERSION:
            if node.lineno != node.end_lineno:
                raise ValueError("Multiline imports require explicit review: " + module)
            line = source.splitlines(keepends=True)[node.lineno - 1]
            prefix = "from " + node.module + " import "
            if not line.startswith(prefix):
                raise ValueError("Unrecognized sidecar import: " + module)
            edits.append((node.lineno - 1, line.replace(prefix, "from " + CONVERSION[node.module] + " import ", 1)))
    lines = source.splitlines(keepends=True)
    for index, line in edits:
        lines[index] = line
    result = "".join(lines)
    compile(result, module + ".py", "exec")
    for node in ast.walk(ast.parse(result)):
        if isinstance(node, ast.ImportFrom) and node.module in CONVERSION and node.level == 0:
            raise ValueError("Absolute sibling import remains: " + module)
    return result.encode("utf-8")

def staged_sidecars():
    result = {"refactor_modules/__init__.py": b""}
    for name in SIDECAR_MODULES:
        original = (SOURCE / (name + ".py")).read_text(encoding="utf-8")
        result["refactor_modules/" + name + ".py"] = _repackage(original, name)
    return result

if __name__ == "__main__":
    import sys
    folder = Path(sys.argv[1]) if len(sys.argv) == 2 else ROOT / "refactor_candidates" / "sidecar_preview"
    for name, data in staged_sidecars().items():
        dest = folder / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        print("SIDECAR_READY", name, len(data))

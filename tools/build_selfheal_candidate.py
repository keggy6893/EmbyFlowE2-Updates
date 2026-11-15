#!/usr/bin/env python3
"""Build a candidate EmbyFlowE2 plugin with updater self-healing enabled.

The normal RC26.5 download, update.json and release stay untouched.
"""
from pathlib import Path
import re

source_path = Path("plugin_2026111411.py")
target_path = Path("recovery/plugin_selfheal_candidate.py")
source = source_path.read_text(encoding="utf-8")
helper = Path("tools/embyflow_updater_selfheal.py").read_text(encoding="utf-8")
marker = "_embyflow_update_install_plugin"
header = re.compile(r"(?m)^def _embyflow_update_install_plugin\(manifest\):[ \t]*$")
matches = list(header.finditer(source))
if len(matches) != 1:
    raise SystemExit("STOP: updater installation entrypoint not uniquely located")
if "def _embyflow_ensure_py_compile_fallback" in source:
    raise SystemExit("STOP: the candidate already contains a bootstrap")

# Insert the helper immediately before the installer. The module's
# local imports avoid changing global import ordering.
helper_body = helper.split("def ensure_syntax_checker():", 1)[1]
helper_body = "def _embyflow_ensure_py_compile_fallback():" + helper_body
# Ensure no import/relative dependency on the external tools package.
helper_body = "import sys as _embyflow_sys\nimport types as _embyflow_types\n\n" + helper_body
helper_body = helper_body.replace("sys.modules", "_embyflow_sys.modules").replace(
    "types.ModuleType", "_embyflow_types.ModuleType"
)
start, end = matches[0].span()
updated = (
    source[:start]
    + helper_body
    + "\n\n"
    + source[start:end]
    + "\n    _embyflow_ensure_py_compile_fallback()"
    + source[end:]
)
compile(updated, str(target_path), "exec", dont_inherit=True)
assert updated.count("    _embyflow_ensure_py_compile_fallback()") == 1
assert len(updated) > 3_000_000
target_path.parent.mkdir(parents=True, exist_ok=True)
target_path.write_text(updated, encoding="utf-8")
print("Candidate syntax OK; official release untouched.")

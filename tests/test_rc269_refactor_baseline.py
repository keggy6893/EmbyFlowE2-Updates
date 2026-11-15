#!/usr/bin/env python3
"""Read-only checks before refactoring the RC26.9 Enigma2 plugin.

This deliberately avoids importing plugin.py on the build host because the
real receiver-specific enigma/enigma2 modules are unavailable.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin_2026111523.py"
MANIFEST = ROOT / "update.json"
RC269_SHA256 = "b7bcf3dc4bbefd4c938b7747258eb8bcbc061be0d303aa0b19c11ec31d7cdbb9"

def verify_release_baseline():
    assert PLUGIN.is_file(), "RC26.9 plugin missing"
    source = PLUGIN.read_bytes()
    assert hashlib.sha256(source).hexdigest() == RC269_SHA256, "RC26.9 plugin modified"
    compile(source, str(PLUGIN), "exec")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["version"] == "2026-RC26.9"
    assert manifest["build"] == 2026111523
    assert manifest["target"] == "plugin.py"
    assert manifest["artifact_type"] == "plugin_py"
    assert manifest["sha256"] == RC269_SHA256
    assert manifest["download"].endswith("/plugin_2026111523.py")
    for marker in (
        b"EMBYFLOW_CONTINUE_SAFE_DISPLAY_DEDUP_V1",
        b"EMBYFLOW_CONTINUE_SERIES_POSTER_FIRST_V1",
        b"EMBYFLOW_CONTINUE_DOT_FOOTER_V2",
        b"EMBYFLOW_CONTINUE_HIDE_ALPHABET_V2",
        b"EMBYFLOW_STARTUP_UPDATE_PROMPT_V1",
        b"EMBYFLOW_CONTINUE_LOCAL_HIDE_V1",
    ):
        assert source.count(marker) == 1, f"Required function missing or duplicated: {marker!r}"

def inventory():
    source = PLUGIN.read_text(encoding="utf-8", errors="replace")
    classes = re.findall(r"(?m)^class\s+(\w+)\s*\(", source)
    funcs = re.findall(r"(?m)^def\s+(\w+)\s*\(", source)
    print(f"RC26.9 baseline: {len(source.encode('utf-8')):,} source bytes")
    print(f"Top-level classes: {len(classes)}; top-level functions: {len(funcs)}")
    print("Checks limited to syntax, release metadata, and known regression markers.")
    print("Receiver-only checks (UI, key actions, E2 player, NAS, updater): NOT executed.")

if __name__ == "__main__":
    verify_release_baseline()
    inventory()
    print("RC26.9 BASELINE PASS")

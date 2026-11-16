#!/usr/bin/env python3
"""Package a receiver-ready modular RC26.9 development candidate.

No production release/manifest changes. This bundle is for staged testing only.
The existing single-file update.json MUST remain untouched.
"""
import ast
import hashlib
import json
from pathlib import Path
from build_modular_candidate import build as build_candidate

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "refactor_candidates" / "rc269_bundle"
BASELINE = ROOT / "plugin_2026111523.py"
BASELINE_HASH = "b7bcf3dc4bbefd4c938b7747258eb8bcbc061be0d303aa0b19c11ec31d7cdbb9"
OLD_IMPORT = "from refactor_modules.local_media_utils import "
NEW_IMPORT = "from .refactor_modules.local_media_utils import "


def make_bundle():
    assert hashlib.sha256(BASELINE.read_bytes()).hexdigest() == BASELINE_HASH, "Baseline changed"
    candidate = build_candidate().read_text(encoding="utf-8")
    assert candidate.count(OLD_IMPORT) == 2, "Unexpected extraction import count"
    converted = candidate.replace(OLD_IMPORT, NEW_IMPORT)
    assert converted.count(NEW_IMPORT) == 2
    tree = ast.parse(converted, "plugin.py")
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)
               and node.level == 1 and node.module == "refactor_modules.local_media_utils"]
    assert len(imports) == 2, "Package imports missing"
    compile(converted, "plugin.py", "exec")
    helper = (ROOT / "refactor_modules" / "local_media_utils.py").read_bytes()
    compile(helper, "refactor_modules/local_media_utils.py", "exec")
    files = {
        "plugin.py": converted.encode("utf-8"),
        "refactor_modules/__init__.py": b"",
        "refactor_modules/local_media_utils.py": helper,
    }
    DIST.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        path = DIST / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    manifest = {
        "schema": 2,
        "artifact_type": "python_bundle",
        "version": "2026-RC26.9-modular-dev",
        "build": 2026111523,
        "files": [
            {"path": name, "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in files.items()
        ],
    }
    (DIST / "manifest.dev.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert len(files["plugin.py"]) > 3_900_000
    return DIST, manifest


if __name__ == "__main__":
    dist, manifest = make_bundle()
    print("DEV_BUNDLE_READY", dist, "files:", len(manifest["files"]))

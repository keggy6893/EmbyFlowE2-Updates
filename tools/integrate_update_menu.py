#!/usr/bin/env python3
"""Build experimental modular-update GUI candidate from a real EmbyFlowE2 plugin.

No production writes. Keep the existing legacy plugin.py and PNG tar.gz paths
byte-identical except for the explicit opt-in modular branch.
Requires modular_tar_bridge and its dependencies in refactor_modules/.
This is NOT the first-update migration mechanism for receivers lacking them.
"""
import argparse
import ast
from pathlib import Path

MARKER = "# EMBYFLOW_MODULAR_UPDATER_DEV_BRIDGE_V1"
NORMALIZE_START = '    installable = bool(legacy_plugin or bundle_tar_gz)\n'
NORMALIZE_RETURN = '        "bundle_tar_gz": bundle_tar_gz,\n'
INSTALL_GUARD = '    # Keep the proven V1 single-file updater path fully compatible.\n'

MODULAR_CLASSIFICATION = '''    # Experimental modular tar.gz, separate from the legacy PNG-only bundle.
    modular_bundle = bool(
        manifest.get("schema") == 2
        and artifact_type == "python_bundle"
        and target == "bundle"
        and (clean_download.endswith(".tar.gz") or clean_download.endswith(".tgz"))
        and isinstance(manifest.get("files"), list)
    )
'''
MODULAR_DISPATCH = '''    %s
    # The sidecar is not shipped by old single-file updates. Fail closed if
    # it is absent; do not treat a modular release as legacy or PNG tarball.
    if bool(manifest.get("modular_bundle")):
        try:
            from .refactor_modules.modular_tar_bridge import install_modular_archive
        except ImportError as exc:
            raise RuntimeError("Modularer Updater nicht installiert; Bootstrap erforderlich") from exc
        # The full archive has already been downloaded, pinned by the normal
        # manifest URL policy and verified against its release SHA256 above.
        v2 = {
            "schema": 2,
            "artifact_type": "python_bundle",
            "version": str(manifest["version"]),
            "build": int(manifest["build"]),
            "files": manifest["files"],
        }
        result = install_modular_archive(
            target_dir, data, v2, archive_sha256=expected_sha.lower()
        )
        _embyflow_update_mark_installed(str(manifest["version"]), int(manifest["build"]))
        return {
            "ok": True, "version": str(manifest["version"]),
            "build": int(manifest["build"]), "sha256": actual_sha,
            "backup": None, "rollback": False,
            "modular_files": result["installed_files"],
        }

''' % MARKER


def patch_source(source):
    if MARKER in source:
        raise ValueError("Modular bridge already applied")
    if source.count(NORMALIZE_START) != 1:
        raise ValueError("Cannot find unique legacy installability check")
    if source.count(NORMALIZE_RETURN) != 1:
        raise ValueError("Cannot find unique manifest return")
    if source.count(INSTALL_GUARD) != 1:
        raise ValueError("Cannot find unique legacy installer branch")
    source = source.replace(
        NORMALIZE_START,
        MODULAR_CLASSIFICATION + '    installable = bool(legacy_plugin or bundle_tar_gz or modular_bundle)\n',
    )
    source = source.replace(
        NORMALIZE_RETURN,
        NORMALIZE_RETURN + '        "modular_bundle": modular_bundle,\n        "files": manifest.get("files") if modular_bundle else None,\n',
    )
    source = source.replace(INSTALL_GUARD, MODULAR_DISPATCH + INSTALL_GUARD)
    tree = ast.parse(source)
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    for name in ("_embyflow_update_normalize_manifest", "_embyflow_update_install_plugin"):
        if name not in functions:
            raise ValueError("Missing expected updater function: " + name)
    return source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.destination.resolve():
        parser.error("Never overwrite the source plugin")
    code = patch_source(args.source.read_text(encoding="utf-8"))
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(code, encoding="utf-8")
    print("MODULAR_UPDATE_MENU_CANDIDATE_READY", args.destination)


if __name__ == "__main__":
    main()

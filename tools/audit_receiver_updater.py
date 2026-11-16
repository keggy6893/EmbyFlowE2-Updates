"""Read-only audit of the actual EmbyFlowE2 plugin's updater integration.

This does not edit, import or execute the Enigma2 plugin; it checks AST wiring
and prevents a future modular updater from being accidentally enabled without
a safe, explicit integration strategy. Use with an on-receiver plugin.py copy.
"""
import ast
from pathlib import Path

class UpdaterAuditError(RuntimeError):
    pass

def inspect_updater(source_file):
    source_file = Path(source_file)
    source = source_file.read_bytes()
    tree = ast.parse(source, filename=str(source_file))
    functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}

    required = (
        "_embyflow_update_normalize_manifest",
        "_embyflow_update_fetch_manifest",
        "_embyflow_update_install_plugin",
    )
    for name in required:
        if name not in functions:
            raise UpdaterAuditError("Missing updater function: " + name)
    if "EmbyFlowUpdateScreen" not in classes:
        raise UpdaterAuditError("Missing update GUI screen")

    screen = classes["EmbyFlowUpdateScreen"]
    screen_functions = {node.name: node for node in screen.body if isinstance(node, ast.FunctionDef)}
    if "_install_confirmed" not in screen_functions:
        raise UpdaterAuditError("Missing update confirmation handler")
    confirm = screen_functions["_install_confirmed"]
    if not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "_embyflow_update_install_plugin"
        for node in ast.walk(confirm)
    ):
        raise UpdaterAuditError("Update button is not wired to installer")

    install = functions["_embyflow_update_install_plugin"]
    normalize = functions["_embyflow_update_normalize_manifest"]
    def constant_strings(node):
        return {v.value for v in ast.walk(node) if isinstance(v, ast.Constant) and isinstance(v.value, str)}
    install_strings = constant_strings(install)
    manifest_strings = constant_strings(normalize)
    return {
        "syntax_ok": True,
        "gui_installer_wired": True,
        "legacy_plugin_py_supported": "plugin.py" in install_strings,
        "existing_tar_gz_supported": ".tar.gz" in manifest_strings,
        "existing_tar_explicit_png_assets": all(n in install_strings for n in (
            "EmbyFlowE2/images/audio_controls/ring.png",
            "EmbyFlowE2/images/audio_controls/ring_focus.png",
        )),
        "modular_v2_manifest_supported": "python_bundle" in manifest_strings,
        "installer_line": install.lineno,
        "manifest_line": normalize.lineno,
    }

if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 tools/audit_receiver_updater.py /path/to/plugin.py")
    print(json.dumps(inspect_updater(sys.argv[1]), indent=2, sort_keys=True))

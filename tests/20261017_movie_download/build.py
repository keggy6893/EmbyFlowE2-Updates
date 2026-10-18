"""Build an unpublished local plugin; leave the release manifest untouched."""
from pathlib import Path
import ast
import types
from settings_patch import patch_settings
from install_library import patched as patch_library
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

def build_source():
    base = patch_settings((ROOT / 'EmbyFlowE2_2026101801.py').read_text())
    engine = (HERE / 'engine.py').read_text()
    assets = (HERE / 'style_assets.py').read_text()
    dialogs = (HERE / 'dialogs.py').read_text()
    ui = (HERE / 'ui.py').read_text()
    append = '\nimport types as _efdl_types\n_efdl_engine = _efdl_types.ModuleType("embyflow_movie_download")\nexec(compile(%r, "movie_download_engine.py", "exec"), _efdl_engine.__dict__)\n' % engine + assets + '\n' + dialogs + '\n' + ui
    output = patch_library(base + append, (HERE / 'library.py').read_text())
    output = output.replace('PLUGIN_VERSION = "2026-RCDEV-TEST-20261018-PGS-AUTO"', 'PLUGIN_VERSION = "2026-LOCAL-TEST-DOWNLOAD-LIMIT5"', 1)
    compile(output, 'plugin.py', 'exec')
    return output


if __name__ == '__main__':
    destination = Path('/workspace/local-artifacts/EmbyFlowE2_movie_download_LOCAL_v11.py')
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(build_source())
    print(destination)

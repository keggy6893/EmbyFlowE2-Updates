"""Upgrade a local v8/v9 download to quota plus visible counter, without reset."""
from pathlib import Path
import ast
import os
import shutil
import tempfile
import time
from install_quota import patched as quota_patch


def patched(source, engine, status_helper, display):
    if ('# EMBYFLOW_DOWNLOAD_QUOTA_DISPLAY_ADDON_V10' in source or
            '# EMBYFLOW_DOWNLOAD_QUOTA_VISIBLE_V10' in source):
        return source
    source = quota_patch(source, engine)
    start = source.index('exec(compile(', source.index('import types as _efdl_types'))
    end = source.index('\n', start)
    line = source[start:end]
    old = ast.parse(line).body[0].value.args[0].args[0].value
    if 'def quota_status():' not in old:
        if line.count(repr(old)) != 1:
            raise RuntimeError('Downloadmodul abweichend. Nichts geaendert.')
        source = source[:start] + line.replace(repr(old), repr(old + '\n\n' + status_helper + '\n'), 1) + source[end:]
    result = source + '\n\n' + display
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, engine, status_helper, display):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad.')
    source = path.read_text()
    result = patched(source, engine, status_helper, display)
    if result == source:
        print('Sichtbarer Tageszaehler bereits installiert.')
        return
    backup = str(path) + '.vor-dl-zaehler-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path, backup)
    fd, name = tempfile.mkstemp(prefix='plugin.py.dl-zaehler-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(result); handle.flush(); os.fsync(handle.fileno())
        shutil.copystat(path, name)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print('Tageslimit und sichtbarer Zaehler installiert. Sicherung:', backup)
    print('GUI neu starten. Download-Dialog zeigt Heute X von 5 und verbleibende Plaetze.')

"""Narrow V1 -> V2 display-parent test; no stream or audio changes."""
from pathlib import Path
import os
import shutil
import tempfile
import time

MARKER = '# EMBYFLOW_PGS_NATIVE_LOCAL_V1'
NEW_MARKER = '# EMBYFLOW_PGS_PARENT_LOCAL_V2'
OLD = "    widget = getattr(window, 'instance', None)"
NEW = "    widget = getattr(self, 'instance', None)"


def repaired(source):
    if NEW_MARKER in source:
        raise RuntimeError('PGS-Fenstertest V2 bereits vorhanden. Nichts geaendert.')
    before, sep, tail = source.partition(MARKER)
    if not sep or tail.count(OLD) != 1:
        raise RuntimeError('Passender PGS-V1-Test fehlt. Nichts geaendert.')
    result = before + sep + '\n' + NEW_MARKER + tail.replace(OLD, NEW, 1)
    compile(result, 'plugin.py', 'exec')
    return result


def main():
    path = Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad. Nichts geaendert.')
    result = repaired(path.read_text())
    backup = str(path) + '.vor-pgs-fenster-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path, backup)
    fd, name = tempfile.mkstemp(prefix='plugin.py.pgs-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(result)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copystat(path, name)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print('PGS-Fenstertest V2 installiert. Sicherung:', backup)
    print('GUI neu starten. Danach Deutsch PGS ohne Erzw. waehlen.')


if __name__ == '__main__':
    main()

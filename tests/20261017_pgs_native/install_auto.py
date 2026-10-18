"""Append only automatic selection to an installed, working V2 PGS test."""
from pathlib import Path
import os
import shutil
import tempfile
import time


def patched(source, patch):
    if '# EMBYFLOW_PGS_AUTO_LOCAL_V3' in source:
        raise RuntimeError('PGS-Automatik bereits installiert. Nichts geaendert.')
    before, marker, tail = source.partition('# EMBYFLOW_PGS_NATIVE_LOCAL_V1')
    if (not marker or '# EMBYFLOW_PGS_PARENT_LOCAL_V2' not in tail or
            "widget = getattr(self, 'instance', None)" not in tail or
            'def _efpg_start(' not in tail):
        raise RuntimeError('Der funktionierende PGS-Fenstertest V2 fehlt. Nichts geaendert.')
    result = source + '\n\n' + patch
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, patch):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad.')
    result = patched(path.read_text(), patch)
    backup = str(path) + '.vor-pgs-auto-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path, backup)
    fd, name = tempfile.mkstemp(prefix='plugin.py.pgs-auto-', dir=str(path.parent))
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
    print('PGS-Automatik installiert. Sicherung:', backup)
    print('GUI neu starten. Film frisch oeffnen und keine Untertitel manuell waehlen.')


if __name__ == '__main__':
    install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py',
            Path(__file__).with_name('auto.py').read_text())

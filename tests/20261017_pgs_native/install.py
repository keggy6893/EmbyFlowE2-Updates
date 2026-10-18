"""Install an appended local test without replacing any existing plugin features."""
from pathlib import Path
import os
import shutil
import tempfile
import time

MARKER = '# EMBYFLOW_PGS_NATIVE_LOCAL_V1'


def patched(source, patch):
    if MARKER in source:
        raise RuntimeError('PGS-Test bereits installiert. Nichts geaendert.')
    for required in ('def _efut2_streams(', 'def _embyflow_subtitle_finished_0629(',
                     'def _embyflow_srt_v2_stop('):
        if required not in source:
            raise RuntimeError('Diese Pluginversion passt nicht zum PGS-Test.')
    result = source + '\n\n' + patch
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, patch):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Pluginpfad ist ein Symlink. Nichts geaendert.')
    result = patched(path.read_text(), patch)
    backup = path.with_name(path.name + '.vor-pgs-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()))
    if backup.exists():
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
    print('PGS-Test installiert. Sicherung:', backup)
    print('GUI neu starten. Danach Deutsch PGS im Untertitelmenue manuell waehlen.')


if __name__ == '__main__':
    install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py',
            Path(__file__).with_name('patch.py').read_text())

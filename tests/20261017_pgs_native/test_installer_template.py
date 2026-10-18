"""Single-file installer template; build_test.py embeds the tested patches."""
from pathlib import Path
import os
import shutil
import tempfile
import time

NATIVE_MARKER = '# EMBYFLOW_PGS_NATIVE_LOCAL_V1'
PARENT_MARKER = '# EMBYFLOW_PGS_PARENT_LOCAL_V2'
AUTO_MARKER = '# EMBYFLOW_PGS_AUTO_LOCAL_V3'


def patched(source, native_patch, auto_patch):
    for required in ('def _efut2_streams(', 'def _embyflow_subtitle_finished_0629(',
                     'def _embyflow_srt_v2_stop('):
        if required not in source:
            raise RuntimeError('Basis mit aktivem MediaSource-UT-Fix fehlt. Bitte zuerst EmbyFlow aktualisieren.')
    result = source
    if NATIVE_MARKER not in result:
        if PARENT_MARKER in result or AUTO_MARKER in result:
            raise RuntimeError('Unvollstaendige PGS-Installation. Nichts geaendert.')
        result += '\n\n' + native_patch
    elif PARENT_MARKER not in result:
        before, sep, tail = result.partition(NATIVE_MARKER)
        old = "    widget = getattr(window, 'instance', None)"
        if tail.count(old) != 1:
            raise RuntimeError('PGS-V1-Einbaustelle abweichend. Nichts geaendert.')
        result = before + sep + '\n' + PARENT_MARKER + tail.replace(
            old, "    widget = getattr(self, 'instance', None)", 1)
    if AUTO_MARKER not in result:
        result += '\n\n' + auto_patch
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, native_patch, auto_patch):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Pluginpfad ist ein Symlink. Nichts geaendert.')
    source = path.read_text()
    result = patched(source, native_patch, auto_patch)
    if source == result:
        print('PGS-Test mit Automatik bereits installiert. Nichts geaendert.')
        return
    backup = str(path) + '.vor-pgs-test-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
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
    print('PGS-Test mit Automatik installiert. Sicherung:', backup)
    print('GUI neu starten. Film frisch oeffnen und keine Untertitel manuell waehlen.')

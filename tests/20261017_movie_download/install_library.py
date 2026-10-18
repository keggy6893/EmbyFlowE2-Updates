"""Append the offline library to an existing local download build atomically."""
from pathlib import Path
import os
import shutil
import tempfile
import time


def patched(source, library):
    if '# EMBYFLOW_DOWNLOAD_LIBRARY_LOCAL_V11' in source:
        return source
    if '# EMBYFLOW_LOCAL_MOVIE_DOWNLOAD_20261017' not in source:
        raise RuntimeError('Lokale Downloadfunktion fehlt. Nichts geaendert.')
    needle = "            self.events.put(('done', path))"
    if source.count(needle) != 1:
        raise RuntimeError('Downloadversion abweichend. Nichts geaendert.')
    source = source.replace(needle, "            _efdl_library_save(path, self.item, self.data)\n" + needle, 1)
    result = source + '\n\n' + library
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, library):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad.')
    source = path.read_text()
    result = patched(source, library)
    if result == source:
        print('Downloaduebersicht bereits installiert.')
        return
    backup = str(path) + '.vor-downloads-v11-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path, backup)
    fd, temporary = tempfile.mkstemp(prefix='plugin.py.downloads-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(result)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copystat(path, temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('Downloads-Uebersicht installiert. Sicherung:', backup)
    print('Nach GUI-Neustart: EmbyFlow > Downloads > OK zum Abspielen.')

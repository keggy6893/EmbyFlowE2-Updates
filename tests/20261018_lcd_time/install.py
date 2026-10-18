"""Receiver-local addon; compile, back up and replace without changing LCD4linux."""
from pathlib import Path
import os
import shutil
import tempfile
import time


def patched(source, runtime):
    if '# EMBYFLOW_LCD_CONTENT_CLOCK_V1' in source:
        return source
    for required in ('class EmbyFlowMoviePlayer', 'def current_position_ticks(', 'def item_duration_ticks('):
        if required not in source:
            raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
    result = source + '\n\n' + runtime
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, runtime):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad.')
    source = path.read_text()
    result = patched(source, runtime)
    if source == result:
        print('LCD-Zeittest bereits installiert.', flush=True)
        return False
    backup = str(path)+'.vor-lcdzeit-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path, backup)
    fd, name = tempfile.mkstemp(prefix='plugin.py.lcd-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(result);handle.flush();os.fsync(handle.fileno())
        shutil.copystat(path, name)
        os.replace(name, path)
    finally:
        if os.path.exists(name):os.unlink(name)
    print('LCD-Zeittest installiert. Sicherung:', backup, flush=True)
    return True

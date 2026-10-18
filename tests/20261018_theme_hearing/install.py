from pathlib import Path
import os
import shutil
import tempfile
import time


def patched(source, runtime):
    if '# EMBYFLOW_AUTOMATIC_THEME_HEARING_V1' in source:return source
    for required in ('def _efbg_music(', 'def _triso_code(', 'def _efserver_theme_url(', 'def _efbg_cancel('):
        if required not in source:raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
    result = source+'\n\n'+runtime
    compile(result,'plugin.py','exec')
    return result


def install(path, runtime):
    path=Path(path)
    if path.is_symlink():raise RuntimeError('Unerwarteter Pluginpfad.')
    source=path.read_text();result=patched(source,runtime)
    if source == result:
        print('Theme-Hoertest bereits installiert.',flush=True)
        return False
    backup=str(path)+'.vor-theme-hoertest-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    if os.path.exists(backup):raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path,backup)
    fd,name=tempfile.mkstemp(prefix='plugin.py.theme-',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w') as handle:
            handle.write(result);handle.flush();os.fsync(handle.fileno())
        shutil.copystat(path,name);os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
    print('Theme-Hoertest installiert. Sicherung:',backup,flush=True)
    return True

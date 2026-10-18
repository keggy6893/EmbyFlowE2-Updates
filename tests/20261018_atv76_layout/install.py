"""Append-only local openATV 7.6 detail layout test with a backup."""
from pathlib import Path
import os
import shutil
import tempfile
import time


def patch(source,addon):
    if '# EMBYFLOW_ATV76_DETAIL_LAYOUT_LOCAL_V1' in source:return source
    for required in ('class EmbyFlowDetailScreen','EMBYFLOW_CINEMA_POLISH_V2_20261013','EMBYFLOW_DETAIL_TEXT_SPACE_V4_20261013'):
        if required not in source:raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
    result=source+'\n\n'+addon
    compile(result,'plugin.py','exec')
    return result


def install(path,addon):
    path=Path(path)
    if path.is_symlink():raise RuntimeError('Pluginpfad ungueltig.')
    source=path.read_text();result=patch(source,addon)
    if result==source:print('Layout-Test bereits installiert.');return
    backup=str(path)+'.vor-atv76-layout-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    if os.path.exists(backup):raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path,backup)
    fd,name=tempfile.mkstemp(prefix='plugin.py.atv76-layout-',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w') as handle:
            handle.write(result);handle.flush();os.fsync(handle.fileno())
        shutil.copystat(path,name);os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
    print('ATV-7.6-Layout-Test installiert. Sicherung:',backup)
    print('GUI neu starten und dieselbe Film-Detailseite oeffnen.')

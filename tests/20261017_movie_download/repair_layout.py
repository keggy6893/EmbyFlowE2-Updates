"""Repair only the openATV layout callback, preserving the installed plugin."""
import ast
import os
from pathlib import Path
import shutil
import tempfile
import time

OLD = "        self.onLayoutFinish.append(lambda: _efdl_style_apply(self['panel'], 'panel'))"
NEW = '        self.onLayoutFinish.append(self._efdl_layout)'
ANCHOR = '    def cleanup(self):\n'
METHOD = "    def _efdl_layout(self):\n        _efdl_style_apply(self['panel'], 'panel')\n\n"

def patched(source):
    start = source.index('class EmbyFlowLocalDownloadScreen(Screen):')
    end = source.index('_EFDL_DETAIL_INIT =', start)
    block = source[start:end]
    if OLD not in block and NEW in block and METHOD in block:
        return source
    if block.count(OLD) != 1 or block.count(ANCHOR) != 1 or 'def _efdl_layout(' in block:
        raise ValueError('Download-Layout nicht eindeutig erkannt. Nichts geaendert.')
    block = block.replace(OLD, NEW, 1).replace(ANCHOR, METHOD + ANCHOR, 1)
    result = source[:start] + block + source[end:]
    ast.parse(result)
    compile(result, 'plugin.py', 'exec')
    return result

def main():
    target = Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    source = target.read_text()
    result = patched(source)
    if source == result:
        print('Layout-Reparatur ist bereits vorhanden.')
        return
    backup = target.with_name('plugin.py.vor-layout-reparatur-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()))
    if backup.exists():
        raise ValueError('Sicherung existiert bereits. Nichts geaendert.')
    shutil.copy2(str(target), str(backup))
    fd, name = tempfile.mkstemp(prefix='plugin.py.layout-', dir=str(target.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(result)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copystat(str(target), name)
        os.replace(name, str(target))
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print('Download-Layout repariert. Sicherung: ' + str(backup))

if __name__ == '__main__':
    main()

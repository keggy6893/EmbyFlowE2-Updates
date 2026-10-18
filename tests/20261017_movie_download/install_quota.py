"""Patch an existing local download plugin, preserving PGS and other additions."""
from pathlib import Path
import ast
import os
import shutil
import tempfile
import time

REPLACEMENTS = (
    ("            if item.get('Type') != 'Movie':\n                raise ValueError('Dieser Test unterstuetzt nur Filme.')",
     "            if item.get('Type') not in ('Movie', 'Episode'):\n                raise ValueError('Bitte einen Film oder eine einzelne Serienfolge waehlen.')"),
    ("    if not self._efdl_button_enabled or _efsv_episode(self):",
     "    if not self._efdl_button_enabled or str(data.get('type') or data.get('Type') or 'Movie').lower() not in ('movie', 'episode'):"),
)


def patched(source, engine):
    marker = 'import types as _efdl_types'
    if source.count(marker) != 1:
        raise RuntimeError('Passender lokaler Download-Test fehlt. Nichts geaendert.')
    start = source.index('exec(compile(', source.index(marker))
    end = source.index('\n', start)
    line = source[start:end]
    old = ast.parse(line).body[0].value.args[0].args[0].value
    if 'class DailyQuota:' in old:
        if all(new in source for previous, new in REPLACEMENTS):
            return source
        raise RuntimeError('Unvollstaendiger Tageslimit-Test. Nichts geaendert.')
    if line.count(repr(old)) != 1:
        raise RuntimeError('Unerwartetes Downloadmodul. Nichts geaendert.')
    result = source[:start] + line.replace(repr(old), repr(engine), 1) + source[end:]
    for old, new in REPLACEMENTS:
        if result.count(old) != 1:
            raise RuntimeError('Download-Einbaustelle abweichend. Nichts geaendert.')
        result = result.replace(old, new, 1)
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, engine):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad.')
    source = path.read_text()
    result = patched(source, engine)
    if source == result:
        print('Tageslimit von 5 Downloads bereits eingebaut.')
        return
    backup = str(path) + '.vor-dl-limit5-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path, backup)
    fd, name = tempfile.mkstemp(prefix='plugin.py.dl-limit-', dir=str(path.parent))
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
    print('Film-/Folgen-Download: zusammen maximal 5 pro Tag. Sicherung:', backup)
    print('GUI neu starten. PGS und vorhandene lokale Funktionen bleiben erhalten.')


if __name__ == '__main__':
    install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py',
            Path(__file__).with_name('engine.py').read_text())

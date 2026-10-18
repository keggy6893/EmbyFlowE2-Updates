#!/usr/bin/env python3
"""Optional SRT readability test; preserves all other plugin code and settings."""
from pathlib import Path
import os
import re
import shutil
import tempfile
import time

MARKER = '# EMBYFLOW_SRT_READABLE_V1'
WIDGET = re.compile(r'<widget\b[^>]*\bname="external_subtitle_text"[^>]*/>', re.S)


def patched(source):
    widgets = list(WIDGET.finditer(source))
    if len(widgets) != 1:
        raise RuntimeError('SRT-Textfeld nicht eindeutig gefunden. Nichts geaendert.')
    match = widgets[0]
    widget = match.group()
    values = {'position': '150,810', 'size': '1620,180',
              'font': 'Regular;52', 'valign': 'bottom'}
    for attribute, value in values.items():
        pattern = r'\b' + attribute + r'="[^"]*"'
        if len(re.findall(pattern, widget)) != 1:
            raise RuntimeError('SRT-Layout weicht ab. Nichts geaendert.')
        widget = re.sub(pattern, attribute + '="' + value + '"', widget)
    result = source[:match.start()] + widget + source[match.end():]
    if MARKER not in result:
        result += '\n' + MARKER + '\n'
    compile(result, 'plugin.py', 'exec')
    return result


def install(path):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad. Nichts geaendert.')
    source = path.read_text(encoding='utf-8')
    result = patched(source)
    if result == source:
        print('Groessere SRT-Schrift bereits installiert.', flush=True)
        return False
    backup = str(path) + '.vor-srt-schrift-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits. Nichts geaendert.')
    shutil.copy2(path, backup)
    descriptor, temporary = tempfile.mkstemp(prefix='plugin.py.srt-', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(result)
            output.flush()
            os.fsync(output.fileno())
        shutil.copystat(path, temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('SRT-Schrift: 52 statt 25 (Full HD), automatische HD-Skalierung.', flush=True)
    print('Sicherung:', backup, flush=True)
    return True


if __name__ == '__main__':
    if install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py'):
        print('GUI startet neu. Danach Mayday mit SRT testen.', flush=True)
        os.system('init 4')
        time.sleep(3)
        os.system('init 3')

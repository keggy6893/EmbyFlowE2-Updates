#!/usr/bin/env python3
"""Expose source-finalization fields above their opaque background."""
import ast
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from datetime import datetime


def transform(source):
    tree = ast.parse(source)
    nodes = [node for node in tree.body if isinstance(node, ast.ClassDef)
             and node.name == 'EmbyFlowLocalSourceFinalizeScreenV18']
    if len(nodes) != 1:
        raise ValueError('Erwarteter Abschlussdialog nicht eindeutig vorhanden.')
    node = nodes[0]
    lines = source.splitlines(keepends=True)
    before = ''.join(lines[node.lineno - 1:node.end_lineno])
    changed = []

    def replace(match):
        tag = match.group(0)
        name = match.group(1)
        if re.search(r'\bzPosition\s*=', tag):
            raise ValueError('Anzeigeebene fuer %s bereits gesetzt; nichts geaendert.' % name)
        changed.append(name)
        return tag[:-2] + ' zPosition="3" />'

    after = re.sub(r'<widget\s+name="(path|config|hint)"[^>]*?/>', replace, before)
    if sorted(changed) != ['config', 'hint', 'path']:
        raise ValueError('Abschlussfelder weichen vom geprueften Stand ab.')
    result = ''.join(lines[:node.lineno - 1]) + after + ''.join(lines[node.end_lineno:])
    compile(result, '<EmbyFlowE2-folder-textfix>', 'exec')
    return result


def main():
    path = Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    original = path.read_bytes()
    updated = transform(original.decode('utf-8')).encode('utf-8')
    backup = path.with_name(path.name + '.before_source_text_' +
                            datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')
    if path.read_bytes() != original:
        raise RuntimeError('Quelldatei wurde geaendert; Abbruch.')
    shutil.copy2(path, backup)
    if backup.read_bytes() != original:
        raise RuntimeError('Sicherung stimmt nicht mit dem Original ueberein.')
    info = path.stat()
    fd, temporary = tempfile.mkstemp(prefix='.folder_text_', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(updated)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, stat.S_IMODE(info.st_mode))
        if hasattr(os, 'chown'):
            os.chown(temporary, info.st_uid, info.st_gid)
        if path.read_bytes() != original:
            raise RuntimeError('Quelldatei wurde geaendert; Abbruch.')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('Sicherung: ' + str(backup))
    print('OK: Nur Pfad, Name-/Typ-Liste und Hinweis im Abschlussdialog auf Ebene 3 gesetzt. Syntax korrekt.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ABBRUCH: ' + str(error), file=sys.stderr)
        sys.exit(1)

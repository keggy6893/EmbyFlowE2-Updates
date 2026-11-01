#!/usr/bin/env python3
"""Selected-source panel for EmbyFlowE2; preserves existing card layout/player."""
import argparse
import ast
from datetime import datetime
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

RUNTIME = "# EMBYFLOW_SOURCE_CARD_FOCUS_V1_20261101_BEGIN\n_EFSCF_INIT = EmbyFlowLocalSourcesScreenV17.__init__\n_EFSCF_REFRESH = EmbyFlowLocalSourcesScreenV17.refresh\n_EFSCF_BG = EmbyFlowLocalSourcesScreenV17._set_bg_color\n\n\ndef _efscf_init(screen, *args, **kwargs):\n    _EFSCF_INIT(screen, *args, **kwargs)\n    screen['source_selection_fill'] = Label(' ')\n\n\ndef _efscf_bg(screen, name, color):\n    # The five base tiles now keep their skin color. Only one separate fill moves.\n    if name in ('card_bg0', 'card_bg1', 'card_bg2', 'card_bg3', 'card_bg4'):\n        return\n    return _EFSCF_BG(screen, name, color)\n\n\ndef _efscf_refresh(screen):\n    result = _EFSCF_REFRESH(screen)\n    if 'source_selection_fill' not in screen:\n        return result\n    fill = screen['source_selection_fill']\n    if fill.instance is None:\n        return result\n    index = int(getattr(screen, 'selected_index', 0) or 0)\n    offset = int(getattr(screen, 'card_offset', 0) or 0)\n    count = len(getattr(screen, 'sources', []) or [])\n    slot = index - offset\n    # The existing virtual All Media tile is placed after the real sources.\n    valid = count > 0 and 0 <= index <= count and 0 <= slot < 5\n    if valid and getattr(screen, 'focus_zone_v17', 'cards') == 'cards':\n        fill.instance.move(EFP(205 + slot * 216, 330))\n        fill.show()\n        fill.instance.show()\n    else:\n        fill.hide()\n        if fill.instance:\n            fill.instance.hide()\n    return result\n\n\nEmbyFlowLocalSourcesScreenV17.__init__ = _efscf_init\nEmbyFlowLocalSourcesScreenV17._set_bg_color = _efscf_bg\nEmbyFlowLocalSourcesScreenV17.refresh = _efscf_refresh\n# EMBYFLOW_SOURCE_CARD_FOCUS_V1_20261101_END\n"
PANEL = '''
            <widget name="source_info_icon" position="1325,282" size="90,90" zPosition="10" alphatest="blend" />
            <widget name="source_info_name" position="1430,282" size="390,70" font="Bold;26" foregroundColor="#F4F7FB" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="source_info_type" position="1430,355" size="390,34" font="Regular;21" foregroundColor="#AEB8C5" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="source_info_state" position="1320,410" size="500,34" font="Regular;21" foregroundColor="#53D769" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <eLabel text="Speicherort" position="1320,453" size="500,28" font="Regular;19" foregroundColor="#8190A4" backgroundColor="#0C1827" transparent="1" zPosition="5" />
            <widget name="source_info_path" position="1320,485" size="500,80" font="Regular;20" foregroundColor="#AEB8C5" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="source_info_content" position="1320,580" size="500,56" font="Regular;21" foregroundColor="#F4F7FB" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="source_info_storage" position="1320,650" size="500,30" font="Regular;19" foregroundColor="#AEB8C5" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="source_info_checked" position="1320,695" size="500,30" font="Regular;19" foregroundColor="#8190A4" backgroundColor="#0C1827" transparent="1" zPosition="10" />
'''


def transform(source):
    if '# EMBYFLOW_SOURCE_CARD_FOCUS_V1_20261101_BEGIN' in source:
        raise ValueError('Kachel-Fokus V1 ist bereits installiert; nichts geaendert.')
    tree = ast.parse(source)
    constants = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_EMBYFLOW_V16_CARD_SKIN' for t in n.targets)]
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'EmbyFlowLocalSourcesScreenV17']
    if len(constants) != 1 or len(classes) != 1:
        raise ValueError('Erwartete Quellen-Kacheln fehlen; Abbruch.')
    nodes = [n for n in classes[0].body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'skin' for t in n.targets)]
    if len(nodes) != 1:
        raise ValueError('Quellen-Skin nicht eindeutig.')
    lines = source.splitlines(keepends=True)
    const = constants[0]
    oldconst = ''.join(lines[const.lineno-1:const.end_lineno])
    pattern = r'(<widget name="card_bg%d"[^>]*?backgroundColor=")#0C1827(")'
    newconst, number = re.subn(pattern, r'\g<1>#0D2138\2', oldconst)
    if number != 1:
        raise ValueError('Kachelhintergrund weicht vom geprueften Stand ab.')
    node = nodes[0]
    oldskin = ''.join(lines[node.lineno-1:node.end_lineno])
    if oldskin.count('_EMBYFLOW_V16_CARD_SKIN') != 1:
        raise ValueError('Kacheleinbindung nicht eindeutig.')
    addition = '\n<widget name="source_selection_fill" position="205,330" size="200,302" backgroundColor="#12355C" transparent="0" cornerRadius="12" zPosition="2" />\n'
    newskin = oldskin.replace('_EMBYFLOW_V16_CARD_SKIN', '_EMBYFLOW_V16_CARD_SKIN + ' + repr(addition), 1)
    edits = [(const.lineno-1, const.end_lineno, newconst), (node.lineno-1, node.end_lineno, newskin)]
    for start, stop, changed in sorted(edits, reverse=True):
        lines[start:stop] = [changed]
    result = ''.join(lines).rstrip() + '\n\n' + RUNTIME.rstrip() + '\n'
    compile(result, '<EmbyFlowE2-card-focus>', 'exec')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--path', default='/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    args = parser.parse_args()
    path = Path(args.path)
    original = path.read_bytes()
    after = transform(original.decode('utf-8')).encode('utf-8')
    print('Quellenansicht gefunden; vollstaendige Syntaxpruefung: OK')
    if not args.apply:
        print('Nur geprueft, keine Datei geaendert.')
        return
    backup = path.with_name(path.name + '.before_card_focus_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')
    if path.read_bytes() != original:
        raise RuntimeError('Quelle wurde zwischenzeitlich geaendert.')
    shutil.copy2(path, backup)
    if backup.read_bytes() != original:
        raise RuntimeError('Sicherungspruefung fehlgeschlagen.')
    details = path.stat()
    fd, temporary = tempfile.mkstemp(prefix='.card_focus_', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(details.st_mode))
        if hasattr(os, 'chown'):
            os.chown(temporary, details.st_uid, details.st_gid)
        if path.read_bytes() != original:
            raise RuntimeError('Quelle wurde zwischenzeitlich geaendert.')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('Sicherung: ' + str(backup))
    print('OK: Kachelfokus mit einer beweglichen Auswahlflaeche installiert. SHA256: ' + hashlib.sha256(after).hexdigest())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ABBRUCH: ' + str(error), file=sys.stderr)
        sys.exit(1)

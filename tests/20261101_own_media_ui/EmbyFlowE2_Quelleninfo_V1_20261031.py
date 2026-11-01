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

RUNTIME = "# EMBYFLOW_SELECTED_SOURCE_INFO_V1_20261031_BEGIN\nimport queue as _efsi_queue\nimport threading as _efsi_threading\nimport textwrap as _efsi_textwrap\n\n_EFSI_INIT = EmbyFlowLocalSourcesScreenV17.__init__\n_EFSI_REFRESH = EmbyFlowLocalSourcesScreenV17.refresh\n_EFSI_CLEANUP = EmbyFlowLocalSourcesScreenV17.cleanup\n_EFSI_STATUS_REFRESH = EmbyFlowLocalSourcesScreenV17.refresh_sources\n\n\ndef _efsi_key(source):\n    return (str(source.get('id') or ''), str(source.get('path') or ''),\n            str(source.get('mode') or 'mixed'))\n\n\ndef _efsi_probe(source, cancelled):\n    import shutil\n    result = dict(online=False, checked=time.time(), connection='',\n                  free=None, videos=0, folders=0, partial=False)\n    path = os.path.realpath(str(source.get('path') or ''))\n    network = source.get('network') or {}\n    protocol = str(network.get('protocol') or '').lower()\n    is_network = protocol in ('smb', 'cifs', 'nfs', 'nfs4')\n    best = ''\n    try:\n        with open('/proc/mounts', 'r') as handle:\n            for line in handle:\n                fields = line.split()\n                if len(fields) < 4:\n                    continue\n                mount = fields[1].replace('\\\\040', ' ').replace('\\\\011', '\\t').replace('\\\\134', '\\\\')\n                if (path == mount or path.startswith(mount.rstrip('/') + '/')) and len(mount) > len(best):\n                    best = mount\n                    kind = fields[2].lower()\n                    if kind == 'cifs':\n                        is_network = True\n                        version = next((v[5:] for v in fields[3].split(',') if v.startswith('vers=')), '')\n                        result['connection'] = 'Netzwerk · ' + ('SMB3' if version.startswith('3') else 'SMB2' if version.startswith('2') else 'SMB/CIFS')\n                    elif kind in ('nfs', 'nfs4'):\n                        is_network = True\n                        result['connection'] = 'Netzwerk · NFS'\n                    elif kind != 'autofs':\n                        result['connection'] = ('USB-Laufwerk' if path.startswith('/media/usb') else 'Lokaler Datenträger')\n    except OSError:\n        pass\n    if '/autofs/' in path or '/net/' in path:\n        is_network = True\n    if not result['connection']:\n        result['connection'] = 'Netzwerkquelle' if is_network else 'Lokaler Ordner'\n    deadline = time.monotonic() + 1.5\n    try:\n        with os.scandir(path) as entries:\n            result['online'] = True\n            for number, entry in enumerate(entries):\n                if cancelled.is_set():\n                    return result\n                if number >= 5000 or time.monotonic() > deadline:\n                    result['partial'] = True\n                    break\n                if entry.name.startswith('.'):\n                    continue\n                try:\n                    if entry.is_dir(follow_symlinks=False):\n                        result['folders'] += 1\n                    elif entry.is_file(follow_symlinks=False) and os.path.splitext(entry.name)[1].lower() in EMBYFLOW_LOCAL_VIDEO_EXTENSIONS:\n                        result['videos'] += 1\n                except OSError:\n                    continue\n        # Do not risk a blocking network statvfs call. Missing space stays unknown.\n        if not is_network and not cancelled.is_set():\n            try:\n                result['free'] = shutil.disk_usage(path).free\n            except OSError:\n                pass\n    except OSError:\n        result['online'] = False\n    result['checked'] = time.time()\n    return result\n\n\ndef _efsi_start_pending(screen):\n    if screen._efsi_busy or screen._efsi_cancel.is_set() or screen._efsi_pending is None:\n        return\n    source = screen._efsi_pending\n    screen._efsi_pending = None\n    key = _efsi_key(source)\n    results, cancelled = screen._efsi_results, screen._efsi_cancel\n    screen._efsi_busy = True\n\n    def worker():\n        try:\n            result = _efsi_probe(source, cancelled)\n        except Exception:\n            result = dict(online=False, checked=time.time(), connection='Nicht ermittelt',\n                          free=None, videos=0, folders=0, partial=False)\n        if not cancelled.is_set():\n            results.put((key, result))\n\n    try:\n        _efsi_threading.Thread(target=worker, name='EmbyFlowSourceInfo', daemon=True).start()\n    except Exception:\n        screen._efsi_busy = False\n        screen._efsi_cache[key] = dict(online=False, checked=time.time(), connection='Prüfung nicht verfügbar',\n                                      free=None, videos=0, folders=0, partial=False)\n    if screen._efsi_busy:\n        screen._efsi_timer.start(120, True)\n\n\ndef _efsi_selected(screen):\n    index = int(getattr(screen, 'selected_index', 0) or 0)\n    sources = list(getattr(screen, 'sources', []) or [])\n    return sources[index] if 0 <= index < len(sources) else None\n\n\ndef _efsi_draw(screen):\n    if screen._efsi_cancel.is_set():\n        return\n    source = _efsi_selected(screen)\n    if source is None:\n        screen._efsi_pending = None\n        screen['source_info_name'].setText('Alle Medien' if screen.sources else 'Keine Quelle ausgewählt')\n        screen['source_info_type'].setText('Gemeinsame Übersicht' if screen.sources else '')\n        screen['source_info_state'].setText('%d eingerichtete Quellen' % len(screen.sources) if screen.sources else '')\n        screen['source_info_path'].setText('Alle eingerichteten Medienquellen' if screen.sources else 'Medienquelle hinzufügen')\n        screen['source_info_content'].setText('OK öffnet die gemeinsame Übersicht.' if screen.sources else '')\n        screen['source_info_storage'].setText('')\n        screen['source_info_checked'].setText('')\n        screen['source_info_icon'].hide()\n        return\n    key = _efsi_key(source)\n    result = screen._efsi_cache.get(key)\n    fresh = result is not None and 0 <= time.time() - result['checked'] < 60\n    screen['source_info_name'].setText(str(source.get('name') or 'Medienquelle'))\n    screen['source_info_type'].setText(_embyflow_v16_source_type_label(str(source.get('mode') or 'mixed')))\n    path = str(source.get('path') or '')\n    rows = _efsi_textwrap.wrap(path, width=45, break_long_words=True, break_on_hyphens=False) or ['—']\n    screen['source_info_path'].setText('\\n'.join(rows[:2] + [rows[2] if len(rows) == 3 else rows[2][:42] + '…'] if len(rows) > 2 else rows))\n    screen._show_icon('source_info_icon', source)\n    if result is None:\n        screen['source_info_state'].setText('Quelle wird geprüft …')\n        screen._set_text_color('source_info_state', '#8190A4')\n        screen['source_info_content'].setText('Direkt enthalten: wird ermittelt …')\n        screen['source_info_storage'].setText('')\n        screen['source_info_checked'].setText('')\n    else:\n        screen['source_info_state'].setText(('Online' if result['online'] else 'Nicht erreichbar') + ' · ' + result['connection'])\n        screen._set_text_color('source_info_state', '#53D769' if result['online'] else '#FF5B57')\n        suffix = '+' if result['partial'] else ''\n        content = 'Direkt enthalten:\\n%d%s Videodateien · %d%s Unterordner' % (result['videos'], suffix, result['folders'], suffix) if result['online'] else 'Inhalt derzeit nicht abrufbar'\n        screen['source_info_content'].setText(content)\n        free = result.get('free')\n        screen['source_info_storage'].setText('Freier Speicher: ' + str(embyflow_local_human_size(free)).replace('.', ',') if free is not None else 'Freier Speicher: keine Angabe')\n        screen['source_info_checked'].setText('Zuletzt geprüft: ' + time.strftime('%H:%M:%S', time.localtime(result['checked'])))\n    if fresh:\n        screen._efsi_pending = None\n    else:\n        # Only one worker; while it runs, keep just the most recent selection.\n        screen._efsi_pending = {k: source[k] for k in ('id', 'path', 'mode') if k in source}\n        network = source.get('network')\n        if isinstance(network, dict):\n            screen._efsi_pending['network'] = {'protocol': str(network.get('protocol') or '')}\n        _efsi_start_pending(screen)\n\n\ndef _efsi_poll(screen):\n    if screen._efsi_cancel.is_set():\n        return\n    try:\n        key, result = screen._efsi_results.get_nowait()\n    except _efsi_queue.Empty:\n        if screen._efsi_busy:\n            screen._efsi_timer.start(120, True)\n        return\n    screen._efsi_cache[key] = result\n    screen._efsi_busy = False\n    # Re-read the selected source, never paint a stale worker's source directly.\n    _efsi_draw(screen)\n\n\ndef _efsi_init(screen, *args, **kwargs):\n    screen._efsi_cancel = _efsi_threading.Event()\n    screen._efsi_results = _efsi_queue.Queue()\n    screen._efsi_cache = {}\n    screen._efsi_pending = None\n    screen._efsi_busy = False\n    _EFSI_INIT(screen, *args, **kwargs)\n    for name in ('name', 'type', 'state', 'path', 'content', 'storage', 'checked'):\n        screen['source_info_' + name] = Label('')\n    screen['source_info_icon'] = Pixmap()\n    screen._efsi_timer = eTimer()\n    callback = lambda: _efsi_poll(screen)\n    try:\n        screen._efsi_timer.callback.append(callback)\n    except AttributeError:\n        screen._efsi_connection = screen._efsi_timer.timeout.connect(callback)\n\n\ndef _efsi_refresh(screen):\n    result = _EFSI_REFRESH(screen)\n    if hasattr(screen, '_efsi_timer'):\n        _efsi_draw(screen)\n    return result\n\n\ndef _efsi_cleanup(screen):\n    if hasattr(screen, '_efsi_cancel'):\n        screen._efsi_cancel.set()\n        screen._efsi_pending = None\n        if hasattr(screen, '_efsi_timer'):\n            screen._efsi_timer.stop()\n    return _EFSI_CLEANUP(screen)\n\n\ndef _efsi_status_refresh(screen):\n    screen._efsi_cache.clear()\n    result = _EFSI_STATUS_REFRESH(screen)\n    if hasattr(screen, '_efsi_timer'):\n        _efsi_draw(screen)\n    return result\n\n\nEmbyFlowLocalSourcesScreenV17.__init__ = _efsi_init\nEmbyFlowLocalSourcesScreenV17.refresh = _efsi_refresh\nEmbyFlowLocalSourcesScreenV17.cleanup = _efsi_cleanup\nEmbyFlowLocalSourcesScreenV17.refresh_sources = _efsi_status_refresh\n# EMBYFLOW_SELECTED_SOURCE_INFO_V1_20261031_END\n"
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
    if '# EMBYFLOW_SELECTED_SOURCE_INFO_V1_20261031_BEGIN' in source:
        raise ValueError('Quelleninfo ist bereits installiert. Nichts geaendert.')
    tree = ast.parse(source)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)
               and n.name == 'EmbyFlowLocalSourcesScreenV17']
    if len(classes) != 1:
        raise ValueError('Erwartete Quellenansicht fehlt oder ist mehrdeutig.')
    skins = [n for n in classes[0].body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'skin' for t in n.targets)]
    if len(skins) != 1:
        raise ValueError('Erwarteter Skin fehlt oder ist mehrdeutig.')
    node = skins[0]
    lines = source.splitlines(keepends=True)
    skin = ''.join(lines[node.lineno - 1:node.end_lineno])
    if skin.count('_EMBYFLOW_V16_MANAGER_ROWS_SKIN') != 1 or skin.count('text="Quellen verwalten"') != 1:
        raise ValueError('Quellen-Skin weicht vom geprueften Stand ab.')
    updated = skin.replace('_EMBYFLOW_V16_MANAGER_ROWS_SKIN', repr(PANEL), 1)
    updated = updated.replace('text="Quellen verwalten"', 'text="Quelleninformationen"', 1)
    def hint(match):
        tag = match.group(0)
        return tag if re.search(r'\bzPosition\s*=', tag) else tag[:-2] + ' zPosition="10" />'
    updated, count = re.subn(r'<widget\s+name="manager_hint"[^>]*?/>', hint, updated)
    if count != 1:
        raise ValueError('Quellen-Hinweis nicht eindeutig vorhanden.')
    result = ''.join(lines[:node.lineno - 1]) + updated + ''.join(lines[node.end_lineno:])
    result = result.rstrip() + '\n\n' + RUNTIME.rstrip() + '\n'
    compile(result, '<EmbyFlowE2-source-info>', 'exec')
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
    backup = path.with_name(path.name + '.before_source_info_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')
    if path.read_bytes() != original:
        raise RuntimeError('Quelle wurde zwischenzeitlich geaendert.')
    shutil.copy2(path, backup)
    if backup.read_bytes() != original:
        raise RuntimeError('Sicherungspruefung fehlgeschlagen.')
    details = path.stat()
    fd, temporary = tempfile.mkstemp(prefix='.source_info_', dir=str(path.parent))
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
    print('OK: Quelleninformationen installiert. SHA256: ' + hashlib.sha256(after).hexdigest())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ABBRUCH: ' + str(error), file=sys.stderr)
        sys.exit(1)

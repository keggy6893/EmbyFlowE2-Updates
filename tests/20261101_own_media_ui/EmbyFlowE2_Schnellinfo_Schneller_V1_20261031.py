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

RUNTIME = "# EMBYFLOW_QUICKSTATS_FAST_V1_20261031_BEGIN\nimport threading as _efqs_threading\n\n\ndef _efqs_inside(root, path):\n    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)\n\n\ndef _efqs_scan(snapshot, cancelled):\n    started = time.monotonic()\n    stats = dict(movies=0, series=0, episodes=0, docs=0, size=0, truncated=False)\n    series_names, seen_files, completed = set(), set(), set()\n    files = folders = pruned = 0\n    skipped = set(EMBYFLOW_LOCAL_LIBRARY_SKIP_DIRS_V3)\n    for source in sorted(snapshot, key=lambda item: len(str(item.get('path') or '')), reverse=True):\n        if cancelled.is_set():\n            return None\n        raw = str(source.get('path') or '')\n        if not raw:\n            continue\n        root = os.path.realpath(raw)\n        if root in completed:\n            continue\n        mode = str(source.get('mode') or 'mixed').casefold()\n        stack = [root]\n        root_ok = True\n        while stack and not stats['truncated']:\n            if cancelled.is_set():\n                return None\n            current = stack.pop()\n            if current != root and current in completed:\n                pruned += 1\n                continue\n            try:\n                with os.scandir(current) as entries:\n                    folders += 1\n                    for entry in entries:\n                        if cancelled.is_set():\n                            return None\n                        try:\n                            # Match os.walk(followlinks=False): never descend directory links.\n                            if entry.is_dir(follow_symlinks=False):\n                                if not entry.name.startswith('.') and entry.name.casefold() not in skipped:\n                                    if entry.path in completed:\n                                        pruned += 1\n                                    else:\n                                        stack.append(entry.path)\n                                continue\n                            if os.path.splitext(entry.name)[1].lower() not in EMBYFLOW_LOCAL_VIDEO_EXTENSIONS:\n                                continue\n                            linked = entry.is_symlink()\n                            path = os.path.realpath(entry.path) if linked else entry.path\n                            if linked and entry.is_dir():\n                                continue\n                            if not _efqs_inside(root, path) or path in seen_files:\n                                continue\n                            seen_files.add(path)\n                            files += 1\n                            try:\n                                stats['size'] += int(entry.stat().st_size or 0)\n                            except OSError:\n                                pass\n                            if mode == 'movies':\n                                stats['movies'] += 1\n                            elif mode == 'series':\n                                stats['episodes'] += 1\n                                relative = os.path.relpath(path, root).split(os.sep)\n                                if len(relative) > 1:\n                                    name = relative[0].replace('_', ' ').strip()\n                                else:\n                                    name = embyflow_local_v3_series_name(root, path)\n                                if name:\n                                    series_names.add(name.casefold())\n                            elif mode == 'documentary':\n                                stats['docs'] += 1\n                            if files >= EMBYFLOW_LOCAL_SOURCE_MAX_SCAN_FILES_V16:\n                                stats['truncated'] = True\n                                break\n                        except OSError:\n                            continue\n            except OSError:\n                root_ok = False\n        # Failed subtrees remain eligible for the broader source's retry.\n        if root_ok:\n            completed.add(root)\n        if stats['truncated']:\n            break\n    stats['series'] = len(series_names)\n    stats['scan_ms'] = round((time.monotonic() - started) * 1000, 1)\n    stats['scan_files'] = files\n    stats['scan_folders'] = folders\n    stats['skipped_subtrees'] = pruned\n    return stats\n\n\ndef _efqs_rescan(screen):\n    snapshot = [dict(s) for s in screen.sources if s.get('enabled', True)]\n    if screen.stats_running:\n        screen._efqs_pending = snapshot\n        return\n    if not snapshot:\n        screen.stats_result = dict(movies=0, series=0, episodes=0, docs=0, size=0, truncated=False)\n        screen.apply_timer.start(120, True)\n        return\n    screen._efqs_cancel = _efqs_threading.Event()\n    screen._efqs_pending = None\n    screen._efqs_failed = False\n    screen.stats_running = True\n    screen.stats_result = None\n    screen['status'].setText('Schnellinfo wird im Hintergrund aktualisiert; bisherige Werte bleiben sichtbar.')\n    cancelled = screen._efqs_cancel\n\n    def worker():\n        sources = snapshot\n        try:\n            while not cancelled.is_set():\n                stats = _efqs_scan(sources, cancelled)\n                if cancelled.is_set() or stats is None:\n                    return\n                pending = screen._efqs_pending\n                screen._efqs_pending = None\n                if pending is not None and pending != sources:\n                    sources = pending\n                    continue\n                screen.stats_result = stats\n                return\n        except Exception as error:\n            _embyflow_v16_log('QUICKSTATS_ERROR type=%s' % type(error).__name__)\n            # Leave the last successful on-disk counts intact after an unexpected failure.\n            screen._efqs_failed = True\n\n    try:\n        _efqs_threading.Thread(target=worker, name='EmbyFlowQuickStatsFast', daemon=True).start()\n    except Exception:\n        screen.stats_running = False\n        screen['status'].setText('Schnellinfo konnte nicht gestartet werden.')\n        return\n    screen.apply_timer.start(120, True)\n\n\n_EFQS_CLEANUP = EmbyFlowLocalSourcesScreenV17.cleanup\n_EFQS_APPLY = EmbyFlowLocalSourcesScreenV17.apply_async_results\n\n\ndef _efqs_cleanup(screen):\n    cancelled = getattr(screen, '_efqs_cancel', None)\n    if cancelled is not None:\n        cancelled.set()\n    return _EFQS_CLEANUP(screen)\n\n\ndef _efqs_apply(screen):\n    if getattr(screen, '_efqs_failed', False):\n        screen._efqs_failed = False\n        screen.stats_running = False\n        screen['status'].setText('Schnellinfo konnte nicht aktualisiert werden; bisherige Werte bleiben erhalten.')\n    result = _EFQS_APPLY(screen)\n    if not screen.closed_sources_v16 and not screen.stats_running and getattr(screen, '_efqs_pending', None) is not None:\n        screen._efqs_pending = None\n        _efqs_rescan(screen)\n    return result\n\n\nEmbyFlowLocalSourcesScreenV16.rescan_stats = _efqs_rescan\nEmbyFlowLocalSourcesScreenV17.cleanup = _efqs_cleanup\nEmbyFlowLocalSourcesScreenV17.apply_async_results = _efqs_apply\n# EMBYFLOW_QUICKSTATS_FAST_V1_20261031_END\n"
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
    marker = '# EMBYFLOW_QUICKSTATS_FAST_V1_20261031_BEGIN'
    if marker in source:
        raise ValueError('Schnellinfo-Fix V1 ist bereits installiert; nichts geaendert.')
    tree = ast.parse(source)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'EmbyFlowLocalSourcesScreenV17']
    if len(classes) != 1:
        raise ValueError('Erwartete Quellenansicht fehlt; Abbruch.')
    methods = [n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name == 'layout_ready']
    if len(methods) != 1:
        raise ValueError('Erwarteter Startablauf fehlt; Abbruch.')
    lines = source.splitlines(keepends=True)
    method = methods[0]
    text = ''.join(lines[method.lineno-1:method.end_lineno])
    block = ''.join('                self["%s"].setText("...")\n' % key for key in ('stat_movies', 'stat_series', 'stat_episodes', 'stat_docs', 'stat_size'))
    if text.count(block) != 1 or 'self.rescan_stats()' not in text:
        raise ValueError('Schnellinfo-Start weicht vom geprueften Stand ab.')
    replacement = '                if not isinstance(stats, dict):\n' + ''.join('    ' + line for line in block.splitlines(keepends=True))
    text = text.replace(block, replacement, 1)
    result = ''.join(lines[:method.lineno-1]) + text + ''.join(lines[method.end_lineno:])
    result = result.rstrip() + '\n\n' + RUNTIME.rstrip() + '\n'
    compile(result, '<EmbyFlowE2-fast-quickstats>', 'exec')
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
    backup = path.with_name(path.name + '.before_quickstats_fast_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')
    if path.read_bytes() != original:
        raise RuntimeError('Quelle wurde zwischenzeitlich geaendert.')
    shutil.copy2(path, backup)
    if backup.read_bytes() != original:
        raise RuntimeError('Sicherungspruefung fehlgeschlagen.')
    details = path.stat()
    fd, temporary = tempfile.mkstemp(prefix='.quickstats_fast_', dir=str(path.parent))
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
    print('OK: Schnellinfo optimiert; gespeicherte Werte bleiben sichtbar. SHA256: ' + hashlib.sha256(after).hexdigest())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ABBRUCH: ' + str(error), file=sys.stderr)
        sys.exit(1)

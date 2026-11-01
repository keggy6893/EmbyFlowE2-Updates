#!/usr/bin/env python3
"""Normal Emby library to native network TS playback; optional receiver test."""
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

RUNTIME = "# EMBYFLOW_EMBY_LIBRARY_NAS_SKYFALL_TEST1_20261101_BEGIN\n# Keep normal Emby UI, remote item identity, metadata and playback reports.\n# Resolve TS movies through mounted or configured network roots.\nimport json as _ebnt_json\nimport os as _ebnt_os\n\n_EBNT_OPEN = _open_embyflow_player_now\n\n\ndef _ebnt_log(event, **fields):\n    try:\n        fields.update(event=event, time=time.strftime('%H:%M:%S'))\n        with open('/tmp/embyflow-emby-nas-test1.log', 'a') as handle:\n            handle.write(_ebnt_json.dumps(fields, ensure_ascii=True) + '\\n')\n    except Exception:\n        pass\n\n\ndef _ebnt_resolve(info):\n    from urllib.parse import urlsplit, parse_qs\n    import re\n    info = info or {}\n    item = info.get('item') or {}\n    if info.get('local_file') or not str(info.get('url') or '').lower().startswith(('http://', 'https://')):\n        return None, 'not-remote'\n    if str(item.get('Type') or item.get('type') or '').casefold() != 'movie':\n        return None, 'not-movie'\n    if not str(item.get('Id') or item.get('id') or '').strip():\n        return None, 'missing-emby-item-id'\n    sources = item.get('MediaSources') or item.get('media_sources') or []\n    if not isinstance(sources, list):\n        return None, 'missing-media-sources'\n    query = parse_qs(urlsplit(str(info.get('url') or '')).query)\n    wanted = str(info.get('media_source_id') or info.get('MediaSourceId') or\n                 next((v[0] for k, v in query.items() if k.casefold() == 'mediasourceid' and v), '') or '')\n    selected = [s for s in sources if isinstance(s, dict) and\n                (not wanted or str(s.get('Id') or s.get('id') or '') == wanted)]\n    if len(selected) != 1:\n        return None, 'ambiguous-media-source'\n    source = selected[0]\n    server_path = str(source.get('Path') or item.get('Path') or '').replace('\\\\', '/')\n    if not server_path.lower().endswith('.ts') or '://' in server_path:\n        return None, 'server-source-not-ts'\n    parts = [p for p in server_path.split('/') if p]\n    if not parts or any(p in ('.', '..') for p in parts):\n        return None, 'invalid-server-path'\n    try:\n        size = int(source.get('Size') or item.get('Size') or 0)\n    except (TypeError, ValueError):\n        size = 0\n    if size <= 0:\n        return None, 'missing-server-file-size'\n    # Only mounted network filesystems; never enumerate all files or trigger\n    # unmounted autofs entries. Kernel mount escapes are octal, not URL escapes.\n    roots = set()\n    try:\n        with open('/proc/mounts', 'r') as handle:\n            for row in handle:\n                fields = row.split()\n                if len(fields) < 3 or fields[2] not in ('cifs', 'nfs', 'nfs4'):\n                    continue\n                mount = re.sub(r'\\\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), fields[1])\n                if not mount.startswith('/') or mount == '/':\n                    continue\n                roots.add(_ebnt_os.path.realpath(mount))\n    except OSError:\n        return None, 'mount-list-unavailable'\n    # Known configured network roots also cover idle autofs mounts.\n    # Do not load the UI source loader: it may create default sources.\n    try:\n        import json\n        with open('/etc/enigma2/embyflow_local_sources.json', 'r') as handle:\n            configured = json.load(handle)\n        for entry in configured.get('sources', []):\n            if not isinstance(entry, dict) or not entry.get('enabled', True):\n                continue\n            raw = str(entry.get('path') or '')\n            network = entry.get('network') or {}\n            protocol = str(network.get('protocol') or '') if isinstance(network, dict) else ''\n            if not raw.startswith('/') or '..' in raw.split('/'):\n                continue\n            if not (raw.startswith(('/media/autofs/', '/media/net/')) or\n                    protocol in ('smb', 'cifs', 'nfs', 'nfs4')):\n                continue\n            resolved = _ebnt_os.path.realpath(raw).rstrip(_ebnt_os.sep)\n            if resolved:\n                roots.add(resolved)\n    except (OSError, ValueError, TypeError, AttributeError):\n        pass\n    if len(roots) > 16:\n        return None, 'too-many-network-mounts'\n    _ebnt_log('NAS_MATCH_INPUT', file=parts[-1], server_size=size, roots=sorted(roots))\n    matches = set()\n    for root in sorted(roots):\n        for depth in range(1, min(4, len(parts)) + 1):\n            candidate = _ebnt_os.path.join(root, *parts[-depth:])\n            try:\n                path = _ebnt_os.path.realpath(candidate)\n                if not path.startswith(root + _ebnt_os.sep):\n                    continue\n                if _ebnt_os.path.isfile(path) and _ebnt_os.path.getsize(path) == size:\n                    matches.add(path)\n            except OSError:\n                continue\n    _ebnt_log('NAS_MATCH_RESULT', matches=len(matches))\n    if len(matches) != 1:\n        return None, 'no-unique-copy-with-same-size'\n    return (matches.pop(), source), 'verified-copy'\n\n\ndef _ebnt_launch(session, ref, title, stream_url, playback_info=None):\n    info = dict(playback_info or {})\n    info.setdefault('url', stream_url)\n    try:\n        match, reason = _ebnt_resolve(info)\n    except Exception as error:\n        match, reason = None, 'resolve-error-' + type(error).__name__\n    if match is None:\n        if reason not in ('not-remote', 'not-movie', 'outside-skyfall-test'):\n            _ebnt_log('HTTP_FALLBACK', reason=reason)\n        return _EBNT_OPEN(session, ref, title, stream_url, playback_info)\n    path, source = match\n    # Keep original remote item and server credentials for Emby progress reports.\n    # Only transport flags and source URL change. No local:* item ID is invented.\n    info.update(url=path, local_file=True, local_service_type=1, local_extension='.ts',\n                playback_mode='directplay', embyflow_emby_nas_test1=True,\n                local_probe={'ok': True, 'media_streams': list(source.get('MediaStreams') or [])})\n    reference = eServiceReference(1, 0, path)\n    reference.setName(title)\n    _ebnt_log('NAS_NATIVE_START', service_type=1, verified_size=_ebnt_os.path.getsize(path),\n              file=_ebnt_os.path.basename(path))\n    return _EBNT_OPEN(session, reference, title, path, info)\n\n\n_open_embyflow_player_now = _ebnt_launch\n# EMBYFLOW_EMBY_LIBRARY_NAS_SKYFALL_TEST1_20261101_END\n"
PANEL = '''
            <widget name="emby_nas_native_icon" position="1325,282" size="90,90" zPosition="10" alphatest="blend" />
            <widget name="emby_nas_native_name" position="1430,282" size="390,70" font="Bold;26" foregroundColor="#F4F7FB" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="emby_nas_native_type" position="1430,355" size="390,34" font="Regular;21" foregroundColor="#AEB8C5" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="emby_nas_native_state" position="1320,410" size="500,34" font="Regular;21" foregroundColor="#53D769" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <eLabel text="Speicherort" position="1320,453" size="500,28" font="Regular;19" foregroundColor="#8190A4" backgroundColor="#0C1827" transparent="1" zPosition="5" />
            <widget name="emby_nas_native_path" position="1320,485" size="500,80" font="Regular;20" foregroundColor="#AEB8C5" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="emby_nas_native_content" position="1320,580" size="500,56" font="Regular;21" foregroundColor="#F4F7FB" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="emby_nas_native_storage" position="1320,650" size="500,30" font="Regular;19" foregroundColor="#AEB8C5" backgroundColor="#0C1827" transparent="1" zPosition="10" />
            <widget name="emby_nas_native_checked" position="1320,695" size="500,30" font="Regular;19" foregroundColor="#8190A4" backgroundColor="#0C1827" transparent="1" zPosition="10" />
'''


def transform(source):
    if 'def _ebnt_launch(' in source:
        raise ValueError('NAS-Testweg bereits vorhanden. Funktionierenden Stand nicht ueberschreiben.')
    tree = ast.parse(source)
    functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if '_eftsh_launch' not in functions or '_efua_native' not in functions:
        raise ValueError('Native lokale TS-/Ton-Unterstuetzung fehlt. Zuerst kompatible Pluginbasis installieren.')
    hooks = [n for n in tree.body if isinstance(n, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == '_open_embyflow_player_now' for t in n.targets)]
    if not hooks or not isinstance(hooks[-1].value, ast.Name) or hooks[-1].value.id != '_eftsh_launch':
        raise ValueError('Player-Einstieg weicht von der geprueften Grundlage ab.')
    result = source.rstrip() + '\n\n' + RUNTIME.rstrip() + '\n'
    compile(result, '<EmbyFlowE2-NAS-native>', 'exec')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--path', default='/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    args = parser.parse_args()
    path = Path(args.path)
    original = path.read_bytes()
    after = transform(original.decode('utf-8')).encode('utf-8')
    print('Native TS-Grundlage gefunden; vollstaendige Syntaxpruefung: OK')
    if not args.apply:
        print('Nur geprueft, keine Datei geaendert.')
        return
    backup = path.with_name(path.name + '.before_emby_nas_native_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')
    if path.read_bytes() != original:
        raise RuntimeError('Quelle wurde zwischenzeitlich geaendert.')
    shutil.copy2(path, backup)
    if backup.read_bytes() != original:
        raise RuntimeError('Sicherungspruefung fehlgeschlagen.')
    details = path.stat()
    fd, temporary = tempfile.mkstemp(prefix='.emby_nas_native_', dir=str(path.parent))
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
    print('OK: Nativer Emby-NAS-Testweg installiert. SHA256: ' + hashlib.sha256(after).hexdigest())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ABBRUCH: ' + str(error), file=sys.stderr)
        sys.exit(1)

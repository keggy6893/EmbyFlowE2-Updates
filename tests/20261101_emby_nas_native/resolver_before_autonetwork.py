def _ebnt_resolve(info):
    from urllib.parse import urlsplit, parse_qs
    import re
    info = info or {}
    item = info.get('item') or {}
    if info.get('local_file') or not str(info.get('url') or '').lower().startswith(('http://', 'https://')):
        return None, 'not-remote'
    if str(item.get('Type') or item.get('type') or '').casefold() != 'movie':
        return None, 'not-movie'
    if not str(item.get('Id') or item.get('id') or '').strip():
        return None, 'missing-emby-item-id'
    sources = item.get('MediaSources') or item.get('media_sources') or []
    if not isinstance(sources, list):
        return None, 'missing-media-sources'
    query = parse_qs(urlsplit(str(info.get('url') or '')).query)
    wanted = str(info.get('media_source_id') or info.get('MediaSourceId') or
                 next((v[0] for k, v in query.items() if k.casefold() == 'mediasourceid' and v), '') or '')
    selected = [s for s in sources if isinstance(s, dict) and
                (not wanted or str(s.get('Id') or s.get('id') or '') == wanted)]
    if len(selected) != 1:
        return None, 'ambiguous-media-source'
    source = selected[0]
    server_path = str(source.get('Path') or item.get('Path') or '').replace('\\', '/')
    if not server_path.lower().endswith('.ts') or '://' in server_path:
        return None, 'server-source-not-ts'
    parts = [p for p in server_path.split('/') if p]
    if not parts or any(p in ('.', '..') for p in parts):
        return None, 'invalid-server-path'
    try:
        size = int(source.get('Size') or item.get('Size') or 0)
    except (TypeError, ValueError):
        size = 0
    if size <= 0:
        return None, 'missing-server-file-size'
    # Only mounted network filesystems; never enumerate all files or trigger
    # unmounted autofs entries. Kernel mount escapes are octal, not URL escapes.
    roots = set()
    try:
        with open('/proc/mounts', 'r') as handle:
            for row in handle:
                fields = row.split()
                if len(fields) < 3 or fields[2] not in ('cifs', 'nfs', 'nfs4'):
                    continue
                mount = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), fields[1])
                if not mount.startswith('/') or mount == '/':
                    continue
                roots.add(_ebnt_os.path.realpath(mount))
    except OSError:
        return None, 'mount-list-unavailable'
    # Known configured network roots also cover idle autofs mounts.
    # Do not load the UI source loader: it may create default sources.
    try:
        import json
        with open('/etc/enigma2/embyflow_local_sources.json', 'r') as handle:
            configured = json.load(handle)
        for entry in configured.get('sources', []):
            if not isinstance(entry, dict) or not entry.get('enabled', True):
                continue
            raw = str(entry.get('path') or '')
            network = entry.get('network') or {}
            protocol = str(network.get('protocol') or '') if isinstance(network, dict) else ''
            if not raw.startswith('/') or '..' in raw.split('/'):
                continue
            if not (raw.startswith(('/media/autofs/', '/media/net/')) or
                    protocol in ('smb', 'cifs', 'nfs', 'nfs4')):
                continue
            resolved = _ebnt_os.path.realpath(raw).rstrip(_ebnt_os.sep)
            if resolved:
                roots.add(resolved)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    if len(roots) > 16:
        return None, 'too-many-network-mounts'
    _ebnt_log('NAS_MATCH_INPUT', file=parts[-1], server_size=size, roots=sorted(roots))
    matches = set()
    for root in sorted(roots):
        for depth in range(1, min(4, len(parts)) + 1):
            candidate = _ebnt_os.path.join(root, *parts[-depth:])
            try:
                path = _ebnt_os.path.realpath(candidate)
                if not path.startswith(root + _ebnt_os.sep):
                    continue
                if _ebnt_os.path.isfile(path) and _ebnt_os.path.getsize(path) == size:
                    matches.add(path)
            except OSError:
                continue
    _ebnt_log('NAS_MATCH_RESULT', matches=len(matches))
    if len(matches) != 1:
        return None, 'no-unique-copy-with-same-size'
    return (matches.pop(), source), 'verified-copy'

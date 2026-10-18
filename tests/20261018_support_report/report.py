"""Bounded local support snapshot; raw logs and account files are never exported."""
import collections as _efsr_collections
import datetime as _efsr_datetime
import os as _efsr_os
import re as _efsr_re
import stat as _efsr_stat
import sys as _efsr_sys
import tempfile as _efsr_tempfile
from pathlib import Path as _EFSRPath

_EFSR_LOGS = (
    'embyflow_external_subtitle_error.log', 'embyflow_updater_error.log',
    'embyflow_playback_report_error.log', 'embyflow_login.log',
    'embyflow_background_debug.log', 'embyflow_trailer_debug.log',
    'embyflow_chapter_clock_v16_1.log', 'embyflow_serversafe_v17_5_7.log',
    'embyflow_images.log', 'embyflow_tv_return.log',
)
_EFSR_ERRORS = (
    'TypeError', 'ValueError', 'NameError', 'AttributeError', 'KeyError',
    'IndexError', 'RuntimeError', 'ImportError', 'ModuleNotFoundError',
    'SyntaxError', 'OSError', 'IOError', 'PermissionError', 'FileNotFoundError',
    'TimeoutError', 'ConnectionError', 'HTTPError', 'SSLError',
    'JSONDecodeError', 'UnicodeDecodeError', 'Timeout', 'ReadTimeout',
    'ConnectTimeout',
)


def _efsr_read(path, limit=65536):
    """Read only the tail of regular files without following symlinks or FIFOs."""
    descriptor = _efsr_os.open(str(path), _efsr_os.O_RDONLY | _efsr_os.O_NOFOLLOW | _efsr_os.O_NONBLOCK)
    try:
        info = _efsr_os.fstat(descriptor)
        if not _efsr_stat.S_ISREG(info.st_mode):
            raise OSError('Not a regular file')
        with _efsr_os.fdopen(descriptor, 'rb', closefd=False) as handle:
            if info.st_size > limit:
                handle.seek(-limit, 2)
            return handle.read(limit).decode('utf-8', errors='replace')
    finally:
        _efsr_os.close(descriptor)


def _efsr_summary(text):
    # Only emit fixed error names and numeric fields. Never emit raw messages,
    # URLs, headers, paths, user names, title names, tokens or exception values.
    counts = _efsr_collections.Counter()
    for name in _EFSR_ERRORS:
        found = len(_efsr_re.findall(r'\b' + name + r'\b', text))
        if found:
            counts[name] = found
    statuses = _efsr_collections.Counter(_efsr_re.findall(
        r'\b(?:HTTP(?:Error)?(?:\s+Error)?|status(?:_code)?)\s*[:=]?\s*([45]\d\d)\b', text,
        flags=_efsr_re.I))
    lines = sorted(set(int(number) for number in _efsr_re.findall(
        r'File "[^"\r\n]*/plugin\.py", line (\d{1,7})\b', text)))[:20]
    result = ['%s: %d' % item for item in sorted(counts.items())]
    result += ['HTTP %s: %d' % item for item in sorted(statuses.items())]
    if lines:
        result.append('plugin.py Zeilen: ' + ', '.join(map(str, lines)))
    return '; '.join(result) or 'Keine erkannten Fehlerarten im gelesenen Ausschnitt.'


def _efsr_safe(value, fallback='unbekannt'):
    value = str(value).strip()
    return value if _efsr_re.fullmatch(r'[A-Za-z0-9_.+() /;:-]{1,100}', value) and '://' not in value else fallback


def _efsr_collect(version, build, flags, root='/', log_directory='/tmp/embyflow-private-logs'):
    root = _EFSRPath(root)
    rows = ['EmbyFlow Supportbericht V1',
            'Erstellt (UTC): ' + _efsr_datetime.datetime.now(_efsr_datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            'Plugin: ' + _efsr_safe(version), 'Build: ' + str(int(build)),
            'Python: ' + '.'.join(map(str, _efsr_sys.version_info[:3]))]
    try:
        model = _efsr_read(root / 'proc/stb/info/model', 256)
    except OSError:
        model = 'unbekannt'
    rows.append('Box-Modellkennung: ' + _efsr_safe(model))
    try:
        image = _efsr_read(root / 'etc/image-version', 16384)
    except OSError:
        image = ''
    for key in ('distro', 'version', 'build', 'machine_brand', 'machine_name'):
        value = next((line.split('=', 1)[1] for line in image.splitlines() if line.startswith(key + '=')), 'unbekannt')
        rows.append('Image ' + key + ': ' + _efsr_safe(value))
    for key in ('Debug', 'Downloads', 'Trailer', 'LCD-Zeitfix'):
        value = flags.get(key)
        rows.append(key + ': ' + ('an' if value is True else 'aus' if value is False else 'unbekannt'))
    rows += ['', 'Fehlerhinweise (je Datei maximal die letzten 64 KiB):']
    for name in _EFSR_LOGS:
        try:
            text = _efsr_read(_EFSRPath(log_directory) / name)
            rows.append(name + ': ' + _efsr_summary(text))
        except FileNotFoundError:
            rows.append(name + ': nicht vorhanden')
        except OSError:
            rows.append(name + ': nicht lesbar')
    rows += ['', 'Keine Rohlogs, Kontodateien, Serveradressen oder Zugangsdaten enthalten.',
             'Fehlerhinweise sind eine Auswahl; fehlende Logs bedeuten nicht Fehlerfreiheit.',
             'Nur lokal erstellt; nichts automatisch versendet.']
    return '\n'.join(rows) + '\n'


def _efsr_write(path, text):
    path = _EFSRPath(path)
    descriptor, temporary = _efsr_tempfile.mkstemp(prefix='.embyflow-support-', dir=str(path.parent))
    try:
        with _efsr_os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            _efsr_os.fchmod(output.fileno(), 0o600)
            output.write(text)
            output.flush()
            _efsr_os.fsync(output.fileno())
        _efsr_os.replace(temporary, path)
    finally:
        if _efsr_os.path.exists(temporary):
            _efsr_os.unlink(temporary)


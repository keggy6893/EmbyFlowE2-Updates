"""Read-only receiver evidence. No player controls, settings, restart or HTTP."""
import glob
import json
import os
import re
import time


def clean(line):
    line = re.sub(r'(?i)https?(?::|%3a)(?://|%2f%2f)[^\s\x22\x27<>]+', '[URL]', str(line))
    line = re.sub(r'(?i)((?:api_key|access_?token|x-emby-token|authorization|password|passwd|token)[\x22\x27]?\s*[:=]\s*)[^\s,;]+', r'\1[REDACTED]', line)
    return line[:1200]


def tail(path, limit):
    with open(path, 'rb') as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size-limit))
        data = handle.read(limit)
    if size > limit:
        data = data.split(b'\n', 1)[-1]
    return data.decode('utf-8', 'replace')


def current_comparison():
    try:
        rows = []
        for line in tail('/tmp/embyflow_http_compare.jsonl', 131072).splitlines():
            try:
                row = json.loads(line)
                if row.get('event') in ('START', 'AUDIO_REQUEST', 'SEEK_REQUEST', 'SAMPLE'):
                    rows.append(row)
            except (ValueError, TypeError):
                pass
        events = [row for row in rows if row['event'] != 'SAMPLE'][-5:]
        samples = [row for row in rows if row['event'] == 'SAMPLE'][-3:]
        for row in events + samples:
            print('COMPARE ' + json.dumps({k: row[k] for k in (
                'time', 'event', 'mode', 'service_type', 'index', 'audio',
                'position', 'length', 'paused', 'target_ticks', 'accepted') if k in row}), flush=True)
    except OSError:
        print('COMPARE: kein Vergleichslog vorhanden', flush=True)


def decoder_paths():
    paths = []
    for base in ('/proc/stb/vmpeg/0/', '/proc/stb/adec/0/'):
        for name in ('pts', 'decoded_frames', 'displayed_frames', 'frame_count',
                     'framecount', 'frame_rate', 'framerate', 'xres', 'yres', 'state'):
            path = base + name
            if os.path.isfile(path):
                paths.append(path)
    return paths


def decoder_sample(paths):
    values = {}
    for path in paths:
        try:
            with open(path, 'r') as handle:
                values[path] = handle.read(256).strip()
        except OSError:
            values[path] = 'nicht lesbar'
    return values


def debug_files():
    folders = ['/home/root/logs', '/media/hdd/logs', '/tmp', '/var/log', '/home/root']
    try:
        with open('/etc/enigma2/settings') as handle:
            for line in handle:
                if line.startswith('config.crash.debug_path='):
                    folder = line.split('=', 1)[1].strip()
                    if os.path.isabs(folder):
                        folders.insert(0, folder)
    except OSError:
        pass
    found = set()
    for folder in folders:
        for pattern in ('enigma2*.log', '*enigma2-debug.log', '*enigma2-crash.log'):
            for path in glob.glob(os.path.join(folder, pattern)):
                if os.path.isfile(path) and not os.path.islink(path):
                    found.add(path)
    return sorted(found, key=os.path.getmtime, reverse=True)[:2]


def debug_excerpt(path):
    text = tail(path, 2097152)
    lines = text.splitlines()
    pattern = re.compile(r'(selectTrack|switched to audio|current.audio|GStreamer|\bGST_|gst-stream|gst.*(?:error|warn)|dvb.*sink|decoder.*(?:error|fail)|not.negotiated|Internal data|streaming stopped|CLOCK_LOST|FLUSH_|ASYNC_DONE|Traceback|RuntimeError|ERROR|FF_ERROR|PLAYBACK_OPEN)', re.I)
    selected = set()
    for index, line in enumerate(lines):
        if pattern.search(line):
            selected.update(range(max(0, index-1), min(len(lines), index+3)))
    return [clean(lines[index]) for index in sorted(selected)[-160:]]


def main():
    print('READONLY DECODERDIAG V1: keine Plugin-Aenderung, kein Neustart, keine Wiedergabesteuerung.', flush=True)
    for path in ('/proc/stb/info/model', '/etc/image-version'):
        try:
            with open(path) as handle:
                value = handle.read(1024)
            print('SYSTEM ' + path + ': ' + clean(value).replace('\n', ' | '), flush=True)
        except OSError:
            pass
    current_comparison()
    paths = decoder_paths()
    if not paths:
        print('DECODER: Box stellt unter den bekannten Pfaden keine lesbaren Zaehler bereit.', flush=True)
    for index in range(3 if paths else 0):
        print('DECODER ' + json.dumps({'time': time.strftime('%H:%M:%S'), 'raw': decoder_sample(paths)}), flush=True)
        if index < 2:
            time.sleep(1)
    logs = debug_files()
    if not logs:
        print('DEBUGLOG: kein vorhandenes Enigma2-Debuglog gefunden; Logging wurde nicht eingeschaltet.', flush=True)
    for path in logs:
        try:
            print('DEBUGLOG ' + clean(path), flush=True)
            for line in debug_excerpt(path):
                print(line, flush=True)
        except OSError as error:
            print('DEBUGLOG nicht lesbar: ' + type(error).__name__, flush=True)
    print('FERTIG. Keine Einstellungen oder Videodateien geaendert.', flush=True)


if __name__ == '__main__':
    main()

"""Read-only ThemerrDB and YouTube stream test; never starts receiver playback."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import os
import signal
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request

SAMPLES = [('Skyfall', 'movies', '37724'), ('Interstellar', 'movies', '157336'),
           ('Game of Thrones', 'tv_shows', '1399'), ('Breaking Bad', 'tv_shows', '1396')]


def progress(phase, **fields):
    print(json.dumps(dict(phase=phase, **fields)), flush=True)


def classify(message):
    text = message.lower()
    if '403' in text:return 'http_403'
    if '429' in text:return 'http_429'
    if 'sign in' in text or 'not a bot' in text:return 'youtube_login_or_bot_check'
    if 'timed out' in text or 'timeout' in text:return 'network_timeout'
    if 'not available' in text or 'unavailable' in text:return 'video_unavailable'
    if 'format' in text:return 'audio_format_unavailable'
    return 'resolver_error'


def resolve(url):
    progress('resolver_import')
    try:
        # Use an already installed resolver; never install or upgrade on the box.
        import importlib.util
        import zipfile
        if importlib.util.find_spec('yt_dlp') is None:
            for candidate in ('/usr/bin/yt-dlp', '/etc/enigma2/embyflow-trailer/yt-dlp'):
                if Path(candidate).is_file() and zipfile.is_zipfile(candidate):
                    sys.path.insert(0, candidate)
                    break
        import yt_dlp
        from yt_dlp.version import __version__
    except ImportError:
        return {'stream_reachable': False, 'reason': 'yt_dlp_missing'}
    progress('resolver_ready', resolver=__version__, node_available=bool(shutil.which('node')))
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('www.youtube.com', 'youtube.com', 'youtu.be'):
        return {'stream_reachable': False, 'reason': 'unexpected_theme_host'}
    class Logger:
        def __init__(self):self.last=None
        def debug(self, message):
            text=str(message).lower()
            if not text.startswith('[youtube]'):return
            phase = ('youtube_javascript' if 'challenge' in text or 'javascript' in text
                     else 'youtube_player_api' if 'api json' in text
                     else 'youtube_webpage' if 'webpage' in text
                     else 'youtube_player' if 'player' in text else None)
            if phase and phase != self.last:
                self.last=phase;progress(phase)
        def warning(self, message):pass
        def error(self, message):pass
    try:
        options = dict(quiet=True, no_warnings=True, logger=Logger(),
            noplaylist=True, skip_download=True, socket_timeout=8, retries=1, extractor_retries=0,
            allowed_extractors=['youtube'], js_runtimes={'node': {}},
            remote_components=['ejs:github'],
            format='bestaudio[ext=m4a]/bestaudio')
        progress('youtube_extract')
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=False)
        stream = info.get('url') or ''
        parsed = urllib.parse.urlparse(stream)
        if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.googlevideo.com'):
            return {'stream_reachable': False, 'reason': 'no_direct_https_audio', 'resolver': __version__}
        headers = dict(info.get('http_headers') or {})
        headers['Range'] = 'bytes=0-0'
        progress('audio_connection')
        request = urllib.request.Request(stream, headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            available = bool(response.read(1))
            status = response.status
        return {'stream_reachable': available, 'status': status, 'codec': info.get('acodec'),
                'extension': info.get('ext'), 'resolver': __version__}
    except Exception as error:
        # Never expose signed URLs, cookies or raw extractor messages.
        return {'stream_reachable': False, 'reason': classify(str(error)), 'resolver': __version__}


def run_resolver(theme, deadline=55):
    started=time.monotonic()
    child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--resolve',theme],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    expired=False
    try:
        stdout,stderr=child.communicate(timeout=deadline)
    except subprocess.TimeoutExpired:
        expired=True
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        stdout,stderr=child.communicate()
    events=[]
    for line in stdout.splitlines():
        try:
            event=json.loads(line)
            if isinstance(event,dict):events.append(event)
        except ValueError:pass
    phases=[e for e in events if e.get('phase')]
    results=[e for e in events if 'stream_reachable' in e]
    result=(results[-1] if results and not expired and child.returncode == 0 else
            {'stream_reachable':False,'reason':'resolver_deadline' if expired else 'resolver_process_error'})
    result['elapsed_seconds']=round(time.monotonic()-started,1)
    result['last_phase']=phases[-1]['phase'] if phases else 'process_start'
    for event in phases:
        for key in ('resolver','node_available'):
            if key in event:result[key]=event[key]
    return result


def probe(sample):
    title, kind, ident = sample
    result = {'title': title, 'tmdb': ident, 'lookup': False}
    url = 'https://app.lizardbyte.dev/ThemerrDB/%s/themoviedb/%s.json' % (kind, ident)
    try:
        with urllib.request.urlopen(url, timeout=12) as response:
            data = response.read(2*1024*1024+1)
        if len(data) > 2*1024*1024:raise ValueError('Response too large')
        entry = json.loads(data)
        if str(entry.get('id')) != ident:raise ValueError('Metadata mismatch')
        theme = entry.get('youtube_theme_url')
        if not theme:
            result['reason'] = 'no_theme'
            return result
        result['lookup'] = True
        result['stream'] = run_resolver(theme)
    except Exception as error:
        result['reason'] = 'lookup_' + classify(str(error))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resolve')
    parser.add_argument('--all',action='store_true')
    args = parser.parse_args()
    if args.resolve:
        print(json.dumps(resolve(args.resolve)))
        return
    print('THEME-TEST V2: Trailer-Resolver-Konfiguration, ein Titel nach dem anderen. Keine Plugin-Aenderung.', flush=True)
    for sample in SAMPLES if args.all else SAMPLES[:1]:
        print(json.dumps(probe(sample),ensure_ascii=False),flush=True)


if __name__ == '__main__':main()

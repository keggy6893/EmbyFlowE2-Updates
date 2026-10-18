"""Read-only ThemerrDB and YouTube stream test; never starts receiver playback."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

SAMPLES = [('Skyfall', 'movies', '37724'), ('Interstellar', 'movies', '157336'),
           ('Game of Thrones', 'tv_shows', '1399'), ('Breaking Bad', 'tv_shows', '1396')]


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
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('www.youtube.com', 'youtube.com', 'youtu.be'):
        return {'stream_reachable': False, 'reason': 'unexpected_theme_host'}
    class Logger:
        def debug(self, message):pass
        def warning(self, message):pass
        def error(self, message):pass
    try:
        options = dict(quiet=True, no_warnings=True, logger=Logger(),
            noplaylist=True, socket_timeout=8, retries=0, extractor_retries=0,
            format='bestaudio[ext=m4a]/bestaudio')
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=False)
        stream = info.get('url') or ''
        parsed = urllib.parse.urlparse(stream)
        if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.googlevideo.com'):
            return {'stream_reachable': False, 'reason': 'no_direct_https_audio', 'resolver': __version__}
        headers = dict(info.get('http_headers') or {})
        headers['Range'] = 'bytes=0-0'
        request = urllib.request.Request(stream, headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            available = bool(response.read(1))
            status = response.status
        return {'stream_reachable': available, 'status': status, 'codec': info.get('acodec'),
                'extension': info.get('ext'), 'resolver': __version__}
    except Exception as error:
        # Never expose signed URLs, cookies or raw extractor messages.
        return {'stream_reachable': False, 'reason': classify(str(error)), 'resolver': __version__}


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
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()),
            '--resolve', theme], capture_output=True, text=True, timeout=40)
        result['stream'] = json.loads(child.stdout) if child.returncode == 0 else {'stream_reachable': False, 'reason': 'resolver_process_error'}
    except subprocess.TimeoutExpired:
        result['stream'] = {'stream_reachable': False, 'reason': 'resolver_deadline'}
    except Exception as error:
        result['reason'] = 'lookup_' + classify(str(error))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resolve')
    args = parser.parse_args()
    if args.resolve:
        print(json.dumps(resolve(args.resolve)))
        return
    print('THEME-TEST: keine Plugin-Aenderung, kein GUI-Neustart, keine Musikdateien gespeichert.', flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(probe, SAMPLES):
            print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':main()

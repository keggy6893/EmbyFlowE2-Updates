# -*- coding: utf-8 -*-
"""Theme and trailer lookup. Call resolve_theme_and_trailer from a worker thread."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

THEMERR_BASE = 'https://app.lizardbyte.dev/ThemerrDB'


def _json(url, token=None, timeout=8):
    headers = {'User-Agent': 'EmbyFlowE2/1.0'}
    if token:
        headers['X-Emby-Token'] = token
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read(2 * 1024 * 1024).decode('utf-8'))
    except (OSError, ValueError, UnicodeError) as error:
        print('[EmbyFlow][ThemeMedia] Lookup failed: %s' % error)
        return None


class ThemeMediaManager(object):
    """Network calls are synchronous; use from a background worker only."""

    def __init__(self, yt_dlp_module=None):
        if yt_dlp_module is None:
            try:
                import yt_dlp as yt_dlp_module
            except ImportError:
                pass
        self.yt_dlp = yt_dlp_module

    @staticmethod
    def _stream(base, token, media_id, kind):
        return '%s/%s/%s/stream?%s' % (
            base.rstrip('/'), kind, urllib.parse.quote(str(media_id), safe=''),
            urllib.parse.urlencode({'Static': 'true', 'api_key': token}))

    def official(self, server_url, api_key, item_id):
        result = {'theme_song_url': None, 'trailer_url': None}
        if not all((server_url, api_key, item_id)):
            return result
        base = server_url.rstrip('/')
        quoted = urllib.parse.quote(str(item_id), safe='')
        songs = _json('%s/Items/%s/ThemeSongs?InheritFromParent=true' % (base, quoted), api_key)
        entries = (songs or {}).get('Items', []) if isinstance(songs, dict) else []
        if entries and isinstance(entries[0], dict) and entries[0].get('Id'):
            result['theme_song_url'] = self._stream(base, api_key, entries[0]['Id'], 'Audio')
        trailers = _json('%s/Items/%s/LocalTrailers' % (base, quoted), api_key)
        entries = trailers if isinstance(trailers, list) else (trailers or {}).get('Items', []) if isinstance(trailers, dict) else []
        if entries and isinstance(entries[0], dict) and entries[0].get('Id'):
            result['trailer_url'] = self._stream(base, api_key, entries[0]['Id'], 'Videos')
        return result

    def theme_from_themerr(self, tmdb_id, media_type):
        if not tmdb_id or not re.fullmatch(r'[0-9]+', str(tmdb_id)):
            return None
        kind = 'tv_shows' if str(media_type).lower() == 'series' else 'movies'
        info = _json('%s/%s/themoviedb/%s.json' % (THEMERR_BASE, kind, tmdb_id))
        url = info.get('youtube_theme_url') if isinstance(info, dict) else None
        if not url or not self.yt_dlp:
            return None
        return self._youtube_stream(url, 'bestaudio[ext=m4a]/bestaudio')

    def _youtube_stream(self, url, fmt):
        try:
            with self.yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True,
                                        'format': fmt, 'noplaylist': True,
                                        'socket_timeout': 8}) as ydl:
                info = ydl.extract_info(url, download=False)
                stream = info.get('url') if isinstance(info, dict) else None
                return stream if stream and stream.startswith(('http://', 'https://')) else None
        except Exception as error:
            print('[EmbyFlow][ThemeMedia] Stream unavailable: %s' % error)
            return None

    def resolve_theme_and_trailer(self, server_url, api_key, item):
        item = item or {}
        result = self.official(server_url, api_key, item.get('Id') or item.get('id'))
        source = {'theme_song': 'server' if result['theme_song_url'] else None,
                  'trailer': 'server' if result['trailer_url'] else None}
        if not result['theme_song_url']:
            providers = item.get('ProviderIds') or {}
            tmdb = next((value for key, value in providers.items()
                         if str(key).lower() == 'tmdb'), None)
            result['theme_song_url'] = self.theme_from_themerr(tmdb, item.get('Type'))
            if result['theme_song_url']:
                source['theme_song'] = 'ThemerrDB'
        result['source'] = source
        return result

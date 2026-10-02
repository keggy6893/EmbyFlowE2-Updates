# EMBYFLOW_TRAILERS_20261002
import hashlib as _eftr_hash
import json as _eftr_json
import os as _eftr_os
import shutil as _eftr_shutil
import subprocess as _eftr_subprocess
import sys as _eftr_sys
import tempfile as _eftr_tempfile
import threading as _eftr_threading
import time as _eftr_time
import xml.etree.ElementTree as _eftr_xml
from pathlib import Path as _eftr_Path
from urllib.parse import urlparse as _eftr_urlparse, quote as _eftr_quote
from urllib.request import urlopen as _eftr_urlopen
from Screens.MessageBox import MessageBox as _eftr_MessageBox
from enigma import eServiceReference as _eftr_ServiceReference, eDVBVolumecontrol as _eftr_Volume

_EFTR_RESOLVER_URL = 'https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp'
_EFTR_RESOLVER_SHA = '1fa6733c37ea6fb51c99ad8fe785e7b7e5f3246c9b980230329d4fb72ed8d4d6'
_EFTR_RESOLVER_PATH = '/etc/enigma2/embyflow-trailer/yt-dlp'
_EFTR_DOWNLOAD_LOCK = _eftr_threading.Lock()

def _eftr_youtube_url(url):
    parsed = _eftr_urlparse(str(url or ''))
    host = (parsed.hostname or '').lower()
    return parsed.scheme in ('https', 'http') and (
        host == 'youtu.be' or host == 'youtube.com' or host.endswith('.youtube.com'))

def _eftr_remote_url(item):
    trailers = item.get('RemoteTrailers') or item.get('remote_trailers') or []
    for trailer in trailers:
        url = trailer.get('Url') if isinstance(trailer, dict) else None
        if url and _eftr_youtube_url(url):
            return str(url)
    return None

def _eftr_lookup(data, auth, cancel):
    url = _eftr_remote_url(data)
    if url:
        return url
    server, token, user_id = auth
    item_id = data.get('id') or data.get('Id') or data.get('item_id')
    if not server or not token or not item_id:
        raise RuntimeError('Keine Trailer-Daten fuer diesen Titel vorhanden.')
    headers = {'X-Emby-Token': token, 'X-Emby-Authorization': AUTH_HEADER}
    visited = set()
    for unused in range(3):
        if cancel.is_set():
            raise RuntimeError('Abgebrochen')
        if not item_id or str(item_id) in visited:
            break
        visited.add(str(item_id))
        base = server.rstrip('/')
        if user_id:
            endpoint = '%s/Users/%s/Items/%s' % (
                base, _eftr_quote(str(user_id), safe=''),
                _eftr_quote(str(item_id), safe=''))
        else:
            endpoint = '%s/Items/%s' % (base, _eftr_quote(str(item_id), safe=''))
        response = embyflow_http_get(
            endpoint, headers=headers,
            params={'Fields': 'RemoteTrailers,SeriesId,ParentId,Type'},
            timeout=12, verify=True)
        if response.status_code != 200:
            raise RuntimeError('Trailer-Daten konnten nicht vom Emby-Server geladen werden.')
        item = response.json() or {}
        url = _eftr_remote_url(item)
        if url:
            return url
        item_type = str(item.get('Type') or data.get('type') or '').lower()
        if item_type in ('episode', 'season'):
            item_id = (item.get('SeriesId') or data.get('SeriesId')
                       or data.get('series_id') or item.get('ParentId'))
        else:
            break
    raise RuntimeError('Bei Emby ist fuer diesen Titel kein YouTube-Trailer hinterlegt.')

def _eftr_ensure_resolver(cancel):
    if _eftr_sys.version_info < (3, 10):
        raise RuntimeError('YouTube-Trailer benoetigen auf dieser Box Python 3.10 oder neuer.')
    path = _eftr_Path(_EFTR_RESOLVER_PATH)
    with _EFTR_DOWNLOAD_LOCK:
        if cancel.is_set():
            raise RuntimeError('Abgebrochen')
        if path.is_file() and _eftr_hash.sha256(path.read_bytes()).hexdigest() == _EFTR_RESOLVER_SHA:
            return str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with _eftr_urlopen(_EFTR_RESOLVER_URL, timeout=20) as response:
                content = response.read(8 * 1024 * 1024 + 1)
            if cancel.is_set():
                raise RuntimeError('Abgebrochen')
            if _eftr_hash.sha256(content).hexdigest() != _EFTR_RESOLVER_SHA:
                raise RuntimeError('Die heruntergeladene Trailer-Komponente ist nicht korrekt.')
            fd, temporary = _eftr_tempfile.mkstemp(dir=str(path.parent), prefix='yt-dlp-')
            with _eftr_os.fdopen(fd, 'wb') as handle:
                handle.write(content)
            _eftr_os.chmod(temporary, 0o644)
            _eftr_os.replace(temporary, str(path))
            temporary = None
            return str(path)
        finally:
            if temporary:
                _eftr_os.unlink(temporary)

def _eftr_select_stream(info):
    formats = info.get('formats') or []
    videos = [f for f in formats if
              str(f.get('protocol') or '').startswith('m3u8')
              and str(f.get('vcodec') or '').startswith('avc1')
              and 0 < (f.get('height') or 0) <= 720 and f.get('url')]
    audios = [f for f in formats if
              str(f.get('protocol') or '').startswith('m3u8')
              and f.get('vcodec') == 'none'
              and f.get('acodec') not in (None, 'none') and f.get('url')]
    if videos:
        video = max(videos, key=lambda f: (f.get('height') or 0, f.get('tbr') or 0))
        if video.get('acodec') not in (None, 'none'):
            return video['url'], None
        if audios:
            audio = max(audios, key=lambda f: f.get('tbr') or 0)
            for url in (video['url'], audio['url']):
                if any(c in url for c in ('\r', '\n', '"')):
                    raise RuntimeError('Ungueltige Trailer-Adresse.')
            playlist = (
                '#EXTM3U\n'
                '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Ton",DEFAULT=YES,AUTOSELECT=YES,URI="'
                + audio['url'] + '"\n'
                '#EXT-X-STREAM-INF:BANDWIDTH=4000000,AUDIO="audio"\n'
                + video['url'] + '\n')
            return None, playlist
    combined = [f for f in formats if
                str(f.get('vcodec') or '').startswith('avc1')
                and str(f.get('acodec') or '').startswith('mp4a')
                and 0 < (f.get('height') or 0) <= 720 and f.get('url')]
    if combined:
        return max(combined, key=lambda f: f.get('height') or 0)['url'], None
    raise RuntimeError('Kein passender Trailer mit H.264-Bild und Ton bis 720p verfuegbar.')

class EmbyFlowTrailerPlayer(Screen):
    skin = '<screen position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#ff000000"><eLabel text="Trailer  |  STOP / EXIT: Zurueck" position="80,1000" size="1700,45" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#80000000" /></screen>'

    def __init__(self, session, path, title):
        Screen.__init__(self, session)
        self._trailer_path = path
        self._trailer_title = title
        self._trailer_finished = False
        self._trailer_control = None
        self._trailer_muted = False
        self['trailer_actions'] = ActionMap(
            ['OkCancelActions', 'MediaPlayerActions', 'InfobarActions',
             'MoviePlayerActions', 'ColorActions'],
            {'cancel': self.leave, 'stop': self.leave,
             'leavePlayer': self.leave, 'red': self.leave}, -10)
        self.onLayoutFinish.append(self.start)
        self.onClose.append(self.cleanup)
        try:
            from Components.ServiceEventTracker import ServiceEventTracker
            from enigma import iPlayableService
            self._trailer_events = ServiceEventTracker(
                screen=self, eventmap={iPlayableService.evEOF: self.leave})
        except ImportError:
            pass

    def start(self):
        try:
            self._trailer_control = _eftr_Volume.getInstance()
            self._trailer_muted = bool(self._trailer_control.isMuted())
            ref = _eftr_ServiceReference(4097, 0, self._trailer_path)
            ref.setName(self._trailer_title + ' - Trailer')
            result = self.session.nav.playService(ref)
            if result:
                raise RuntimeError('Die Box konnte den Trailer nicht starten.')
            self._trailer_control.volumeUnMute()
        except Exception:
            self.session.open(_eftr_MessageBox,
                              'Trailer konnte nicht gestartet werden.',
                              _eftr_MessageBox.TYPE_ERROR)
            self.leave()

    def cleanup(self):
        if self._trailer_finished:
            return
        self._trailer_finished = True
        try:
            self.session.nav.stopService()
        finally:
            if self._trailer_control is not None:
                if self._trailer_muted:
                    self._trailer_control.volumeMute()
                else:
                    self._trailer_control.volumeUnMute()

    def leave(self):
        if self._trailer_finished:
            return
        self.cleanup()
        self.close()

_EFTR_DETAIL_INIT = EmbyFlowDetailScreen.__init__
_EFTR_DETAIL_FOCUS = EmbyFlowDetailScreen.update_detail_focus
_EFTR_DETAIL_UP = EmbyFlowDetailScreen.detail_up
_EFTR_DETAIL_DOWN = EmbyFlowDetailScreen.detail_down
_EFTR_DETAIL_OK = EmbyFlowDetailScreen.detail_ok

def _eftr_detail_init(self, session, data):
    self._trailer_enabled = False
    _EFTR_DETAIL_INIT(self, session, data)
    self._trailer_closed = False
    self._trailer_cancel = _eftr_threading.Event()
    self._trailer_lock = _eftr_threading.Lock()
    self._trailer_media_active = False
    self._trailer_result = None
    self._trailer_process = None
    self._trailer_busy = False
    self._trailer_directory = None
    self._trailer_timer = eTimer()
    self._trailer_timer.callback.append(self.trailer_poll)
    self.onClose.append(self.trailer_close)
    item_type = str(self.data.get('type') or self.data.get('Type')
                    or self.data.get('item_type') or '').lower()
    if item_type in ('audio', 'musicalbum', 'musicartist'):
        return
    root = _eftr_xml.fromstring(self.skin)
    positions = {'detail_play_btn': 280, 'detail_back_btn': 370}
    for element in root:
        if (element.tag == 'eLabel'
                and element.get('position') in ('1260,320', '1260,420')
                and element.get('size') == '300,70'
                and element.get('zPosition') == '9'):
            y = 280 if element.get('position') == '1260,320' else 370
            element.set('position', '%d,%d' % (sx(1260), sy(y)))
            element.set('size', '%d,%d' % (sx(300), sy(70)))
        if element.get('name') in positions:
            element.set('position', '%d,%d' % (sx(1260), sy(positions[element.get('name')])))
            element.set('size', '%d,%d' % (sx(300), sy(70)))
            element.set('font', 'Regular;%d' % sy(30))
            element.set('halign', 'center')
            element.set('valign', 'center')
    self['trailer_button'] = Label('Trailer')
    _eftr_xml.SubElement(root, 'widget', {
        'name': 'trailer_button', 'position': '%d,%d' % (sx(1260), sy(460)),
        'size': '%d,%d' % (sx(300), sy(70)), 'font': 'Regular;%d' % sy(30),
        'foregroundColor': '#ffffff', 'backgroundColor': '#0C1827',
        'transparent': '0', 'zPosition': '40', 'halign': 'center', 'valign': 'center'})
    self.skin = _eftr_xml.tostring(root, encoding='unicode')
    self._trailer_enabled = True
    self['trailer_number'] = ActionMap(['NumberActions'], {'9': self.trailer_begin}, -10)
    self.update_detail_focus()

def _eftr_focus(self):
    if not getattr(self, '_trailer_enabled', False):
        return _EFTR_DETAIL_FOCUS(self)
    for index, key, text in (
            (0, 'detail_play_btn', 'Abspielen'),
            (1, 'detail_back_btn', 'Zurueck'),
            (2, 'trailer_button', 'Trailer')):
        prefix = '   \u25b6  ' if self.detail_focus == index else '      '
        self[key].setText(prefix + text)

def _eftr_up(self):
    if not getattr(self, '_trailer_enabled', False):
        return _EFTR_DETAIL_UP(self)
    self.detail_focus = max(0, self.detail_focus - 1)
    self.update_detail_focus()

def _eftr_down(self):
    if not getattr(self, '_trailer_enabled', False):
        return _EFTR_DETAIL_DOWN(self)
    self.detail_focus = min(2, self.detail_focus + 1)
    self.update_detail_focus()

def _eftr_ok(self):
    if getattr(self, '_trailer_busy', False):
        return
    if getattr(self, '_trailer_enabled', False) and self.detail_focus == 2:
        return self.trailer_begin()
    return _EFTR_DETAIL_OK(self)

def _eftr_begin(self):
    if not self._trailer_enabled or self._trailer_busy:
        return
    try:
        auth = get_emby_auth()
    except Exception:
        self.session.open(_eftr_MessageBox, 'Emby-Anmeldung konnte nicht gelesen werden.', _eftr_MessageBox.TYPE_ERROR)
        return
    self._trailer_busy = True
    self._trailer_result = None
    self._trailer_cancel = _eftr_threading.Event()
    data = dict(self.data)
    cancel = self._trailer_cancel
    self['trailer_button'].setText('Wird geladen ...')
    def worker():
        directory = None
        try:
            url = _eftr_lookup(data, auth, cancel)
            resolver = _eftr_ensure_resolver(cancel)
            if cancel.is_set():
                return
            directory = _eftr_tempfile.mkdtemp(prefix='embyflow-trailer-')
            command = [_eftr_sys.executable, resolver, '--ignore-config', '--no-playlist',
                       '--skip-download', '--socket-timeout', '15', '--retries', '1',
                       '-f', 'bv*[height<=720]/b', '--dump-single-json', url]
            process = _eftr_subprocess.Popen(
                command, stdout=_eftr_subprocess.PIPE, stderr=_eftr_subprocess.PIPE)
            self._trailer_process = process
            try:
                if cancel.is_set():
                    process.kill()
                stdout, stderr = process.communicate(timeout=60)
            except _eftr_subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise RuntimeError('Das Laden des Trailers hat zu lange gedauert.')
            finally:
                self._trailer_process = None
            if cancel.is_set():
                return
            if process.returncode:
                raise RuntimeError('YouTube konnte diesen Trailer nicht aufloesen.')
            info = _eftr_json.loads(stdout.decode('utf-8'))
            path, playlist = _eftr_select_stream(info)
            if playlist:
                path = str(_eftr_Path(directory) / 'trailer.m3u8')
                _eftr_Path(path).write_text(playlist)
            if cancel.is_set():
                return
            with self._trailer_lock:
                if not cancel.is_set():
                    self._trailer_result = {'path': path, 'directory': directory}
                    directory = None
        except Exception as error:
            if not cancel.is_set():
                self._trailer_result = {'error': str(error)}
        finally:
            if directory:
                _eftr_shutil.rmtree(directory, ignore_errors=True)
    _eftr_threading.Thread(target=worker, daemon=True).start()
    self._trailer_timer.start(200, True)

def _eftr_poll(self):
    if self._trailer_closed:
        return
    result = self._trailer_result
    if result is None:
        self._trailer_timer.start(200, True)
        return
    self._trailer_result = None
    self._trailer_busy = False
    self.update_detail_focus()
    if result.get('error'):
        self.session.open(_eftr_MessageBox, result['error'], _eftr_MessageBox.TYPE_INFO)
        return
    self._trailer_directory = result.get('directory')
    try:
        self._trailer_media_active = True
        self._fallback_poll_timer.stop()
        _fallback_detail_stop(self, restore=False)
        _embyflow_theme_stop_v1(self, restore=False)
        _skyfall_local_theme_stop(self, restore=False)
        _embyflow_theme_volume_release(self)
        self.session.nav.stopService()
        self.session.openWithCallback(
            self.trailer_return, EmbyFlowTrailerPlayer,
            result['path'], str(self.data.get('title') or 'Trailer'))
    except Exception:
        self.trailer_return()
        self.session.open(_eftr_MessageBox,
                          'Trailer konnte nicht gestartet werden.',
                          _eftr_MessageBox.TYPE_ERROR)

def _eftr_return(self, *args):
    self._trailer_media_active = False
    directory = self._trailer_directory
    self._trailer_directory = None
    if directory:
        _eftr_shutil.rmtree(directory, ignore_errors=True)
    if not self._trailer_closed:
        state = getattr(self.session, '_embyflow_local_tv_mute', None)
        if state is not None and not getattr(state, 'finished', False):
            state.check()
        if hasattr(self, '_blue_detail_return'):
            self._blue_detail_return()
        self.update_detail_focus()
        if getattr(self, '_fallback_result', None) is not None:
            self._fallback_poll_timer.start(200, True)

def _eftr_close(self):
    self._trailer_closed = True
    with self._trailer_lock:
        self._trailer_cancel.set()
        result = self._trailer_result or {}
        self._trailer_result = None
    self._trailer_timer.stop()
    process = self._trailer_process
    if process is not None:
        try:
            process.kill()
        except OSError:
            pass
    for directory in (self._trailer_directory, result.get('directory')):
        if directory:
            _eftr_shutil.rmtree(directory, ignore_errors=True)
    self._trailer_result = None

EmbyFlowDetailScreen.__init__ = _eftr_detail_init
EmbyFlowDetailScreen.update_detail_focus = _eftr_focus
EmbyFlowDetailScreen.detail_up = _eftr_up
EmbyFlowDetailScreen.detail_down = _eftr_down
EmbyFlowDetailScreen.detail_ok = _eftr_ok
EmbyFlowDetailScreen.trailer_begin = _eftr_begin
EmbyFlowDetailScreen.trailer_poll = _eftr_poll
EmbyFlowDetailScreen.trailer_return = _eftr_return
EmbyFlowDetailScreen.trailer_close = _eftr_close

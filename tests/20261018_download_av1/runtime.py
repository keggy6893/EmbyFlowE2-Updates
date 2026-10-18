# EMBYFLOW_DOWNLOAD_AV1_LOCAL_TEST_V1
import copy as _efav_copy
import queue as _efav_queue
import re as _efav_re
import threading as _efav_threading
from urllib.parse import quote as _efav_quote


class _EFAVError(Exception):
    pass


def _efav_identity(entry):
    name = _eflib_os.path.basename(entry['path'])
    match = _efav_re.search(r'_(\d+|[a-fA-F0-9]{32})_([A-Za-z0-9_-]{1,48})\.[^.]+$', name)
    if not match:
        raise _EFAVError('AV1: Originaltitel konnte nicht sicher zugeordnet werden.')
    title = (entry.get('metadata') or {}).get('Name') or name[:match.start()]
    return match.group(1), str(title)


def _efav_resolve(entry, cancel):
    item_id, expected_title = _efav_identity(entry)
    server, token, user = get_emby_auth()
    if not server or not token or not user:
        raise _EFAVError('AV1 benoetigt eine Verbindung zum urspruenglichen Emby-Server.')
    if cancel.is_set():
        return None
    response = embyflow_http_get(
        server.rstrip('/') + '/Users/%s/Items/%s' % (_efav_quote(str(user), safe=''), _efav_quote(item_id, safe='')),
        headers={'X-Emby-Token': token, 'X-Emby-Authorization': AUTH_HEADER}, timeout=8, verify=True)
    if response.status_code != 200:
        raise _EFAVError('AV1: Originaltitel auf dem verbundenen Server nicht erreichbar.')
    item = response.json() or {}
    # Never substitute a fuzzy search result or a different title/account item.
    if (str(item.get('Id') or '') != item_id
            or _embyflow_v22_norm(item.get('Name')) != _embyflow_v22_norm(expected_title)):
        raise _EFAVError('AV1: Titel passt nicht zum Download. Bitte den Originalserver verbinden.')
    kind = (entry.get('metadata') or {}).get('Type')
    if kind and item.get('Type') != kind:
        raise _EFAVError('AV1: Titeltyp passt nicht zum Download.')
    if cancel.is_set():
        return None
    position, duration = get_embyflow_local_resume('local:' + entry['path'])
    item = _efav_copy.deepcopy(item)
    item['UserData'] = dict(item.get('UserData') or {})
    item['UserData']['PlaybackPositionTicks'] = int(position or 0)
    item['PlaybackPositionTicks'] = int(position or 0)
    # This is the current, working direct-stream decision path. It detects AV1
    # and negotiates H.264 HLS. The older audio_mode='aac' forces progressive
    # MP4 before that HLS decision and is intentionally not used here.
    info = fetch_stream_info(item.get('Name'), 'direct', item_id=item_id, item_data=item)
    if cancel.is_set():
        return None
    if not isinstance(info, dict) or not info.get('url'):
        raise _EFAVError('AV1: Emby konnte keinen kompatiblen Stream bereitstellen.')
    info['embyflow_local_av1_fallback'] = True
    info['embyflow_local_source_path'] = entry['path']
    return item.get('Name') or expected_title, info


_efav_init_before = EmbyFlowDownloadsScreen.__init__
_efav_play_before = EmbyFlowDownloadsScreen.play


def _efav_cleanup(self):
    self._efav_cancel.set()
    self._efav_timer.stop()
    self._efav_running = False


def _efav_init(self, *args, **kwargs):
    _efav_init_before(self, *args, **kwargs)
    self._efav_cancel = _efav_threading.Event()
    self._efav_results = _efav_queue.Queue()
    self._efav_running = False
    self._efav_timer = eTimer()
    try:
        self._efav_timer.callback.append(lambda: _efav_poll(self))
    except Exception:
        self._efav_timer_connection = self._efav_timer.timeout.connect(lambda: _efav_poll(self))
    self.onClose.append(lambda: _efav_cleanup(self))


def _efav_poll(self):
    if self.closed or self._efav_cancel.is_set():
        return _efav_cleanup(self)
    try:
        entry, result, error = self._efav_results.get_nowait()
    except _efav_queue.Empty:
        return
    self._efav_timer.stop()
    self._efav_running = False
    if error:
        self['status'].setText(error)
        return
    if not result or not _eflib_valid(entry):
        self['status'].setText('AV1: Download wurde entfernt oder veraendert. Bitte aktualisieren.')
        return
    title, info = result
    self['status'].setText('AV1 wird online ueber Emby abgespielt. Die lokale Datei bleibt erhalten.')
    reference = eServiceReference(STREAM_SERVICE_TYPE, 0, info['url'])
    reference.setName(title)
    _open_embyflow_player_now(self.session, reference, title, info['url'], info)


def _efav_play(self):
    if self.closed or self.loading or self._efav_running or not self.entries:
        return
    entry = self.entries[self.index]
    if not _eflib_valid(entry):
        self['status'].setText('Datei oder Datentraeger nicht mehr verfuegbar. BLAU: Aktualisieren')
        return
    probe = _embyflow_v21b_probe_local_file(entry['path']) or {}
    streams = probe.get('media_streams') or []
    av1 = any(str(stream.get('Codec') or '').lower() in ('av1', 'av01')
              for stream in streams if str(stream.get('Type') or '').lower() == 'video')
    if not av1:
        return _efav_play_before(self)
    self._efav_running = True
    self['status'].setText('AV1 erkannt - kompatible Wiedergabe ueber Emby wird vorbereitet ...')
    entry = _efav_copy.deepcopy(entry)
    cancel = self._efav_cancel
    def worker():
        result, error = None, ''
        try:
            result = _efav_resolve(entry, cancel)
        except _EFAVError as exception:
            error = str(exception)
        except Exception:
            error = 'AV1: Emby-Verbindung oder Transcoding fehlgeschlagen. Originaldatei bleibt erhalten.'
        if not cancel.is_set():
            self._efav_results.put((entry, result, error))
    try:
        _efav_threading.Thread(target=worker, daemon=True).start()
        self._efav_timer.start(200, False)
    except Exception:
        self._efav_running = False
        self['status'].setText('AV1-Wiedergabe konnte nicht vorbereitet werden.')


EmbyFlowDownloadsScreen.__init__ = _efav_init
EmbyFlowDownloadsScreen.play = _efav_play

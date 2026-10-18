"""Server-authorized progressive conversion, saved as a complete offline MP4."""
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from urllib.parse import quote, urljoin, urlsplit, parse_qsl, urlencode, urlunsplit
from uuid import uuid4

BITRATE = 6200000


class CompatibilityError(ValueError):
    pass


def estimate(ticks):
    seconds = int(ticks or 0) / 10000000
    if not 1 <= seconds <= 86400:
        raise CompatibilityError('Kompatibler Download: gueltige Laufzeit fehlt.')
    return math.ceil(seconds * BITRATE / 8 * 1.25)


def authorized_url(server, address, token):
    base, target = urlsplit(server), urlsplit(urljoin(server.rstrip('/') + '/', str(address)))
    if (base.scheme not in ('http', 'https') or target.scheme != base.scheme
            or target.hostname != base.hostname or target.port != base.port
            or target.username or target.password or target.fragment
            or not target.path.lower().endswith('.mp4')):
        raise CompatibilityError('Server liefert keinen passenden MP4-Download. Es wurde nichts gespeichert.')
    query = parse_qsl(target.query, keep_blank_values=True)
    if not any(key.lower() in ('api_key', 'x-emby-token') for key, value in query):
        query.append(('api_key', token))
    return urlunsplit((target.scheme, target.netloc, target.path, urlencode(query), ''))


def negotiate(client, server, token, user, item_id, source_id, auth_header, cancel):
    if cancel.is_set():
        return None
    headers = {'X-Emby-Token': token, 'X-Emby-Authorization': auth_header}
    with client.get(server.rstrip('/') + '/Users/%s/Items/%s' %
                    (quote(str(user), safe=''), quote(str(item_id), safe='')),
                    headers=headers, timeout=(8, 20), verify=True, allow_redirects=False) as response:
        if response.status_code != 200:
            raise CompatibilityError('Titel oder Downloadfreigabe nicht mehr erreichbar.')
        item = response.json()
    if not isinstance(item, dict) or str(item.get('Id')) != str(item_id) or item.get('Type') not in ('Movie', 'Episode'):
        raise CompatibilityError('Titel konnte nicht sicher geprueft werden.')
    if item.get('CanDownload') is False:
        raise CompatibilityError('Der Anbieter erlaubt diesen Download nicht.')
    source = next((s for s in item.get('MediaSources') or [] if str(s.get('Id')) == str(source_id)), None)
    if not source:
        raise CompatibilityError('Gewaehlte Filmversion ist nicht mehr verfuegbar.')
    ticks = int(source.get('RunTimeTicks') or item.get('RunTimeTicks') or 0)
    size = estimate(ticks)
    tracks = [s for s in source.get('MediaStreams') or [] if s.get('Type') == 'Audio']
    audio = next((s.get('Index') for s in tracks if s.get('Index') == source.get('DefaultAudioStreamIndex')),
                 next((s.get('Index') for s in tracks if s.get('IsDefault')), tracks[0].get('Index') if tracks else None))
    session = str(uuid4())
    body = {
        'UserId': str(user), 'MediaSourceId': str(source_id), 'IsPlayback': True,
        'AutoOpenLiveStream': False, 'EnableDirectPlay': False, 'EnableDirectStream': False,
        'EnableTranscoding': True, 'AllowVideoStreamCopy': False, 'AllowAudioStreamCopy': False,
        'StartTimeTicks': 0, 'SubtitleStreamIndex': -1, 'CurrentPlaySessionId': session,
        'MaxWidth': 1920, 'MaxHeight': 1080, 'MaxStreamingBitrate': BITRATE,
        'MaxAudioChannels': 2, 'AudioBitRate': 192000,
        'DeviceProfile': {
            'Name': 'EmbyFlow Offline H264 AAC MP4', 'MaxStreamingBitrate': BITRATE,
            'DirectPlayProfiles': [], 'CodecProfiles': [], 'ContainerProfiles': [],
            'SubtitleProfiles': [], 'ResponseProfiles': [],
            'TranscodingProfiles': [{'Container': 'mp4', 'Type': 'Video', 'VideoCodec': 'h264',
                                     'AudioCodec': 'aac', 'Protocol': 'http', 'Context': 'Streaming',
                                     'MaxAudioChannels': '2'}],
        },
    }
    if audio is not None:
        body['AudioStreamIndex'] = audio
    if cancel.is_set():
        return None
    with client.post(server.rstrip('/') + '/Items/' + quote(str(item_id), safe='') + '/PlaybackInfo',
                     headers=headers, json=body, timeout=(8, 20), verify=True, allow_redirects=False) as response:
        if response.status_code != 200:
            raise CompatibilityError('Der Anbieter hat die kompatible Umwandlung nicht freigegeben.')
        payload = response.json()
    if not isinstance(payload, dict) or payload.get('ErrorCode'):
        raise CompatibilityError('Keine passende Umwandlungsfreigabe vom Server.')
    selected = next((s for s in payload.get('MediaSources') or [] if str(s.get('Id')) == str(source_id)), None)
    if not selected or selected.get('SupportsTranscoding') is False or not selected.get('TranscodingUrl'):
        raise CompatibilityError('Server bietet keine kompatible Downloadversion an.')
    url = authorized_url(server, selected['TranscodingUrl'], token)
    return dict(url=url, session=str(payload.get('PlaySessionId') or session), ticks=ticks, size=size,
                audio=audio is not None)


def verify_file(path, seconds, expect_audio, cancel=None):
    executable = shutil.which('ffprobe')
    if not executable:
        raise CompatibilityError('ffprobe fehlt: Offline-Datei kann nicht geprueft werden.')
    # Read packet tables AND the media payload: MP4 headers alone can describe
    # a full-length movie even when a chunked HTTP transfer stopped early.
    command = [executable, '-v', 'error', '-count_packets', '-show_entries',
        'format=duration:stream=codec_type,codec_name,width,height,pix_fmt,channels,nb_frames,nb_read_packets',
        '-of', 'json', str(path)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.monotonic() + max(60, min(1800, 30 + os.path.getsize(path) / (4 * 1024**2)))
    try:
        while True:
            if cancel is not None and cancel.is_set():
                raise CompatibilityError('Dateipruefung abgebrochen. Teildatei wird entfernt.')
            if time.monotonic() > deadline:
                raise CompatibilityError('Dateipruefung hat das Zeitlimit erreicht.')
            try:
                stdout, stderr = process.communicate(timeout=.3)
                break
            except subprocess.TimeoutExpired:
                pass
        if process.returncode or stderr.strip():
            raise CompatibilityError('MP4-Datei unvollstaendig oder beschaedigt. Teildatei wird entfernt.')
        payload = json.loads(stdout)
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate()
    video = [s for s in payload.get('streams') or [] if s.get('codec_type') == 'video']
    audio = [s for s in payload.get('streams') or [] if s.get('codec_type') == 'audio']
    if (not video or any(s.get('codec_name') != 'h264' or s.get('pix_fmt') != 'yuv420p' or not 0 < int(s.get('width') or 0) <= 1920
                         or not 0 < int(s.get('height') or 0) <= 1080 for s in video)
            or (expect_audio and not audio) or any(s.get('codec_name') != 'aac' or not 0 < int(s.get('channels') or 0) <= 2 for s in audio)):
        raise CompatibilityError('Gespeicherte Datei ist nicht H.264/AAC-kompatibel. Keine fertige Datei freigegeben.')
    duration = float((payload.get('format') or {}).get('duration') or 0)
    if not math.isfinite(duration) or duration < max(0.1, seconds * .95, seconds - 5) or duration > seconds + 30:
        raise CompatibilityError('Kompatibler Download ist unvollstaendig. Teildatei wird entfernt.')
    for stream in video + audio:
        count = int(stream.get('nb_read_packets') or 0)
        expected = stream.get('nb_frames')
        if count <= 0 or (expected not in (None, 'N/A') and count + 2 < int(expected)):
            raise CompatibilityError('MP4-Mediendaten unvollstaendig. Teildatei wird entfernt.')


def download(client, server, token, user, item, source, target, cancel, progress, base, auth_header, permission=None):
    if not shutil.which('ffprobe'):
        raise CompatibilityError('Fuer den kompatiblen Download wird ffprobe auf der Box benoetigt.')
    if not base.ACTIVE.acquire(False):
        raise CompatibilityError('Es laeuft bereits ein Download.')
    quota, partial, completed, decision = None, None, False, None
    try:
        if cancel.is_set():
            raise base.DownloadCancelled()
        base.check_permission(client, server, token, user, cancel)
        if permission:
            permission()
        if os.path.lexists(target):
            raise CompatibilityError('Zieldatei existiert bereits.')
        decision = negotiate(client, server, token, user, item['Id'], source['_efcmp_original_id'], auth_header, cancel)
        if cancel.is_set() or decision is None:
            raise base.DownloadCancelled()
        base.check_space(os.path.dirname(target), decision['size'])
        quota = base.DailyQuota()
        quota.reserve()
        with client.get(decision['url'], stream=True, headers={'Accept-Encoding': 'identity'},
                        timeout=(8, 30), verify=True, allow_redirects=False) as response:
            if response.status_code != 200:
                raise CompatibilityError('Server hat den kompatiblen Download abgelehnt.')
            content = response.headers.get('Content-Type', '').lower()
            if any(word in content for word in ('text/', 'json', 'mpegurl')):
                raise CompatibilityError('Server liefert keine vollstaendige MP4-Datei.')
            length = response.headers.get('Content-Length')
            length = int(length) if length else None
            if length is not None and not 0 < length <= decision['size']:
                raise CompatibilityError('Server-Dateigroesse ueberschreitet das Speicherbudget.')
            descriptor, partial = tempfile.mkstemp(prefix='.embyflow-compatible-', suffix='.part', dir=os.path.dirname(target))
            received = 0
            with os.fdopen(descriptor, 'wb') as output:
                for chunk in response.iter_content(256 * 1024):
                    if cancel.is_set():
                        raise base.DownloadCancelled()
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > decision['size']:
                        raise CompatibilityError('Speicherbudget ueberschritten. Teildatei wird entfernt.')
                    if shutil.disk_usage(os.path.dirname(target)).free < len(chunk) + base.RESERVE:
                        raise CompatibilityError('Freier Speicherplatz aufgebraucht.')
                    output.write(chunk)
                    progress(received, decision['size'])
                if not received or (length is not None and received != length):
                    raise CompatibilityError('Serveruebertragung unvollstaendig.')
                output.flush()
                os.fsync(output.fileno())
        if cancel.is_set():
            raise base.DownloadCancelled()
        verify_file(partial, decision['ticks'] / 10000000, decision['audio'], cancel)
        if cancel.is_set():
            raise base.DownloadCancelled()
        os.link(partial, target)
        completed = True
        return target
    finally:
        try:
            if partial:
                os.unlink(partial)
        finally:
            try:
                if quota:
                    quota.close(completed)
            finally:
                base.ACTIVE.release()
                if decision:
                    try:
                        client.delete(server.rstrip('/') + '/Videos/ActiveEncodings',
                            headers={'X-Emby-Token': token, 'X-Emby-Authorization': auth_header},
                            params={'deviceId': 'embyflowe2', 'PlaySessionId': decision['session']},
                            timeout=(5, 5), verify=True, allow_redirects=False)
                    except Exception:
                        pass

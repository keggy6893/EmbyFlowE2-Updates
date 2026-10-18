"""Original-file download; no credentials or URLs persisted on disk."""
import os
import re
import shutil
import tempfile
import threading
import json
import time
import fcntl

ACTIVE = threading.Lock()
RESERVE = 512 * 1024 * 1024
DAILY_LIMIT = 5
QUOTA_PATH = '/etc/enigma2/embyflow-download-quota.json'

def quota_status():
    """Read the atomically published counter without waiting on a transfer lock."""
    import stat
    try:
        if not os.path.isdir(os.path.dirname(QUOTA_PATH)):
            return None
        try:
            fd = os.open(QUOTA_PATH, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            days = {}
        else:
            with os.fdopen(fd) as handle:
                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                    return None
                record = json.load(handle)
            if not isinstance(record, dict) or record.get('version') != 1 or not isinstance(record.get('days'), dict):
                return None
            days = record['days']
            if any(not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) or
                   type(count) is not int or not 0 <= count <= DAILY_LIMIT for day, count in days.items()):
                return None
        used = days.get(time.strftime('%Y-%m-%d'), 0)
        return {'used': used, 'remaining': DAILY_LIMIT - used, 'limit': DAILY_LIMIT}
    except Exception:
        return None

class DailyQuota:
    """One shared, persistent box quota. Reserve before HTTP; refund normal errors.

    A process crash retains its reservation conservatively, since the finished
    file and quota cannot be committed in a single filesystem transaction.
    """
    def __init__(self):
        self.lock = None
        self.reserved = False

    def write(self):
        directory = os.path.dirname(QUOTA_PATH)
        fd, temporary = tempfile.mkstemp(prefix='.embyflow-quota-', dir=directory)
        try:
            with os.fdopen(fd, 'w') as handle:
                json.dump({'version': 1, 'days': self.days}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, QUOTA_PATH)
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def reserve(self):
        import stat
        try:
            fd = os.open(QUOTA_PATH + '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            self.lock = os.fdopen(fd, 'r+')
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError('Ungueltige Tageszaehler-Datei.')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('Es laeuft bereits ein Film-/Serien-Download.') from None
            self.day = time.strftime('%Y-%m-%d')
            try:
                fd = os.open(QUOTA_PATH, os.O_RDONLY | os.O_NOFOLLOW)
            except FileNotFoundError:
                self.days = {}
            else:
                with os.fdopen(fd) as handle:
                    record = json.load(handle)
                if (not isinstance(record, dict) or record.get('version') != 1 or
                        not isinstance(record.get('days'), dict)):
                    raise ValueError('Ungueltiger Tageszaehler.')
                self.days = record['days']
                if any(not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) or
                       type(count) is not int or not 0 <= count <= DAILY_LIMIT for day, count in self.days.items()):
                    raise ValueError('Ungueltiger Tageszaehler.')
            if self.days.get(self.day, 0) >= DAILY_LIMIT:
                raise ValueError('Tageslimit erreicht: maximal 5 Filme oder Serienfolgen pro Tag. Morgen wieder moeglich.')
            self.days[self.day] = self.days.get(self.day, 0) + 1
            self.write()
            self.reserved = True
        except ValueError:
            self.close(True)
            raise
        except Exception:
            self.close(True)
            raise ValueError('Tageslimit konnte nicht sicher geprueft werden. Kein Download gestartet.') from None

    def close(self, completed):
        try:
            if self.reserved and not completed:
                self.days[self.day] -= 1
                self.write()
            self.reserved = False
        finally:
            if self.lock is not None:
                self.lock.close()
                self.lock = None

class DownloadCancelled(Exception):
    pass

def filename(title, item_id, source):
    ext = str(source.get('Container') or '').lower()
    if ext not in ('mkv', 'mp4', 'avi', 'ts', 'm2ts', 'mov', 'webm'):
        raise ValueError('Dateiformat wird im lokalen Test nicht unterstuetzt.')
    name = re.sub(r'[^\w .()-]', '_', str(title))[:100].strip(' .') or 'Film'
    ident = re.sub(r'[^a-zA-Z0-9_-]', '_', str(item_id))[:48]
    version = re.sub(r'[^a-zA-Z0-9_-]', '_', str(source.get('Id') or ''))[:48]
    return '%s_%s_%s.%s' % (name, ident, version, ext)

def check_space(directory, size):
    size = int(size)
    if size <= 0:
        raise ValueError('Dateigroesse unbekannt. Download nicht gestartet.')
    if shutil.disk_usage(directory).free < size + RESERVE:
        raise ValueError('Nicht genug freier Platz (zusaetzlich 512 MiB Reserve erforderlich).')

def download(client, url, token, source, target, cancel, progress):
    if not ACTIVE.acquire(False):
        raise ValueError('Es laeuft bereits ein Film-Download.')
    partial = None
    quota = None
    completed = False
    try:
        size = int(source.get('Size') or 0)
        check_space(os.path.dirname(target), size)
        if os.path.lexists(target):
            raise ValueError('Zieldatei existiert bereits.')
        if cancel.is_set():
            raise DownloadCancelled()
        quota = DailyQuota()
        quota.reserve()
        # No redirects: never forward authentication to an unrelated host.
        with client.get(url, params={'api_key': token, 'MediaSourceId': source['Id']},
                        stream=True, timeout=(8, 30), verify=True,
                        allow_redirects=False, headers={'Accept-Encoding': 'identity'}) as response:
            if response.status_code == 403:
                raise DownloadPermissionDenied('Der Anbieter verweigert diesen Download: HTTP 403.')
            if response.status_code != 200:
                raise ValueError('Download abgelehnt: HTTP %s' % response.status_code)
            if 'text/' in response.headers.get('Content-Type', '').lower() or 'json' in response.headers.get('Content-Type', '').lower():
                raise ValueError('Server liefert keine Filmdatei.')
            length = response.headers.get('Content-Length')
            if length and int(length) != size:
                raise ValueError('Server-Dateigroesse weicht von der gewaehlten Filmversion ab.')
            fd, partial = tempfile.mkstemp(prefix='.embyflow-', suffix='.part', dir=os.path.dirname(target))
            received = 0
            with os.fdopen(fd, 'wb') as handle:
                for chunk in response.iter_content(256 * 1024):
                    if cancel.is_set():
                        raise DownloadCancelled()
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > size:
                        raise ValueError('Antwort groesser als erwartete Filmdatei.')
                    if shutil.disk_usage(os.path.dirname(target)).free < len(chunk) + RESERVE:
                        raise ValueError('Freier Speicherplatz aufgebraucht.')
                    handle.write(chunk)
                    progress(received, size)
                if received != size:
                    raise ValueError('Download unvollstaendig.')
                handle.flush()
                os.fsync(handle.fileno())
            if cancel.is_set():
                raise DownloadCancelled()
            # Atomic publication without overwriting an existing file.
            os.link(partial, target)
            completed = True
            return target
    finally:
        try:
            if partial:
                os.unlink(partial)
        finally:
            try:
                if quota is not None:
                    quota.close(completed)
            finally:
                ACTIVE.release()

class DownloadPermissionDenied(ValueError):
    """The server explicitly disabled downloads for this user/item."""

class DownloadPermissionUnknown(ValueError):
    """No reliable permission answer: do not start a download."""

def check_permission(client, server, token, user, cancel):
    from urllib.parse import quote
    if cancel.is_set():
        raise DownloadCancelled()
    if not server or not token or not user:
        raise DownloadPermissionUnknown('Downloadfreigabe nicht prüfbar: Anmeldung fehlt.')
    try:
        with client.get(server.rstrip('/') + '/Users/' + quote(str(user), safe=''),
                        params={'api_key': token}, timeout=(8, 20), verify=True,
                        headers={'Cache-Control': 'no-cache', 'Pragma': 'no-cache'},
                        allow_redirects=False) as response:
            if response.status_code != 200:
                raise DownloadPermissionUnknown('Downloadfreigabe nicht prüfbar: HTTP %s.' % response.status_code)
            payload = response.json()
        if cancel.is_set():
            raise DownloadCancelled()
        policy = payload.get('Policy') if isinstance(payload, dict) else None
        value = policy.get('EnableContentDownloading') if isinstance(policy, dict) else None
        if value is False:
            raise DownloadPermissionDenied('Der Emby-Anbieter erlaubt deinem Benutzerkonto keine Film-Downloads.')
        if value is not True:
            raise DownloadPermissionUnknown('Der Emby-Server meldet keine eindeutige Downloadfreigabe.')
    except (DownloadPermissionDenied, DownloadPermissionUnknown, DownloadCancelled):
        raise
    except Exception:
        # Never put request URLs, tokens or raw exception text into the UI/logs.
        raise DownloadPermissionUnknown('Downloadfreigabe konnte nicht geprüft werden. Bitte später erneut versuchen.') from None
    return True

def storage_info(directory, required):
    """Capacity snapshot for the chooser; transfer checks free space again."""
    required = int(required)
    try:
        usage = shutil.disk_usage(directory)
        return {'known': True, 'free': usage.free, 'total': usage.total,
                'required': required, 'reserve': RESERVE,
                'enough': required > 0 and usage.free >= required + RESERVE}
    except OSError:
        return {'known': False, 'required': required, 'reserve': RESERVE, 'enough': False}

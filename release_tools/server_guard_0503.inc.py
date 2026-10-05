# EMBYFLOW_SERVER_GUARD_0503_START
# Plugin-local requests facade: does not patch requests for other E2 plugins.
import threading as _efguard_threading
import math as _efguard_math
from urllib.parse import urlsplit as _efguard_urlsplit
from email.utils import parsedate_to_datetime as _efguard_httpdate

_efguard_lock = _efguard_threading.RLock()
_efguard_servers = {}
_efguard_logins = {}
_efguard_notice = None
_efguard_clock = time.monotonic
_efguard_requests = requests


class EmbyFlowServerPaused(RuntimeError):
    pass


def _efguard_key(url):
    # /emby, scheme and alternate ports must not evade a host's cooldown.
    return (_efguard_urlsplit(str(url)).hostname or '').lower()


def _efguard_message(status, remaining):
    return ('Server-Anfragen pausiert (HTTP %s). Noch %d Sekunden. '
            'Bitte warten; keine erneute Anmeldung versuchen.'
            % (status, max(1, int(_efguard_math.ceil(remaining)))))


def _efguard_check(url, claim=False):
    key = _efguard_key(url)
    with _efguard_lock:
        state = _efguard_servers.get(key)
        if not state:
            return
        remaining = state['until'] - _efguard_clock()
        if remaining > 0 or state.get('probe'):
            raise EmbyFlowServerPaused(_efguard_message(state['status'], remaining))
        if claim:
            state['probe'] = True


def _efguard_trip(url, response):
    global _efguard_notice
    delay = 300.0
    raw = str(response.headers.get('Retry-After', '')).strip()
    try:
        seconds = float(raw)
        if _efguard_math.isfinite(seconds):
            delay = max(delay, seconds)
    except (ValueError, TypeError):
        try:
            delay = max(delay, _efguard_httpdate(raw).timestamp() - time.time())
        except Exception:
            pass
    with _efguard_lock:
        key = _efguard_key(url)
        previous = _efguard_servers.get(key, {})
        _efguard_servers[key] = dict(
            until=max(previous.get('until', 0), _efguard_clock() + delay),
            status=response.status_code, probe=False)
        _efguard_notice = _efguard_message(response.status_code, delay)


def _efguard_login_state(url, body):
    username = str((body or {}).get('Username') or '') if isinstance(body, dict) else ''
    key = (_efguard_key(url), username)
    with _efguard_lock:
        return _efguard_logins.setdefault(key, dict(
            lock=_efguard_threading.RLock(), failures=0, until=0))


def _efguard_send(session, request, **kwargs):
    url = request.url
    login = (str(request.method).upper() == 'POST' and
             _efguard_urlsplit(url).path.rstrip('/').lower().endswith('/users/authenticatebyname'))
    state = None
    if login:
        try:
            body = json.loads(request.body or '{}')
        except Exception:
            body = {}
        state = _efguard_login_state(url, body)
        state['lock'].acquire()
    try:
        _efguard_check(url)
        if state:
            remaining = state['until'] - _efguard_clock()
            if remaining > 0:
                raise EmbyFlowServerPaused('Login pausiert. Noch %d Sekunden.' %
                                          max(1, int(_efguard_math.ceil(remaining))))
            # Do not forward credentials to another candidate or redirect.
            kwargs['allow_redirects'] = False
        _efguard_check(url, claim=True)
        login_failure = False
        try:
            response = super(_EFGuardSession, session).send(request, **kwargs)
            login_failure = bool(state and response.status_code in (200, 401, 403, 429))
            if response.status_code in (403, 429):
                _efguard_trip(url, response)
                response.close()
                _efguard_check(url)
            with _efguard_lock:
                server_state = _efguard_servers.get(_efguard_key(url))
                if server_state and server_state.get('probe'):
                    _efguard_servers.pop(_efguard_key(url), None)
            if state and response.status_code in (200, 401):
                data = response.json() if response.status_code == 200 else {}
                if not data.get('AccessToken') or not (data.get('User') or {}).get('Id'):
                    raise RuntimeError('Login fehlgeschlagen (HTTP %s).' % response.status_code)
                state.update(failures=0, until=0)
            return response
        except Exception:
            if state and login_failure:
                failures = min(5, state['failures'] + 1)
                state.update(failures=failures,
                             until=_efguard_clock() + min(900, 60 * (2 ** (failures - 1))))
            with _efguard_lock:
                server_state = _efguard_servers.get(_efguard_key(url))
                if server_state and server_state.get('probe'):
                    server_state.update(until=_efguard_clock() + 300, probe=False)
            raise
    finally:
        if state:
            state['lock'].release()


if requests:
    class _EFGuardSession(_efguard_requests.Session):
        def send(self, request, **kwargs):
            return _efguard_send(self, request, **kwargs)

    class _EFGuardRequests:
        Session = _EFGuardSession

        def __getattr__(self, name):
            return getattr(_efguard_requests, name)

        def request(self, method, url, **kwargs):
            with self.Session() as session:
                return session.request(method, url, **kwargs)

        def get(self, url, **kwargs):
            return self.request('GET', url, **kwargs)

        def post(self, url, **kwargs):
            return self.request('POST', url, **kwargs)

        def delete(self, url, **kwargs):
            return self.request('DELETE', url, **kwargs)

        def put(self, url, **kwargs):
            return self.request('PUT', url, **kwargs)

        def head(self, url, **kwargs):
            return self.request('HEAD', url, **kwargs)

        def patch(self, url, **kwargs):
            return self.request('PATCH', url, **kwargs)

    requests = _EFGuardRequests()
# EMBYFLOW_SERVER_GUARD_0503_END

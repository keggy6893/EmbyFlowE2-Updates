"""EmbyFlow optional bounded RAM read-ahead for static HTTP media. No disk cache."""
import collections
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

CAPACITY = 16 * 1024 * 1024  # Per request; at most two requests are admitted.
PREFILL = 4 * 1024 * 1024
CHUNK = 64 * 1024


def eligible(url):
    p = urlsplit(url)
    return (p.scheme in ('http', 'https') and '/videos/' in p.path.lower()
            and '/stream.' in p.path.lower()
            and not p.path.lower().endswith(('.m3u8', '.mpd'))
            and parse_qs(p.query.lower()).get('static') == ['true'])


class ReadAhead:
    def __init__(self, response, manager):
        self.response, self.manager = response, manager
        self.cv = threading.Condition()
        self.parts = collections.deque()
        self.size = 0
        self.done = self.closed = False
        self.error = None
        self.thread = threading.Thread(target=self._produce, daemon=True)
        self.thread.start()

    def _produce(self):
        try:
            while True:
                with self.cv:
                    while self.size + CHUNK > CAPACITY and not self.closed:
                        self.cv.wait(.1)
                    if self.closed:
                        return
                while self.manager.gated() and not self.closed:
                    time.sleep(.05)
                if self.closed:
                    return
                data = self.response.raw.read(CHUNK, decode_content=False)
                # A read may already have been in flight when the gate closed.
                while self.manager.gated() and not self.closed:
                    time.sleep(.05)
                if not data or self.closed:
                    break
                with self.cv:
                    if self.closed:
                        return
                    self.parts.append(data)
                    self.size += len(data)
                    self.cv.notify_all()
        except Exception as error:
            self.error = error
        finally:
            with self.cv:
                self.done = True
                self.cv.notify_all()

    def prefill(self):
        with self.cv:
            while self.size < PREFILL and not self.done and not self.closed:
                self.cv.wait(.1)

    def take(self):
        with self.cv:
            while not self.parts and not self.done and not self.closed:
                self.cv.wait(.1)
            if not self.parts:
                if self.error:
                    raise IOError('Upstream transfer interrupted')
                return b''
            data = self.parts.popleft()
            self.size -= len(data)
            self.cv.notify_all()
            return data

    def close(self):
        with self.cv:
            self.closed = True
            self.parts.clear()
            self.size = 0
            self.cv.notify_all()
        threading.Thread(target=self.response.close, daemon=True).start()


class BufferProxy:
    def __init__(self, request):
        self.request = request  # Plugin's guarded requests facade.
        self.lock = threading.RLock()
        self.routes = {}
        self.active = set()
        self.slots = threading.BoundedSemaphore(2)
        self.until = 0.0
        manager = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self, *args):
                pass  # Never log URLs, tokens or upstream exceptions.
            def do_GET(self):
                self._forward(False)
            def do_HEAD(self):
                self._forward(True)
            def _forward(self, head):
                response = reader = None
                admitted = False
                sent = False
                self.close_connection = True
                try:
                    with manager.lock:
                        url = manager.routes.get(self.path)
                    if not url:
                        self.send_error(404)
                        return
                    if not manager.slots.acquire(False):
                        self.send_error(503)
                        return
                    admitted = True
                    headers = {'Accept-Encoding': 'identity'}
                    for key in ('Range', 'If-Range', 'User-Agent'):
                        if self.headers.get(key):
                            headers[key] = self.headers[key]
                    response = manager.request('HEAD' if head else 'GET', url,
                        headers=headers, stream=True, timeout=(8, 15), allow_redirects=True)
                    ctype = response.headers.get('Content-Type', '').lower()
                    if 'mpegurl' in ctype or 'dash+xml' in ctype:
                        self.send_error(415)
                        return
                    # Preserve 206, Content-Range, 416 and other HTTP statuses.
                    if not head and response.status_code in (200, 206):
                        reader = ReadAhead(response, manager)
                        with manager.lock:
                            manager.active.add(reader)
                        reader.prefill()
                    self.send_response(response.status_code)
                    for key in ('Content-Type', 'Content-Length', 'Content-Range',
                                'Accept-Ranges', 'ETag', 'Last-Modified'):
                        if key in response.headers:
                            self.send_header(key, response.headers[key])
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    sent = True
                    if reader:
                        while True:
                            data = reader.take()
                            if not data:
                                break
                            self.wfile.write(data)
                except Exception:
                    if not sent:
                        try:
                            self.send_error(502, 'Media transfer unavailable')
                        except Exception:
                            pass
                finally:
                    if reader:
                        with manager.lock:
                            manager.active.discard(reader)
                        reader.close()
                    elif response is not None:
                        response.close()
                    if admitted:
                        manager.slots.release()

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def register(self, url):
        if not eligible(url):
            return url
        with self.lock:
            # Switching streams releases stale read-ahead connections and secrets.
            existing = next((p for p, value in self.routes.items() if value == url), None)
            if existing:
                return 'http://127.0.0.1:%d%s' % (self.server.server_port, existing)
            self.routes.clear()
            old = list(self.active)
            path = '/' + secrets.token_hex(24) + '/media'
            self.routes[path] = url
        for reader in old:
            reader.close()
        return 'http://127.0.0.1:%d%s' % (self.server.server_port, path)

    def buffered(self):
        with self.lock:
            readers = list(self.active)
        sizes = []
        for reader in readers:
            with reader.cv:
                sizes.append(reader.size)
        return max(sizes or [0])

    def gated(self):
        with self.lock:
            return time.monotonic() < self.until

    def test(self, seconds=15):
        with self.lock:
            self.until = time.monotonic() + seconds

    def release(self):
        with self.lock:
            self.until = 0.0
            self.routes.clear()
            readers = list(self.active)
        for reader in readers:
            reader.close()

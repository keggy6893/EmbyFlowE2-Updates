"""Read-only, receiver-loopback HTTP range server for ONE original file."""
import os
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _efhc_range(value, size):
    if not value:
        return (0, size - 1, False)
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', value.strip())
    if not match or not any(match.groups()) or size <= 0:
        raise ValueError('range')
    first, last = match.groups()
    if not first:
        count = int(last)
        if count <= 0:
            raise ValueError('range')
        start, end = max(0, size - count), size - 1
    else:
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
        if start >= size or end < start:
            raise ValueError('range')
    return start, end, True


class _EFHCServer:
    def __init__(self, path, log=None):
        self.path = os.path.realpath(path)
        if not os.path.isfile(self.path):
            raise ValueError('Originaldatei fehlt')
        self.route = '/' + secrets.token_hex(16) + '/skyfall.ts'
        self.log = log or (lambda *args: None)
        source = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self, *args):
                pass
            def do_HEAD(self):
                self.serve(False)
            def do_GET(self):
                self.serve(True)
            def serve(self, body):
                if self.path != source.route:
                    self.send_error(404)
                    return
                try:
                    with open(source.path, 'rb') as handle:
                        size = os.fstat(handle.fileno()).st_size
                        try:
                            first, last, partial = _efhc_range(self.headers.get('Range'), size)
                        except ValueError:
                            self.send_response(416)
                            self.send_header('Content-Range', 'bytes */%d' % size)
                            self.send_header('Content-Length', '0')
                            self.send_header('Connection', 'close')
                            self.end_headers()
                            self.close_connection = True
                            return
                        self.send_response(206 if partial else 200)
                        self.send_header('Content-Type', 'video/mp2t')
                        self.send_header('Content-Length', str(max(0, last-first+1)))
                        self.send_header('Accept-Ranges', 'bytes')
                        self.send_header('Connection', 'close')
                        if partial:
                            self.send_header('Content-Range', 'bytes %d-%d/%d' % (first, last, size))
                        self.end_headers()
                        self.close_connection = True
                        source.log('HTTP_RANGE', status=206 if partial else 200,
                                   first=first, last=last, size=size, body=body)
                        if body:
                            handle.seek(first)
                            remaining = last-first+1
                            while remaining > 0 and not source.closing:
                                data = handle.read(min(131072, remaining))
                                if not data:
                                    break
                                self.wfile.write(data)
                                remaining -= len(data)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            block_on_close = False
            allow_reuse_address = False

        self.closing = False
        self.httpd = Server(('127.0.0.1', 0), Handler)
        self.url = 'http://127.0.0.1:%d%s' % (self.httpd.server_port, self.route)
        self.thread = threading.Thread(target=self.httpd.serve_forever,
                                       kwargs={'poll_interval': 0.1}, name='EmbyFlowSkyfallHTTP', daemon=True)
        self.thread.start()

    def close(self):
        if self.closing:
            return
        self.closing = True
        def shutdown():
            self.httpd.shutdown()
            self.httpd.server_close()
        threading.Thread(target=shutdown, name='EmbyFlowSkyfallHTTPStop', daemon=True).start()

import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from types import SimpleNamespace
import requests

spec = importlib.util.spec_from_file_location('engine', Path(__file__).with_name('engine.py'))
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
DATA = b'film-original-data' * 2048
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        self.server.paths.append(self.path)
        if self.path.startswith('/denied'):
            self.send_response(403); self.end_headers(); return
        if self.path.startswith('/redirect'):
            self.send_response(302); self.send_header('Location', '/film'); self.end_headers(); return
        self.send_response(200)
        self.send_header('Content-Type', 'video/x-matroska')
        self.send_header('Content-Length', str(len(DATA)))
        self.end_headers()
        self.wfile.write(DATA)

class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.paths = []
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.quota_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.quota_tmp.cleanup)
        self.quota_patch = patch.object(engine, 'QUOTA_PATH', str(Path(self.quota_tmp.name) / 'quota.json'))
        self.quota_patch.start(); self.addCleanup(self.quota_patch.stop)
        self.target = str(Path(self.tmp.name) / 'film.mkv')
        self.source = {'Id': 'version-4k', 'Size': len(DATA), 'Container': 'mkv'}
        self.cancel = threading.Event()
        self.progress = []
        self.space = patch.object(engine.shutil, 'disk_usage', return_value=SimpleNamespace(free=2**40))
        self.space.start(); self.addCleanup(self.space.stop)
    def run_download(self, path='/film'):
        return engine.download(requests, 'http://127.0.0.1:%d%s' % (self.server.server_port, path), 'test-token', self.source, self.target, self.cancel, lambda a,b: self.progress.append((a,b)))
    def test_original_bytes_progress_version(self):
        self.run_download()
        self.assertEqual(Path(self.target).read_bytes(), DATA)
        self.assertEqual(self.progress[-1], (len(DATA), len(DATA)))
        self.assertIn('MediaSourceId=version-4k', self.server.paths[-1])
        self.assertEqual(len(list(Path(self.tmp.name).iterdir())), 1)
    def test_cancel_removes_partial(self):
        def cancel(a,b): self.cancel.set()
        with self.assertRaises(engine.DownloadCancelled):
            engine.download(requests, 'http://127.0.0.1:%d/film' % self.server.server_port, 'x', self.source, self.target, self.cancel, cancel)
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])
        self.assertFalse(engine.ACTIVE.locked())
        import json
        self.assertEqual(list(json.loads(Path(engine.QUOTA_PATH).read_text())['days'].values()), [0])

    def test_five_downloads_then_no_sixth_http_request(self):
        for index in range(5):
            self.target = str(Path(self.tmp.name) / ('item-%d.mkv' % index))
            self.run_download()
        before = len(self.server.paths)
        self.target = str(Path(self.tmp.name) / 'sixth.mkv')
        with self.assertRaisesRegex(ValueError, 'Tageslimit erreicht'): self.run_download()
        self.assertEqual(len(self.server.paths), before)
        self.assertFalse(Path(self.target).exists())
    def test_permission_denied_no_file(self):
        with self.assertRaisesRegex(ValueError, '403'): self.run_download('/denied')
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])
    def test_redirect_not_followed(self):
        before = len(self.server.paths)
        with self.assertRaisesRegex(ValueError, '302'): self.run_download('/redirect')
        self.assertEqual(len(self.server.paths), before+1)
    def test_insufficient_space_no_request(self):
        before=len(self.server.paths)
        with patch.object(engine.shutil, 'disk_usage', return_value=SimpleNamespace(free=1)):
            with self.assertRaisesRegex(ValueError, 'Platz'): self.run_download()
        self.assertEqual(len(self.server.paths), before)
    def test_existing_file_preserved(self):
        Path(self.target).write_bytes(b'keep')
        with self.assertRaises(ValueError): self.run_download()
        self.assertEqual(Path(self.target).read_bytes(), b'keep')
    def test_wrong_size_rejected(self):
        self.source['Size'] += 100
        with self.assertRaises(ValueError): self.run_download()
        self.assertFalse(Path(self.target).exists())
    def test_single_download(self):
        engine.ACTIVE.acquire()
        try:
            with self.assertRaisesRegex(ValueError, 'bereits'): self.run_download()
        finally: engine.ACTIVE.release()
    def test_filename_cannot_escape(self):
        name=engine.filename('../../evil/film', '../id', dict(self.source, Id='../source'))
        self.assertNotIn('/',name)
        self.assertTrue(name.endswith('.mkv'))
    def test_mid_download_disk_full_cleanup(self):
        with patch.object(engine.shutil, 'disk_usage', side_effect=[SimpleNamespace(free=2**40),SimpleNamespace(free=1)]):
            with self.assertRaisesRegex(ValueError,'Speicherplatz'): self.run_download()
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

if __name__ == '__main__': unittest.main()

import copy
import importlib.util
import json
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load('compatible', HERE / 'engine.py')
base = load('original', HERE.parent / '20261017_movie_download/engine.py')


class Response:
    def __init__(self, payload=None, data=b'', headers=None, code=200, on_chunk=None):
        self.payload, self.data = payload, data
        self.headers, self.status_code = headers or {}, code
        self.on_chunk = on_chunk

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def json(self):
        return self.payload

    def iter_content(self, size):
        for index in range(0, len(self.data), 1024):
            if self.on_chunk:
                self.on_chunk()
            yield self.data[index:index + 1024]


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory()
        cls.mp4 = Path(cls.fixtures.name) / 'sample.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=96x64:r=10',
            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', '6',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ac', '2',
            '-movflags', '+faststart', str(cls.mp4)], check=True, timeout=30)
        cls.movie = cls.mp4.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / 'Film_1731728_mediasource-h264.mp4'
        self.quota = patch.object(base, 'QUOTA_PATH', str(self.root / 'quota.json'))
        self.quota.start()
        self.addCleanup(self.quota.stop)
        self.cancel = threading.Event()
        self.source = {'Id': 'mediasource', 'RunTimeTicks': 60000000, 'DefaultAudioStreamIndex': 2,
            'MediaStreams': [{'Type': 'Video', 'Codec': 'av1', 'Index': 0},
                             {'Type': 'Audio', 'Codec': 'eac3', 'Index': 1},
                             {'Type': 'Audio', 'Codec': 'eac3', 'Index': 2}]}
        self.item = {'Id': '1731728', 'Name': 'Film', 'Type': 'Movie', 'CanDownload': True,
                     'MediaSources': [self.source]}
        self.client = Mock()
        self.client.get.side_effect = self.get
        self.client.post.side_effect = lambda *a, **kw: Response(self.decision)
        self.decision = {'PlaySessionId': 'own-session', 'MediaSources': [
            {'Id': 'mediasource', 'SupportsTranscoding': True,
             'TranscodingUrl': '/Videos/1731728/stream.mp4?VideoCodec=h264&AudioCodec=aac'}]}
        self.permission = True
        self.transfer = Response(data=self.movie, headers={'Content-Type': 'video/mp4'})

    def get(self, url, **kwargs):
        if kwargs.get('stream'):
            return self.transfer
        if '/Items/' in url:
            return Response(self.item)
        return Response({'Policy': {'EnableContentDownloading': self.permission}})

    def run_download(self, **kw):
        source = dict(self.source, _efcmp_original_id='mediasource')
        return engine.download(self.client, 'https://emby.invalid', 'private-token', 'user',
            self.item, source, str(self.target), self.cancel, kw.pop('progress', Mock()), base, 'auth', **kw)

    def assert_refunded(self):
        self.assertFalse(self.target.exists())
        self.assertEqual([], list(self.root.glob('*.part')))
        self.assertEqual(0, base.quota_status()['used'])
        self.assertFalse(base.ACTIVE.locked())

    def test_real_mp4_without_content_length_is_verified_and_saved_offline(self):
        original = self.root / 'Film_original.mkv'
        original.write_bytes(b'original remains unchanged')
        permission = Mock()
        result = self.run_download(permission=permission)
        self.assertEqual(self.movie, Path(result).read_bytes())
        self.assertEqual(b'original remains unchanged', original.read_bytes())
        self.assertEqual(1, base.quota_status()['used'])
        permission.assert_called_once()
        request = self.client.post.call_args.kwargs
        self.assertFalse(request['json']['EnableDirectPlay'])
        self.assertFalse(request['json']['AllowVideoStreamCopy'])
        self.assertFalse(request['json']['AllowAudioStreamCopy'])
        self.assertEqual(2, request['json']['AudioStreamIndex'])
        self.assertEqual('http', request['json']['DeviceProfile']['TranscodingProfiles'][0]['Protocol'])
        self.client.delete.assert_called_once()
        self.assertEqual('own-session', self.client.delete.call_args.kwargs['params']['PlaySessionId'])
        for call in self.client.get.call_args_list + self.client.post.call_args_list:
            self.assertTrue(call.kwargs['verify'])
            self.assertFalse(call.kwargs['allow_redirects'])

    def test_known_length(self):
        self.transfer.headers['Content-Length'] = str(len(self.movie))
        self.run_download()
        self.assertTrue(self.target.exists())

    def test_download_policy_rejection_does_not_negotiate_or_reserve(self):
        self.permission = False
        with self.assertRaises(base.DownloadPermissionDenied):
            self.run_download()
        self.client.post.assert_not_called()
        self.assert_refunded()

    def test_item_download_rejection(self):
        self.item['CanDownload'] = False
        with self.assertRaises(engine.CompatibilityError):
            self.run_download()
        self.client.post.assert_not_called()
        self.assert_refunded()

    def test_hls_or_external_url_never_downloaded(self):
        for address in ('/Videos/x/master.m3u8', 'https://evil.invalid/video.mp4',
                        '//evil.invalid/video.mp4', 'http://emby.invalid/video.mp4'):
            with self.subTest(address=address):
                self.decision['MediaSources'][0]['TranscodingUrl'] = address
                with self.assertRaises(engine.CompatibilityError):
                    self.run_download()
                self.assertFalse(any(c.kwargs.get('stream') for c in self.client.get.call_args_list))
                self.assert_refunded()

    def test_wrong_source_cannot_be_substituted(self):
        self.decision['MediaSources'][0]['Id'] = 'other-source'
        with self.assertRaises(engine.CompatibilityError):
            self.run_download()
        self.assert_refunded()

    def test_server_disables_transcoding(self):
        self.decision['MediaSources'][0]['SupportsTranscoding'] = False
        with self.assertRaises(engine.CompatibilityError):
            self.run_download()
        self.assert_refunded()

    def test_cancel_removes_partial_and_refunds(self):
        self.transfer.on_chunk = self.cancel.set
        with self.assertRaises(base.DownloadCancelled):
            self.run_download()
        self.assert_refunded()
        self.client.delete.assert_called_once()

    def test_truncated_content_length_refunds(self):
        self.transfer.headers['Content-Length'] = str(len(self.movie) + 5)
        with self.assertRaisesRegex(engine.CompatibilityError, 'unvollstaendig'):
            self.run_download()
        self.assert_refunded()

    def test_early_eof_with_valid_short_mp4_refunds(self):
        self.source['RunTimeTicks'] = 880000000
        with self.assertRaisesRegex(engine.CompatibilityError, 'unvollstaendig'):
            self.run_download()
        self.assert_refunded()

    def test_html_error_response_refunds(self):
        self.transfer.headers['Content-Type'] = 'text/html'
        with self.assertRaises(engine.CompatibilityError):
            self.run_download()
        self.assert_refunded()

    def test_existing_file_not_replaced(self):
        self.target.write_bytes(b'existing')
        with self.assertRaises(engine.CompatibilityError):
            self.run_download()
        self.assertEqual(b'existing', self.target.read_bytes())
        self.client.post.assert_not_called()
        self.assertFalse(base.ACTIVE.locked())

    def test_shared_daily_limit(self):
        quota = base.DailyQuota()
        for _ in range(5):
            quota.reserve()
            quota.close(True)
        with self.assertRaisesRegex(ValueError, 'Tageslimit'):
            self.run_download()
        self.assertFalse(self.target.exists())
        self.assertFalse(any(c.kwargs.get('stream') for c in self.client.get.call_args_list))
        self.assertEqual(5, base.quota_status()['used'])

    def test_missing_probe_does_not_start_server(self):
        with patch.object(engine.shutil, 'which', return_value=None):
            with self.assertRaises(engine.CompatibilityError):
                self.run_download()
        self.client.get.assert_not_called()

    def test_bad_codec_rejected(self):
        probe = {'streams': [{'codec_type': 'video', 'codec_name': 'av1',
            'width': 1920, 'height': 1080, 'pix_fmt': 'yuv420p'}], 'format': {'duration': 6}}
        process = Mock(returncode=0)
        process.communicate.return_value = (json.dumps(probe).encode(), b'')
        process.poll.return_value = 0
        with patch.object(engine.subprocess, 'Popen', return_value=process):
            with self.assertRaisesRegex(engine.CompatibilityError, 'H.264'):
                self.run_download()
        self.assert_refunded()

    def test_truncated_chunked_mp4_with_full_duration_header_refunds(self):
        self.transfer.data = self.movie[:len(self.movie) // 2]
        with self.assertRaises(engine.CompatibilityError):
            self.run_download()
        self.assert_refunded()


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        class Screen(dict):
            source_chosen, target_chosen, transfer, poll = Mock(), Mock(), Mock(), Mock()
        self.Screen = Screen
        self.ns = {'EmbyFlowLocalDownloadScreen': Screen, '_efdl_choice_text': Mock(),
            '_efcmp_engine': engine, '_EFDLChoice': object, '_efdl_update_quota': Mock()}
        exec((HERE / 'ui.py').read_text(), self.ns)
        self.screen = Screen()
        self.screen.closed = False
        self.screen.session = Mock()
        self.screen.item = {'RunTimeTicks': 60000000}
        self.screen['status'], self.screen['progress_bar'], self.screen['footer'] = Mock(), Mock(), Mock()
        self.screen.events = queue.Queue()
        self.screen.progress = (0, 0)

    def test_av1_compatible_selection_preserves_original_metadata(self):
        source = {'Id': 'source', 'Container': 'mkv', 'Size': 1000,
                  'MediaStreams': [{'Type': 'Video', 'Codec': 'av1'}]}
        previous = copy.deepcopy(source)
        self.screen.source_chosen(('Film', source))
        callback = self.screen.session.openWithCallback.call_args.args[0]
        callback(('Compatible', 'compatible'))
        compatible = self.ns['_efcmp_source_before'].call_args.args[1][1]
        self.assertEqual(previous, source)
        self.assertEqual('mp4', compatible['Container'])
        self.assertEqual('source-h264', compatible['Id'])
        self.assertEqual('source', compatible['_efcmp_original_id'])
        self.assertGreater(compatible['Size'], 0)

    def test_non_av1_retains_original_download(self):
        choice = ('Film', {'MediaStreams': [{'Type': 'Video', 'Codec': 'h264'}]})
        self.screen.source_chosen(choice)
        self.ns['_efcmp_source_before'].assert_called_once_with(self.screen, choice)
        self.screen.session.openWithCallback.assert_not_called()

    def test_completion_is_not_shown_before_verification_event(self):
        self.screen.source = {'_efcmp_compatible': True}
        self.screen.events.put(('compatible_done', '/media/hdd/movie/EmbyFlow/film.mp4'))
        self.screen.poll()
        self.assertIn('offline abspielbar', self.screen['status'].setText.call_args.args[0])
        self.screen['progress_bar'].setValue.assert_called_with(100)


if __name__ == '__main__':
    unittest.main()

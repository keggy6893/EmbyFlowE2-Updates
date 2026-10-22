import ast
import io
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
ARTIFACT = next(p for p in (ROOT / 'EmbyFlowE2_2026102201.py',
                           ROOT.parent.parent / 'EmbyFlowE2_2026102201.py') if p.is_file())
SOURCE = ARTIFACT.read_text(encoding='utf-8')
TARGETS = {'_efa3_audio_compat_codec', '_efa2_restart_4097', '_efa2_report',
           '_embyflow_v30_send_report_async', '_efa2_enabled', '_efa2_streams', '_efa2_select'}
TREE = ast.parse(SOURCE)
NODES = [n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in TARGETS]


class Thread:
    def __init__(self, target, args=(), **kw):
        self.target, self.args = target, args
    def start(self):
        self.target(*self.args)


class Timer:
    def __init__(self):
        self.callback = []
    def start(self, *args):
        pass
    def stop(self):
        pass


class Ref:
    def __init__(self, kind, flags, url):
        self.type, self.url = kind, url
    def setName(self, name):
        pass


class Label:
    def setText(self, text):
        self.text = text


class Player(NS):
    def __getitem__(self, key):
        return self.label


class AudioHLSTests(unittest.TestCase):
    def setUp(self):
        self.posts, self.services, self.cleanups, self.errors = [], [], [], []
        self.machine, self.codec, self.session_counter = 'dreamone', 'h264', 0
        self.modules = patch.dict(sys.modules, {
            'Components': NS(),
            'Components.SystemInfo': NS(BoxInfo=NS(getItem=lambda key: self.machine)),
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.thread_patch = patch('threading.Thread', Thread)
        self.thread_patch.start()
        self.addCleanup(self.thread_patch.stop)
        self.sleep_patch = patch('time.sleep', lambda seconds: None)
        self.sleep_patch.start()
        self.addCleanup(self.sleep_patch.stop)

        def uuid():
            self.session_counter += 1
            return NS(hex='session-%d' % self.session_counter)

        def post(url, **kwargs):
            self.posts.append((url, dict(kwargs['json'])))
            return NS(status_code=204, text='')

        def base_payload(p, position):
            return dict(PlaySessionId=p.play_session_id, PositionTicks=position,
                        AudioStreamIndex=p.item.get('embyflow_selected_audio_index'),
                        PlayMethod='DirectPlay', ItemId='42')

        self.ns = dict(time=time, requests=True, EMBY_SERVER='', AUTH_HEADER='fake',
                       uuid4=uuid, eServiceReference=Ref, eTimer=Timer,
                       embyflow_http_post=post, embyflow_open_log=lambda *a, **kw: io.StringIO(),
                       _embyflow_seek_async_v17_5_6_log=lambda message: None,
                       _embyflow_seek_async_v17_5_6_cancel_worker=lambda p, sid, *a: self.cleanups.append(sid),
                       _efguard_play_service=lambda nav, ref: self.services.append(ref),
                       _EFA2_REPORT=base_payload, _EFA2_SELECT=lambda *args: None,
                       _embyflow_rcdev7_static_direct=lambda p: 'Static=true' in p.stream_url,
                       _efa2_error=lambda p, error: self.errors.append(str(error)),
                       _efa2_ready=lambda p: None, _efa2_close=lambda p: None)
        exec(compile(ast.Module(body=NODES, type_ignores=[]), 'audio-hls-regression', 'exec'), self.ns)
        streams = [dict(Type='Audio', Index=2, Language='deu', Codec='ac3', Channels=6),
                   dict(Type='Audio', Index=5, Language='eng', Codec='ac3', Channels=6)]
        self.p = Player(item=dict(Id='42', MediaSources=[dict(Id='source', MediaStreams=streams)],
                                  embyflow_selected_audio_index=2),
                        playback_info=dict(server='https://example.invalid', token='fake'),
                        play_session_id='old-session', title_text='Film', media_source_id='source',
                        stream_url='https://example.invalid/Videos/42/stream?Static=true',
                        position=6000000000, paused=False, closed=False,
                        audio_timer=Timer(), seek_fallback_timer=Timer(), initial_big_seek_timer=Timer(),
                        onClose=[], label=Label())
        p = self.p
        p.session = NS(nav=NS(getCurrentlyPlayingServiceReference=lambda: Ref(4097, 0, p.stream_url)))
        p.embyflow_v10_stream_context = lambda: (
            'https://example.invalid', 'fake', '42', 'source', p.item['embyflow_selected_audio_index'])
        p.embyflow_media_streams_by_type = lambda kind: [dict(Codec=self.codec)] if kind == 'Video' else streams
        p.emby_report_payload = lambda pos: self.ns['_efa2_report'](p, pos)
        p.send_emby_playback_report = lambda endpoint, pos: self.ns['_embyflow_v30_send_report_async'](p, endpoint, pos)
        p.show_overlay = p.update_playback_overlay = p.embyflow_stop_audio_confirm = lambda: None
        p.cancel_active_encoding = lambda sid: self.cleanups.append(sid)
        p.current_position_ticks = lambda: p.position
        p.embyflow_extract_audio_payload = lambda result: result
        p.embyflow_audio_language_key = lambda language: {'deu': 'de', 'eng': 'en'}.get(language, language)

    def restart(self, index=5, **kwargs):
        self.assertTrue(self.ns['_efa2_restart_4097'](
            self.p, self.p.position, audio_index_override=index, **kwargs))
        return urlparse(self.services[-1].url), parse_qs(urlparse(self.services[-1].url).query)

    def test_dreamone_selects_hls_aac_and_preserves_position_track_and_source(self):
        url, q = self.restart()
        self.assertTrue(url.path.endswith('/master.m3u8'))
        for key, value in dict(AudioCodec='aac', AudioChannels='2', MaxAudioChannels='2',
                               AudioStreamIndex='5', StartTimeTicks=str(self.p.position),
                               MediaSourceId='source', Container='ts', CopyTimestamps='false',
                               AllowVideoStreamCopy='true', AllowAudioStreamCopy='false').items():
            self.assertEqual(q[key], [value])
        self.assertEqual(self.services[-1].type, 4097)
        self.assertEqual(self.p.embyflow_v10_stream_base_ticks, self.p.position)

    def test_quadpro_uses_same_compatibility_path(self):
        self.machine = 'gbquad4kpro'
        self.assertTrue(self.restart()[0].path.endswith('/master.m3u8'))

    def test_other_receiver_keeps_mkv_and_original_audio(self):
        self.machine = 'vuduo4kse'
        url, q = self.restart()
        self.assertTrue(url.path.endswith('/stream.mkv'))
        self.assertEqual(q['AudioCodec'], ['copy'])
        self.assertFalse(self.p.playback_info['audio_compat_hls'])

    def test_local_file_is_excluded_even_with_remote_metadata(self):
        self.p.playback_info['local_file'] = True
        self.assertEqual(self.ns['_efa3_audio_compat_codec'](self.p), '')

    def test_local_id_and_mounted_nas_path_are_excluded(self):
        self.p.item['Id'] = 'local:/media/net/nas/film.ts'
        self.assertEqual(self.ns['_efa3_audio_compat_codec'](self.p), '')
        self.p.item['Id'] = '42'
        self.p.stream_url = '/media/net/nas/film.ts'
        self.assertEqual(self.ns['_efa3_audio_compat_codec'](self.p), '')

    def test_unsupported_video_keeps_previous_path(self):
        self.codec = 'av1'
        self.assertTrue(self.restart()[0].path.endswith('/stream.mkv'))

    def test_hevc_requests_video_copy_without_h264_conversion(self):
        self.codec = 'hevc'
        self.assertEqual(self.restart()[1]['VideoCodec'], ['hevc'])

    def test_burned_subtitle_restart_retains_previous_profile(self):
        url, q = self.restart(subtitle_stream_index=9)
        self.assertTrue(url.path.endswith('/stream.mkv'))
        self.assertEqual(q['SubtitleStreamIndex'], ['9'])
        self.assertEqual(q['VideoCodec'], ['h264'])
        self.assertNotIn('Container', q)

    def test_single_playing_report_and_progress_through_60_seconds(self):
        self.restart()
        for seconds in (10, 20, 30, 40, 60):
            self.p.send_emby_playback_report('Progress', self.p.position + seconds * 10000000)
        self.assertEqual(len([url for url, data in self.posts if '/Playing?' in url]), 1)
        self.assertEqual(len([url for url, data in self.posts if '/Progress?' in url]), 6)
        self.assertEqual(self.cleanups, ['old-session'])
        for url, data in self.posts:
            self.assertEqual(data['PlayMethod'], 'Transcode')
            self.assertEqual(data['AudioStreamIndex'], 5)
            self.assertEqual(data['PlaySessionId'], 'session-1')

    def test_real_selection_callback_can_switch_both_directions(self):
        for index, language in [(5, 'en'), (2, 'de')]:
            self.ns['_efa2_select'](self.p, dict(action='audio', emby_index=index, label=language))
            self.assertFalse(self.errors)
            self.assertEqual(self.p.item['embyflow_selected_audio_index'], index)
            self.assertEqual(parse_qs(urlparse(self.services[-1].url).query)['AudioStreamIndex'], [str(index)])
            self.assertEqual(self.p.embyflow_active_audio_override['Codec'], 'aac')
            self.assertEqual(self.p.embyflow_active_audio_override['Channels'], 2)
            self.p._efa2_pending = False
        self.assertEqual(self.cleanups, ['old-session', 'session-1'])
        self.assertEqual(len([url for url, data in self.posts if '/Playing?' in url]), 2)
        self.assertEqual(len(self.p.item['MediaSources'][0]['MediaStreams']), 2)

    def test_full_plugin_is_python38_parseable(self):
        ast.parse(SOURCE, feature_version=(3, 8))


if __name__ == '__main__':
    unittest.main(verbosity=2)

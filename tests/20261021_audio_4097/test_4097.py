import ast
import io
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent


class Timer:
    def __init__(self): self.callback = []; self.starts = []; self.stopped = False
    def start(self, *args): self.starts.append(args)
    def stop(self): self.stopped = True


class Ref:
    def __init__(self, kind, flags=0, url=''): self.type = kind; self.url = url
    def setName(self, value): self.name = value


class Player:
    def __init__(self):
        self.reference = Ref(4097)
        self.position = 6000000000
        self.native = 10000000
        self.language = 'en'
        self.calls = []; self.errors = []; self.onClose = []
        self.audio_timer = Timer(); self.seek_fallback_timer = Timer(); self.initial_big_seek_timer = Timer()
        self.item = {'embyflow_selected_audio_index': 2}
        self.streams = [dict(Type='Audio', Index=2, Language='de', Codec='ac3'),
                        dict(Type='Audio', Index=5, Language='en', Codec='ac3')]
        self.play_session_id = 'old'; self.title_text = '2012'; self.item_id = '42'
        self.playback_info = {}; self.static = True
        self.label = NS(setText=lambda text: self.calls.append(('label', text)))
        self.tracks = NS(getNumberOfTracks=lambda: 1, getCurrentTrack=lambda: 0,
                         selectTrack=lambda *a: self.fail_native())
        self.session = NS(nav=NS(getCurrentlyPlayingServiceReference=lambda: self.reference,
                                getCurrentService=lambda: NS(audioTracks=lambda: self.tracks)),
                          open=lambda *a, **k: self.errors.append(a[1]),
                          openWithCallback=lambda callback, cls, **kw: self.calls.append(('menu', kw)))
        self.audio_selection_finished = lambda result: self.ns['_efa2_select'](self, result)
    def __getitem__(self, key): return self.label
    def fail_native(self): raise AssertionError('native selectTrack must not be called')
    def current_position_ticks(self): return self.position
    def native_position_ticks(self): return self.native
    def embyflow_media_streams_by_type(self, kind): return self.streams
    def embyflow_audio_language_key(self, language): return language
    def embyflow_audio_language_label(self, key, fallback): return key or fallback
    def embyflow_audio_track_descriptor(self, *a): return dict(language_key=self.language)
    def embyflow_extract_audio_payload(self, result): return result if result and result.get('action') == 'audio' else None
    def embyflow_v10_stream_context(self): return ('https://example.invalid/emby', 'test-token', '42', 'source-a', self.item.get('embyflow_selected_audio_index', 2))
    def embyflow_stop_audio_confirm(self): self.calls.append(('stop_confirm',))
    def emby_report_payload(self, position): return dict(PositionTicks=position, PlaySessionId=self.play_session_id)
    def show_overlay(self): pass
    def update_playback_overlay(self): self.calls.append(('overlay',))
    def cancel_active_encoding(self, session): self.calls.append(('cancel', session))


class Audio4097Tests(unittest.TestCase):
    def setUp(self):
        self.p = p = Player()
        self.ns = dict(EmbyFlowMoviePlayer=type('Original', (), dict(
            open_audio_selection=lambda p: p.calls.append(('original_menu',)),
            audio_selection_finished=lambda p, r: p.calls.append(('original_select',)),
            emby_report_payload=lambda p, pos: dict(PositionTicks=pos))),
            MessageBox=NS(TYPE_ERROR=1), EmbyFlowTrackSelectionScreen=object,
            eTimer=Timer, _embyflow_rcdev7_static_direct=lambda p: p.static,
            _efa2_restart_4097=lambda p, pos, **kw: p.calls.append(('restart', pos, kw)) or True)
        exec(compile((HERE / 'audio_4097.py').read_text(encoding='utf-8'), 'audio_4097', 'exec'), self.ns)
        p.ns = self.ns
    def call(self, name, *a): return self.ns[name](self.p, *a)
    def choose(self, index=5): self.call('_efa2_select', dict(action='audio', emby_index=index, label='English'))
    def test_menu_uses_server_indexes(self):
        self.call('_efa2_open'); menu = self.p.calls[-1][1]
        self.assertEqual([x['payload']['emby_index'] for x in menu['entries']], [2, 5])
    def test_menu_has_both_languages_after_remux(self):
        self.choose(); self.p._efa2_pending = False; self.p.static = False
        self.call('_efa2_open'); self.assertEqual(len(self.p.calls[-1][1]['entries']), 2)
    def test_position_saved_before_switch(self):
        self.choose(); self.assertIn(('restart', 6000000000, dict(audio_index_override=5)), self.p.calls)
    def test_zero_clock_uses_menu_position(self):
        self.call('_efa2_open'); self.p.position = 0; self.choose()
        self.assertIn(('restart', 6000000000, dict(audio_index_override=5)), self.p.calls)
    def test_second_menu_does_not_reuse_stale_position(self):
        self.call('_efa2_open'); self.p.position = 0; self.call('_efa2_open')
        self.assertEqual(self.p._efa2_menu_position, 0)
    def test_back_to_german(self):
        self.choose(); self.p._efa2_pending = False; self.p.static = False; self.choose(2)
        self.assertEqual(self.p.item['embyflow_selected_audio_index'], 2)
    def test_changed_session_leaves_original_menu(self):
        self.choose(); self.p._efa2_pending = False; self.p.static = False
        self.p.play_session_id = 'other-session'; self.call('_efa2_open')
        self.assertEqual(self.p.calls[-1], ('original_menu',))
    def test_pause_restored_after_startup(self):
        self.p.paused = True
        self.p.pause_playback = lambda: self.p.calls.append(('pause',))
        self.choose(); self.call('_efa2_ready'); self.p.native += 10000000
        self.call('_efa2_ready'); self.assertIn(('pause',), self.p.calls)
    def test_active_source_not_first_source(self):
        self.p.media_source_id = 'b'
        self.p.item['MediaSources'] = [dict(Id='a', MediaStreams=[self.p.streams[0]]),
                                       dict(Id='b', MediaStreams=[self.p.streams[1]])]
        self.assertEqual([s['Index'] for s in self.call('_efa2_streams')], [5])
    def test_report_matches_server_audio_and_method(self):
        self.choose(); report = self.call('_efa2_report', 6000000000)
        self.assertEqual(report['PlayMethod'], 'DirectStream')
        self.assertEqual(report['AudioStreamIndex'], 5)
    def test_duplicate_selection_ignored_while_pending(self):
        self.choose(); self.choose(2)
        self.assertEqual(len([c for c in self.p.calls if c[0] == 'restart']), 1)
    def test_cancel_noop(self): self.call('_efa2_select', None); self.assertFalse(self.p.calls)
    def test_same_track_noop(self): self.choose(2); self.assertFalse(self.p.calls)
    def test_missing_track_never_restarts(self): self.choose(99); self.assertTrue(self.p.errors); self.assertFalse(self.p.calls)
    def test_duplicate_server_index_rejected(self):
        self.p.streams.append(dict(self.p.streams[1])); self.choose(); self.assertTrue(self.p.errors)
    def test_failed_restart_keeps_audio_identity(self):
        self.ns['_efa2_restart_4097'] = lambda *a, **kw: False
        self.choose(); self.assertEqual(self.p.item['embyflow_selected_audio_index'], 2)
        self.assertFalse(self.p.embyflow_manual_audio_selected)
    def test_burned_subtitles_never_silently_reencode(self):
        self.p.embyflow_server_subtitle_stream_index = 8; self.choose()
        self.assertTrue(self.p.errors); self.assertFalse(self.p.calls)
    def test_other_backends_keep_existing_menu(self):
        self.p.reference.type = 5002; self.call('_efa2_open'); self.assertEqual(self.p.calls, [('original_menu',)])
    def test_hls_keeps_existing_menu(self):
        self.p.static = False; self.call('_efa2_open'); self.assertEqual(self.p.calls, [('original_menu',)])
    def test_old_payload_keeps_existing_handler(self):
        self.call('_efa2_select', dict(action='audio', e2_index=1)); self.assertEqual(self.p.calls, [('original_select',)])
    def test_ready_requires_advancing_clock(self):
        self.choose(); self.call('_efa2_ready'); self.call('_efa2_ready'); self.assertTrue(self.p._efa2_pending)
        self.p.native += 10000000; self.call('_efa2_ready'); self.assertFalse(self.p._efa2_pending)
    def test_wrong_language_does_not_confirm(self):
        self.choose(); self.p.language = 'de'; self.call('_efa2_ready')
        self.p.native += 10000000; self.call('_efa2_ready'); self.assertTrue(self.p._efa2_pending)
    def test_timeout_is_bounded(self):
        self.choose()
        for _ in range(30): self.call('_efa2_ready')
        self.assertFalse(self.p._efa2_pending); self.assertTrue(self.p.errors)
    def test_close_stops_monitor(self):
        self.choose(); self.call('_efa2_close'); self.call('_efa2_ready'); self.assertTrue(self.p._efa2_timer.stopped)
    def test_stale_native_mapping_removed(self):
        self.p.embyflow_audio_track_map = {1: self.p.streams[1]}; self.choose()
        self.assertEqual(self.p.embyflow_audio_track_map, {})
    def test_real_restart_url_session_clock_and_cleanup(self):
        calls = []
        class Thread:
            def __init__(self, target, args, **kw): self.target = target; self.args = args
            def start(self): self.target(*self.args)
        ns = dict(time=time, uuid4=lambda: NS(hex='new-session'), eServiceReference=Ref,
                  _embyflow_seek_async_v17_5_6_log=lambda text: None,
                  embyflow_open_log=lambda *a, **kw: io.StringIO(),
                  _embyflow_seek_async_v17_5_6_cancel_worker=lambda p, old, *a: calls.append(('cleanup', old)),
                  _embyflow_seek_async_v17_5_6_report_worker=lambda *a: calls.append(('report', a)),
                  _efguard_play_service=lambda nav, ref: calls.append(('play', ref)))
        source = (HERE / 'restart_4097.py').read_text(encoding='utf-8')
        exec(compile(source, 'restart_4097', 'exec'), ns)
        with patch('threading.Thread', Thread):
            self.assertTrue(ns['_efa2_restart_4097'](self.p, 6000000000, audio_index_override=5))
        ref = next(c[1] for c in calls if c[0] == 'play')
        query = parse_qs(urlparse(ref.url).query)
        for key, expected in dict(Static='false', StartTimeTicks='6000000000', AudioStreamIndex='5',
                                  MediaSourceId='source-a', PlaySessionId='new-session',
                                  VideoCodec='copy', AudioCodec='copy').items():
            self.assertEqual(query[key], [expected])
        self.assertEqual(ref.type, 4097)
        self.assertEqual(self.p.embyflow_v10_stream_base_ticks, 6000000000)
        self.assertEqual(self.p.synthetic_position_ticks, 6000000000)
        self.assertEqual(self.p.play_session_id, 'new-session')
        self.assertIn(('cleanup', 'old'), calls)
        reports = next(c[1] for c in calls if c[0] == 'report')
        self.assertEqual(reports[5]['AudioStreamIndex'], 5)
    def test_python38_and_no_ext_dependency(self):
        for name in ('audio_4097.py', 'restart_4097.py'):
            source = (HERE / name).read_text(encoding='utf-8'); ast.parse(source, feature_version=(3, 8))
            self.assertNotIn('5002', source); self.assertNotIn('selectTrack(', source)


if __name__ == '__main__': unittest.main(verbosity=2)

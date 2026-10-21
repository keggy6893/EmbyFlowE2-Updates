import ast
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

SOURCE = Path(__file__).with_name('audio_runtime.py').read_text(encoding='utf-8')


class Timer:
    def __init__(self): self.callback = []; self.starts = []; self.stopped = False
    def start(self, *args): self.starts.append(args)
    def stop(self): self.stopped = True


class Tracks:
    def __init__(self): self.current = 0
    def getNumberOfTracks(self): return 2
    def getCurrentTrack(self): return self.current


class Player:
    def __init__(self):
        self.backend = 4097; self.tracks = Tracks(); self.calls = []; self.errors = []
        self.position = 6000000000; self.onClose = []; self.audio_timer = Timer()
        self.embyflow_audio_track_map = {0: {'Index': 1}, 1: {'Index': 3}}
        self.session = NS(nav=NS(getCurrentService=lambda: NS(audioTracks=lambda: self.tracks),
                                getCurrentlyPlayingServiceReference=lambda: NS(type=self.backend)),
                          open=lambda *a, **kw: self.errors.append(a[1]))
        self.label = NS(setText=lambda text: None)
        self.embyflow_audio_confirm_requested = None
    def __getitem__(self, name): return self.label
    def current_position_ticks(self): return self.position
    def embyflow_extract_audio_payload(self, result): return result
    def embyflow_stop_audio_confirm(self): self.embyflow_audio_confirm_requested = None
    def embyflow_audio_track_descriptor(self, tracks, index):
        language = ('de', 'en')[index] if self.backend == 4097 else ('en', 'de')[index]
        return dict(language_key=language, codec_key='ac3', channels=6)
    def embyflow_audio_selection_entries(self, *args):
        # Different native ordering after the backend switch.
        self.embyflow_audio_track_map = {0: {'Index': 3}, 1: {'Index': 1}}


class AudioTest(unittest.TestCase):
    def setUp(self):
        self.player = p = Player(); self.static = True; self.available = True; self.mode = 'auto'
        self.confirmed = True
        def select(p, result):
            p.calls.append(('select', result['e2_index']))
            p.embyflow_audio_confirm_requested = result['e2_index']
            p.tracks.current = result['e2_index']
        def confirm(p):
            if self.confirmed: p.embyflow_audio_confirm_requested = None
        cls = type('Original', (), dict(open_audio_selection=lambda p: p.calls.append(('open',)),
                                       audio_selection_finished=select, embyflow_confirm_audio_track=confirm))
        def switch(p, target): p.calls.append(('switch', target)); p.backend = 5002; return True
        self.ns = dict(EmbyFlowMoviePlayer=cls, eTimer=Timer,
                       MessageBox=NS(TYPE_ERROR=1),
                       _embyflow_rcdev7_static_direct=lambda p: self.static,
                       _embyflow_engine_v11_4_exteplayer3_available=lambda: self.available,
                       _embyflow_engine_v11_4_mode=lambda p: self.mode,
                       _embyflow_rcdev7_switch_static_to_ext=switch,
                       _embyflow_qs_v2_schedule_resume=lambda p, target: p.calls.append(('resume', target)))
        exec(compile(SOURCE, 'audio_runtime.py', 'exec'), self.ns)
    def call(self, fn, *args): return self.ns[fn](self.player, *args)
    def choose(self): self.call('_efa_select', dict(e2_index=1, label='Englisch'))
    def test_static_switch_preserves_position(self):
        self.choose(); self.assertEqual(self.player.calls, [('switch', 6000000000)])
    def test_index_remapped_not_reused(self):
        self.choose(); self.call('_efa_poll'); self.assertEqual(self.player.calls[-1], ('select', 0))
    def test_resume_after_confirmation(self):
        self.choose(); self.call('_efa_poll'); self.call('_efa_confirm')
        self.assertEqual(self.player.calls[-1], ('resume', 6000000000))
    def test_wait_for_confirmation(self):
        self.choose(); self.call('_efa_poll'); self.confirmed = False; self.call('_efa_confirm')
        self.assertNotIn('resume', [c[0] for c in self.player.calls])
    def test_unavailable_does_not_switch(self):
        self.available = False; self.choose(); self.assertFalse(self.player.calls); self.assertTrue(self.player.errors)
    def test_explicit_e2_respected(self):
        self.mode = 'e2'; self.choose(); self.assertFalse(self.player.calls); self.assertTrue(self.player.errors)
    def test_no_mapping_does_not_switch(self):
        self.player.embyflow_audio_track_map = {}; self.choose(); self.assertFalse(self.player.calls)
    def test_other_stream_unchanged(self):
        self.static = False; self.choose(); self.assertEqual(self.player.calls, [('select', 1)])
    def test_existing_ext_not_restarted(self):
        self.player.backend = 5002; self.choose(); self.assertEqual(self.player.calls, [('select', 1)])
    def test_cancel_is_noop(self):
        self.call('_efa_select', None); self.assertFalse(self.player.calls)
    def test_same_track_is_noop(self):
        self.call('_efa_select', {'e2_index': 0}); self.assertFalse(self.player.calls)
    def test_menu_zero_fallback(self):
        self.call('_efa_open'); self.player.position = 0; self.choose()
        self.assertEqual(self.player.calls[1], ('switch', 6000000000))
    def test_new_menu_does_not_reuse_old_position(self):
        self.player._efa_menu_position = 999; self.player.position = 0; self.call('_efa_open')
        self.assertEqual(self.player._efa_menu_position, 0)
    def test_duplicate_request_ignored(self):
        self.choose(); self.choose(); self.assertEqual(len(self.player.calls), 1)
    def test_close_cancels_pending(self):
        self.choose(); self.call('_efa_close'); self.call('_efa_poll')
        self.assertTrue(self.player._efa_timer.stopped); self.assertEqual(len(self.player.calls), 1)
    def test_timeout_bounded(self):
        self.choose(); self.player.backend = 4097
        for _ in range(24): self.call('_efa_poll')
        self.assertIsNone(self.player._efa_pending); self.assertTrue(self.player.errors)
    def test_failed_confirmation_does_not_resume(self):
        self.choose(); self.call('_efa_poll'); self.player.tracks.current = 1; self.call('_efa_confirm')
        self.assertNotIn('resume', [c[0] for c in self.player.calls])
    def test_invalid_index_rejected(self):
        self.call('_efa_select', {'e2_index': 8}); self.assertFalse(self.player.calls)
    def test_python38_syntax(self): ast.parse(SOURCE, feature_version=(3, 8))
    def test_mismatched_language_never_selected(self):
        self.choose()
        self.player.embyflow_audio_track_descriptor = lambda *a: dict(language_key='fr')
        for _ in range(24): self.call('_efa_poll')
        self.assertEqual([c[0] for c in self.player.calls], ['switch'])
    def test_actual_existing_backend_helper_keeps_url_and_session(self):
        baseline = Path(__file__).with_name('base.py')
        if not baseline.exists():
            baseline = Path(__file__).resolve().parents[2] / 'EmbyFlowE2_2026102001.py'
        if not baseline.exists(): self.skipTest('Published baseline not present')
        tree = ast.parse(baseline.read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == '_embyflow_rcdev7_switch_static_to_ext')
        code = compile(ast.Module(body=[function], type_ignores=[]), 'existing_helper', 'exec')
        references = []
        class Ref:
            def __init__(self, kind, flags, url): self.type = kind; self.url = url
            def setName(self, name): pass
        ns = dict(_embyflow_engine_v11_4_exteplayer3_available=lambda: True,
                  embyflow_is_static_stream_url=lambda url: 'Static=true' in url,
                  eServiceReference=Ref, _embyflow_rcdev7_log=lambda text: None,
                  _efguard_play_service=lambda nav, ref: references.append(ref),
                  _embyflow_qs_v2_schedule_resume=lambda p, pos: p.calls.append(('resume', pos)))
        exec(code, ns)
        p = self.player; p.stream_url = 'https://example.invalid/stream.mkv?Static=true'; p.play_session_id = 'same'
        p.playback_info = {}; p.show_overlay = lambda: None
        self.assertTrue(ns[function.name](p, 6000000000))
        self.assertEqual(p.play_session_id, 'same'); self.assertEqual(references[0].url, p.stream_url)
        self.assertEqual(references[0].type, 5002)
        self.assertEqual(p.calls, [('resume', 6000000000)])


if __name__ == '__main__': unittest.main()

import pathlib
import tempfile
import types
import unittest

from install import install, patched

HERE = pathlib.Path(__file__).resolve().parent
PATCH = (HERE / 'patch.py').read_text()
ROOT = HERE.parent.parent


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        class Player(dict):
            pass
        Player.subtitle_selection_finished = lambda p, r: self.calls.append(('delegate', r))
        Player.embyflow_close_subtitle_window = lambda p: self.calls.append(('close',))
        self.ns = {'EmbyFlowMoviePlayer': Player,
                   '_embyflow_srt_v2_stop': lambda p, invalidate=True: self.calls.append(('stop',)),
                   '_efut2_streams': lambda p: p.item['MediaSources'][0]['MediaStreams'],
                   '_efut2_source': lambda p: p.item['MediaSources'][0],
                   'MessageBox': types.SimpleNamespace(TYPE_INFO=1)}
        exec(compile(PATCH, 'patch.py', 'exec'), self.ns)
        self.streams = [dict(Type='Subtitle', Index=4+i, Codec='pgs', IsExternal=False,
                             Language=lang, IsForced=forced)
                        for i, (lang, forced) in enumerate([('deu', True), ('deu', False), ('eng', False), ('eng', True)])]
        self.native = [(3, i, 6, 0, lang) for i, lang in enumerate(('ger', 'ger', 'eng', 'eng'))]
        self.ref = types.SimpleNamespace(type=4097)
        self.backend = types.SimpleNamespace(
            getSubtitleList=lambda: self.native,
            disableSubtitles=lambda widget: self.calls.append(('disable', widget)),
            enableSubtitles=self.enable)
        self.window = types.SimpleNamespace(instance=object(),
            show=lambda: self.calls.append(('show',)), hide=lambda: self.calls.append(('hide',)))
        self.p = Player()
        self.p.instance = object()
        self.p.item = {'MediaSources': [{'Id': 'active', 'MediaStreams': self.streams}]}
        self.p.media_source_id = 'active'
        self.p.stream_url = 'http://example.invalid/Videos/1/stream.mkv?Static=true'
        self.p.session = types.SimpleNamespace(nav=types.SimpleNamespace(
            getCurrentlyPlayingServiceReference=lambda: self.ref,
            getCurrentService=lambda: types.SimpleNamespace(subtitle=lambda: self.backend)),
            open=lambda *a, **kw: self.calls.append(('message', a)))
        self.p.embyflow_get_subtitle_window = lambda: self.window
        self.p.show_overlay = lambda: None
        self.p.embyflow_active_subtitle_index = None
        self.p.embyflow_active_subtitle_stream_index = None
        self.p['state_label'] = types.SimpleNamespace(setText=lambda t: None)

    def enable(self, widget, entry):
        self.calls.append(('enable', entry))
        return 0

    def start(self, pos=0):
        self.ns['_efpg_start'](self.p, self.streams[pos], 'Deutsch', pos)

    def test_forced_and_full_tracks_use_subtitle_ordinal_not_emby_index(self):
        for pos in range(4):
            self.start(pos)
            self.assertEqual([c[1] for c in self.calls if c[0] == 'enable'][-1], self.native[pos])
            self.assertEqual(self.p.embyflow_active_subtitle_stream_index, 4+pos)
            self.assertEqual(self.p.embyflow_active_subtitle_index, pos)

    def test_shuffled_native_list_uses_pid(self):
        self.native.reverse()
        self.start()
        self.assertEqual([c[1] for c in self.calls if c[0] == 'enable'], [(3, 0, 6, 0, 'ger')])

    def test_legacy_pgs_tuple_type_two_allowed(self):
        self.native = [(2, i, 6, 0, lang) for _, i, _, _, lang in self.native]
        self.start()
        self.assertEqual(self.p.embyflow_active_subtitle_index, 0)

    def test_mismatch_does_not_stop_existing_subtitles(self):
        for alteration in ('partial', 'language', 'codec', 'duplicate', 'unknown', 'type'):
            with self.subTest(alteration=alteration):
                saved = self.native[:]
                if alteration == 'partial': self.native.pop()
                if alteration == 'language': self.native[0] = (3, 0, 6, 0, 'eng')
                if alteration == 'codec': self.native[0] = (2, 0, 4, 0, 'ger')
                if alteration == 'duplicate': self.native[1] = self.native[0]
                if alteration == 'unknown': self.native[0] = (3, 0, 6, 0, 'und')
                if alteration == 'type': self.native[0] = (0, 0, 6, 0, 'ger')
                before = self.calls[:]
                with self.assertRaises(RuntimeError): self.start()
                self.assertEqual(self.calls, before)
                self.native = saved

    def test_external_pgs_never_attached(self):
        self.streams[0]['IsExternal'] = True
        with self.assertRaises(RuntimeError): self.start()
        self.assertEqual(self.calls, [])

    def test_transcoded_stream_never_attached(self):
        self.p.stream_url = 'http://example.invalid/main.m3u8?Static=false'
        with self.assertRaises(RuntimeError): self.start()

    def test_backend_5002_never_attached(self):
        self.ref.type = 5002
        with self.assertRaises(RuntimeError): self.start()

    def test_backend_rejection_clears_selection_and_hides_window(self):
        self.backend.enableSubtitles = lambda *a: -1
        with self.assertRaises(RuntimeError): self.start()
        self.assertIsNone(self.p.embyflow_active_subtitle_index)
        self.assertIsNone(getattr(self.p, '_efpg_active', None))
        self.assertEqual(self.calls[-1], ('hide',))

    def test_disable_before_enable_rebinds_cached_track(self):
        self.start()
        tags = [c[0] for c in self.calls]
        self.assertLess(tags.index('disable'), tags.index('enable'))

    def test_native_widget_attaches_to_visible_player_not_separate_display(self):
        widgets = []
        self.backend.enableSubtitles = lambda widget, entry: widgets.append(widget) or 0
        self.start()
        self.assertEqual(widgets, [self.p.instance])
        self.assertIsNot(widgets[0], self.window.instance)
        self.ns['_efpg_stop'](self.p)
        self.assertIn(('disable', self.p.instance), self.calls)

    def test_missing_player_widget_fails_without_stopping_previous_selection(self):
        self.p.instance = None
        with self.assertRaises(RuntimeError): self.start()
        self.assertEqual(self.calls, [])

    def test_manual_selection_marks_only_after_success(self):
        result = ('subtitle_bitmap_info_0629', self.streams[0], 'Deutsch', 0)
        self.native = []
        self.p.subtitle_selection_finished(result)
        self.assertIsNone(self.p.embyflow_active_subtitle_index)
        self.assertTrue(self.p._efut_manual)
        self.assertEqual(self.calls[-1][0], 'message')

    def test_off_or_text_switch_disables_native_and_delegates(self):
        for action in ('subtitle_off', 'subtitle'):
            self.start()
            self.p.subtitle_selection_finished((action, None, 'Aus', None))
            self.assertIsNone(self.p._efpg_active)
            self.assertEqual(self.calls[-1][0], 'delegate')

    def test_close_disables_and_delegates(self):
        self.start()
        self.p.embyflow_close_subtitle_window()
        self.assertIsNone(self.p._efpg_active)
        self.assertEqual(self.calls[-1], ('close',))

    def test_non_pgs_and_cancel_keep_existing_handler(self):
        for result in (None, ('subtitle_bitmap_info_0629', {'Codec': 'dvdsub'}, 'Deutsch', 0)):
            self.p.subtitle_selection_finished(result)
            self.assertEqual(self.calls[-1], ('delegate', result))

    def test_install_preserves_published_and_local_additions(self):
        base = (ROOT / 'EmbyFlowE2_2026101704.py').read_text()
        for original in (base, base + '\n# Receiver-local additions must be preserved.\nLOCAL_FEATURE = True\n'):
            output = patched(original, PATCH)
            self.assertTrue(output.startswith(original))
            with self.assertRaises(RuntimeError): patched(output, PATCH)

    def test_installer_backup_and_permission_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'plugin.py'
            original = (ROOT / 'EmbyFlowE2_2026101704.py').read_text()
            path.write_text(original)
            path.chmod(0o640)
            install(path, PATCH)
            self.assertEqual(next(path.parent.glob('*.vor-pgs-*')).read_text(), original)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual(path.read_text(), patched(original, PATCH))


if __name__ == '__main__':
    unittest.main()

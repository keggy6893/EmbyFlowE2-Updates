import ast
from pathlib import Path
import tempfile
import types
import unittest

from install_auto import install, patched
import test_pgs as native_tests
from test_pgs import PATCH, HERE, ROOT

AUTO = (HERE / 'auto.py').read_text()


class AutoTests(unittest.TestCase):
    def setUp(self):
        native_tests.NativeTests.setUp(self)
        names = {'_efut2_source', '_efut2_streams', '_efut2_german', '_efut2_auto'}
        tree = ast.parse((ROOT / 'EmbyFlowE2_2026101704.py').read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'release_helpers.py', 'exec'), self.ns)
        self.text_starts = []
        self.delegated = []
        self.timer_starts = []
        self.p.subtitle_timer = types.SimpleNamespace(start=lambda *args: self.timer_starts.append(args))
        self.p.embyflow_srt_v2_loading = False
        self.ns['_embyflow_srt_v2_is_text_stream'] = lambda s: s.get('Codec') in ('srt', 'subrip')
        self.ns['_embyflow_srt_v2_start'] = lambda *args: self.text_starts.append(args)
        self.ns['_embyflow_srt_v2_language'] = lambda p, s, pos: 'Deutsch'
        def previous(p):
            self.delegated.append(True)
            return self.ns['_efut2_auto'](p)
        self.ns['EmbyFlowMoviePlayer'].set_preferred_subtitle_track = previous
        exec(compile(AUTO, 'auto.py', 'exec'), self.ns)

    enable = native_tests.NativeTests.enable

    def auto(self):
        self.p.set_preferred_subtitle_track()

    def test_german_forced_pgs_auto_starts_using_working_parent(self):
        self.auto()
        self.assertEqual(self.p.embyflow_active_subtitle_stream_index, 4)
        self.assertIs(self.p._efpg_active[1], self.p.instance)
        self.assertFalse(getattr(self.p, '_efut_manual', False))
        self.assertFalse(self.delegated)

    def test_default_full_and_foreign_pgs_are_respected(self):
        source = self.p.item['MediaSources'][0]
        for index in (5, 6, 7):
            self.ns['_efpg_stop'](self.p)
            source['DefaultSubtitleStreamIndex'] = index
            self.auto()
            self.assertEqual(self.p.embyflow_active_subtitle_stream_index, index)

    def test_default_text_uses_existing_srt_path(self):
        text = dict(Type='Subtitle', Index=12, Codec='subrip', Language='deu', IsForced=False)
        self.streams.append(text)
        self.p.item['MediaSources'][0]['DefaultSubtitleStreamIndex'] = 12
        self.auto()
        self.assertEqual(self.text_starts[0][1], text)
        self.assertFalse(any(c[0] == 'enable' for c in self.calls))

    def test_forced_srt_keeps_precedence_over_pgs_fallback(self):
        text = dict(Type='Subtitle', Index=12, Codec='subrip', Language='deu', IsForced=True)
        self.streams.append(text)
        self.auto()
        self.assertEqual(self.text_starts[0][1], text)
        self.assertFalse(any(c[0] == 'enable' for c in self.calls))

    def test_no_full_or_english_fallback_without_explicit_default(self):
        self.streams[0]['IsForced'] = False
        self.auto()
        self.assertFalse(any(c[0] == 'enable' for c in self.calls))
        self.assertIsNone(self.p.embyflow_active_subtitle_index)

    def test_forced_false_string_is_not_true(self):
        self.streams[0]['IsForced'] = 'False'
        self.auto()
        self.assertFalse(any(c[0] == 'enable' for c in self.calls))

    def test_german_region_variants_and_forced_title(self):
        self.streams[0].update(Language='de-DE', IsForced=False, Title='Deutsch erzwungen')
        self.auto()
        self.assertEqual(self.p.embyflow_active_subtitle_stream_index, 4)

    def test_active_source_only_and_position_zero_is_active(self):
        self.p.item['MediaSources'].insert(0, {'Id': 'wrong', 'DefaultSubtitleStreamIndex': 6,
                                              'MediaStreams': []})
        self.auto()
        self.assertEqual(self.p.embyflow_active_subtitle_index, 0)
        count = len(self.calls)
        self.auto()
        self.assertEqual(len(self.calls), count)

    def test_missing_active_source_never_chooses_other_version(self):
        self.p.media_source_id = 'missing'
        self.auto()
        self.assertFalse(any(c[0] == 'enable' for c in self.calls))

    def test_native_inventory_late_retries_then_succeeds(self):
        saved = self.native
        self.native = []
        self.auto()
        self.assertEqual(self.timer_starts, [(750, True)])
        self.assertIsNone(self.p.embyflow_active_subtitle_index)
        self.native = saved
        self.auto()
        self.assertEqual(self.p.embyflow_active_subtitle_stream_index, 4)

    def test_failure_retries_are_bounded_and_do_not_open_popups(self):
        self.native = []
        for _ in range(20): self.auto()
        self.assertEqual(len(self.timer_starts), 7)
        self.assertEqual(self.p._efpga_tries, 8)
        self.assertFalse(any(c[0] in ('enable', 'message') for c in self.calls))

    def test_pending_retry_respects_manual_off(self):
        saved = self.native
        self.native = []
        self.auto()
        self.p._efut_manual = True  # existing selection handler sets this for off/text
        self.native = saved
        self.auto()
        self.assertFalse(any(c[0] == 'enable' for c in self.calls))

    def test_manual_pgs_is_not_overridden_by_pending_auto(self):
        self.p.subtitle_selection_finished(('subtitle_bitmap_info_0629', self.streams[1], 'Deutsch', 1))
        self.auto()
        self.assertEqual(self.p.embyflow_active_subtitle_stream_index, 5)
        self.assertEqual(len([c for c in self.calls if c[0] == 'enable']), 1)

    def test_closed_or_loading_player_is_not_activated(self):
        self.p.closed = True
        self.auto()
        self.p.closed = False
        self.p.embyflow_srt_v2_loading = True
        self.auto()
        self.assertEqual(self.calls, [])

    def test_unknown_default_does_not_fall_back_to_forced_pgs(self):
        self.p.item['MediaSources'][0]['DefaultSubtitleStreamIndex'] = 999
        self.auto()
        self.assertFalse(any(c[0] == 'enable' for c in self.calls))

    def test_standalone_install_preserves_receiver_v2_exactly(self):
        # Same two statement changes as the actual V1 -> V2 receiver installer.
        source = (ROOT / 'EmbyFlowE2_2026101704.py').read_text() + '\n' + PATCH
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'plugin.py'
            path.write_text(source)
            path.chmod(0o640)
            install(path, AUTO)
            self.assertTrue(path.read_text().startswith(source))
            self.assertEqual(next(path.parent.glob('*.vor-pgs-auto-*')).read_text(), source)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            with self.assertRaises(RuntimeError): patched(path.read_text(), AUTO)

    def test_wrong_base_or_unrepaired_v1_rejected(self):
        for source in ('', PATCH.replace('# EMBYFLOW_PGS_PARENT_LOCAL_V2', '')):
            with self.assertRaises(RuntimeError): patched(source, AUTO)


if __name__ == '__main__':
    unittest.main()

import ast
import copy
import re
import unittest
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / 'EmbyFlowE2_2026102501.py').read_text()
TREE = ast.parse(TEXT)
CLASS = next(n for n in TREE.body if getattr(n, 'name', None) == 'EmbyFlowMoviePlayer')
RUNTIME = (Path(__file__).parent / 'runtime.py').read_text()


class Label:
    def __init__(self, text=''):
        self.text = text

    def setText(self, text):
        self.text = text


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.current = 0
        self.languages = ['deu', 'eng']
        self.source = {'Id': 'active', 'DefaultAudioStreamIndex': 4}
        self.video = {'Codec': 'h264', 'Height': 1080}
        self.audio = {'Language': 'deu', 'DisplayLanguage': 'Deutsch', 'Codec': 'ac3', 'Channels': 6}
        self.before_data = copy.deepcopy((self.source, self.video, self.audio))
        self.show = Mock(return_value='shown')
        self.update = Mock(return_value='updated')
        cls = type('Player', (dict,), {
            'tester_osd_selected_streams': lambda p: (self.source, self.video, self.audio),
            'show_overlay': self.show, 'update_playback_overlay': self.update})
        self.ns = {'EmbyFlowMoviePlayer': cls, 're': re}
        methods = ('tester_osd_build_badges', 'embyflow_audio_track_descriptor',
                   'embyflow_audio_language_key', 'embyflow_audio_language_label',
                   'embyflow_audio_codec_key', 'embyflow_audio_codec_label',
                   'embyflow_audio_channels_number', 'embyflow_track_channel_name')
        for name in methods:
            node = next(n for n in CLASS.body if getattr(n, 'name', None) == name)
            exec(ast.get_source_segment(TEXT, node), self.ns)
            setattr(cls, name, self.ns[name])
        exec(RUNTIME, self.ns)
        self.player = p = cls(technical_badges=Label('[DEUTSCH]'), chip_language=Label('Deutsch'))
        p.overlay_language = 'Deutsch'
        p.overlay_resolution = 'Bild'
        p.overlay_codec = 'Codec'
        p.overlay_audio_format = 'Standard'
        p.overlay_visible = True
        p.closed = False
        p.paused = True
        p.play_session_id = 'session-retained'
        p.ref = Obj(toString=lambda: '4097:active')
        self.tracks = Obj(getCurrentTrack=Mock(side_effect=lambda: self.current),
                          getNumberOfTracks=lambda: len(self.languages),
                          getTrackInfo=lambda i: Obj(getLanguage=lambda: self.languages[i],
                                                    getDescription=lambda: 'AC3 5.1'),
                          selectTrack=Mock())
        self.nav = Obj(getCurrentlyPlayingServiceReference=lambda: p.ref,
                       getCurrentService=lambda: Obj(audioTracks=lambda: self.tracks),
                       playService=Mock(), stopService=Mock())
        p.session = Obj(nav=self.nav)
        p.seek = Mock()

    def test_reproduce_old_non_dream_show_leaves_cached_german(self):
        node = next(n for n in TREE.body if getattr(n, 'name', None) == '_df_show')
        ns = {'_DF_SHOW_BEFORE': self.show, '_df_is': lambda p: False}
        exec(ast.get_source_segment(TEXT, node), ns)
        self.current = 1
        ns['_df_show'](self.player)
        self.assertEqual(self.player['technical_badges'].text, '[DEUTSCH]')

    def test_sf8008_english_beats_german_start_metadata(self):
        self.current = 1
        self.player.show_overlay(reset_timeout=True)
        self.assertIn('[ENGLISCH]', self.player['technical_badges'].text)
        self.assertNotIn('[DEUTSCH]', self.player['technical_badges'].text)
        self.assertEqual(self.player['chip_language'].text, 'Englisch')
        self.show.assert_called_once_with(self.player, reset_timeout=True)

    def test_repeated_switch_and_reopen_uses_actual_index(self):
        for index, text in [(1, 'ENGLISCH'), (0, 'DEUTSCH'), (1, 'ENGLISCH')]:
            self.current = index
            self.player.show_overlay()
            self.assertIn('[' + text + ']', self.player['technical_badges'].text)

    def test_pending_selection_does_not_label_unconfirmed_target(self):
        self.player.embyflow_audio_confirm_requested = 1
        self.player.show_overlay()
        self.assertIn('[DEUTSCH]', self.player['technical_badges'].text)
        self.current = 1
        self.assertEqual(self.player.update_playback_overlay(), 'updated')
        self.assertIn('[ENGLISCH]', self.player['technical_badges'].text)

    def test_source_metadata_and_playback_state_are_unchanged(self):
        self.current = 1
        self.player.show_overlay()
        self.player.update_playback_overlay()
        self.assertEqual((self.source, self.video, self.audio), self.before_data)
        self.assertTrue(self.player.paused)
        self.assertEqual(self.player.play_session_id, 'session-retained')
        self.tracks.selectTrack.assert_not_called()
        self.nav.playService.assert_not_called()
        self.nav.stopService.assert_not_called()
        self.player.seek.assert_not_called()

    def test_unknown_native_language_retains_existing_metadata(self):
        self.languages[1] = 'und'
        self.current = 1
        self.player.show_overlay()
        self.assertIn('[DEUTSCH]', self.player['technical_badges'].text)
        self.assertEqual(self.audio, self.before_data[2])

    def test_other_service_does_not_supply_language(self):
        self.current = 1
        self.nav.getCurrentlyPlayingServiceReference = lambda: Obj(toString=lambda: '4097:other')
        self.player.show_overlay()
        self.tracks.getCurrentTrack.assert_not_called()
        self.assertIn('[DEUTSCH]', self.player['technical_badges'].text)

    def test_single_track_server_stream_keeps_selected_english_when_native_is_unlabelled(self):
        self.audio = dict(self.audio, Language='eng', DisplayLanguage='Englisch')
        self.languages = ['und']
        self.current = 0
        self.player.show_overlay()
        self.assertIn('[ENGLISCH]', self.player['technical_badges'].text)

    def test_hidden_overlay_does_not_poll_language(self):
        self.player.overlay_visible = False
        self.player.update_playback_overlay()
        self.tracks.getCurrentTrack.assert_not_called()
        self.update.assert_called_once_with(self.player)

    def test_invalid_native_index_and_missing_tracks_are_safe(self):
        for index in (-1, 99):
            self.current = index
            self.player.show_overlay()
            self.assertIn('[DEUTSCH]', self.player['technical_badges'].text)
        self.nav.getCurrentService = lambda: Obj(audioTracks=lambda: None)
        self.player.show_overlay()

    def test_native_api_exception_keeps_overlay_working(self):
        self.tracks.getCurrentTrack.side_effect = RuntimeError('service transition')
        self.assertEqual(self.player.show_overlay(), 'shown')
        self.assertIn('[DEUTSCH]', self.player['technical_badges'].text)

    def test_closed_player_does_not_read_native_tracks(self):
        self.player.closed = True
        self.player.show_overlay()
        self.tracks.getCurrentTrack.assert_not_called()


if __name__ == '__main__':
    unittest.main()

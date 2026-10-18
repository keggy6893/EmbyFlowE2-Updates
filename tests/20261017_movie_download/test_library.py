from historical import source as historical_source
import ast
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET
from test_ui import load_ui, Session, Screen
from install_library import patched, install

HERE = Path(__file__).resolve().parent
LIBRARY = (HERE / 'library.py').read_text()


def load_library():
    ns = load_ui()
    class Home:
        def __init__(self):
            self.onShow = []
        def _direct_nav_build_entries_ref12(self):
            return [('Start', {'_direct_action_ref12': 'home'}), ('Favoriten', {'_direct_action_ref12': 'favorites'}), ('Updates', {'_direct_action_ref12':'updates'}), ('Info', {'_direct_action_ref12':'settings'})]
        def _direct_nav_refresh_ref12(self):
            self.refreshed = True
        def _direct_nav_activate_ref12(self):
            self.old_activation = True
        def _sidebar_main_rows_v24(self):
            return []
        def _sidebar_activate_main_v24(self, name):
            self.old_side = name
    ns['EmbyFlowE2Screen'] = Home
    ns['_embyflow_nav_groups_v30_transform'] = lambda entries: list(entries)
    exec(compile(LIBRARY, 'library.py', 'exec'), ns)
    return ns


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_library()
        self.ns['config'].embyflow.movie_download_enabled.value = True
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.mount = Path(self.temp.name) / 'usb'
        self.root = self.mount / 'movie' / 'EmbyFlow'
        self.root.mkdir(parents=True)
        self.ns['_EFLIB_MOUNTS'] = (str(self.mount),)
        self.mount_patch = patch('os.path.ismount', side_effect=lambda p: p == str(self.mount))
        self.mount_patch.start()
        self.addCleanup(self.mount_patch.stop)

    def file(self, name='Mayday_123_' + 'a'*32 + '.mkv'):
        path = self.root / name
        path.write_bytes(b'media')
        return path

    def screen(self):
        return self.ns['EmbyFlowDownloadsScreen'](Session())

    def test_completed_only_no_part_symlink_or_empty(self):
        good = self.file()
        self.file('.hidden.mkv'); self.file('unfinished.mkv.part')
        self.file('zero.mp4').write_bytes(b'')
        (self.root / 'link.mkv').symlink_to(good)
        entries, errors = self.ns['_eflib_scan']()
        self.assertEqual([e['path'] for e in entries], [str(good)])
        self.assertEqual(entries[0]['title'], 'Mayday')
        self.assertFalse(errors)

    def test_mount_required_and_readonly_not_excluded(self):
        self.file()
        with patch('os.access', return_value=False):
            self.assertEqual(len(self.ns['_eflib_scan']()[0]), 1)
        with patch('os.path.ismount', return_value=False):
            self.assertEqual(self.ns['_eflib_scan']()[0], [])

    def test_no_symlink_download_directory(self):
        self.root.rmdir()
        external = Path(self.temp.name) / 'elsewhere'; external.mkdir()
        self.root.symlink_to(external)
        self.assertFalse(self.ns['_eflib_roots']())

    def test_aliases_deduplicated(self):
        alias = Path(self.temp.name) / 'hdd'; alias.symlink_to(self.mount)
        self.ns['_EFLIB_MOUNTS'] = (str(self.mount), str(alias))
        self.file()
        self.assertEqual(len(self.ns['_eflib_scan']()[0]), 1)

    def test_sidecar_whitelist_episode_and_bad_json_fallback(self):
        path = self.file()
        item = dict(Name='Gipfel', Type='Episode', SeriesName='Berge', ParentIndexNumber=1, IndexNumber=2, Token='secret')
        self.ns['_efdl_library_save'](str(path), item, {})
        raw = Path(str(path) + '.embyflow.json').read_text()
        self.assertNotIn('secret', raw)
        entry = self.ns['_eflib_scan']()[0][0]
        self.assertEqual(entry['title'], 'Berge · S01E02 · Gipfel')
        Path(str(path) + '.embyflow.json').write_text('bad json')
        self.assertEqual(self.ns['_eflib_scan']()[0][0]['title'], 'Mayday')

    def test_fifo_metadata_does_not_block_scan(self):
        path = self.file()
        os.mkfifo(str(path) + '.embyflow.json')
        self.assertEqual(len(self.ns['_eflib_scan']()[0]), 1)

    def test_offline_play_4097_original_file_and_local_resume(self):
        path = self.file()
        screen = self.screen()
        screen.results.put(self.ns['_eflib_scan']()); screen.poll()
        reference = Mock()
        self.ns['eServiceReference'] = Mock(return_value=reference)
        self.ns['uuid4'] = lambda: 'session'
        self.ns['_embyflow_v21b_probe_local_file'] = lambda path: dict(media_streams=[{'Type':'Audio'}], runtime_ticks=9000)
        self.ns['get_embyflow_local_resume'] = lambda ident: (4000, 9000)
        launch = self.ns['_open_embyflow_player_now'] = Mock()
        self.ns['_efdl_engine'].quota_status = Mock(side_effect=AssertionError('Quota must not be read'))
        screen.play()
        self.ns['eServiceReference'].assert_called_once_with(4097, 0, str(path))
        info = launch.call_args.args[-1]
        self.assertTrue(info['local_file'])
        self.assertEqual(info['item']['PlaybackPositionTicks'], 4000)
        self.assertEqual(info['item']['MediaSources'][0]['MediaStreams'], [{'Type':'Audio'}])

    def test_unmounted_after_listing_blocks_playback(self):
        self.file(); screen = self.screen()
        screen.results.put(self.ns['_eflib_scan']()); screen.poll()
        with patch('os.path.ismount', return_value=False):
            screen.play()
        self.assertIn('nicht mehr verfügbar', screen['status'].text)

    def test_navigation_survives_refresh_and_group_rebuild(self):
        home = self.ns['EmbyFlowE2Screen']()
        home.session = Session()
        entries = home._direct_nav_build_entries_ref12()
        self.assertEqual([e[0] for e in entries], ['Start', 'Favoriten', 'Updates', 'Downloads', 'Info'])
        for raw in (entries, [('Favoriten', {'_direct_action_ref12':'favorites'})]):
            rebuilt = self.ns['_embyflow_nav_groups_v30_transform'](raw)
            self.assertEqual([e[0] for e in rebuilt].count('Downloads'), 1)
        home.direct_nav_entries_ref12 = entries; home.direct_nav_cursor_ref12 = 3
        home._direct_nav_activate_ref12()
        self.assertIs(home.session.opened[0], self.ns['EmbyFlowDownloadsScreen'])
        home.direct_nav_cursor_ref12 = 0; home._direct_nav_activate_ref12()
        self.assertTrue(home.old_activation)

    def test_setting_off_hides_entry_and_return_from_settings_updates_it(self):
        home = self.ns['EmbyFlowE2Screen']()
        home.direct_nav_entries_ref12 = home._direct_nav_build_entries_ref12()
        home.direct_nav_cursor_ref12 = 4  # Preserve focus on Settings.
        self.ns['config'].embyflow.movie_download_enabled.value = False
        home.downloads_setting_refresh()
        self.assertNotIn('Downloads', [e[0] for e in home.direct_nav_entries_ref12])
        self.assertEqual(home.direct_nav_cursor_ref12, 3)
        self.assertNotIn('Downloads', [e[0] for e in home._direct_nav_build_entries_ref12()])
        self.assertNotIn('Downloads', [e[0] for e in home._sidebar_main_rows_v24()])
        self.ns['config'].embyflow.movie_download_enabled.value = True
        home.onShow[0]()
        self.assertEqual(home.direct_nav_entries_ref12[3][0], 'Downloads')
        self.assertEqual(home.direct_nav_cursor_ref12, 4)

    def test_list_pagination_empty_and_bound_callbacks(self):
        screen = self.screen()
        screen.results.put(([], [])); screen.poll()
        self.assertIn('Keine fertigen', screen['status'].text)
        for index in range(6): self.file('Film%d.mkv' % index)
        screen.results.put(self.ns['_eflib_scan']()); screen.poll()
        for i in range(5): screen.down()
        self.assertEqual(screen.index, 5)
        self.assertTrue(screen['title1'].hidden)
        self.assertTrue(all(getattr(fn, '__self__', None) is screen for fn in screen.onLayoutFinish))
        ET.fromstring(screen.skin)
        screen.close(); self.assertTrue(screen.closed)


class InstallerTests(unittest.TestCase):
    def test_actual_v8_and_counter_addon_preserved_and_idempotent(self):
        source = historical_source(8)
        source += '\n# KEEP_PGS_AND_QUOTA\n'
        result = patched(source, LIBRARY)
        compile(result, 'plugin.py', 'exec')
        self.assertIn('# KEEP_PGS_AND_QUOTA', result)
        self.assertIn('_efdl_library_save(path, self.item, self.data)', result)
        self.assertEqual(patched(result, LIBRARY), result)
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'plugin.py'; target.write_text(source)
            install(target, LIBRARY)
            self.assertEqual(target.read_text(), result)
            self.assertEqual(next(Path(temporary).glob('*.vor-downloads-*')).read_text(), source)

    def test_incompatible_file_rejected_before_changes(self):
        with self.assertRaises(RuntimeError): patched('PLUGIN_VERSION = "other"', LIBRARY)


if __name__ == '__main__': unittest.main()

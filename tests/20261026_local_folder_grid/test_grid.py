import ast
import base64
import copy
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace as Obj
from unittest.mock import Mock, patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location('local_grid_installer', ROOT / 'tools/install-local-folder-grid-20261026.py')
INSTALL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALL)
SOURCE = (ROOT / 'EmbyFlowE2_2026102502.py').read_text()
NODE = next(n for n in ast.parse(SOURCE).body if isinstance(n, ast.ClassDef) and n.name == 'EmbyFlowLocalMediaScreen')


class Widget:
    def __init__(self, text=''):
        self.text = text
        self.visible = True
        self.instance = self
    def setText(self, text): self.text = text
    def show(self): self.visible = True
    def hide(self): self.visible = False
    def move(self, value): self.position = value
    def resize(self, value): self.size = value
    def setPixmapFromFile(self, path): self.image = path
    def setScale(self, value): pass


class Screen(dict):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.onLayoutFinish = []
        self.onClose = []
    def close(self): self.was_closed = True


class Timer:
    def __init__(self): self.callback = []
    def stop(self): pass


class GridTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ns = dict(os=os, Screen=Screen, Label=Widget, Pixmap=Widget,
                       ActionMap=lambda contexts, actions, *args: actions,
                       eTimer=Timer, scale_skin=lambda text: text,
                       _EMBYFLOW_LOCAL_ROWS_SKIN='', EMBYFLOW_LOCAL_MEDIA_ROOT=str(self.root),
                       PLUGIN_PATH=str(self.root), EFP=lambda *a: a, EFS=lambda *a: a)
        exec(ast.get_source_segment(SOURCE, NODE), self.ns)
        cls = self.ns['EmbyFlowLocalMediaScreen']
        self.original_open = cls.open_selected
        self.original_play = cls.play_file
        self.original_back = cls.go_back
        exec(INSTALL.RUNTIME, self.ns)
        self.ns['_ELFG_ASSETS'] = str(HERE / 'assets')
        self.screen = cls(Obj(open=Mock()), str(self.root), 'USB-Festplatte')
        self.screen.start_scan = Mock()

    def entry(self, name, kind='dir'):
        return dict(name=name, kind=kind, path=str(self.root / name), meta='Ordner' if kind == 'dir' else 'TS · 6 GB')

    def test_exact_marine_background_and_valid_complete_skin(self):
        root = ET.fromstring(self.screen.skin)
        self.assertEqual(root.attrib['backgroundColor'], '#0C1827')
        self.assertNotIn('#151311', self.screen.skin)
        self.assertEqual(root.attrib['size'], '1920,1080')
        widgets = {n.attrib['name'] for n in root.findall('widget')}
        self.assertEqual(len([n for n in widgets if n.startswith('row')]), 9)
        self.assertTrue({'selection_path', 'selection_name', 'filter_hint', 'focus_bg'}.issubset(widgets))
        nodes = {n.attrib['name']: n for n in root.findall('widget')}
        self.assertLess(int(nodes['focus_bg'].attrib['zPosition']), int(nodes['row0'].attrib['zPosition']))
        self.assertLess(int(nodes['focus_bg'].attrib['zPosition']), int(nodes['tile_icon0'].attrib['zPosition']))

    def test_media_first_and_yellow_reveals_technical_folders(self):
        s = self.screen
        s.entries = [self.entry('backup_openatv'), self.entry('Filme'), self.entry('Serien'), self.entry('images')]
        original = copy.deepcopy(s.entries)
        s.refresh()
        self.assertEqual(s['row0'].text, 'Filme')
        self.assertEqual(s['row1'].text, 'Serien')
        self.assertIn('2 weitere', s['filter_hint'].text)
        s['_unused'] = Widget()
        s['actions']['yellow']()
        self.assertEqual(len(self.ns['_elfg_entries'](s)), 4)
        self.assertIn('backup_openatv', [e['name'] for e in self.ns['_elfg_entries'](s)])
        self.assertEqual(s.entries, original)

    def test_unknown_media_folder_names_are_not_hidden_without_known_media(self):
        s = self.screen
        s.entries = [self.entry('My Collection'), self.entry('Archiv')]
        s.refresh()
        self.assertEqual(len(self.ns['_elfg_entries'](s)), 2)

    def test_video_files_remain_visible_in_media_view(self):
        s = self.screen
        movie = self.entry('Skyfall.ts', 'file')
        s.entries = [self.entry('backup'), self.entry('Filme'), movie]
        s.refresh()
        self.assertEqual(self.ns['_elfg_entries'](s), [s.entries[1], movie])
        self.assertTrue(s['tile_icon1'].image.endswith('video.png'))

    def test_existing_open_still_opens_selected_filtered_real_folder(self):
        s = self.screen
        (self.root / 'Filme').mkdir()
        s.entries = [self.entry('backup'), self.entry('Filme')]
        s.refresh()
        s['actions']['ok']()
        self.assertEqual(s.current_path, str(self.root / 'Filme'))
        s.start_scan.assert_called_once()
        self.assertIs(type(s).open_selected, self.original_open)

    def test_existing_file_playback_method_is_not_replaced(self):
        s = self.screen
        s.entries = [self.entry('Skyfall.ts', 'file')]
        s.refresh()
        s.play_file = Mock()
        s.open_selected()
        s.play_file.assert_called_once_with(str(self.root / 'Skyfall.ts'))
        self.assertIs(type(s).play_file, self.original_play)

    def test_root_boundary_and_return_to_dashboard_preserved(self):
        s = self.screen
        s.entries = [dict(name='outside', path='/outside', kind='dir', meta='Ordner')]
        s.refresh()
        s.open_selected()
        s.start_scan.assert_not_called()
        self.assertIs(type(s).go_back, self.original_back)
        s.go_back()
        self.assertTrue(s.was_closed)

    def test_three_column_navigation_and_page_alignment(self):
        s = self.screen
        s.entries = [self.entry('Folder%02d' % i) for i in range(17)]
        s.refresh()
        s['actions']['right']()
        self.assertEqual(s.selected_index, 1)
        s['actions']['up']()
        self.assertEqual(s.selected_index, 1)
        s['actions']['down']()
        self.assertEqual(s.selected_index, 4)
        s['actions']['down']();s['actions']['down']()
        self.assertEqual(s.selected_index, 10)
        self.assertEqual(s.offset, 9)
        self.assertEqual(s['focus_bg'].position, (485, 250))
        self.assertEqual(s['row1'].text, 'Folder10')
        self.assertEqual(s['page'].text, '2 / 2')

    def test_navigation_reuses_sorted_snapshot_until_scanner_replaces_entries(self):
        s = self.screen
        s.entries = [self.entry('Folder%02d' % i) for i in range(20)]
        original = self.ns['_elfg_priority']
        counting = Mock(wraps=original)
        self.ns['_elfg_priority'] = counting
        s.refresh()
        self.assertGreater(counting.call_count, 0)
        counting.reset_mock()
        s._elfg_right();s._elfg_right();s.move_down()
        counting.assert_not_called()
        s.entries = s.entries + [self.entry('New Folder')]
        s.refresh()
        self.assertGreater(counting.call_count, 0)

    def test_full_path_visible_and_empty_slots_hidden(self):
        s = self.screen
        s.entries = [self.entry('A long collection name that needs two lines')]
        s.refresh()
        self.assertTrue(s['tile_bg0'].visible)
        self.assertFalse(s['tile_bg1'].visible)
        self.assertEqual(s['selection_path'].text.replace('\n', ''), s.entries[0]['path'])
        self.assertNotIn('[Ordner]', s['row0'].text)

    def test_empty_scanning_and_scan_blocking_are_safe(self):
        s = self.screen
        s.refresh()
        self.assertFalse(s['focus_bg'].visible)
        self.assertFalse(s['selection_icon'].visible)
        s.entries = [self.entry('Filme')]
        s.scan_loading = True
        s.open_selected()
        s.start_scan.assert_not_called()

    def test_loading_new_path_resets_filter_and_selection(self):
        s = self.screen
        s.entries = [self.entry('Filme'), self.entry('backup')]
        s.refresh();s._elfg_toggle()
        s.selected_index = 1
        s.current_path = str(self.root / 'Filme')
        s.entries = [self.entry('Skyfall.ts', 'file')]
        s.refresh()
        self.assertFalse(s._elfg_show_all)
        self.assertEqual(s.selected_index, 0)


class InstallerTests(unittest.TestCase):
    def test_only_local_browser_extension_is_added_and_is_idempotent(self):
        result = INSTALL.patched(SOURCE)
        self.assertEqual(ast.dump(ast.parse(result.split(INSTALL.BEGIN)[0])), ast.dump(ast.parse(SOURCE)))
        self.assertEqual(INSTALL.patched(result), result)
        ast.parse(result, feature_version=(3, 8))

    def test_pictures_match_bundled_files_and_decode(self):
        self.assertEqual(set(INSTALL.ASSETS), {'folder.png', 'video.png'})
        for name, encoded in INSTALL.ASSETS.items():
            raw = base64.b64decode(encoded, validate=True)
            self.assertEqual(raw, (HERE / 'assets' / name).read_bytes())
            with Image.open(io.BytesIO(raw)) as image:
                self.assertEqual(image.size, (256, 256))
                image.verify()

    def test_install_preserves_settings_and_backs_up_existing_plugin(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plugin = root / 'plugin.py';plugin.write_text(SOURCE)
            sources = root / 'embyflow_local_sources.json';sources.write_bytes(b'keep-local-sources')
            with patch.object(INSTALL.subprocess, 'run') as run, patch.object(INSTALL.time, 'sleep'):
                INSTALL.main(str(plugin), str(root / 'lock'))
            self.assertEqual(sources.read_bytes(), b'keep-local-sources')
            self.assertEqual(next(root.glob('plugin.py.vor-local-browser-*')).read_text(), SOURCE)
            self.assertEqual([c.args[0] for c in run.call_args_list], [['init', '4'], ['init', '3']])
            self.assertTrue((root / 'assets/local_folder_grid_20261026/folder.png').is_file())


if __name__ == '__main__':
    unittest.main()

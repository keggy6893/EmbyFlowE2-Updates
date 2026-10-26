import ast
import base64
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace as Obj
from unittest.mock import Mock, patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location('source_picon_installer', ROOT / 'tools/install-local-source-picons-20261026.py')
INSTALL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALL)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.old = Mock(return_value='old')
        base = type('Base', (dict,), {'_show_icon': self.old})
        self.cls = type('SourceDashboard', (base,), {})
        self.ns = {'EmbyFlowLocalSourcesScreenV16': base, 'os': __import__('os'),
                   'PLUGIN_PATH': '/unused', 'EFP': lambda *a: ('point', a),
                   'EFS': lambda *a: ('size', a)}
        exec(INSTALL.RUNTIME, self.ns)
        self.ns['_ELSI_ASSETS'] = str(HERE / 'assets')
        self.instance = Obj(move=Mock(), resize=Mock(), setPixmapFromFile=Mock(),
                            setScale=Mock(), show=Mock())
        self.widget = Obj(instance=self.instance, show=Mock())
        self.screen = self.cls(card_icon0=self.widget, mgr_icon0=self.widget)

    def test_source_category_mapping_including_virtual_all(self):
        cases = [({'mode': 'movies'}, 'movies'), ({'mode': 'series'}, 'series'),
                 ({'mode': 'recordings'}, 'recordings'), ({'mode': 'documentary'}, 'documentary'),
                 ({'mode': 'mixed', 'path': '/media/usb'}, 'drive'),
                 ({'mode': 'mixed', 'path': '/media/hdd'}, 'drive'),
                 ({'mode': 'mixed', 'path': '/media/net/nas'}, 'network'),
                 ({'id': '__embyflow_all_media_v1__', 'mode': 'mixed'}, 'all')]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(self.ns['_elsi_kind'](source), expected)

    def test_inherited_dashboard_loads_card_icon_with_existing_scaling(self):
        self.screen._show_icon('card_icon0', {'mode': 'movies'})
        self.instance.setPixmapFromFile.assert_called_once_with(str(HERE / 'assets/movies.png'))
        self.instance.move.assert_called_once_with(('point', (249, 354)))
        self.instance.resize.assert_called_once_with(('size', (112, 112)))
        self.widget.show.assert_called_once()
        self.old.assert_not_called()

    def test_manager_uses_same_picon_without_resizing_row(self):
        self.screen._show_icon('mgr_icon0', {'mode': 'series'})
        self.instance.setPixmapFromFile.assert_called_once_with(str(HERE / 'assets/series.png'))
        self.instance.move.assert_not_called()
        self.instance.resize.assert_not_called()

    def test_fifth_card_fits_existing_layout(self):
        self.screen['card_icon4'] = self.widget
        self.screen._show_icon('card_icon4', {'id': '__embyflow_all_media_v1__'})
        self.instance.move.assert_called_once_with(('point', (1113, 354)))
        self.assertLess(1113 + 112, 1269)
        self.assertLess(354 + 112, 490)

    def test_source_data_is_not_changed(self):
        source = {'id': 'usb', 'mode': 'movies', 'path': '/media/usb/Filme', 'enabled': False}
        before = dict(source)
        self.screen._show_icon('card_icon0', source)
        self.assertEqual(source, before)

    def test_missing_asset_uses_original_handler(self):
        self.ns['_ELSI_ASSETS'] = '/does-not-exist'
        source = {'mode': 'movies'}
        self.assertEqual(self.screen._show_icon('card_icon0', source), 'old')
        self.old.assert_called_once_with(self.screen, 'card_icon0', source)

    def test_widget_not_ready_or_failed_decoder_uses_original_handler(self):
        self.widget.instance = None
        self.screen._show_icon('card_icon0', {})
        self.old.assert_called_once()
        self.old.reset_mock()
        self.widget.instance = self.instance
        self.instance.setPixmapFromFile.side_effect = RuntimeError('decode failed')
        self.screen._show_icon('card_icon0', {})
        self.old.assert_called_once()


class AssetAndInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'EmbyFlowE2_2026102502.py').read_bytes()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.plugin = self.folder / 'plugin.py'
        self.plugin.write_bytes(self.source)
        self.run = self.enterContext(patch.object(INSTALL.subprocess, 'run'))
        self.enterContext(patch.object(INSTALL.time, 'sleep'))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def main(self):
        INSTALL.main(str(self.plugin), str(self.folder / 'lock'))

    def test_embedded_pngs_match_reviewed_assets_and_have_transparency(self):
        self.assertEqual(len(INSTALL.ASSETS), 7)
        for name, encoded in INSTALL.ASSETS.items():
            with self.subTest(name=name):
                raw = base64.b64decode(encoded, validate=True)
                self.assertEqual(raw, (HERE / 'assets' / name).read_bytes())
                with Image.open(io.BytesIO(raw)) as image:
                    image.verify()
                with Image.open(io.BytesIO(raw)) as image:
                    self.assertEqual(image.size, (256, 256))
                    self.assertEqual(image.mode, 'RGBA')
                    self.assertEqual(image.getpixel((0, 0))[3], 0)
                    self.assertIsNotNone(image.getbbox())

    def test_only_appended_dashboard_image_hook_changes(self):
        result = INSTALL.patched(self.source.decode())
        self.assertEqual(ast.dump(ast.parse(result.split(INSTALL.BEGIN)[0])),
                         ast.dump(ast.parse(self.source)))
        self.assertEqual(INSTALL.patched(result), result)
        self.assertEqual(INSTALL.RUNTIME, (HERE / 'runtime.py').read_text())
        ast.parse(result, feature_version=(3, 8))

    def test_install_writes_picons_backs_up_plugin_and_restarts(self):
        settings = self.folder / 'embyflow_local_sources.json'
        settings.write_bytes(b'unchanged-sources')
        self.main()
        self.assertEqual(settings.read_bytes(), b'unchanged-sources')
        backup = next(self.folder.glob('plugin.py.vor-local-picons-*'))
        self.assertEqual(backup.read_bytes(), self.source)
        self.assertEqual([c.args[0] for c in self.run.call_args_list], [['init', '4'], ['init', '3']])
        target = self.folder / 'assets/local_source_picons_20261026'
        self.assertEqual(len(list(target.glob('*.png'))), 7)

    def test_repeat_install_recovers_missing_picon_without_gui_restart(self):
        self.main()
        target = self.folder / 'assets/local_source_picons_20261026/movies.png'
        target.unlink()
        self.run.reset_mock()
        self.main()
        self.run.assert_not_called()
        self.assertTrue(target.is_file())

    def test_existing_skyfall_and_player_changes_are_preserved(self):
        spec = importlib.util.spec_from_file_location('skyfall_restore', ROOT / 'tools/restore-local-skyfall-20261026.py')
        skyfall = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(skyfall)
        previous = skyfall.patched(self.source.decode())
        result = INSTALL.patched(previous)
        self.assertEqual(ast.dump(ast.parse(result.split(INSTALL.BEGIN)[0])), ast.dump(ast.parse(previous)))

    def test_asset_directory_symlink_is_rejected_without_gui_stop(self):
        assets = self.folder / 'assets'
        assets.mkdir()
        (assets / 'local_source_picons_20261026').symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            self.main()
        self.run.assert_not_called()
        self.assertEqual(self.plugin.read_bytes(), self.source)

    def test_failed_replacement_still_restarts(self):
        real_replace = INSTALL.os.replace
        def replace(src, dst):
            if Path(dst) == self.plugin:
                raise OSError('plugin replace failed')
            return real_replace(src, dst)
        with patch.object(INSTALL.os, 'replace', side_effect=replace):
            with self.assertRaisesRegex(OSError, 'plugin replace failed'):
                self.main()
        self.assertEqual(self.plugin.read_bytes(), self.source)
        self.assertEqual([c.args[0] for c in self.run.call_args_list], [['init', '4'], ['init', '3']])


if __name__ == '__main__':
    unittest.main()

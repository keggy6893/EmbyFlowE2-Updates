from historical import source as historical_source
import ast
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from types import SimpleNamespace

from test_ui import load_ui, Session
from install_quota_display import patched, install

HERE = Path(__file__).resolve().parent
ENGINE = (HERE / 'engine.py').read_text()
HELPER = next(ast.get_source_segment(ENGINE, node) for node in ast.parse(ENGINE).body
              if isinstance(node, ast.FunctionDef) and node.name == 'quota_status')
DISPLAY = (HERE / 'quota_display.py').read_text()


class QuotaDisplayTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_ui()
        self.used = 2
        self.ns['_efdl_engine'].quota_status = lambda: dict(used=self.used, remaining=5-self.used, limit=5)
        self.skin_patch = patch.dict('sys.modules', {'skin': self.ns['_test_skin_module']})
        self.skin_patch.start(); self.addCleanup(self.skin_patch.stop)

    def test_choices_show_same_counter_and_refresh_at_limit(self):
        for confirmation in (False, True):
            dialog = self.ns['EmbyFlowDownloadChoice'](Session(), title='Download',
                list=[('USB', '/media/usb')], confirmation=confirmation)
            self.assertEqual(dialog['quota'].text, 'Heute 2 von 5 · noch 3 verfügbar')
            self.used = 5
            dialog._quota_timer.callback[0]()
            self.assertEqual(dialog['quota'].text, 'Heute 5 von 5 · Tageslimit erreicht')
            dialog.close()
            self.assertFalse(dialog._quota_timer.running)
            self.used = 2

    def test_progress_updates_after_success_or_refund_and_uses_warning_colour(self):
        screen = self.ns['EmbyFlowLocalDownloadScreen'](Session(), {'title': 'Film'})
        self.assertEqual(screen['quota'].text, 'Heute 2 von 5 · noch 3 verfügbar')
        colours = []
        screen['quota'].instance = SimpleNamespace(setForegroundColor=colours.append)
        self.used = 5; screen.poll()
        self.assertEqual(colours[-1], '#D49A9F')
        self.used = 4; screen.poll()
        self.assertEqual(screen['quota'].text, 'Heute 4 von 5 · noch 1 verfügbar')
        self.assertEqual(colours[-1], '#26DFF5')

    def test_unknown_quota_does_not_show_available_slots(self):
        self.ns['_efdl_engine'].quota_status = lambda: None
        screen = self.ns['EmbyFlowLocalDownloadScreen'](Session(), {})
        self.assertEqual(screen['quota'].text, 'Tageslimit nicht prüfbar · kein Download möglich')

    def test_counter_permission_rows_and_footer_do_not_overlap(self):
        for confirmation in (False, True):
            dialog = self.ns['EmbyFlowDownloadChoice'](Session(), title='Download',
                list=[('USB', '/media/usb'), ('HDD', '/media/hdd')], confirmation=confirmation)
            nodes = {n.get('name'): n for n in ET.fromstring(dialog.skin) if n.get('name')}
            y = lambda name: int(nodes[name].get('position').split(',')[1])
            h = lambda name: int(nodes[name].get('size').split(',')[1])
            self.assertLessEqual(y('quota')+h('quota'), y('permission'))
            self.assertLessEqual(y('permission')+h('permission'), y('card0'))

    def old_classes(self):
        source = historical_source(9)
        nodes = [n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and
                 n.name in ('EmbyFlowDownloadChoice', 'EmbyFlowLocalDownloadScreen')]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'receiver_v9.py', 'exec'), self.ns)
        self.ns['_EFDLChoice'] = self.ns['EmbyFlowDownloadChoice']

    def test_direct_addon_on_actual_v9_has_same_geometry_and_live_values(self):
        current = self.ns['EmbyFlowDownloadChoice'](Session(), title='Download', list=[('USB','/media/usb')])
        self.old_classes()
        exec(compile(DISPLAY, 'quota_display.py', 'exec'), self.ns)
        upgraded = self.ns['EmbyFlowDownloadChoice'](Session(), title='Download', list=[('USB','/media/usb')])
        def geometry(screen):
            root = ET.fromstring(screen.skin)
            return root.get('size'), {n.get('name'): (n.get('position'), n.get('size')) for n in root if n.get('name')}
        self.assertEqual(geometry(current), geometry(upgraded))
        self.assertEqual(upgraded['quota'].text, 'Heute 2 von 5 · noch 3 verfügbar')
        self.used = 5; upgraded._quota_timer.callback[0]()
        self.assertIn('Tageslimit erreicht', upgraded['quota'].text)
        progress = self.ns['EmbyFlowLocalDownloadScreen'](Session(), {})
        self.assertIn('Tageslimit erreicht', progress['quota'].text)
        self.used = 3; progress.poll()
        self.assertEqual(progress['quota'].text, 'Heute 3 von 5 · noch 2 verfügbar')

    def test_v8_and_v9_installer_preserves_pgs_and_counter_file(self):
        for version in (8, 9):
            source = historical_source(version)
            source += '\n# keep custom PGS and local additions\n'
            result = patched(source, ENGINE, HELPER, DISPLAY)
            self.assertIn('# keep custom PGS and local additions', result)
            self.assertEqual(patched(result, ENGINE, HELPER, DISPLAY), result)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)/'plugin.py'; path.write_text(source)
                counter = Path(tmp)/'quota.json'; counter.write_text('{"version":1,"days":{"2026-10-18":2}}')
                install(path, ENGINE, HELPER, DISPLAY)
                self.assertEqual(path.read_text(), result)
                self.assertEqual(next(path.parent.glob('*.vor-dl-zaehler-*')).read_text(), source)
                self.assertIn('"2026-10-18":2', counter.read_text())

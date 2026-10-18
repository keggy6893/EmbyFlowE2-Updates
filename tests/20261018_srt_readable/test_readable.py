import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('srt_readable', ROOT / 'install-srt-readable.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
SOURCE = (ROOT / 'EmbyFlowE2_2026101802.py').read_text()


class Readability(unittest.TestCase):
    def test_only_srt_widget_changes_and_source_compiles(self):
        changed = helper.patched(SOURCE)
        self.assertEqual(helper.WIDGET.sub('SRT_WIDGET', changed).replace('\n' + helper.MARKER + '\n', ''),
                         helper.WIDGET.sub('SRT_WIDGET', SOURCE))
        compile(changed, 'plugin.py', 'exec')
        widget = ET.fromstring(helper.WIDGET.search(changed).group())
        self.assertEqual(widget.get('font'), 'Regular;58')
        self.assertEqual(widget.get('valign'), 'bottom')
        self.assertEqual(widget.get('borderColor'), '#000000')
        self.assertEqual(widget.get('borderWidth'), '3')

    def test_actual_scaler_preserves_readability_and_screen_bounds(self):
        tree = ast.parse(SOURCE)
        names = ('sx', 'sy', 'sf', 'scale_skin')
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        code = compile(ast.Module(body=functions, type_ignores=[]), 'actual-scaler', 'exec')
        for factor, width, height, font in [(1, 1920, 1080, 58), (2/3, 1280, 720, 39)]:
            ns = {'SCALE_X': factor, 'SCALE_Y': factor, 'SCALE_FONT': factor, 'apply_embyflow_colors': lambda s: s}
            exec(code, ns)
            widget = ET.fromstring(ns['scale_skin'](helper.WIDGET.search(helper.patched(SOURCE)).group()))
            x, y = map(int, widget.get('position').split(','))
            w, h = map(int, widget.get('size').split(','))
            self.assertEqual(widget.get('font'), 'Regular;%d' % font)
            self.assertLessEqual(x + w, width)
            self.assertLessEqual(y + h, height)
            self.assertGreaterEqual(h, font * 3)

    def test_upgrade_from_52_retains_geometry_border_and_single_marker(self):
        previous = helper.patched(SOURCE).replace('font="Regular;58"', 'font="Regular;52"')
        upgraded = helper.patched(previous)
        self.assertEqual(upgraded, helper.patched(SOURCE))
        self.assertEqual(upgraded.count(helper.MARKER), 1)

    def test_backup_preserves_local_edits_and_repeat_install_is_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plugin.py'
            original = SOURCE + '\n# existing local language or LCD fix\n'
            path.write_text(original)
            path.chmod(0o644)
            self.assertTrue(helper.install(path))
            backup = next(path.parent.glob('plugin.py.vor-srt-*'))
            self.assertEqual(backup.read_text(), original)
            self.assertIn('# existing local language or LCD fix', path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
            self.assertFalse(helper.install(path))
            self.assertEqual(len(list(path.parent.glob('plugin.py.vor-srt-*'))), 1)

    def test_missing_ambiguous_or_invalid_source_cannot_modify_file(self):
        for source in ['pass', SOURCE + helper.WIDGET.search(SOURCE).group(), SOURCE + '\nbroken (']:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'plugin.py'
                path.write_text(source)
                with self.assertRaises((RuntimeError, SyntaxError)):
                    helper.install(path)
                self.assertEqual(path.read_text(), source)
                self.assertEqual(list(path.parent.glob('plugin.py.vor-srt-*')), [])


if __name__ == '__main__':
    unittest.main()

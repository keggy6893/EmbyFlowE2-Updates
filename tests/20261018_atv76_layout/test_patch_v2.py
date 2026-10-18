import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock_patch
from types import ModuleType, SimpleNamespace
import sys

from install_v2 import patch, install
from test_layout import load, skin, Geometry, Widget

HERE = Path(__file__).resolve().parent
RUNTIME = (HERE / 'runtime.py').read_text()


class PatchV2Tests(unittest.TestCase):
    def test_corrupted_condition_is_replaced_and_local_suffix_preserved(self):
        bad = RUNTIME.replace("if name.startswith('detail_overview_line_') else y", "if name.startswith('detail_overviewline') else y")
        prefix = (HERE.parents[1] / 'EmbyFlowE2_2026101802.py').read_text()
        suffix = '\nLOCAL_CUSTOM_SETTING = True\n'
        result = patch(prefix + '\n' + bad + suffix, RUNTIME)
        self.assertNotIn('detail_overviewline', result)
        self.assertTrue(result.startswith(prefix))
        self.assertTrue(result.endswith(suffix))
        self.assertEqual(patch(result, RUNTIME), result)

    def test_install_on_published_download_base_and_backup(self):
        source = (HERE.parents[1] / 'EmbyFlowE2_2026101802.py').read_text()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'plugin.py'
            target.write_text(source)
            target.chmod(0o640)
            self.assertTrue(install(target, RUNTIME))
            self.assertEqual(next(Path(directory).glob('*.vor-layout-v2-*')).read_text(), source)
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
            self.assertFalse(install(target, RUNTIME))

    def test_superseded_multiline_field_hidden_and_native_row_spacing(self):
        ns = load(); ns['_efl_image_76'] = lambda: True
        screen = ns['EmbyFlowDetailScreen']()
        screen.instance = SimpleNamespace(size=lambda: Geometry(1920,1080))
        screen.skin = skin(1920,1080)
        for name in ns['_efl_plan'](screen.skin,1920,1080):
            screen[name] = SimpleNamespace(instance=Widget())
        hidden = []
        screen['detail_overview'] = SimpleNamespace(hide=lambda: hidden.append(True))
        enigma = ModuleType('enigma');enigma.ePoint=enigma.eSize=enigma.eRect=Geometry
        skinmod = ModuleType('skin');skinmod.parseFont=lambda x:x
        with mock_patch.dict(sys.modules, {'enigma':enigma,'skin':skinmod}):
            with mock_patch('tempfile.mkstemp', side_effect=OSError('No diagnostic directory')):
                screen.onLayoutFinish[0]()
        self.assertEqual(hidden,[True])
        ys=[screen['detail_overview_line_%d'%i].instance.xy.y() for i in range(6)]
        self.assertEqual([b-a for a,b in zip(ys,ys[1:])],[38]*5)

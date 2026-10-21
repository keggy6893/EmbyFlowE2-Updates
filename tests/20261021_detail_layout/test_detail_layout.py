from pathlib import Path
from types import SimpleNamespace as NS
import ast
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from build_detail_layout import fixed_source

HERE = Path(__file__).resolve().parent
BASELINE = HERE / 'EmbyFlowE2_2026102102.py'
if not BASELINE.exists():
    BASELINE = HERE.parents[1] / 'EmbyFlowE2_2026102102.py'
SOURCE = fixed_source(BASELINE.read_text(encoding='utf-8'))


class LayoutTests(unittest.TestCase):
    def namespace(self, width, height):
        sx = lambda n: int(n * width / 1920)
        sy = lambda n: int(n * height / 1080)
        def seed(player, *args):
            root = ET.Element('screen', size='%d,%d' % (width, height))
            ET.SubElement(root, 'eLabel', text='Inhaltsangabe', position='%d,%d' % (sx(90), sy(495)), size='%d,%d' % (sx(900), sy(45)))
            for i in range(6):
                ET.SubElement(root, 'widget', name='detail_overview_line_%d' % i,
                              position='%d,%d' % (sx(90), sy(545 + i*38)), size='%d,%d' % (sx(1290), sy(38)))
            for name in ('detail_country_value','detail_director_value','detail_studio_value','detail_actors_value'):
                ET.SubElement(root, 'widget', name=name)
            player.skin = ET.tostring(root, encoding='unicode')
        ns = dict(sx=sx, sy=sy, _efup_ET=ET, _efread_ET=ET,
                  _EFUP_INIT=seed, _EFREAD_INIT=seed, _EFUP_BAD_RENDER=lambda p: None)
        tree = ast.parse(SOURCE)
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('_efup_init','_efup_bad_render','_efread_init')]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'layout', 'exec'), ns)
        return ns
    def test_heading_and_body_do_not_overlap_at_receiver_resolutions(self):
        for width, height in ((1280,720),(1920,1080),(3840,2160)):
            with self.subTest(resolution=(width,height)):
                ns = self.namespace(width,height); p = NS()
                ns['_efup_init'](p,None,{})
                root = ET.fromstring(p.skin); heading = root.find('eLabel')
                hy = int(heading.get('position').split(',')[1]); hh = int(heading.get('size').split(',')[1])
                body = root.find("widget[@name='detail_overview_line_0']")
                by = int(body.get('position').split(',')[1])
                self.assertGreater(by, hy+hh)
                ys = [int(root.find("widget[@name='detail_overview_line_%d']" % i).get('position').split(',')[1]) for i in range(6)]
                self.assertEqual(ys, sorted(set(ys)))
    def test_metadata_and_captions_scale_to_receiver(self):
        for width,height in ((1280,720),(1920,1080),(3840,2160)):
            ns=self.namespace(width,height); p=NS(); ns['_efread_init'](p,None,{})
            root=ET.fromstring(p.skin)
            for node in root:
                if node.get('text') in ('Land','Regie','Filmstudio','Darsteller') or node.get('name','').endswith('_value'):
                    x,y=map(int,node.get('position').split(',')); w,h=map(int,node.get('size').split(','))
                    self.assertLessEqual(x+w,width); self.assertLessEqual(y+h,height)
                    self.assertEqual(node.get('font'),'Regular;%d' % ns['sy'](24))
    def test_badge_refresh_has_scaled_shift_and_no_drift(self):
        for width,height in ((1280,720),(1920,1080),(3840,2160)):
            ns=self.namespace(width,height)
            class Point:
                def __init__(self,x,y): self.a=x; self.b=y
                def x(self): return self.a
                def y(self): return self.b
            class Instance:
                def __init__(self): self.point=Point(ns['sx'](90),ns['sy'](325))
                def position(self): return self.point
                def move(self,p): self.point=p
            p={'detail_badge_%d_%s'%(i,s): NS(instance=Instance()) for i in range(9) for s in ('text','bg')}
            with patch.dict(sys.modules, {'enigma':NS(ePoint=Point)}):
                ns['_efup_bad_render'](p); ns['_efup_bad_render'](p)
            self.assertEqual(p['detail_badge_0_text'].instance.position().y(),ns['sy'](325)-ns['sy'](30))


if __name__ == '__main__': unittest.main(verbosity=2)

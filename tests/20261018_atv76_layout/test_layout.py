import ast
from pathlib import Path
from types import SimpleNamespace,ModuleType
import sys
import tempfile
import unittest
from unittest.mock import patch,mock_open,Mock
import xml.etree.ElementTree as ET
from install import patch as patch_source,install

HERE=Path(__file__).resolve().parent
RUNTIME=(HERE/'runtime.py').read_text()


def load():
    class Detail(dict):
        def __init__(self,*args):self.onLayoutFinish=[]
        def update_detail_focus(self):self.focus_called=True
    ns={'EmbyFlowDetailScreen':Detail}
    exec(RUNTIME,ns)
    return ns


def skin(width,height,episode=False,hidden_overview=True):
    sx=lambda x:round(x*width/1920);sy=lambda y:round(y*height/1080)
    root=ET.Element('screen',size='%d,%d'%(width,height))
    def widget(name,x,y,w,h):
        ET.SubElement(root,'widget',name=name,position='%d,%d'%(sx(x),sy(y)),size='%d,%d'%(sx(w),sy(h)),font='Regular;%d'%sy(30))
    ET.SubElement(root,'eLabel',text='Inhaltsangabe',position='%d,%d'%(sx(90),sy(495)),size='%d,%d'%(sx(900),sy(45)))
    widget('detail_overview',0,0,1,1) if hidden_overview else widget('detail_overview',90,510,1290,245)
    for i in range(6):widget('detail_overview_line_%d'%i,90,545+38*i,1290,38)
    for name,index,y in (('detail_play_btn',0,615),('detail_back_btn',1,710 if episode else 805),('trailer_button',2,-500 if episode else 710)):
        widget(name,1510,y-40,330,72) # Reproduce shifted label geometry.
        widget('cinema_button_bg_%d'%index,1506,y-4,338,80)
    return ET.tostring(root,encoding='unicode')


class Geometry:
    def __init__(self,*values):self.values=values
    def x(self):return self.values[0]
    def y(self):return self.values[1]
    def width(self):return self.values[0]
    def height(self):return self.values[1]


class Widget:
    def __init__(self):self.xy=Geometry(0,0);self.wh=Geometry(1,1)
    def move(self,point):self.xy=point
    def resize(self,size):self.wh=size
    def position(self):return self.xy
    def size(self):return self.wh
    def setPadding(self,value):self.padding=value
    def setFont(self,value):self.font=value
    def setHAlign(self,value):self.halign=value
    def setVAlign(self,value):self.valign=value


class LayoutTests(unittest.TestCase):
    def test_block_shift_preserves_all_row_gaps(self):
        root=ET.fromstring(skin(1280,720))
        for node in root.iter('widget'):
            if node.get('name','').startswith('detail_overview_line_'):
                x,y=_pair=tuple(map(int,node.get('position').split(',')))
                node.set('position','%d,%d'%(x,y-100))
        plan=load()['_efl_plan'](ET.tostring(root,encoding='unicode'),1280,720)
        ys=[plan['detail_overview_line_%d'%i][1] for i in range(6)]
        self.assertTrue(all(b-a>=25 for a,b in zip(ys,ys[1:])))

    def test_geometry_at_hd_fullhd_and_sd(self):
        ns=load()
        for width,height in ((1280,720),(1920,1080),(720,576)):
            plan=ns['_efl_plan'](skin(width,height),width,height)
            x,y,w,h,ha,va,font=plan['detail_play_btn']
            self.assertEqual((x,y),(round(1506*width/1920)+max(1,round(width/1920*4)),round(611*height/1080)+max(1,round(width/1920*4))))
            self.assertEqual((ha,va),('center','center'))
            self.assertGreaterEqual(plan['detail_overview_line_0'][1],round(540*height/1080))
            self.assertNotIn('detail_overview',plan)
            for key,row in plan.items():self.assertLessEqual(row[0]+row[2],width+2)

    def test_episode_trailer_hidden_and_back_retains_compact_position(self):
        ns=load();plan=ns['_efl_plan'](skin(1920,1080,episode=True),1920,1080)
        self.assertNotIn('trailer_button',plan)
        self.assertEqual(plan['detail_back_btn'][1],710)

    def test_old_multiline_body_moves_below_heading(self):
        plan=load()['_efl_plan'](skin(1920,1080,hidden_overview=False),1920,1080)
        self.assertEqual(plan['detail_overview'][1],546)

    def test_gate_76_only_without_guessing_hardware_model(self):
        ns=load()
        for data,expected in [('distro=openatv\nversion=7.6.0\n',True),('distro=openatv\nversion=8.0.1\n',False),('distro=other\nversion=7.6\n',False)]:
            with patch('builtins.open',mock_open(read_data=data)):
                self.assertEqual(ns['_efl_image_76'](),expected)

    def test_real_widget_alignment_and_bound_callback(self):
        ns=load();ns['_efl_image_76']=lambda:True
        screen=ns['EmbyFlowDetailScreen']()
        self.assertIs(screen.onLayoutFinish[0].__self__,screen)
        screen.instance=SimpleNamespace(size=lambda:Geometry(1280,720));screen.skin=skin(1280,720)
        for key in ns['_efl_plan'](screen.skin,1280,720):screen[key]=SimpleNamespace(instance=Widget())
        enigma=ModuleType('enigma');enigma.ePoint=enigma.eSize=enigma.eRect=Geometry
        skinmod=ModuleType('skin');skinmod.parseFont=lambda x:x
        with patch.dict(sys.modules,{'enigma':enigma,'skin':skinmod}):
            with patch.object(ns['_efl_os'],'replace',Mock()):
                screen.onLayoutFinish[0]()
                screen.update_detail_focus()
        self.assertTrue(screen.focus_called)
        widget=screen['detail_play_btn'].instance
        self.assertEqual((widget.halign,widget.valign),(1,1))
        self.assertEqual(widget.padding.values,(0,0,0,0))
        self.assertEqual(screen['detail_overview_line_0'].instance.valign,0)

    def test_append_only_installer_on_exact_reported_release(self):
        source=(HERE.parent.parent/'EmbyFlowE2_2026101801.py').read_text()
        result=patch_source(source,RUNTIME)
        self.assertTrue(result.startswith(source))
        self.assertEqual(patch_source(result,RUNTIME),result)
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'plugin.py';target.write_text(source)
            install(target,RUNTIME)
            self.assertEqual(target.read_text(),result)
            self.assertEqual(next(Path(folder).glob('*.vor-atv76-layout-*')).read_text(),source)


if __name__=='__main__':unittest.main()

import ast
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
from test_ui import load_ui, Session

class StyleTests(unittest.TestCase):
    def setUp(self):
        self.ns=load_ui();self.session=Session()
        p=patch.dict(sys.modules,{'skin':self.ns['_test_skin_module']})
        p.start();self.addCleanup(p.stop)
    def choice(self,**kwargs):return self.ns['EmbyFlowDownloadChoice'](self.session,**kwargs)
    def test_no_system_dialogs_used(self):
        code=Path(__file__).with_name('ui.py').read_text()
        imports=[n.module for n in ast.walk(ast.parse(code)) if isinstance(n,ast.ImportFrom)]
        self.assertNotIn('Screens.ChoiceBox',imports)
        self.assertNotIn('Screens.MessageBox',imports)
    def test_choices_style_is_borderless_navy_cyan(self):
        dialog=self.choice(title='Filmversion auswählen',list=[('4K · 20 GiB',{'Id':'4k'})])
        root=ET.fromstring(dialog.skin)
        self.assertEqual(root.get('flags'),'wfNoBorder')
        self.assertEqual(root.get('backgroundColor'),'#FF000000')
        self.assertIn('#26DFF5',dialog.skin)
        self.assertEqual(dialog['brand_emby'].text+dialog['brand_flow'].text,'EMBYFLOW')
    def test_long_selected_filename_complete_and_wrapped(self):
        text='Film.2026.GERMAN.2160p.'+'a'*200+' — 25.42 GiB'
        dialog=self.choice(title='Filmversion',list=[(text,{'Id':'version'})])
        dialog.draw()
        self.assertIn('…',dialog['row0'].text)
        self.assertEqual(dialog['details'].text.replace('\n',''),text)
        self.assertIn('\n',dialog['details'].text)
    def test_paging_returns_exact_version(self):
        entries=[('Version %d'%i,{'Id':str(i)}) for i in range(8)]
        dialog=self.choice(title='Filmversion',list=entries)
        dialog.move(6)
        self.assertIn('Version 6',dialog['row0'].text)
        self.assertTrue(dialog['row2'].hidden)
        dialog.accept()
        self.assertEqual(dialog.result,(entries[6],))
    def test_confirmation_defaults_to_cancel(self):
        dialog=self.choice(title='Download starten?',confirmation=True,description='Größe: 25 GiB\nFrei: 100 GiB\nZiel: /media/hdd/movie/EmbyFlow',list=[('Abbrechen',False),('Herunterladen',True)])
        dialog.accept();self.assertEqual(dialog.result,(('Abbrechen',False),))
        dialog.move(1);dialog.accept()
        self.assertEqual(dialog.result,(('Herunterladen',True),))
    def test_cancel_returns_none(self):
        dialog=self.choice(title='Ziel',list=[('/media/hdd','/media/hdd')])
        dialog.cancel();self.assertEqual(dialog.result,(None,))
    def test_source_flow_uses_custom_dialog(self):
        screen=self.ns['EmbyFlowLocalDownloadScreen'](self.session,{'title':'Film'})
        screen.permission_state='granted'
        screen.events.put(('sources',({'Id':'movie'},[{'Id':'4k','Name':'4K','Size':2**30}])))
        screen.poll()
        self.assertIs(self.ns['_EFDLChoice'],self.ns['EmbyFlowDownloadChoice'])
        self.assertEqual(self.session.kwargs['title'],'Filmversion auswählen')
        dialog=self.choice(**self.session.kwargs)
        dialog.draw()
        self.assertIn('1.00 GiB',dialog['info0'].text)
    def test_single_source_uses_compact_height_and_separate_size(self):
        source={'Id':'4k','Size':8*2**30,'Container':'mkv','MediaStreams':[{'Type':'Video','Width':3840,'Codec':'hevc'}]}
        dialog=self.choice(title='Filmversion',list=[('Film.2160p.release',source)])
        dialog.draw()
        root=ET.fromstring(dialog.skin)
        width,height=map(int,root.get('size').split(','))
        self.assertEqual(width,1120)
        self.assertLess(height,600)
        self.assertIn('4K UHD',dialog['row0'].text)
        self.assertIn('8.00 GiB',dialog['info0'].text)
        self.assertIn('badge0_0',dialog)
        self.assertEqual(dialog['badge0_0'].text,'2160p')
    def test_focus_moves_with_styled_cards(self):
        dialog=self.choice(title='Ziel',list=[('/media/hdd','/media/hdd'),('/media/usb','/media/usb')])
        applied=[]
        self.ns['_efdl_style_apply']=lambda widget,name:applied.append((widget,name))
        dialog.draw();dialog.move(1)
        self.assertEqual(applied[-2][1],'normal_plain')
        self.assertEqual(applied[-1][1],'selected_plain')
        self.assertIn('USB-Speicher',dialog['row1'].text)
        self.assertIn('/media/usb',dialog['info1'].text)
    def test_dialog_widgets_remain_inside_compact_panel(self):
        for count in (0,1,2,5,8):
            dialog=self.choice(title='Filmversion',list=[('Version %d'%i,{'Id':str(i)}) for i in range(count)])
            root=ET.fromstring(dialog.skin)
            width,height=map(int,root.get('size').split(','))
            for node in root:
                x,y=map(int,node.get('position').split(','))
                w,h=map(int,node.get('size').split(','))
                self.assertLessEqual(x+w,width)
                self.assertLessEqual(y+h,height)
    def test_progress_and_completion_use_brand_skin(self):
        screen=self.ns['EmbyFlowLocalDownloadScreen'](self.session,{'title':'Film'})
        root=ET.fromstring(screen.skin)
        self.assertEqual(root.get('flags'),'wfNoBorder')
        self.assertEqual(root.get('backgroundColor'),'#FF000000')
        screen.target='/media/hdd/movie/EmbyFlow/film.mkv'
        screen.progress=(50,100);screen.poll()
        self.assertEqual(screen['progress_bar'].value,50)
        screen.events.put(('done',screen.target));screen.poll()
        self.assertEqual(screen['progress_bar'].value,100)
        self.assertIn('Schließen',screen['footer'].text)

if __name__=='__main__':unittest.main()

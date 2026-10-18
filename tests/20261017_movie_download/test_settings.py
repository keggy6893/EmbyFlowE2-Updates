import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from settings_patch import patch_settings

class Label:
    def __init__(self,text=''): self.text=text
    def setText(self,text): self.text=text
    def getText(self): return self.text
    def hide(self):pass
class Settings(dict):
    def refresh_all(self): self.ns['_efbs_refresh'](self)

class SettingsTests(unittest.TestCase):
    def setUp(self):
        source=patch_settings((Path(__file__).resolve().parents[2]/'EmbyFlowE2_2026101704.py').read_text())
        start=source.index('# EMBYFLOW_BUFFER_SCROLL_SETTINGS_V3')
        end=source.index('# Runtime status comes directly',start)
        tree=ast.parse(source[start:end])
        wanted=[]
        for node in tree.body:
            if isinstance(node,ast.FunctionDef):wanted.append(node)
            elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('_efbs_fields','_efbs_focuses','_efbs_labels') for t in node.targets):wanted.append(node)
        setting=SimpleNamespace(value=False,save=Mock())
        ns=dict(config=SimpleNamespace(embyflow=SimpleNamespace(movie_download_enabled=setting)), configfile=SimpleNamespace(save=Mock()),_efbs_old_refresh=lambda self:None, _efbs_old_toggle=Mock(),_efbs_old_save=lambda *a,**k:None,_efbs_old_target=lambda self:(0,0),_efb_save=Mock(),_efb_log=Mock())
        exec(compile(ast.Module(body=wanted,type_ignores=[]),'settings.py','exec'),ns)
        self.ns=ns;self.setting=setting
        s=Settings();s.ns=ns;s.focus=12;s._efbs_offset=0;s._efdl_enabled=False;s._efbs_enabled=False;s._efbs_test=False
        for name in ns['_efbs_fields']+('middle_help','left_help','efbs_range','account_status'):s[name]=Label()
        for i in range(6):s['efbs_label%d'%i]=Label();s['efbs_value%d'%i]=Label()
        self.screen=s
    def test_ninth_row_scrolls_in_second_column(self):
        self.screen.refresh_all()
        self.assertEqual(self.screen._efbs_offset,3)
        self.assertIn('Film-Download',self.screen['efbs_label5'].text)
        self.assertIn('AUS',self.screen['efbs_value5'].text)
        self.assertIn('/ 9',self.screen['efbs_range'].text)
        self.assertEqual(self.ns['_efbs_target'](self.screen),(688,784))
    def test_toggle_waits_for_green_save(self):
        self.ns['_efbs_toggle'](self.screen)
        self.assertTrue(self.screen._efdl_enabled)
        self.assertFalse(self.setting.value)
        self.setting.save.assert_not_called()
        self.assertTrue(self.ns['_efbs_save'](self.screen))
        self.assertTrue(self.setting.value)
        self.setting.save.assert_called_once()
        self.ns['configfile'].save.assert_called_once()
    def test_failed_previous_save_does_not_store_download(self):
        self.screen._efdl_enabled=True
        self.screen['account_status'].setText('Speichern fehlgeschlagen')
        self.assertFalse(self.ns['_efbs_save'](self.screen))
        self.assertFalse(self.setting.value)
    def test_navigation_preserves_all_options(self):
        self.screen.focus=11
        self.ns['_efbs_move'](self.screen,1)
        self.assertEqual(self.screen.focus,12)
        self.ns['_efbs_move'](self.screen,1)
        self.assertEqual(self.screen.focus,5)
        self.ns['_efbs_move'](self.screen,-1)
        self.assertEqual(self.screen.focus,12)
        self.screen.focus=2;self.screen.refresh_all()
        self.assertEqual(self.screen._efbs_offset,0)
        self.assertIn('Adaptive',self.screen['efbs_label0'].text)

if __name__=='__main__':unittest.main()

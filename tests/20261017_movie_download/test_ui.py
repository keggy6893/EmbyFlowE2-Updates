import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

class Screen(dict):
    def __init__(self,session):
        self.session=session;self.onClose=[];self.onFirstExecBegin=[];self.onLayoutFinish=[]
    def close(self,*args):
        self.result=args
        for callback in self.onClose: callback()
class Label:
    instance=None
    def __init__(self,text):self.text=text
    def setText(self,text):self.text=text
    def hide(self):self.hidden=True
    def show(self):self.hidden=False
class Timer:
    def __init__(self):self.callback=[]
    def start(self,*args):self.running=True
    def stop(self):self.running=False
class Detail(Screen):
    def __init__(self,session,data):super().__init__(session);self.data=data
class Setting:
    def __init__(self,default):self.value=default
    def save(self):pass
class Session:
    def openWithCallback(self,callback,screen,**kwargs):self.callback=callback;self.kwargs=kwargs
    def open(self,*args):self.opened=args

def load_ui():
    modules={name:types.ModuleType(name) for name in ('Components','Components.ProgressBar','skin')}
    class Progress:
        def setValue(self,value):self.value=value
    modules['Components.ProgressBar'].ProgressBar=Progress
    modules['skin'].parseColor=lambda value:value
    class TestDetail(Screen):
        def __init__(self,session,data):
            super().__init__(session);self.data=data;self.detail_focus=0
            self._trailer_enabled=data.get('trailer',True)
            self.skin='<screen><widget name="detail_back_btn" position="1510,805"/><widget name="cinema_button_bg_1" position="1506,801"/></screen>'
        def update_detail_focus(self):
            if self.detail_focus not in (0,1,2):raise ValueError('Unsupported original focus')
            self.old_focus=self.detail_focus
        def detail_ok(self):self.old_ok=self.detail_focus
        def detail_up(self):self.old_up=True
        def detail_down(self):self.old_down=True
    class Pixmap:
        instance=None
        def show(self):self.hidden=False
        def hide(self):self.hidden=True
    config=SimpleNamespace(embyflow=SimpleNamespace())
    ns=dict(Screen=Screen,Label=Label,eTimer=Timer,ActionMap=lambda *args:args,scale_skin=lambda s:s,config=config,ConfigYesNo=Setting,configfile=SimpleNamespace(save=lambda:None),EmbyFlowDetailScreen=TestDetail,Pixmap=Pixmap,sx=lambda x:x,sy=lambda y:y,_efsv_episode=lambda s:s.data.get('type')=='Episode')
    engine=types.ModuleType('local_download_engine')
    exec(compile(Path(__file__).with_name('engine.py').read_text(),'engine.py','exec'),engine.__dict__)
    engine.quota_status=lambda:dict(used=0,remaining=5,limit=5)
    ns['_efdl_engine']=engine
    with patch.dict(sys.modules,modules):
        exec(compile(Path(__file__).with_name('style_assets.py').read_text(),'style_assets.py','exec'),ns)
        exec(compile(Path(__file__).with_name('dialogs.py').read_text(),'dialogs.py','exec'),ns)
        exec(compile(Path(__file__).with_name('ui.py').read_text(),'ui.py','exec'),ns)
    ns['_test_skin_module']=modules['skin']
    return ns
class UITests(unittest.TestCase):
    def setUp(self):
        self.ns=load_ui();self.session=Session()
        self.skin_patch=patch.dict(sys.modules,{'skin':self.ns['_test_skin_module']})
        self.skin_patch.start();self.addCleanup(self.skin_patch.stop)
    def detail(self, enabled=True, **data):
        self.ns['config'].embyflow.movie_download_enabled.value=enabled
        return self.ns['EmbyFlowDetailScreen'](self.session,dict(id='film',**data))
    def test_optional_button_not_present_when_disabled(self):
        detail=self.detail(False)
        self.assertNotIn('movie_download_button',detail)
        detail.detail_down()
        self.assertTrue(detail.old_down)
    def test_button_navigation_and_ok_with_trailer(self):
        detail=self.detail()
        self.assertIn('movie_download_button',detail)
        detail.detail_down();self.assertEqual(detail.detail_focus,2)
        detail.detail_down();self.assertEqual(detail.detail_focus,3)
        detail.detail_ok()
        self.assertIs(self.session.opened[0],self.ns['EmbyFlowLocalDownloadScreen'])
        detail.detail_down();self.assertEqual(detail.detail_focus,1)
        detail.detail_ok();self.assertEqual(detail.old_ok,1)
        detail.detail_up();self.assertEqual(detail.detail_focus,3)
    def test_compact_order_without_trailer(self):
        detail=self.detail(trailer=False)
        detail.detail_down();self.assertEqual(detail.detail_focus,3)
        detail.detail_down();self.assertEqual(detail.detail_focus,1)
    def test_download_button_keeps_both_layouts_inside_screen(self):
        import xml.etree.ElementTree as ET
        for trailer, download_y, back_y in ((True,805,900),(False,710,805)):
            detail=self.detail(trailer=trailer)
            nodes={n.get('name'):n for n in ET.fromstring(detail.skin).iter('widget')}
            self.assertEqual(nodes['movie_download_button'].get('position'),'1510,%d'%download_y)
            self.assertEqual(nodes['detail_back_btn'].get('position'),'1510,%d'%back_y)
            self.assertLess(back_y+72,1080)
    def test_episode_has_download_button_but_series_container_does_not(self):
        detail=self.detail(type='Episode')
        self.assertIn('movie_download_button',detail)
        self.assertNotIn('movie_download_button',self.detail(type='Series'))
    def test_old_focus_never_receives_new_index(self):
        detail=self.detail()
        detail.detail_focus=3
        detail.update_detail_focus()
        self.assertEqual(detail.old_focus,0)
        self.assertEqual(detail.detail_focus,3)
    def test_play_still_uses_original_action(self):
        detail=self.detail()
        detail.detail_ok()
        self.assertEqual(detail.old_ok,0)
    def test_no_disk_no_start(self):
        screen=self.ns['EmbyFlowLocalDownloadScreen'](self.session,{'id':'film'})
        screen.permission_state='granted'
        self.ns['_efdl_targets']=lambda:[]
        screen.source_chosen(('4k',{'Id':'source'}))
        screen.poll()
        self.assertIn('Keine beschreibbare',screen['status'].text)
    def test_exit_cancels_worker(self):
        screen=self.ns['EmbyFlowLocalDownloadScreen'](self.session,{})
        screen.abort()
        self.assertTrue(screen.closed)
        self.assertTrue(screen.cancel.is_set())
    def test_decline_confirmation_no_transfer(self):
        screen=self.ns['EmbyFlowLocalDownloadScreen'](self.session,{})
        screen.confirmed(False)
        self.assertTrue(screen.closed)
    def test_completion_display(self):
        screen=self.ns['EmbyFlowLocalDownloadScreen'](self.session,{})
        screen.events.put(('done','/media/hdd/movie/EmbyFlow/film.mkv'))
        screen.poll()
        self.assertIn('Download abgeschlossen',screen['status'].text)
        self.assertIn('Externe Untertitel',screen['status'].text)

if __name__=='__main__':unittest.main()

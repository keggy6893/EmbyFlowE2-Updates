import ast,importlib.util,json,os,shlex,tempfile,time,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock
HERE=Path(__file__).resolve().parent
RUNTIME=(HERE/'runtime.py').read_text()
class Widget:
 def __init__(self,text=''):self.text=text;self.visible=True;self.instance=self
 def setText(self,text):self.text=text
 def show(self):self.visible=True
 def hide(self):self.visible=False
 def move(self,value):self.position=value
class Screen(dict):
 def __init__(self,session):self.session=session;self.onLayoutFinish=[];self.onClose=[]
 def close(self):
  for callback in self.onClose:callback()
class Timer:
 def __init__(self):self.callback=[];self.active=False
 def start(self,*args):self.active=True
 def stop(self):self.active=False
class SkyfallTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.movie=self.root/'James Bond 007 - Skyfall (2012).ts';self.movie.write_bytes(b'original movie')
  self.local_open=Mock();self.nav_builder=Mock(return_value=[('Start',{}),('Einstellungen',{'_direct_action_ref12':'settings'})]);self.nav_activate=Mock();self.play=Mock()
  self.ns={'Screen':Screen,'Label':Widget,'Pixmap':Widget,'eTimer':Timer,'ActionMap':lambda *a:a,'scale_skin':lambda s:s,'sx':lambda v:v,'sy':lambda v:v,'ePoint':lambda *v:v,'EmbyFlowLocalLibraryScreenV3':Obj(open_selected=self.local_open),'EmbyFlowLocalMediaScreen':Obj(play_file=self.play),'EmbyFlowE2Screen':Obj(_direct_nav_build_entries_ref12=self.nav_builder,_direct_nav_activate_ref12=self.nav_activate),'_embyflow_nav_groups_v30_transform':lambda rows:rows,'get_emby_auth':Mock(return_value=(None,None,None)),'_embyflow_v21b_probe_local_file':Mock(return_value={'runtime_ticks':10000000*60*143}),'embyflow_http_get':Mock(),'AUTH_HEADER':'auth','embyflow_decode_image_to_widget':Mock()}
  exec(RUNTIME,self.ns);self.ns['_ELS_PATH']=str(self.movie);self.ns['_ELS_CACHE']=str(self.root/'metadata.json');self.ns['_ELS_ART']=str(self.root/'art')
  self.session=Obj(open=Mock());self.screen=self.ns['EmbyFlowLocalSkyfallDetail'](self.session)
 def test_original_opens_detail_while_theme_and_other_files_keep_previous_behavior(self):
  p=Obj(scan_loading=False,selected_entry=lambda:{'path':str(self.movie)},session=self.session)
  self.ns['_els_open'](p);self.session.open.assert_called_once_with(self.ns['EmbyFlowLocalSkyfallDetail'],{'path':str(self.movie)})
  p.selected_entry=lambda:{'path':str(self.root/'Skyfall-Theme-Test.ts')};self.ns['_els_open'](p);self.local_open.assert_called_once_with(p)
 def test_original_play_no_copy_and_no_network_stream(self):
  self.screen.play_local();self.play.assert_called_once_with(self.screen,str(self.movie));self.assertEqual(self.movie.read_bytes(),b'original movie');self.ns['embyflow_http_get'].assert_not_called()
 def test_dashboard_uses_original_usb_hdd_screen(self):
  source=(HERE.parents[1]/'EmbyFlowE2_2026102502.py').read_text();tree=ast.parse(source)
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_embyflow_v17_open_local_media_dashboard')
  screen=object();ns={'EmbyFlowLocalSourcesScreenV17':screen};exec(ast.get_source_segment(source,node),ns)
  ns['_embyflow_v17_open_local_media_dashboard'](Obj(session=self.session))
  self.session.open.assert_called_once_with(screen)
  cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EmbyFlowLocalSourcesScreenV17')
  skin=ast.get_source_segment(source,cls)
  self.assertIn('Meine Quellen',skin);self.assertIn('Quellen verwalten',skin)
 def test_detail_has_synopsis_offline_and_measured_runtime(self):
  s=self.screen;s.render_local();self.assertIn('MI6',s['overview'].text)
  s.load_local();s.poll_local();self.assertIn('143 Min.',s['meta'].text);self.assertEqual(s.data['directors'],['Sam Mendes']);self.assertTrue(Path(self.ns['_ELS_CACHE']).exists())
 def test_metadata_remains_offline_even_when_server_account_is_available(self):
  self.ns['get_emby_auth'].return_value=('https://unused.invalid','test-token','test-user')
  self.screen.load_local();self.screen.poll_local()
  self.ns['get_emby_auth'].assert_not_called();self.ns['embyflow_http_get'].assert_not_called()
 def test_exact_movie_metadata_match_not_theme_or_wrong_year(self):
  fn=self.ns['_els_metadata'];self.assertIsNone(fn([{'Name':'Skyfall','ProductionYear':2024,'Type':'Movie'}]))
  correct={'Name':'James Bond 007 - Skyfall','ProductionYear':2012,'Type':'Movie'};self.assertEqual(fn([correct]),correct)
 def test_navigation_adds_one_entry_and_opens_only_skyfall(self):
  fn=self.ns['_els_nav'];p=Obj(open_local_media_menu=Mock(),session=self.session)
  rows=fn(p);self.assertEqual(sum(x[0]=='Emby Local' for x in rows),1)
  self.nav_builder.return_value=rows;self.assertEqual(fn(p),rows)
  p.direct_nav_entries_ref12=rows;p.direct_nav_cursor_ref12=1;self.ns['_els_activate'](p);p.open_local_media_menu.assert_called_once_with();self.session.open.assert_not_called()
 def test_close_stops_timer_and_no_ready_updates_are_applied(self):
  self.screen.timer_local.start();self.screen.close();self.assertFalse(self.screen.timer_local.active);self.assertTrue(self.screen.closed_local)
 def test_valid_skin_and_focus_button_visibility(self):
  root=ET.fromstring(self.screen.skin);widgets={n.attrib['name']:n for n in root.findall('widget')};self.assertEqual(root.attrib['size'],'1920,1080');self.assertEqual(widgets['focus'].attrib['transparent'],'1')
  self.screen.toggle_local();self.assertEqual(self.screen['focus'].position,(1485,775));self.screen.accept_local();self.assertTrue(self.screen.closed_local)
 def test_real_local_player_uses_service_one_for_ts(self):
  source=(HERE.parents[1]/'EmbyFlowE2_2026102502.py').read_text();tree=ast.parse(source)
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_embyflow_v21b_local_play_file')
  class Reference:
   def __init__(self,kind,flags,path):self.type=kind;self.path=path
   def setName(self,name):pass
  opened=Mock()
  ns={'os':os,'time':time,'uuid4':lambda:'session','_embyflow_v21b_probe_local_file':lambda p:{'runtime_ticks':123,'media_streams':[]},'_embyflow_v21b_first_stream':lambda *a:{},'_embyflow_v21b_int':lambda v,f=0:int(v or f),'embyflow_local_clean_title':lambda p:'Skyfall','get_embyflow_local_resume':lambda p:(0,0),'eServiceReference':Reference,'_open_embyflow_player_now':opened,'STREAM_SERVICE_TYPE':4097}
  exec(ast.get_source_segment(source,node),ns);ns['_embyflow_v21b_local_play_file'](self.screen,str(self.movie))
  self.assertEqual(opened.call_args.args[1].type,1);self.assertEqual(opened.call_args.args[3],str(self.movie));self.assertTrue(opened.call_args.args[4]['local_file'])
if __name__=='__main__':unittest.main()

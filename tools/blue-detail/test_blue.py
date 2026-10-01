import ast,re,sys,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace as N
class BlueTests(unittest.TestCase):
 def setUp(self):
  ns={};tree=ast.parse(Path(sys.argv[1]).read_text())
  nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('_embyflow_blue_detail_skin','_embyflow_blue_detail_poll')]
  self.called=[]
  ns['_BLUE_DETAIL_POLL']=lambda s:None
  ns['_embyflow_blue_detail_apply']=lambda s:self.called.append('blue')
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'blue','exec'),ns);self.ns=ns
 def test_actual_detail_skin_preserves_text_and_lines(self):
  t=ast.parse(Path(sys.argv[2]).read_text());cls=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=='EmbyFlowDetailScreen')
  skin=next(n.value for n in ast.walk(cls) if isinstance(n,ast.Constant) and isinstance(n.value,str) and '<screen name="EmbyFlowDetailScreen"' in n.value)
  skin=re.sub(r'%[sd]','',skin)
  root=ET.fromstring(skin);before=[n.attrib for n in root if n.get('text') is not None]
  after=ET.fromstring(self.ns['_embyflow_blue_detail_skin'](skin,1920,1080,'96,80','1728,920'))
  self.assertEqual(before,[n.attrib for n in after if n.get('text') is not None])
  self.assertFalse(any(n.tag=='eLabel' and n.get('size') in ('1920,1080','1728,920') for n in after))
  background=next(n for n in after if n.get('name')=='detail_blue_background')
  self.assertEqual(background.get('backgroundColor'),'#0C1827')
  self.assertEqual(background.get('transparent'),'0')
 def test_poster_is_preserved(self):
  s='<screen><widget name="skyfall_theme_poster" position="1490,560" size="270,405" zPosition="36" /></screen>'
  r=ET.fromstring(self.ns['_embyflow_blue_detail_skin'](s,1920,1080,'96,80','1728,920'))
  self.assertEqual(r[0].get('position'),'1490,560');self.assertEqual(r[0].get('zPosition'),'36')
 def test_video_revealed(self):
  hidden=[]
  class Screen(dict):pass
  s=Screen(detail_blue_background=N(hide=lambda:hidden.append(True)))
  s._fallback_result={'video':'url'};s._fallback_theme_active=True
  self.ns['_embyflow_blue_detail_poll'](s)
  self.assertEqual(hidden,[True]);self.assertEqual(self.called,[])
 def test_song_keeps_blue(self):
  s=N(_fallback_result={'song':'url'},_fallback_theme_active=True)
  self.ns['_embyflow_blue_detail_poll'](s);self.assertEqual(self.called,['blue'])
 def test_openatv_layout_callbacks_are_bound_methods(self):
  tree=ast.parse(Path(sys.argv[1]).read_text())
  funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
  class Screen(dict):
   def close(self): pass
  def base_init(screen,session,data):
   screen.skin='<screen><widget name="skyfall_theme_poster" position="1490,560" size="270,405" /></screen>'
   screen.onLayoutFinish=[]
   screen.onShow=[]
   screen._skyfall_local_theme_enabled=bool(data.get('video'))
  ns=dict(_BLUE_DETAIL_INIT=base_init,sx=lambda x:x,sy=lambda x:x,Label=lambda text:None)
  exec(compile(ast.Module(body=funcs,type_ignores=[]),'blue','exec'),ns)
  Screen._blue_detail_apply=ns['_embyflow_blue_detail_apply']
  Screen._blue_detail_return=ns['_embyflow_blue_detail_return']
  Screen._blue_detail_hide=ns.get('_embyflow_blue_detail_hide',lambda self:None)
  for video in (False,True):
   screen=Screen();ns['_embyflow_blue_detail_init'](screen,None,{'video':video})
   self.assertTrue(screen.onLayoutFinish)
   for callback in screen.onLayoutFinish:
    # Mirrors openATV Screen.createGUIScreen's distinction: other types
    # are passed to exec(), which rejects anonymous function objects.
    self.assertIsInstance(callback,type(screen.close))
 def test_return_restores_blue_only_when_theme_is_stopped(self):
  tree=ast.parse(Path(sys.argv[1]).read_text())
  f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_embyflow_blue_detail_return')
  ns={};exec(compile(ast.Module(body=[f],type_ignores=[]),'return','exec'),ns)
  for local,remote,expected in ((False,False,1),(True,False,0),(False,True,0)):
   calls=[]
   screen=N(_skyfall_local_theme_active=local,_fallback_theme_active=remote,_blue_detail_apply=lambda:calls.append(True))
   ns['_embyflow_blue_detail_return'](screen)
   self.assertEqual(len(calls),expected)
class TvReturnTests(unittest.TestCase):
 def setUp(self):
  tree=ast.parse(Path(sys.argv[1]).read_text())
  funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name.startswith('_embyflow_tv_return')]
  self.timers=[];self.logs=[]
  owner=self
  class Timer:
   def __init__(self): self.callback=[];owner.timers.append(self)
   def start(self,ms,once): self.delay=ms
  self.ns=dict(eTimer=Timer,_TV_RETURN_TIMERS=[],_TV_RETURN_MAIN=lambda session,**kw:None,_TV_RETURN_ROOT_INIT=lambda self,session,*a,**kw:None)
  exec(compile(ast.Module(body=funcs,type_ignores=[]),'tvreturn','exec'),self.ns)
  self.ns['_embyflow_tv_return_log']=self.logs.append
 def test_captures_before_main_and_restores_only_when_stopped(self):
  for current in (None,'another-service'):
   played=[];state=['original-tv']
   session=N(nav=N(getCurrentlyPlayingServiceReference=lambda:state[0],playService=played.append))
   self.ns['_embyflow_tv_return_main'](session)
   self.assertEqual(session._embyflow_entry_service,'original-tv')
   root=N(session=session,_embyflow_entry_service=session._embyflow_entry_service)
   state[0]=current
   self.ns['_embyflow_tv_return_close'](root)
   self.assertEqual(self.timers[-1].delay,350)
   self.assertEqual(played,[])
   self.timers[-1].callback[0]()
   self.assertEqual(played,['original-tv'] if current is None else [])
   self.assertEqual(self.ns['_TV_RETURN_TIMERS'],[])
 def test_no_previous_service_does_not_start_arbitrary_channel(self):
  self.ns['_embyflow_tv_return_close'](N(session=N(),_embyflow_entry_service=None))
  self.assertEqual(self.timers,[])
 def test_root_close_hook_is_bound_method(self):
  class Root:
   def close(self):pass
  Root._tv_return_close=self.ns['_embyflow_tv_return_close']
  root=Root();root.onClose=[]
  self.ns['_embyflow_tv_return_root_init'](root,N(_embyflow_entry_service='tv'))
  self.assertIsInstance(root.onClose[0],type(root.close))
  self.assertEqual(root._embyflow_entry_service,'tv')
class ExitTests(unittest.TestCase):
 def test_exit_bypasses_cast_panel_and_retains_stop_actions(self):
  from build_blue import build
  source=Path(sys.argv[2]).read_bytes()
  result=build(source,Path(sys.argv[1]).read_text()+'\n\n'+Path(__file__).with_name('tv_mute_layer.py').read_text()).decode()
  tree=ast.parse(result)
  player=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EmbyFlowMoviePlayer')
  init=next(n for n in player.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
  mappings=[n for n in ast.walk(init) if isinstance(n,ast.Dict)]
  actions=next(n for n in mappings if any(isinstance(k,ast.Constant) and k.value=='leavePlayer' for k in n.keys))
  values={k.value:v for k,v in zip(actions.keys,actions.values) if isinstance(k,ast.Constant)}
  for key in ('cancel','red','stop','leavePlayer'):
   self.assertIsInstance(values[key],ast.Attribute)
   self.assertEqual(values[key].attr,'leave_player')
if __name__=='__main__':unittest.main(argv=[sys.argv[0]])

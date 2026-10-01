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
   screen._skyfall_local_theme_enabled=bool(data.get('video'))
  ns=dict(_BLUE_DETAIL_INIT=base_init,sx=lambda x:x,sy=lambda x:x,Label=lambda text:None)
  exec(compile(ast.Module(body=funcs,type_ignores=[]),'blue','exec'),ns)
  Screen._blue_detail_apply=ns['_embyflow_blue_detail_apply']
  Screen._blue_detail_hide=ns.get('_embyflow_blue_detail_hide',lambda self:None)
  for video in (False,True):
   screen=Screen();ns['_embyflow_blue_detail_init'](screen,None,{'video':video})
   self.assertTrue(screen.onLayoutFinish)
   for callback in screen.onLayoutFinish:
    # Mirrors openATV Screen.createGUIScreen's distinction: other types
    # are passed to exec(), which rejects anonymous function objects.
    self.assertIsInstance(callback,type(screen.close))
class ExitTests(unittest.TestCase):
 def test_exit_bypasses_cast_panel_and_retains_stop_actions(self):
  from build_blue import build
  source=Path(sys.argv[2]).read_bytes()
  result=build(source,Path(sys.argv[1]).read_text()).decode()
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

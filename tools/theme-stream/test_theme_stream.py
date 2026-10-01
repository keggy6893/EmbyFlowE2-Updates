import ast, sys, unittest
from types import SimpleNamespace as N
from urllib.parse import urlsplit, parse_qs
from pathlib import Path
from build_theme_stream import build
class ThemeTest(unittest.TestCase):
 def setUp(self):
  data=build(Path(sys.argv[1]).read_bytes())
  tree=ast.parse(data)
  fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_embyflow_theme_poll_lookup_v1')
  self.played=[]; self.logs=[]
  class Ref:
   def __init__(s,kind,unused,url): s.kind=kind; s.url=url
   def setName(s,name): pass
  ns=dict(get_emby_auth=lambda:('http://server:8096/','secret&key','user'),
   _embyflow_theme_selected_item_v1=lambda s:{'Id':'film'},
   eServiceReference=Ref,STREAM_SERVICE_TYPE=4097,
   _embyflow_theme_volume_play=lambda s,r:self.played.append(r),
   _embyflow_theme_log_v1=self.logs.append,
   config=N(embyflow=N(theme_volume=N(value='5'))))
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'theme','exec'),ns)
  self.poll=ns[fn.name]
  self.screen=N(_theme_lookup_result_v1={'generation':1,'owner_id':'film','theme':{'Id':'158158'}},
   _theme_generation_v1=1,session=N(nav=N(getCurrentlyPlayingServiceReference=lambda:None)))
 def test_static_playback_and_private_log(self):
  self.poll(self.screen)
  ref=self.played[0]; url=urlsplit(ref.url)
  self.assertEqual(ref.kind,4097)
  self.assertEqual(url.path,'/Videos/158158/stream')
  self.assertEqual(parse_qs(url.query)['api_key'],['secret&key'])
  self.assertEqual(parse_qs(url.query)['static'],['True'])
  self.assertNotIn('secret',''.join(self.logs)); self.assertIn('volume_limit=5',self.logs[0])
 def test_stale_selection_does_not_start(self):
  self.screen._theme_lookup_result_v1['owner_id']='other'
  self.poll(self.screen); self.assertEqual(self.played,[])
 def test_fallback_remains_external(self):
  self.screen._theme_lookup_result_v1.update(theme={},theme_url='https://fallback/theme.mp3')
  self.poll(self.screen); self.assertEqual(self.played[0].url,'https://fallback/theme.mp3')
if __name__=='__main__': unittest.main(argv=[sys.argv[0]])

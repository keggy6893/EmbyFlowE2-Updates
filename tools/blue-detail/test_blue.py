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
  self.assertTrue(any(n.get('name')=='detail_blue_gradient' for n in after))
 def test_poster_is_preserved(self):
  s='<screen><widget name="skyfall_theme_poster" position="1490,560" size="270,405" zPosition="36" /></screen>'
  r=ET.fromstring(self.ns['_embyflow_blue_detail_skin'](s,1920,1080,'96,80','1728,920'))
  self.assertEqual(r[0].get('position'),'1490,560');self.assertEqual(r[0].get('zPosition'),'36')
 def test_video_revealed(self):
  hidden=[]
  class Screen(dict):pass
  s=Screen(detail_blue_gradient=N(hide=lambda:hidden.append(True)))
  s._fallback_result={'video':'url'};s._fallback_theme_active=True
  self.ns['_embyflow_blue_detail_poll'](s)
  self.assertEqual(hidden,[True]);self.assertEqual(self.called,[])
 def test_song_keeps_blue(self):
  s=N(_fallback_result={'song':'url'},_fallback_theme_active=True)
  self.ns['_embyflow_blue_detail_poll'](s);self.assertEqual(self.called,['blue'])
if __name__=='__main__':unittest.main(argv=[sys.argv[0]])

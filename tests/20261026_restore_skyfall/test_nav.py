import ast,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
TEXT=(HERE/'runtime.py').read_text();RUNTIME=TEXT[TEXT.index('# EMBYFLOW_LOCAL_SKYFALL_ASYNC_NAV_V1_BEGIN'):TEXT.index('# EMBYFLOW_LOCAL_SKYFALL_ASYNC_NAV_V1_END')+len('# EMBYFLOW_LOCAL_SKYFALL_ASYNC_NAV_V1_END')]
SOURCE=(HERE.parents[1]/'EmbyFlowE2_2026102502.py').read_text();TREE=ast.parse(SOURCE)
class NavTests(unittest.TestCase):
 def setUp(self):
  self.ns={'_embyflow_nav_groups_v30_transform':lambda rows:list(rows),'embyflow_collection_include_types':lambda t:'Movie'}
  for name in ('_embyflow_navfix_v29_entries','_embyflow_nav_groups_v30_v29_entries'):
   node=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name==name);exec(ast.get_source_segment(SOURCE,node),self.ns)
  self.ns['_EMBYFLOW_NAV_GROUPS_V30_PREV_V29_ENTRIES']=self.ns['_embyflow_navfix_v29_entries']
  self.views=[{'id':'m','name':'Filme','type':'movies'}]
 def test_original_background_rebuild_loses_local_entry(self):
  rows=self.ns['_embyflow_nav_groups_v30_v29_entries'](self.views);self.assertFalse(any(r[0]=='Emby Local' for r in rows))
 def test_fixed_background_rebuild_preserves_local(self):
  exec(RUNTIME,self.ns);rows=self.ns['_embyflow_nav_groups_v30_v29_entries'](self.views);self.assertEqual(sum(r[0]=='Emby Local' for r in rows),1);self.assertEqual(rows[-2][0],'Emby Local')
 def test_repeated_rebuilds_and_parent_group_changes_do_not_duplicate(self):
  exec(RUNTIME,self.ns);fn=self.ns['_embyflow_nav_groups_v30_transform'];rows=self.ns['_embyflow_nav_groups_v30_v29_entries'](self.views)
  for _ in range(6):rows=fn(rows)
  self.assertEqual(sum(r[0]=='Emby Local' for r in rows),1)
 def test_wishes_and_downloads_preserved(self):
  exec(RUNTIME,self.ns);rows=[('Downloads',{'_direct_action_ref12':'downloads'}),('Medienwuensche',{'_direct_action_ref12':'wishes'}),('Einstellungen',{'_direct_action_ref12':'settings'})];result=self.ns['_embyflow_nav_groups_v30_transform'](rows);self.assertEqual(result[:2],rows[:2]);self.assertEqual(result[-1],rows[-1])
if __name__=='__main__':unittest.main()

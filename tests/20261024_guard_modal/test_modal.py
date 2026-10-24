import ast,threading,unittest
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock
HERE=Path(__file__).resolve().parent
BASE=(HERE.parents[1]/'EmbyFlowE2_2026102401.py').read_text()
NODE=next(n for n in ast.parse(BASE).body if isinstance(n,ast.FunctionDef) and n.name=='_efguard_gui_tick')
ORIGINAL=ast.get_source_segment(BASE,NODE)
FIXED=(HERE/'runtime.py').read_text()
class ModalTests(unittest.TestCase):
 def namespace(self,fixed=True):
  dialog=type('EmbyFlowMoviePlayer',(),{'__module__':'plugin'})()
  session=Obj(current_dialog=dialog,dialog_stack=[],in_exec=False,open=Mock(side_effect=RuntimeError('Modal open are allowed only from a screen which is modal!')))
  ns={'__name__':'plugin','_efguard_gui_session':session,'_efguard_notice':'Stream unterbrochen','_efguard_gui_timer':Mock(),'_efguard_lock':threading.Lock(),'MessageBox':Obj(TYPE_INFO=1)}
  exec(FIXED if fixed else ORIGINAL,ns);return ns,session
 def test_original_reproduces_exact_crash(self):
  ns,session=self.namespace(False)
  with self.assertRaisesRegex(RuntimeError,'Modal open'):ns['_efguard_gui_tick']()
 def test_nonexecuting_modal_defers_without_losing_notice(self):
  ns,s=self.namespace();ns['_efguard_gui_tick']();s.open.assert_not_called();self.assertEqual(ns['_efguard_notice'],'Stream unterbrochen')
 def test_later_executing_dialog_shows_once(self):
  ns,s=self.namespace();ns['_efguard_gui_tick']();s.in_exec=True;s.open.side_effect=None;ns['_efguard_gui_tick']();ns['_efguard_gui_tick']();s.open.assert_called_once();self.assertIsNone(ns['_efguard_notice'])
 def test_race_during_open_cannot_crash_and_preserves_notice(self):
  ns,s=self.namespace();s.in_exec=True;ns['_efguard_gui_tick']();self.assertEqual(ns['_efguard_notice'],'Stream unterbrochen')
 def test_newer_notice_not_overwritten_on_failure(self):
  ns,s=self.namespace();s.in_exec=True
  def fail(*a,**k):ns['_efguard_notice']='Neuer Hinweis';raise RuntimeError('modal')
  s.open.side_effect=fail;ns['_efguard_gui_tick']();self.assertEqual(ns['_efguard_notice'],'Neuer Hinweis')
 def test_unrelated_screen_stops_timer(self):
  ns,s=self.namespace();s.current_dialog=Obj();ns['_efguard_gui_tick']();ns['_efguard_gui_timer'].stop.assert_called_once();self.assertIsNone(ns['_efguard_gui_session'])
 def test_nested_plugin_dialog_is_recognized(self):
  ns,s=self.namespace();plugin=s.current_dialog;s.current_dialog=Obj();s.dialog_stack=[(plugin,False)];ns['_efguard_gui_tick']();ns['_efguard_gui_timer'].stop.assert_not_called()
 def test_no_session_is_noop(self):
  ns,s=self.namespace();ns['_efguard_gui_session']=None;ns['_efguard_gui_tick']();s.open.assert_not_called()
 def test_only_notification_tick_changes_in_candidate(self):
  lines=BASE.splitlines(True);result=''.join(lines[:NODE.lineno-1])+FIXED+'\n'+''.join(lines[NODE.end_lineno:]);compile(result,'plugin.py','exec')
  before=ast.parse(BASE);after=ast.parse(result)
  for tree in (before,after):tree.body=[n for n in tree.body if getattr(n,'name',None)!='_efguard_gui_tick']
  self.assertEqual(ast.dump(before),ast.dump(after))
 def test_release_contains_exact_fixed_timer(self):
  source=(HERE.parents[1]/'EmbyFlowE2_2026102402.py').read_text()
  node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_efguard_gui_tick')
  self.assertEqual(ast.dump(node),ast.dump(ast.parse(FIXED).body[0]))
 def test_release_changes_only_timer_and_identity(self):
  updated=(HERE.parents[1]/'EmbyFlowE2_2026102402.py').read_text()
  trees=[ast.parse(x) for x in (BASE,updated)]
  names={'PLUGIN_VERSION','PLUGIN_BUILD_DATE','PLUGIN_UPDATE_BUILD','PLUGIN_UPDATE_CHANGELOG'}
  for tree in trees:
   tree.body=[n for n in tree.body if getattr(n,'name',None)!='_efguard_gui_tick' and not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
  self.assertEqual(ast.dump(trees[0]),ast.dump(trees[1]))
if __name__=='__main__':unittest.main()

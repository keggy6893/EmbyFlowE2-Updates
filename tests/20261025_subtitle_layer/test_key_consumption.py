import unittest
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock
import test_local_subtitles as fixtures
OLD=(Path(__file__).parents[1]/'20261025_local_subtitles_v2/runtime.py').read_text()
NEW=(Path(__file__).parent/'runtime.py').read_text()
# Actual Enigma2 contract: ActionMap.action maps None to 1, otherwise passes
# the result through. ePython::call treats a non-integer Python result as 0.
# eActionMap snapshots callbacks before invocation; 0 executes the next queued
# binding, even if opening a modal screen has unbound its parent's ActionMaps.
def dispatch_key(open_handler, queued_pause):
    response=open_handler()
    action_result=1 if response is None else response
    native_result=int(action_result) if isinstance(action_result,int) else 0
    if native_result==0:
        queued_pause()
    return native_result

class KeyTests(unittest.TestCase):
 def player(self,runtime):
  p,i,ns,*_=fixtures.Tests().setup_player()
  # Re-evaluate runtime with fresh before handlers, retaining the fixture's
  # ownership, native inventory and widgets.
  cls=type('Fresh',(),{'open_subtitle_selection':Mock(),'subtitle_selection_finished':Mock()})
  ns['EmbyFlowMoviePlayer']=cls;exec(runtime,ns)
  p.session.openWithCallback.return_value=object()
  return p,lambda:ns['_eflu_open'](p)
 def test_previous_screen_return_reproduces_unintended_pause(self):
  p,handler=self.player(OLD);pause=Mock()
  self.assertEqual(dispatch_key(handler,pause),0);pause.assert_called_once()
  p.session.openWithCallback.assert_called_once()
 def test_fixed_open_consumes_key_and_prevents_queued_pause(self):
  p,handler=self.player(NEW);pause=Mock()
  self.assertEqual(dispatch_key(handler,pause),1);pause.assert_not_called()
  p.session.openWithCallback.assert_called_once()
 def test_open_does_not_activate_any_subtitle_or_touch_service(self):
  p,handler=self.player(NEW);service=p.session.nav.getCurrentService();interface=service.subtitle()
  self.assertEqual(handler(),1);interface.enableSubtitles.assert_not_called();interface.disableSubtitles.assert_not_called()
 def test_none_return_contract_also_consumes_key(self):
  pause=Mock();self.assertEqual(dispatch_key(lambda:None,pause),1);pause.assert_not_called()
 def test_empty_inventory_still_consumes_key(self):
  p,handler=self.player(NEW);p.session.nav.getCurrentService().subtitle().getSubtitleList.return_value=[]
  pause=Mock();self.assertEqual(dispatch_key(handler,pause),1);pause.assert_not_called()
  self.assertEqual(len(p.session.openWithCallback.call_args.kwargs['entries']),1)
if __name__=='__main__':unittest.main()

import sys,types,unittest
from pathlib import Path
class Control:
 def __init__(self,muted=False):self.muted=muted;self.events=[]
 def isMuted(self):return self.muted
 def volumeMute(self):self.muted=True;self.events.append('mute')
 def volumeUnMute(self):self.muted=False;self.events.append('unmute')
class Timer:
 def __init__(self):self.callback=[];self.active=False
 def start(self,ms,once):self.active=True
 def stop(self):self.active=False
class Tests(unittest.TestCase):
 def setup(self,muted=False):
  self.c=Control(muted)
  sys.modules['enigma']=types.SimpleNamespace(eDVBVolumecontrol=types.SimpleNamespace(getInstance=lambda:self.c))
  self.session=types.SimpleNamespace(dialog_stack=[],current_dialog=None,nav=types.SimpleNamespace(getCurrentlyPlayingServiceReference=lambda:None,playService=lambda *a,**kw:None))
  self.ns=dict(__name__='plugin_under_test',eTimer=Timer,main=lambda s:None,_embyflow_theme_volume_play=lambda s,r:None,_open_embyflow_player_now=lambda s,*a:None)
  exec(Path(sys.argv[1]).read_text(),self.ns)
  self.screen=type('EmbyFlowScreen',(),{'__module__':'plugin_under_test'})()
  self.screen.session=self.session
  self.ns['_LOCAL_TV_MUTE_MAIN']=lambda s:setattr(s,'current_dialog',self.screen)
  self.ns['main'](self.session)
  return self.session._embyflow_local_tv_mute
 def test_entry_mute_and_cancel_restore_both_original_states(self):
  for original in (False,True):
   state=self.setup(original);self.assertTrue(self.c.muted)
   self.session.current_dialog=None;state.check()
   self.assertEqual(self.c.muted,original);self.assertIsNone(self.session._embyflow_local_tv_mute)
 def test_external_dialog_above_plugin_keeps_state(self):
  state=self.setup();self.session.dialog_stack=[(self.screen,True)]
  self.session.current_dialog=object();state.check()
  self.assertFalse(state.finished);self.assertTrue(self.c.muted)
 def test_theme_switch_happens_before_unmute(self):
  state=self.setup(True)
  def play(screen,ref):
   self.assertTrue(self.c.muted);self.c.events.append('theme-start');return 0
  self.ns['_LOCAL_TV_MUTE_THEME_PLAY']=play
  self.assertEqual(self.ns['_embyflow_theme_volume_play'](self.screen,'theme'),0)
  self.assertFalse(self.c.muted);self.assertEqual(self.c.events[-2:],['theme-start','unmute'])
  state.finish();self.assertTrue(self.c.muted)
 def test_movie_launcher_stops_tv_before_unmute(self):
  self.setup()
  def launch(session,*args):self.assertTrue(self.c.muted);self.c.events.append('tv-stopped')
  self.ns['_LOCAL_TV_MUTE_OPEN_PLAYER']=launch
  self.ns['_open_embyflow_player_now'](self.session,'movie')
  self.assertEqual(self.c.events[-2:],['tv-stopped','unmute'])
 def test_entry_failure_restores_volume(self):
  self.setup();self.session._embyflow_local_tv_mute.finish()
  def fail(s):raise RuntimeError('failure')
  self.ns['_LOCAL_TV_MUTE_MAIN']=fail
  with self.assertRaises(RuntimeError):self.ns['main'](self.session)
  self.assertFalse(self.c.muted);self.assertIsNone(self.session._embyflow_local_tv_mute)
if __name__=='__main__':unittest.main(argv=[sys.argv[0]])

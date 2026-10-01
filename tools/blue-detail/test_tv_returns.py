import types,sys,unittest
from pathlib import Path
class Ref:
 def __init__(self,name):self.name=name
 def toString(self):return self.name
class Timer:
 def __init__(self):self.callback=[]
 def start(self,*a):pass
 def stop(self):pass
class Control:
 def __init__(self,muted=False):self.muted=muted
 def isMuted(self):return self.muted
 def volumeMute(self):self.muted=True
 def volumeUnMute(self):self.muted=False
class Test(unittest.TestCase):
 def setup(self,original=False):
  c=Control(original);tv=Ref('tv');theme=Ref('theme');events=[]
  class Nav:
   def __init__(self):self.current=tv
   def getCurrentlyPlayingServiceReference(self):return self.current
   def playService(self,ref,*a,**kw):events.append((ref.name,c.muted));self.current=ref;return 0
  nav=Nav();screen=type('Grid',(),{'__module__':'plugin_test'})()
  session=types.SimpleNamespace(nav=nav,current_dialog=screen,dialog_stack=[])
  sys.modules['enigma']=types.SimpleNamespace(eDVBVolumecontrol=types.SimpleNamespace(getInstance=lambda:c))
  ns=dict(__name__='plugin_test',eTimer=Timer,main=lambda s:None,_embyflow_theme_volume_play=lambda *a:None,_open_embyflow_player_now=lambda *a:None)
  exec(Path(sys.argv[1]).read_text(),ns)
  state=ns['_EmbyFlowLocalTvMute'](session);session._embyflow_local_tv_mute=state
  return c,tv,theme,events,nav,session,state
 def test_theme_to_tv_mutes_before_tv_starts(self):
  c,tv,theme,events,nav,session,state=self.setup()
  nav.playService(theme);state.release_for_media();self.assertFalse(c.muted)
  nav.playService(tv);self.assertTrue(c.muted);self.assertEqual(events[-1],('tv',True))
 def test_missing_theme_cannot_unmute_tv(self):
  c,tv,theme,events,nav,session,state=self.setup()
  state.release_for_media();self.assertTrue(c.muted)
 def test_poll_remutes_tv_after_external_unmute(self):
  c,tv,theme,events,nav,session,state=self.setup()
  c.volumeUnMute();state.check();self.assertTrue(c.muted)
 def test_leave_restores_state_and_removes_navigation_hook(self):
  for original in (False,True):
   c,tv,theme,events,nav,session,state=self.setup(original)
   nav.playService(theme);state.release_for_media()
   session.current_dialog=object();state.check()
   self.assertTrue(state.finished);self.assertEqual(c.muted,original)
   self.assertEqual(nav.playService,state.original_play_service)
   nav.playService(tv);self.assertEqual(c.muted,original)
if __name__=='__main__':unittest.main(argv=[sys.argv[0]])

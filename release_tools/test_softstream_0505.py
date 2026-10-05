from pathlib import Path
import ast,types,unittest
from test_server_guard_0503 import GuardTests,ROOT

class Ref:
 def __init__(self,url):self.url=url
 def getPath(self):return self.url
 def toString(self):return self.url
class Timer:
 def __init__(self):self.callback=[];self.active=False
 def start(self,*args):self.active=True
 def stop(self):self.active=False
class Nav:
 def __init__(self):self.event=[];self.current=None;self.plays=[];self.stops=0;self.result=0
 def playService(self,ref,*args,**kwargs):
  self.current=ref;self.plays.append(ref);return self.result
 def getCurrentlyPlayingServiceReference(self):return self.current
 def stopService(self):self.stops+=1;self.current=None
class Player:
 def __init__(self,session):self.session=session

class PlayerTests(GuardTests):
 def setUp(self):
  super().setUp()
  self.nav=Nav();self.owner=types.SimpleNamespace(duration_ticks=1000,current_position_ticks=lambda:1000)
  session=types.SimpleNamespace(nav=self.nav,current_dialog=self.owner)
  self.env.update(eTimer=Timer,iPlayableService=types.SimpleNamespace(evTuneFailed=1,evEOF=2),
                  EmbyFlowMoviePlayer=type('Player',(Player,),{}),_efguard_gui_session=session)
  source=(ROOT/'EmbyFlowE2_Softstream_20261005_0505.py').read_text();tree=ast.parse(source)
  message=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_efguard_message')
  exec(ast.get_source_segment(source,message),self.env)
  exec((ROOT/'release_tools/softstream_0505.inc.py').read_text(),self.env)
 def play(self,url='https://emby.test/Videos/1/stream.mkv'):
  return self.env['_efguard_play_service'](self.nav,Ref(url))
 def block(self):
  self.status=403
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.get()
 def test_stream_start_is_blocked_without_extra_http(self):
  self.block();calls=len(self.calls)
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.play()
  self.assertEqual(self.nav.plays,[]);self.assertEqual(len(self.calls),calls)
 def test_live_stream_stopped_after_api_403(self):
  self.play();self.block();self.env['_efstream_poll']()
  self.assertEqual(self.nav.stops,1);self.assertIsNone(self.env['_efstream_active'])
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.play()
 def test_softstream_escalation_and_browsing(self):
  self.play();self.env['_efstream_event'](1)
  self.assertEqual(self.nav.stops,1)
  self.env['_efguard_check']('https://emby.test/Items')
  self.assertIn('Securitycheck by Paul',self.env['_efguard_notice'])
  self.play();self.env['_efstream_event'](1)
  self.env['_efguard_check']('https://emby.test/Images')
  self.assertEqual(self.env['_efstream_blocked']['emby.test']-self.now,60)
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.play()
  self.now+=60
  self.play();self.env['_efstream_event'](1)
  self.assertEqual(self.env['_efstream_blocked']['emby.test']-self.now,300)
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.play()
  self.now+=300;self.play();self.env['_efstream_event'](1)
  self.play() # old strikes expired: first failure is free again
 def test_credit_and_host_blocks_override_soft_retry(self):
  self.play();self.env['_efstream_event'](1)
  self.block()
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.play()
 def test_local_and_other_host_playback_unaffected(self):
  self.block();self.play('/media/hdd/movie.mkv');self.play('https://other.test/video')
  self.assertEqual(len(self.nav.plays),2)
 def test_success_normal_eof_and_intentional_replacement(self):
  self.play();self.env['_efstream_event'](2);self.assertEqual(self.nav.stops,0)
  self.owner.current_position_ticks=lambda:10
  self.owner._embyflow_stream_replacement_in_progress=True
  self.env['_efstream_event'](2);self.assertEqual(self.nav.stops,0)
 def test_premature_eof_pauses(self):
  self.owner.current_position_ticks=lambda:100
  self.play();self.env['_efstream_event'](2);self.assertEqual(self.nav.stops,1)
 def test_unknown_duration_eof_does_not_pause(self):
  self.owner.duration_ticks=0
  self.play();self.env['_efstream_event'](2);self.assertEqual(self.nav.stops,0)
 def test_returned_start_error_pauses(self):
  self.nav.result=1
  with self.assertRaises(RuntimeError):self.play()
  self.assertEqual(self.nav.stops,1)
  self.env['_efguard_check']('https://emby.test/Items');self.nav.result=0;self.play()
 def test_timer_does_not_stop_service_switched_outside_plugin(self):
  self.play();self.block();self.nav.current=Ref('dvb')
  self.env['_efstream_poll']();self.assertEqual(self.nav.stops,0)
 def test_current_prestarted_player_gets_owner(self):
  self.play();player=self.env['EmbyFlowMoviePlayer'](self.env['_efguard_gui_session'])
  self.assertIs(self.env['_efstream_active']['owner'],player)
 def test_build_all_native_starts_gated_and_credit_present(self):
  p=ROOT/'EmbyFlowE2_Softstream_20261005_0505.py';source=p.read_text()
  tree=ast.parse(source);compile(source,str(p),'exec')
  direct=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='playService']
  helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_efguard_play_service')
  self.assertEqual(len(direct),2)
  self.assertTrue(all(helper.lineno <= n.lineno <= helper.end_lineno for n in direct))
  self.assertIn('Securitycheck by Paul',source)

if __name__=='__main__':unittest.main()

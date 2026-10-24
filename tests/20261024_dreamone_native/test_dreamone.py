import ast,copy,importlib.util,io,re,sys,time,types,unittest
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock,patch
HERE=Path(__file__).resolve().parent
TEXT=(Path(__file__).resolve().parents[2]/'EmbyFlowE2_2026102401.py').read_text();TREE=ast.parse(TEXT)
CLASS=next(n for n in TREE.body if getattr(n,'name',None)=='EmbyFlowMoviePlayer')
RUNTIME=(HERE/'runtime.py').read_text()
class Widget:
 def __init__(self):self.text=''
 def setText(self,value):self.text=value
class DreamOneTests(unittest.TestCase):
 def setUp(self):
  self.machine='dreamone';components=types.ModuleType('Components');system=types.ModuleType('Components.SystemInfo');system.BoxInfo=Obj(getItem=lambda key:self.machine)
  self.modules=patch.dict(sys.modules,{'Components':components,'Components.SystemInfo':system});self.modules.start();self.addCleanup(self.modules.stop)
  self.cls=type('Player',(dict,),{})
  self.ns={'EmbyFlowMoviePlayer':self.cls,'re':re,'time':time,'MessageBox':Obj(TYPE_INFO=1,TYPE_ERROR=2),'EmbyFlowTrackSelectionScreen':object(),'embyflow_open_log':lambda *a,**k:io.StringIO()}
  names=('embyflow_track_codec_name','embyflow_audio_language_key','embyflow_audio_language_label','embyflow_audio_codec_key','embyflow_audio_codec_label','embyflow_audio_channels_number','embyflow_track_channel_name','embyflow_match_emby_audio_stream','embyflow_audio_selection_entries','embyflow_extract_audio_payload','embyflow_apply_confirmed_audio_track','embyflow_confirm_audio_track','embyflow_stop_audio_confirm','audio_selection_finished','open_audio_selection','embyflow_media_streams_by_type')
  for name in names:
   n=next(n for n in CLASS.body if getattr(n,'name',None)==name);exec(ast.get_source_segment(TEXT,n),self.ns);setattr(self.cls,name,self.ns[name])
  self.native_open=self.cls.open_audio_selection;self.native_select=self.cls.audio_selection_finished
  self.server_open=Mock();self.server_select=Mock();self.old_start=Mock();self.old_show=Mock()
  self.cls.open_audio_selection=self.server_open;self.cls.audio_selection_finished=self.server_select;self.cls.set_preferred_audio_track=self.old_start;self.cls.show_overlay=self.old_show
  self.ns.update(_EFA2_OPEN=self.native_open,_EFA2_SELECT=self.native_select,_efa2_restart_4097=Mock(side_effect=AssertionError('must never restart')))
  for name in ('audio_stream_text','audio_stream_is_unwanted','audio_stream_score'):
   n=next(n for n in TREE.body if getattr(n,'name',None)==name);exec(ast.get_source_segment(TEXT,n),self.ns)
  self.ns['audio_codec_is_risky']=lambda c:False
  exec(RUNTIME,self.ns);self.ns['_dfas_log']=Mock()
  p=self.p=self.cls(technical_badges=Widget(),state_label=Widget());p.item={'MediaSources':[{'Id':'other','DefaultAudioStreamIndex':17,'MediaStreams':[{'Type':'Audio','Language':'fra','Index':17}]},{'Id':'active','DefaultAudioStreamIndex':1,'MediaStreams':[{'Type':'Audio','Language':'eng','Codec':'dts','Index':1,'Channels':6},{'Type':'Audio','Language':'deu','Codec':'dts','Index':4,'Channels':6}]}]}
  p.media_source_id='active';p.playback_info={'item':p.item};p.audio_timer=Mock();p.audio_confirm_timer=Mock();p.current_position_ticks=Mock(return_value=3000000000);p.play_session_id='unchanged';p.stream_url='http://server/Videos/movie/stream.ts?Static=true';p.onClose=[]
  self.current=0;self.descriptors=[{'e2_index':0,'language_key':'en','codec_key':'dts','description':'English DTS 5.1','channels':6},{'e2_index':1,'language_key':'de','codec_key':'dts','description':'German DTS 5.1','channels':6}]
  def select(i):self.current=i
  self.tracks=Obj(getCurrentTrack=lambda:self.current,getNumberOfTracks=lambda:len(self.descriptors),selectTrack=Mock(side_effect=select))
  p.embyflow_audio_track_descriptor=lambda tracks,index:self.descriptors[index]
  self.nav=Obj(getCurrentlyPlayingServiceReference=lambda:Obj(type=4097),getCurrentService=lambda:Obj(audioTracks=lambda:self.tracks),playService=Mock(),stopService=Mock())
  p.session=Obj(nav=self.nav,open=Mock(),openWithCallback=Mock());p.embyflow_schedule_audio_confirm=Mock()
  p.tester_osd_build_badges=lambda:p.overlay_language+' '+p.embyflow_active_audio_override.get('Codec','')
 def switch(self,index):
  self.p.audio_selection_finished({'action':'audio','e2_index':index,'label':'choice'})
  self.p.embyflow_confirm_audio_track();self.p.embyflow_confirm_audio_track()
 def assert_no_restart(self):
  self.nav.playService.assert_not_called();self.nav.stopService.assert_not_called();self.ns['_efa2_restart_4097'].assert_not_called();self.assertEqual(self.p.play_session_id,'unchanged')
 def test_ts_german_start_english_after_five_minutes_stays_at_position(self):
  self.p.set_preferred_audio_track();self.assertEqual(self.current,1)
  self.switch(0);self.assertEqual(self.current,0);self.assertEqual(self.p['technical_badges'].text,'Englisch dts');self.assertEqual(self.p.overlay_language,'Englisch')
  self.assertEqual(self.p.current_position_ticks(),3000000000);self.assertTrue(self.p.stream_url.endswith('Static=true'));self.assert_no_restart()
 def test_mkv_also_switches_native_without_hls(self):
  self.p.stream_url='http://server/Videos/movie/stream.mkv?Static=true'
  self.switch(1);self.assertEqual(self.p['technical_badges'].text,'Deutsch dts');self.assert_no_restart()
 def test_reverse_after_five_minutes_same_session(self):
  self.switch(1);self.switch(0);self.switch(1);self.assertEqual(self.current,1);self.assert_no_restart()
 def test_confirmed_selection_updates_only_active_version(self):
  self.switch(1);sources=self.p.item['MediaSources'];self.assertEqual(sources[0]['DefaultAudioStreamIndex'],17);self.assertEqual(sources[1]['DefaultAudioStreamIndex'],4)
 def test_language_choice_not_overridden_by_auto(self):
  self.switch(0);self.tracks.selectTrack.reset_mock();self.p.set_preferred_audio_track();self.tracks.selectTrack.assert_not_called()
 def test_menu_hak_and_labels_use_actual_tracks(self):
  self.current=1;self.p.open_audio_selection();kw=self.p.session.openWithCallback.call_args.kwargs
  self.assertEqual(kw['active_index'],1);self.assertEqual([e['primary'] for e in kw['entries']],['Englisch','Deutsch']);self.assertEqual([e['active'] for e in kw['entries']],[False,True]);self.server_open.assert_not_called()
 def test_no_german_in_native_stream_never_marks_english_german(self):
  self.descriptors=self.descriptors[:1];self.p.set_preferred_audio_track();self.assertEqual(self.current,0);self.assertFalse(hasattr(self.p,'overlay_language'));self.tracks.selectTrack.assert_not_called()
 def test_wrong_source_has_no_ordinal_guess(self):
  self.p.media_source_id='missing';self.descriptors=[dict(d,language_key='') for d in self.descriptors];self.p.set_preferred_audio_track();self.tracks.selectTrack.assert_not_called()
 def test_old_server_menu_payload_does_not_restart(self):
  self.p.audio_selection_finished({'action':'audio','emby_index':4});self.p.session.open.assert_called_once();self.assert_no_restart()
 def test_other_receivers_keep_their_paths(self):
  for name in ['gbquad4kpro','hd51','h17','duo4kse']:
   self.machine=name;self.p.open_audio_selection();self.p.audio_selection_finished({'action':'audio','e2_index':1});self.p.set_preferred_audio_track()
  self.assertEqual(self.server_open.call_count,4);self.assertEqual(self.server_select.call_count,4);self.assertEqual(self.old_start.call_count,4)
 def test_failed_native_switch_does_not_claim_success(self):
  self.tracks.selectTrack=Mock();self.p.audio_selection_finished({'action':'audio','e2_index':1});self.p.embyflow_confirm_audio_track();self.assertFalse(hasattr(self.p,'overlay_language'));self.assert_no_restart()
 def test_service_5002_retains_existing_path(self):
  self.nav.getCurrentlyPlayingServiceReference=lambda:Obj(type=5002)
  self.p.open_audio_selection();self.server_open.assert_called_once()
 def test_dmone_alias_uses_native_selection(self):
  self.machine='dmone';self.switch(1);self.assertEqual(self.current,1);self.assert_no_restart()
 def test_startup_already_german_needs_no_selection(self):
  self.current=1;self.p.set_preferred_audio_track();self.tracks.selectTrack.assert_not_called();self.assertEqual(self.p.overlay_language,'Deutsch')
 def test_closed_player_does_not_autoselect(self):
  self.p.closed=True;self.p.set_preferred_audio_track();self.tracks.selectTrack.assert_not_called()
 def test_single_transcoded_english_does_not_fake_german(self):
  self.descriptors=self.descriptors[:1];self.p.playback_info['audio_compat_hls']=True
  self.p.set_preferred_audio_track();self.assertEqual(self.current,0);self.tracks.selectTrack.assert_not_called()
if __name__=='__main__':unittest.main()

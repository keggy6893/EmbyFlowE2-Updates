import ast,unittest
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock
HERE=Path(__file__).resolve().parent
RUNTIME=(HERE/'runtime.py').read_text()
BASE=(HERE.parents[1]/'EmbyFlowE2_2026102402.py').read_text()
class Player:
 def __getitem__(self,key):return self.widgets[key]
class Tests(unittest.TestCase):
 def setup_player(self,local=True,native=None):
  before_open=Mock(return_value='remote-open');before_select=Mock(return_value='remote-select')
  cls=type('TestPlayer',(Player,),{'open_subtitle_selection':before_open,'subtitle_selection_finished':before_select})
  stopped=Mock();ns={'EmbyFlowMoviePlayer':cls,'EmbyFlowTrackSelectionScreen':object,'_embyflow_srt_v2_stop':stopped};exec(RUNTIME,ns)
  native=[(0,420,0,0,'deu'),(0,421,0,0,'eng')] if native is None else native
  interface=Obj(getSubtitleList=Mock(return_value=native),enableSubtitles=Mock(return_value=0),disableSubtitles=Mock())
  ref=Obj(toString=lambda:'same-file');session=Obj(nav=Obj(getCurrentlyPlayingServiceReference=lambda:ref,getCurrentService=lambda:Obj(subtitle=lambda:interface)),openWithCallback=Mock(),open=Mock())
  p=cls();p.embyflow_active_subtitle_index=None;p.playback_info={'local_file':local};p.ref=ref;p.session=session;p.instance=object();p.widgets={'state_label':Mock()};p.subtitle_timer=Mock();p.show_overlay=Mock();p.embyflow_track_language_name=lambda lang,fallback:{'deu':'Deutsch','eng':'Englisch'}.get(lang,fallback);p.embyflow_get_subtitle_window=Mock(return_value=Obj(instance=object(),show=Mock(),hide=Mock()))
  return p,interface,ns,before_open,before_select,stopped
 def test_reproduces_original_screenshot_error(self):
  tree=ast.parse(BASE);node=next(n for n in tree.body if getattr(n,'name',None)=='_embyflow_subtitle_open_0629')
  p,interface,ns,*_=self.setup_player();ns.update(_embyflow_subtitle_streams_0629=lambda p:[],MessageBox=Obj(TYPE_INFO=1))
  exec(ast.unparse(node),ns);ns['_embyflow_subtitle_open_0629'](p)
  self.assertIn('Keine Untertitelspuren in der aktiven MediaSource',p.session.open.call_args.args[1])
 def test_native_dvb_pid_inventory_without_emby_metadata(self):
  p,i,ns,*_=self.setup_player();p.open_subtitle_selection();rows=p.session.openWithCallback.call_args.kwargs['entries']
  self.assertEqual([r['primary'] for r in rows],['Untertitel aus','Deutsch','Englisch']);self.assertEqual(rows[1]['payload'][1],(0,420,0,0,'deu'));p.session.open.assert_not_called()
 def test_exact_native_tuple_enabled_and_shared_shutdown_registered(self):
  p,i,ns,bo,bs,stop=self.setup_player();p.open_subtitle_selection();p.subtitle_selection_finished(('eflu_native',(0,421,0,0,'eng'),'Englisch',1))
  i.enableSubtitles.assert_called_once_with(p.embyflow_get_subtitle_window.return_value.instance,(0,421,0,0,'eng'));self.assertIs(p._efpg_active[0],i);self.assertEqual(p.embyflow_selected_subtitle,(0,421,0,0,'eng'));stop.assert_called_once_with(p,True)
 def test_off_stops_timers_and_native_display(self):
  p,i,ns,*_=self.setup_player();p.embyflow_subtitle_window=p.embyflow_get_subtitle_window.return_value;p.open_subtitle_selection();p.subtitle_selection_finished(('eflu_off',None,'Aus',None));i.disableSubtitles.assert_called_once_with(p.embyflow_subtitle_window.instance);i.enableSubtitles.assert_not_called();p.subtitle_timer.stop.assert_called_once();self.assertTrue(p.embyflow_manual_subtitle_selected)
 def test_no_tracks_off_menu_instead_of_false_metadata_error(self):
  p,i,ns,*_=self.setup_player(native=[]);p.open_subtitle_selection();self.assertEqual(len(p.session.openWithCallback.call_args.kwargs['entries']),1);p.session.open.assert_not_called()
 def test_active_selection_checkmark(self):
  p,i,ns,*_=self.setup_player();p.embyflow_selected_subtitle=(0,421,0,0,'eng');p.open_subtitle_selection();self.assertEqual(p.session.openWithCallback.call_args.kwargs['active_index'],2)
 def test_stale_service_rejected(self):
  p,i,ns,*_=self.setup_player();p.open_subtitle_selection();p.session.nav.getCurrentlyPlayingServiceReference=lambda:Obj(toString=lambda:'other');p.subtitle_selection_finished(('eflu_native',(0,420,0,0,'deu'),'Deutsch',0));i.enableSubtitles.assert_not_called()
 def test_removed_track_rejected(self):
  p,i,ns,*_=self.setup_player();p.open_subtitle_selection();i.getSubtitleList.return_value=[];p.subtitle_selection_finished(('eflu_native',(0,420,0,0,'deu'),'Deutsch',0));i.enableSubtitles.assert_not_called()
 def test_rejection_cleans_up_without_active_marker(self):
  p,i,ns,*_=self.setup_player();p.open_subtitle_selection();i.enableSubtitles.return_value=-1;p.subtitle_selection_finished(('eflu_native',(0,420,0,0,'deu'),'Deutsch',0));self.assertIsNone(p.embyflow_selected_subtitle);self.assertFalse(hasattr(p,'_efpg_active'));p.embyflow_get_subtitle_window.return_value.hide.assert_called_once()
 def test_remote_menus_and_selection_unchanged(self):
  p,i,ns,bo,bs,_=self.setup_player(False);self.assertEqual(p.open_subtitle_selection(),'remote-open');result=('subtitle',{},'Deutsch',0);self.assertEqual(p.subtitle_selection_finished(result),'remote-select');bs.assert_called_once_with(p,result);i.getSubtitleList.assert_not_called()
 def test_native_gstreamer_types_and_malformed_entries(self):
  p,i,ns,*_=self.setup_player(native=[None,(2,1,4,0,'eng'),(2,1,4,0,'eng'),('bad',0,0,0,''),(9,0,0,0,''),(1,77,4,5,'deu')]);p.open_subtitle_selection();rows=p.session.openWithCallback.call_args.kwargs['entries'];self.assertEqual([r['secondary'] for r in rows],['','SRT','Videotext'])
 def test_close_uses_existing_native_shutdown_implementation(self):
  tree=ast.parse(BASE);node=next(n for n in tree.body if getattr(n,'name',None)=='_efpg_stop')
  p,i,ns,*_=self.setup_player();p.open_subtitle_selection();p.subtitle_selection_finished(('eflu_native',(0,420,0,0,'deu'),'Deutsch',0));window=p._efpg_active[2]
  ns['_efpg_stop_before']=Mock();exec(ast.unparse(node),ns);ns['_efpg_stop'](p,True);self.assertIsNone(p._efpg_active);window.hide.assert_called_once()
 def test_movie_screen_never_used_as_native_subtitle_parent(self):
  p,i,ns,*_=self.setup_player(native=[(1,34,0x78,7,'eng')]);p.paused=False;p.synthetic_position_ticks=123
  p.open_subtitle_selection();p.subtitle_selection_finished(('eflu_native',(1,34,0x78,7,'eng'),'Englisch',1))
  parent,entry=i.enableSubtitles.call_args.args
  self.assertIsNot(parent,p.instance);self.assertIs(parent,p.embyflow_get_subtitle_window.return_value.instance)
  self.assertFalse(p.paused);self.assertEqual(p.synthetic_position_ticks,123)
 def test_optional_native_title_dropped_only_for_activation(self):
  entry=(1,34,0x78,7,'eng','English teletext')
  p,i,ns,*_=self.setup_player(native=[entry]);p.open_subtitle_selection();p.subtitle_selection_finished(('eflu_native',entry,'Englisch',0))
  self.assertEqual(i.enableSubtitles.call_args.args[1],entry[:5]);self.assertEqual(p.embyflow_selected_subtitle,entry)
  p.open_subtitle_selection();self.assertEqual(p.session.openWithCallback.call_args.kwargs['active_index'],1)
 def test_missing_subtitle_window_instance_fails_without_native_activation(self):
  p,i,ns,*_=self.setup_player();p.embyflow_get_subtitle_window.return_value=Obj(instance=None,show=Mock(),hide=Mock())
  p.open_subtitle_selection();p.subtitle_selection_finished(('eflu_native',(0,420,0,0,'deu'),'Deutsch',0));i.enableSubtitles.assert_not_called()
 def test_already_paused_playback_remains_paused(self):
  p,i,ns,*_=self.setup_player();p.paused=True;p.open_subtitle_selection();p.subtitle_selection_finished(('eflu_native',(0,420,0,0,'deu'),'Deutsch',0));self.assertTrue(p.paused)
if __name__=='__main__':unittest.main()

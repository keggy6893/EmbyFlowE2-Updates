import unittest
import test_local_subtitles as fixtures
class LayerTests(unittest.TestCase):
 def active_player(self):
  p,i,ns,*_=fixtures.Tests().setup_player();w=p.embyflow_get_subtitle_window.return_value;p.embyflow_subtitle_window=w
  p.open_subtitle_selection();p.subtitle_selection_finished(('eflu_native',(0,420,0,0,'deu'),'Deutsch',0))
  return p,i,ns,w
 def test_display_raised_above_player(self):
  p,i,ns,w=self.active_player();w.instance.setZPosition.assert_called_once_with(10);self.assertIs(p._efpg_active[1],w.instance)
 def test_opening_other_dialog_hides_display_and_return_restores(self):
  p,i,ns,w=self.active_player();w.reset_mock() if hasattr(w,'reset_mock') else None
  w.hide.reset_mock();w.show.reset_mock()
  for callback in p.onHide:callback()
  w.hide.assert_called_once()
  for callback in p.onShow:callback()
  w.show.assert_called_once()
 def test_off_is_not_restored_when_menu_closes(self):
  p,i,ns,w=self.active_player();p.subtitle_selection_finished(('eflu_off',None,'Aus',None));w.show.reset_mock()
  for callback in p.onShow:callback()
  w.show.assert_not_called()
 def test_different_movie_never_restores_overlay(self):
  p,i,ns,w=self.active_player();p.session.nav.getCurrentlyPlayingServiceReference=lambda:type('Ref',(),{'toString':lambda s:'other'})();w.show.reset_mock()
  for callback in p.onShow:callback()
  w.show.assert_not_called()
 def test_closed_player_never_restores_overlay(self):
  p,i,ns,w=self.active_player();p.closed=True;w.show.reset_mock()
  for callback in p.onShow:callback()
  w.show.assert_not_called()
 def test_hooks_registered_once_across_language_changes(self):
  p,i,ns,w=self.active_player();p.subtitle_selection_finished(('eflu_native',(0,421,0,0,'eng'),'Englisch',1));self.assertEqual(len(p.onHide),1);self.assertEqual(len(p.onShow),1)
if __name__=='__main__':unittest.main()

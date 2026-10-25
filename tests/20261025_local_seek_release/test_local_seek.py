import ast, unittest
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock
HERE=Path(__file__).resolve().parent
BASE=(HERE.parents[1]/'EmbyFlowE2_2026102402.py').read_text()
RUNTIME=(HERE/'runtime.py').read_text()
class Tests(unittest.TestCase):
 def setup_player(self,local=True):
  old=[Mock(return_value='old') for _ in range(3)]
  cls=type('Player',(),dict(zip(('embyflow_seek_to_chapter','embyflow_v10_restart_stream','restart_stream_at_ticks'),old)))
  ns={'EmbyFlowMoviePlayer':cls};exec(RUNTIME,ns)
  ref=Obj(type=1,toString=lambda:'1:file',getPath=lambda:'/media/usb/Filme/Skyfall.ts')
  seek=Obj(seekTo=Mock(return_value=0),getLength=lambda:(0,600*90000),isCurrentlySeekable=lambda:1)
  nav=Obj(getCurrentlyPlayingServiceReference=lambda:ref,getCurrentService=lambda:Obj(seek=lambda:seek),playService=Mock(),stopService=Mock())
  p=cls();p.playback_info={'local_file':local};p.ref=ref;p.stream_url=ref.getPath();p.session=Obj(nav=nav);p.closed=False;p.paused=True;p.synthetic_position_ticks=123;p.show_overlay=Mock()
  return p,seek,old,ns
 def test_old_local_chapter_reaches_server_restart(self):
  cls=next(n for n in ast.parse(BASE).body if isinstance(n,ast.ClassDef) and n.name=='EmbyFlowMoviePlayer')
  node=next(n for n in cls.body if getattr(n,'name',None)=='embyflow_seek_to_chapter')
  ns={};exec(ast.unparse(node),ns)
  p=Obj(embyflow_v10_restart_stream=Mock(return_value=True))
  self.assertTrue(ns['embyflow_seek_to_chapter'](p,3000000000));p.embyflow_v10_restart_stream.assert_called_once_with(3000000000,None,'Aus')
 def test_three_entrypoints_seek_current_local_service_only(self):
  for name in ('embyflow_seek_to_chapter','embyflow_v10_restart_stream','restart_stream_at_ticks'):
   p,s,old,ns=self.setup_player();self.assertTrue(getattr(p,name)(3000000000));s.seekTo.assert_called_once_with(300*90000)
   for fn in old:fn.assert_not_called()
   p.session.nav.playService.assert_not_called();p.session.nav.stopService.assert_not_called()
   self.assertTrue(p.paused);self.assertEqual(p.synthetic_position_ticks,123)
 def test_nonlocal_routes_unchanged(self):
  p,s,old,ns=self.setup_player(False)
  self.assertEqual(p.embyflow_seek_to_chapter(100),'old');old[0].assert_called_once_with(p,100)
  self.assertEqual(p.embyflow_v10_restart_stream(100,2,'Deutsch'),'old');old[1].assert_called_once_with(p,100,2,'Deutsch')
  self.assertEqual(p.restart_stream_at_ticks(100),'old');old[2].assert_called_once_with(p,100);s.seekTo.assert_not_called()
 def test_native_rejection_never_falls_back_to_restart(self):
  p,s,old,ns=self.setup_player();s.seekTo.return_value=-1
  self.assertFalse(p.embyflow_seek_to_chapter(3000000000))
  for fn in old:fn.assert_not_called()
 def test_exception_fails_closed(self):
  p,s,old,ns=self.setup_player();s.seekTo.side_effect=RuntimeError('not ready')
  self.assertFalse(p.embyflow_seek_to_chapter(3000000000))
  for fn in old:fn.assert_not_called()
 def test_current_different_file_is_not_touched(self):
  p,s,old,ns=self.setup_player();p.session.nav.getCurrentlyPlayingServiceReference=lambda:Obj(toString=lambda:'other')
  self.assertFalse(p.embyflow_seek_to_chapter(10));s.seekTo.assert_not_called()
 def test_current_path_must_match(self):
  p,s,old,ns=self.setup_player();p.ref.getPath=lambda:'/other'
  self.assertFalse(p.embyflow_seek_to_chapter(10));s.seekTo.assert_not_called()
 def test_unseekable_or_closed_not_touched(self):
  p,s,old,ns=self.setup_player();s.isCurrentlySeekable=lambda:0
  self.assertFalse(p.embyflow_seek_to_chapter(10));s.seekTo.assert_not_called()
  s.isCurrentlySeekable=lambda:1;p.closed=True
  self.assertFalse(p.embyflow_seek_to_chapter(10));s.seekTo.assert_not_called()
 def test_clamp_uses_native_duration(self):
  p,s,old,ns=self.setup_player();p.embyflow_seek_to_chapter(9999*10000000);s.seekTo.assert_called_once_with(599*90000)
 def test_negative_clamped(self):
  p,s,old,ns=self.setup_player();p.embyflow_seek_to_chapter(-100);s.seekTo.assert_called_once_with(0)
if __name__=='__main__':unittest.main()

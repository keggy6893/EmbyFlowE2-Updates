import unittest
from pathlib import Path
from types import SimpleNamespace as Obj
from unittest.mock import Mock
RUNTIME=(Path(__file__).parent/'runtime.py').read_text()
class RuntimeTests(unittest.TestCase):
 def setup(self,mode='http4097'):
  methods={name:Mock(return_value='before') for name in ('__init__','audio_selection_finished','send_emby_playback_report','cancel_active_encoding')}
  cls=type('Player',(),methods)
  detail=type('Detail',(),{'__init__':Mock(),'render_local':Mock()})
  native=Mock(return_value='native-before')
  ns={'EmbyFlowMoviePlayer':cls,'EmbyFlowLocalSkyfallDetail':detail,'_efls_native':native};exec(RUNTIME,ns)
  url='http://127.0.0.1:12345/test/skyfall.ts';ref=Obj(toString=lambda:'4097:'+url,getPath=lambda:url)
  seek=Obj(isCurrentlySeekable=lambda:1,getLength=lambda:(0,600*90000),seekTo=Mock(return_value=0))
  p=Obj(playback_info={'http_compare_mode':mode},closed=False,stream_url=url,ref=ref,session=Obj(nav=Obj(getCurrentlyPlayingServiceReference=lambda:ref,getCurrentService=lambda:Obj(seek=lambda:seek))))
  return ns,cls,p,seek,methods,native
 def test_probe_reports_never_sent_to_provider(self):
  ns,cls,p,s,methods,n=self.setup();self.assertIsNone(cls.send_emby_playback_report(p,'Playing',0));methods['send_emby_playback_report'].assert_not_called()
 def test_probe_encoding_cleanup_never_sent_to_provider(self):
  ns,cls,p,s,methods,n=self.setup();self.assertIsNone(cls.cancel_active_encoding(p));methods['cancel_active_encoding'].assert_not_called()
 def test_other_playback_reports_unchanged(self):
  ns,cls,p,s,methods,n=self.setup('');self.assertEqual(cls.send_emby_playback_report(p,'Stopped',1),'before');self.assertEqual(cls.cancel_active_encoding(p),'before')
 def test_loopback_seek_uses_existing_service_only(self):
  ns,cls,p,s,methods,n=self.setup();self.assertTrue(ns['_efhc_native'](p,3000000000));s.seekTo.assert_called_once_with(300*90000);n.assert_not_called()
 def test_rejected_seek_has_no_fallback(self):
  ns,cls,p,s,methods,n=self.setup();s.seekTo.return_value=-1;self.assertFalse(ns['_efhc_native'](p,3000000000));n.assert_not_called()
 def test_unseekable_no_call(self):
  ns,cls,p,s,methods,n=self.setup();s.isCurrentlySeekable=lambda:0;self.assertFalse(ns['_efhc_native'](p,10));s.seekTo.assert_not_called()
 def test_changed_current_service_no_call(self):
  ns,cls,p,s,methods,n=self.setup();p.session.nav.getCurrentlyPlayingServiceReference=lambda:Obj(toString=lambda:'different');self.assertFalse(ns['_efhc_native'](p,10));s.seekTo.assert_not_called()
 def test_external_host_never_handled_as_test(self):
  ns,cls,p,s,methods,n=self.setup();p.stream_url='http://example.org/test.ts';self.assertFalse(ns['_efhc_native'](p,10));s.seekTo.assert_not_called()
 def test_usb_seek_delegates_to_tested_local_fix(self):
  ns,cls,p,s,methods,n=self.setup('file4097');self.assertEqual(ns['_efhc_native'](p,10),'native-before');n.assert_called_once_with(p,10)
 def test_audio_selection_preserves_existing_handler(self):
  ns,cls,p,s,methods,n=self.setup();p.embyflow_extract_audio_payload=lambda r:r
  payload={'e2_index':1};self.assertEqual(cls.audio_selection_finished(p,payload),'before');methods['audio_selection_finished'].assert_called_once_with(p,payload)
if __name__=='__main__':unittest.main()

class LaunchTests(unittest.TestCase):
 def test_both_modes_use_identical_original_probe_and_4097(self):
  from tempfile import TemporaryDirectory
  for mode in ('file4097','http4097'):
   with self.subTest(mode=mode),TemporaryDirectory() as tmp:
    path=Path(tmp)/'original.ts';path.write_bytes(b'original')
    original_probe=Mock(return_value={'runtime_ticks':100000000,'media_streams':[{'Type':'Audio','Language':'deu','Index':1}]})
    launcher=Mock();server=Obj(url='http://127.0.0.1:40000/test/skyfall.ts')
    class Ref:
     def __init__(self,typ,flags,url):self.type=typ;self.url=url
     def setName(self,title):self.title=title
    player=type('Player',(),{name:Mock() for name in ('__init__','audio_selection_finished','send_emby_playback_report','cancel_active_encoding')})
    detail=type('Detail',(),{'__init__':Mock(),'render_local':Mock()})
    ns={'EmbyFlowMoviePlayer':player,'EmbyFlowLocalSkyfallDetail':detail,'_efls_native':Mock(),'_ELS_PATH':str(path),'_embyflow_v21b_probe_local_file':original_probe,'_open_embyflow_player_now':launcher,'_EFHCServer':Mock(return_value=server),'eServiceReference':Ref}
    exec(RUNTIME,ns);d=Obj(_efhc_server=None,session=Obj(),render_local=Mock())
    ns['_efhc_play'](d,mode);original_probe.assert_called_once_with(str(path));launcher.assert_called_once()
    info=launcher.call_args.args[-1];ref=launcher.call_args.args[1]
    self.assertEqual(ref.type,4097);self.assertEqual(info['http_compare_mode'],mode);self.assertTrue(info['local_file']);self.assertEqual(info['engine_mode'],'e2')
    self.assertNotIn('token',info);self.assertNotIn('server',info)
    self.assertEqual(info['item']['MediaSources'][0]['MediaStreams'][0]['Language'],'deu')
    self.assertEqual(info['url'],str(path) if mode=='file4097' else server.url)

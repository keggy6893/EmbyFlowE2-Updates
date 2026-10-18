import importlib.util
import os
from pathlib import Path
import queue
import re
import tempfile
import threading
import unittest
from unittest.mock import Mock

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


class Timer:
    def __init__(self):self.callback=[];self.running=False
    def start(self,*args):self.running=True
    def stop(self):self.running=False


class Tests(unittest.TestCase):
    def setUp(self):
        class Screen(dict):
            def __init__(self,session):
                self.session=session;self.closed=False;self.loading=False;self.entries=[];self.index=0;self.onClose=[]
                self['status']=Mock()
            def play(self):self.native_called=True
        self.remote={'Id':'1731728','Name':'Die Wuestenratten','Type':'Movie','UserData':None,
                     'MediaSources':[{'MediaStreams':[{'Type':'Video','Codec':'av1'}]}]}
        self.http=Mock(return_value=Mock(status_code=200,json=lambda:self.remote))
        self.fetch=Mock(return_value={'url':'https://server.example/hls/master.m3u8'})
        self.ns=dict(EmbyFlowDownloadsScreen=Screen,eTimer=Timer,_eflib_os=os,
            _eflib_valid=lambda e:True,get_emby_auth=lambda:('https://server.example','secret-token','user'),
            embyflow_http_get=self.http,AUTH_HEADER='client',fetch_stream_info=self.fetch,
            _embyflow_v22_norm=lambda t:re.sub(r'\W','',str(t).lower()),
            get_embyflow_local_resume=lambda i:(9000,99999),
            _embyflow_v21b_probe_local_file=lambda p:{'media_streams':[{'Type':'Video','Codec':'av1'}]},
            eServiceReference=Mock(),STREAM_SERVICE_TYPE=4097,_open_embyflow_player_now=Mock())
        exec((HERE/'runtime.py').read_text(),self.ns)
        self.screen=Screen(Mock())
        self.entry={'path':'/media/hdd/movie/EmbyFlow/Die Wuestenratten_1731728_mediasource_1731728.mkv',
                    'metadata':{'Name':'Die Wuestenratten','Type':'Movie'},'title':'Die Wuestenratten'}
        self.screen.entries=[self.entry]
        self.cancel=threading.Event()

    def resolve(self):return self.ns['_efav_resolve'](self.entry,self.cancel)

    def test_real_download_name_exact_id_and_direct_stream_decision_used(self):
        title,info=self.resolve()
        self.assertEqual(title,'Die Wuestenratten')
        self.assertIn('/Users/user/Items/1731728',self.http.call_args.args[0])
        self.assertTrue(self.http.call_args.kwargs['verify'])
        self.assertEqual(self.fetch.call_args.args,('Die Wuestenratten','direct'))
        self.assertEqual(self.fetch.call_args.kwargs['item_id'],'1731728')
        self.assertEqual(self.fetch.call_args.kwargs['item_data']['UserData']['PlaybackPositionTicks'],9000)
        self.assertIsNone(self.remote['UserData'])
        self.assertEqual(info['embyflow_local_source_path'],self.entry['path'])

    def test_legacy_download_without_sidecar_uses_filename_title(self):
        self.entry['metadata']={}
        self.assertTrue(self.resolve())

    def test_other_account_id_or_title_or_type_cannot_launch(self):
        for field,value in [('Id','999'),('Name','Different movie'),('Type','Episode')]:
            original=self.remote[field];self.remote[field]=value
            with self.assertRaises(self.ns['_EFAVError']):self.resolve()
            self.remote[field]=original
        self.fetch.assert_not_called()

    def test_unidentified_download_is_not_fuzzily_matched(self):
        self.entry['path']='/media/hdd/movie/EmbyFlow/Random.mkv'
        with self.assertRaises(self.ns['_EFAVError']):self.resolve()
        self.http.assert_not_called()

    def test_offline_or_unreachable_original_is_clear_error(self):
        self.ns['get_emby_auth']=lambda:('','','')
        with self.assertRaises(self.ns['_EFAVError']):self.resolve()
        self.ns['get_emby_auth']=lambda:('https://server.example','token','user')
        self.http.return_value.status_code=404
        with self.assertRaises(self.ns['_EFAVError']):self.resolve()
        self.fetch.assert_not_called()

    def test_cancel_before_or_during_resolution_never_returns_playable_result(self):
        self.cancel.set();self.assertIsNone(self.resolve());self.http.assert_not_called()
        self.cancel.clear()
        def fetch(*a,**kw):self.cancel.set();return {'url':'https://server.example/video'}
        self.fetch.side_effect=fetch
        self.assertIsNone(self.resolve())

    def test_missing_stream_reports_error(self):
        self.fetch.return_value=None
        with self.assertRaises(self.ns['_EFAVError']):self.resolve()

    def test_non_av1_keeps_native_offline_player(self):
        for codec in ('h264','hevc','mpeg2video'):
            self.ns['_embyflow_v21b_probe_local_file']=lambda p,c=codec:{'media_streams':[{'Type':'Video','Codec':c}]}
            self.screen.play();self.assertTrue(self.screen.native_called)
        self.http.assert_not_called();self.fetch.assert_not_called()

    def test_late_result_after_close_never_launches(self):
        self.screen._efav_results.put((self.entry,('Film',{'url':'https://server.example/video'}),''))
        self.screen.closed=True
        self.ns['_efav_poll'](self.screen)
        self.assertTrue(self.screen._efav_cancel.is_set())
        self.ns['_open_embyflow_player_now'].assert_not_called()

    def test_ready_result_uses_existing_player_and_never_local_reference(self):
        self.screen._efav_results.put((self.entry,('Film',{'url':'https://server.example/video'}),''))
        self.ns['_efav_poll'](self.screen)
        self.ns['eServiceReference'].assert_called_once_with(4097,0,'https://server.example/video')
        self.ns['_open_embyflow_player_now'].assert_called_once()

    def test_worker_private_errors_are_not_exposed(self):
        class Immediate:
            def __init__(self,target,**kw):self.target=target
            def start(self):self.target()
        self.ns['_efav_threading']=type('Threading',(),{'Thread':Immediate})
        self.http.side_effect=ValueError('secret-token')
        self.screen.play()
        self.ns['_efav_poll'](self.screen)
        self.assertNotIn('secret-token',str(self.screen['status'].setText.call_args))
        self.ns['_open_embyflow_player_now'].assert_not_called()

    def test_installer_backups_latest_release_preserves_local_fixes_and_repeats(self):
        import subprocess
        subprocess.run(['python3',str(HERE/'build.py')],check=True,capture_output=True)
        ns={'__name__':'package_check'}
        exec((ROOT/'install-download-av1-test.py').read_text(),ns)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'plugin.py'
            source=(ROOT/'EmbyFlowE2_2026101804.py').read_text()+'\n# existing LCD or language fix\n'
            path.write_text(source);path.chmod(0o644)
            self.assertTrue(ns['install'](path))
            self.assertTrue(path.read_text().startswith(source))
            self.assertEqual(next(Path(d).glob('plugin.py.vor-av1-download-*')).read_text(),source)
            self.assertEqual(path.stat().st_mode&0o777,0o644)
            self.assertFalse(ns['install'](path))
            compile(path.read_text(),'patched-plugin','exec')


if __name__=='__main__':unittest.main()

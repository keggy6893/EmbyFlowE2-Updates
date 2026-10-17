import importlib.util, pathlib, types, unittest, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import requests

spec = importlib.util.spec_from_file_location('installer', pathlib.Path(__file__).with_name('install.py'))
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class FixTests(unittest.TestCase):
    def setUp(self):
        self.started, self.original, self.selected = [], [], []
        class Player:
            set_preferred_subtitle_track = lambda p: self.original.append(p)
            subtitle_selection_finished = lambda p, r: self.selected.append(r)
        self.ns = dict(EmbyFlowMoviePlayer=Player, requests=requests,
            embyflow_http_get=requests.get,
            _embyflow_srt_v2_streams=lambda p:p.streams,
            _embyflow_srt_v2_is_text_stream=lambda s:s.get('Codec') == 'srt',
            _embyflow_srt_v2_start=lambda *args:self.started.append(args),
            _embyflow_srt_v2_language=lambda *args:'Deutsch')
        exec(installer.PATCH, self.ns)
        self.player=Player()
        self.player.item={'MediaSources':[{'DefaultSubtitleStreamIndex':-1}]}
        self.player.streams=[]
        self.player.embyflow_srt_v2_loading=False
        self.player.embyflow_active_subtitle_index=None
    def test_forced(self):
        self.player.streams=[{'Index':4,'Language':'ger','IsForced':True,'Codec':'srt'}]
        self.player.set_preferred_subtitle_track()
        self.assertEqual(self.started[0][1]['Index'],4)
        self.assertEqual(self.started[0][3:],(0,False))
    def test_full_foreign_bitmap_not_forced(self):
        self.player.streams=[{'Language':'ger','Codec':'srt'},
            {'Language':'eng','IsForced':True,'Codec':'srt'},
            {'Language':'ger','IsForced':True,'Codec':'pgs'}]
        self.player.set_preferred_subtitle_track()
        self.assertFalse(self.started)
    def test_server_default_zero_preserved(self):
        self.player.item['MediaSources'][0]['DefaultSubtitleStreamIndex']=0
        self.player.streams=[{'Language':'ger','IsForced':True,'Codec':'srt'}]
        self.player.set_preferred_subtitle_track()
        self.assertFalse(self.started)
        self.assertEqual(len(self.original),1)
    def test_manual_off(self):
        self.player.subtitle_selection_finished(('subtitle_off',None,'Aus',None))
        self.player.streams=[{'Language':'ger','IsForced':True,'Codec':'srt'}]
        self.player.set_preferred_subtitle_track()
        self.assertFalse(self.started)
        self.assertEqual(len(self.selected),1)
    def test_string_false_not_forced(self):
        self.player.streams=[{'Language':'ger','IsForced':'False','Codec':'srt'}]
        self.player.set_preferred_subtitle_track()
        self.assertFalse(self.started)
    def test_loading_no_duplicate(self):
        self.player.embyflow_srt_v2_loading=True
        self.player.set_preferred_subtitle_track()
        self.assertFalse(self.original)
    def test_http_disconnect_recovered(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_GET(self):
                calls.append(dict(self.headers))
                if len(calls)==1:
                    self.close_connection=True
                    return
                data=b'1\n00:00:01,000 --> 00:00:02,000\nHallo\n'
                self.send_response(200);self.send_header('Content-Length',str(len(data)))
                self.end_headers();self.wfile.write(data)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            response=self.ns['_efut_get']('http://127.0.0.1:%d/sub'%server.server_port,
                headers={'X-Emby-Token':'test-only'},timeout=2,verify=True)
            self.assertEqual(response.status_code,200)
            self.assertIn(b'Hallo',response.content)
            self.assertEqual(len(calls),2)
            self.assertEqual(calls[1]['Connection'],'close')
            self.assertEqual(calls[1]['X-Emby-Token'],'test-only')
        finally:
            server.shutdown();server.server_close();thread.join()
    def test_tls_failure_never_retried(self):
        def fail(*a,**k):raise requests.exceptions.SSLError('certificate')
        self.ns['embyflow_http_get']=fail
        with self.assertRaises(requests.exceptions.SSLError):
            self.ns['_efut_get']('https://example.invalid',verify=True)
    def test_patch_preserves_rest(self):
        path=pathlib.Path(__file__).resolve().parents[2]/'EmbyFlowE2_2026101603.py'
        original=path.read_text();new=installer.patched(original)
        before=new[:-len('\n'+installer.PATCH)]
        self.assertEqual(before.replace('response = _efut_get(', 'response = embyflow_http_get(',1),original)
        with self.assertRaises(RuntimeError):installer.patched(new)

if __name__=='__main__':unittest.main()

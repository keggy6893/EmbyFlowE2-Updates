import ast, pathlib, re, threading, time, types, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock
import requests
from install import GET, PATCH, patched

ROOT=pathlib.Path(__file__).resolve().parents[2]

class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.ns=dict(requests=requests, _embyflow_srt_v2_urls=lambda *a:([], 'token', 4))
        exec(GET+'\n'+PATCH,self.ns)
        self.ns['_efut3_diag']=Mock()
    def test_empty_then_content(self):
        empty=Mock(status_code=200,content=b'');full=Mock(status_code=200,content=b'SRT')
        get=Mock(side_effect=[empty,full])
        self.ns['requests']=types.SimpleNamespace(get=get,exceptions=requests.exceptions)
        response=self.ns['_efut_get']('http://example.invalid',headers={'Accept-Encoding':'identity','X-Emby-Token':'test'},verify=True)
        self.assertIs(response,full);empty.close.assert_called_once()
        self.assertEqual(get.call_count,2)
        kwargs=get.call_args.kwargs
        self.assertTrue(kwargs['verify'])
        self.assertEqual(kwargs['headers']['X-Emby-Token'],'test')
        self.assertNotIn('Accept-Encoding',kwargs['headers'])
    def test_empty_retries_bounded(self):
        get=Mock(return_value=Mock(status_code=200,content=b''))
        self.ns['requests']=types.SimpleNamespace(get=get,exceptions=requests.exceptions)
        self.ns['_efut_get']('http://example.invalid')
        self.assertEqual(get.call_count,2)
    def test_no_retries_auth_rate_limit_tls(self):
        for status in (401,403,429):
            get=Mock(return_value=Mock(status_code=status,content=b''))
            self.ns['requests']=types.SimpleNamespace(get=get,exceptions=requests.exceptions)
            self.ns['_efut_get']('http://example.invalid');self.assertEqual(get.call_count,1)
        get=Mock(side_effect=requests.exceptions.SSLError('certificate'))
        self.ns['requests']=types.SimpleNamespace(get=get,exceptions=requests.exceptions)
        with self.assertRaises(requests.exceptions.SSLError):self.ns['_efut_get']('https://example.invalid')
        self.assertEqual(get.call_count,1)
    def test_urls_do_not_change_hostname(self):
        self.ns['_efut3_urls_before']=lambda *a:(['https://Items.example/emby/Items/a/b/Subtitles/4/stream.srt'],'token',4)
        urls,token,index=self.ns['_efut3_urls'](None,None)
        self.assertEqual(urls[1],'https://Items.example/emby/Videos/a/b/Subtitles/4/Stream.srt')
        self.assertEqual((token,index),('token',4))
    def test_original_worker_handles_empty_legacy_routes(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_GET(self):
                calls.append(self.path)
                data=(b'1\n00:00:01,000 --> 00:00:03,000\nDeutscher Dialog\n'
                    if '/Videos/' in self.path else b'')
                self.send_response(200);self.send_header('Content-Length',str(len(data)))
                self.end_headers();self.wfile.write(data)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        class Timer:
            def start(self,*a):pass
        class Label:
            def setText(self,*a):pass
        class Player(dict):pass
        p=Player(state_label=Label());p.item_id='film';p.media_source_id='source'
        p.playback_info=dict(server='http://127.0.0.1:%d'%server.server_port,token='test-only')
        p.embyflow_srt_v2_generation=0;p.embyflow_srt_v2_download_result=None
        p.embyflow_srt_v2_download_timer=Timer()
        ns=dict(self.ns,re=re,AUTH_HEADER='test',EMBY_AUTH_CACHE={},EMBY_SERVER='',
            embyflow_http_get=Mock(side_effect=AssertionError('metadata pool must not be used')),
            _embyflow_srt_v2_stop=lambda *a:None)
        names={'_embyflow_srt_v2_'+n for n in ('start','urls','parse','clean_text','timestamp_ms','is_text_stream')}
        source=patched((ROOT/'EmbyFlowE2_2026101702.py').read_text())
        nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in names]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'player','exec'),ns)
        exec(GET+'\n'+PATCH,ns);ns['_efut3_diag']=Mock()
        try:
            ns['_embyflow_srt_v2_start'](p,{'Index':4,'Codec':'srt'},'Deutsch',0,False)
            deadline=time.monotonic()+5
            while p.embyflow_srt_v2_download_result is None and time.monotonic()<deadline:time.sleep(.01)
            result=p.embyflow_srt_v2_download_result
            self.assertIsNotNone(result);self.assertTrue(result['ok'],result)
            self.assertEqual(result['cues'],[(1000,3000,'Deutscher Dialog')])
            self.assertEqual(len(calls),5)
            self.assertIn('/Videos/film/source/Subtitles/4/Stream.srt',calls[-1])
            ns['embyflow_http_get'].assert_not_called()
        finally:
            server.shutdown();server.server_close();thread.join()
    def test_patch_rejects_repeated_install(self):
        source=(ROOT/'EmbyFlowE2_2026101702.py').read_text()
        result=patched(source)
        with self.assertRaises(RuntimeError):patched(result)
        compile(result,'plugin.py','exec')

if __name__=='__main__':unittest.main()

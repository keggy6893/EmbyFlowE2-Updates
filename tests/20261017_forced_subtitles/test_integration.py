"""Exercise original player functions with real HTTP and an isolated fake E2 UI."""
import ast, pathlib, re, threading, time, types, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import requests
from install import patched, PATCH

SOURCE = pathlib.Path(__file__).resolve().parents[2]/'EmbyFlowE2_2026101603.py'

class Timer:
    def __init__(self): self.running=False
    def start(self,*a): self.running=True
    def stop(self): self.running=False

class Label:
    def setText(self,text): self.text=text

class IntegrationTests(unittest.TestCase):
    def run_player(self, default):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def do_GET(self):
                calls.append(self.path)
                if len(calls)==1:
                    self.close_connection=True
                    return
                data='1\n00:00:01,000 --> 00:00:03,000\nDeutscher Dialog\n'.encode()
                self.send_response(200)
                self.send_header('Content-Length',str(len(data)))
                self.end_headers();self.wfile.write(data)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        class Player(dict):
            def show_overlay(self): pass
        errors=[]
        ns=dict(re=re,time=time,requests=requests,AUTH_HEADER='test-only',
            EMBY_AUTH_CACHE={},EMBY_SERVER='',embyflow_http_get=requests.get,
            _embyflow_srt_v2_streams=lambda p:p.streams,
            _embyflow_srt_v2_language=lambda *a:'Deutsch',
            _embyflow_srt_v2_hide_overlay=lambda p:None,
            _embyflow_srt_v2_overlay=lambda *a:None,
            _embyflow_srt_v2_render_tick=lambda p:None,
            MessageBox=types.SimpleNamespace(TYPE_ERROR=1),
            EmbyFlowMoviePlayer=Player)
        names={'_embyflow_srt_v2_'+x for x in (
            'start','stop','urls','parse','clean_text','timestamp_ms',
            'is_text_stream','auto_select','poll_download','selection_finished')}
        tree=ast.parse(patched(SOURCE.read_text()))
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        self.assertEqual(len(nodes),len(names))
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'player','exec'),ns)
        Player.set_preferred_subtitle_track=ns['_embyflow_srt_v2_auto_select']
        Player.subtitle_selection_finished=ns['_embyflow_srt_v2_selection_finished']
        exec(PATCH,ns)
        p=Player()
        p.item={'MediaSources':[{'DefaultSubtitleStreamIndex':default}]}
        p.item_id='film';p.media_source_id='source'
        p.playback_info={'server':'http://127.0.0.1:%d'%server.server_port,'token':'test-only'}
        p.streams=[{'Index':5,'Language':'ger','IsForced':True,'Codec':'srt'}]
        p.embyflow_srt_v2_generation=0
        p.embyflow_srt_v2_loading=False
        p.embyflow_srt_v2_download_result=None
        p.embyflow_active_subtitle_index=None
        p.embyflow_srt_v2_download_timer=Timer()
        p.embyflow_srt_v2_render_timer=Timer()
        p.session=types.SimpleNamespace(open=lambda *a,**kw:errors.append(a))
        p['state_label']=Label()
        try:
            p.set_preferred_subtitle_track()
            deadline=time.monotonic()+5
            while p.embyflow_srt_v2_download_result is None and time.monotonic()<deadline:
                time.sleep(.01)
            self.assertIsNotNone(p.embyflow_srt_v2_download_result)
            ns['_embyflow_srt_v2_poll_download'](p)
            self.assertFalse(errors)
            self.assertEqual(p.embyflow_srt_v2_cues,[(1000,3000,'Deutscher Dialog')])
            self.assertEqual(p.embyflow_active_subtitle_stream_index,5)
            self.assertTrue(p.embyflow_srt_v2_render_timer.running)
            self.assertEqual(len(calls),2)
            self.assertTrue(all('/film/source/Subtitles/5/stream.srt?' in u for u in calls))
            p.subtitle_selection_finished(('subtitle_off',None,'Aus',None))
            self.assertFalse(p.embyflow_srt_v2_cues)
            self.assertFalse(p.embyflow_srt_v2_render_timer.running)
            p.set_preferred_subtitle_track()
            self.assertFalse(p.embyflow_srt_v2_loading)
            self.assertEqual(len(calls),2)
        finally:
            server.shutdown();server.server_close();thread.join()
    def test_missing_default_forced_download_parse_activate_off(self):
        self.run_player(-1)
    def test_server_default_download_parse_activate_off(self):
        self.run_player(5)

if __name__=='__main__': unittest.main()

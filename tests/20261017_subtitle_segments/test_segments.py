import ast,importlib.util,pathlib,threading,time,types,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from unittest.mock import Mock
import requests

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUNTIME=(HERE/'runtime.py').read_text()

class Timer:
    def __init__(self):self.callback=[];self.running=False
    def start(self,*a):self.running=True
    def stop(self):self.running=False
    def fire(self):
        if self.running:
            for cb in self.callback:cb()

class Label:
    def __init__(self):self.text='';self.visible=False
    def setText(self,text):self.text=text
    def show(self):self.visible=True
    def hide(self):self.visible=False

class SegmentTests(unittest.TestCase):
    def setUp(self):
        self.position=2000;self.calls=[];self.logs=[];self.fail=False;self.empty=False;self.block=None
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_GET(self):
                q=parse_qs(urlsplit(self.path).query)
                owner.calls.append(q)
                if owner.block is not None:owner.block.wait(3)
                if owner.fail:self.send_error(503);return
                if q.get('CopyTimestamps')!=['true'] or q.get('api_key')!=['test-only']:
                    self.send_error(400);return
                start=int(q['StartPositionTicks'][0])//10000
                end=int(q['EndPositionTicks'][0])//10000
                if end-start!=60000:self.send_error(400);return
                def stamp(ms):
                    return '%02d:%02d:%02d,%03d'%(ms//3600000,(ms//60000)%60,(ms//1000)%60,ms%1000)
                data=b'' if owner.empty else ('1\n%s --> %s\nDeutsch %d\n'%(stamp(start+1000),stamp(start+3000),start)).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(data)))
                self.end_headers();self.wfile.write(data)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        class Player(dict):
            def show_overlay(self):pass
        self.downloads=[]
        Player.set_preferred_subtitle_track=lambda p:None
        ns=dict(requests=requests,re=__import__('re'),time=time,eTimer=Timer,
            EMBY_AUTH_CACHE={},EMBY_SERVER='',EmbyFlowMoviePlayer=Player,
            _embyflow_srt_v2_connect_timer=lambda p,t,cb,n:(t.callback.append(cb) or True))
        source=ast.parse((ROOT/'EmbyFlowE2_2026101703.py').read_text())
        names={'_embyflow_srt_v2_'+x for x in ('parse','timestamp_ms','clean_text','urls','stop','is_text_stream','selection_finished')}
        names.update('_embyflow_srt_v4_'+x for x in ('overlay','hide_overlay','render_tick','close'))
        nodes=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in names]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'original-player','exec'),ns)
        ns['_embyflow_srt_v2_overlay']=ns['_embyflow_srt_v4_overlay']
        ns['_embyflow_srt_v2_hide_overlay']=ns['_embyflow_srt_v4_hide_overlay']
        ns['_embyflow_srt_v2_start']=lambda *a:self.downloads.append(a)
        Player.embyflow_close_subtitle_window=ns['_embyflow_srt_v4_close']
        spec=importlib.util.spec_from_file_location('v2',ROOT/'tests/20261017_forced_subtitles_v2/install.py')
        v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(v2)
        exec(v2.PATCH,ns)
        ns['_embyflow_srt_v2_language']=lambda *a:'Deutsch'
        exec(RUNTIME,ns);ns['_efseg_log']=lambda **row:self.logs.append(row)
        self.ns=ns
        self.p=Player();p=self.p
        self.stream=dict(Type='Subtitle',Index=3,Codec='subrip',Language='ger',IsForced=True,IsExternal=False)
        self.source=dict(Id='source',MediaStreams=[dict(Type='Video',Width=3840,Height=2160),self.stream])
        p.item=dict(MediaSources=[self.source]);p.item_id='film';p.media_source_id='source'
        p.playback_info=dict(server='http://127.0.0.1:%d'%self.server.server_port,token='test-only')
        p['state_label']=Label();p['external_subtitle_text']=Label()
        p.embyflow_v10_content_position_ticks=lambda:self.position*10000
        p.embyflow_srt_v2_generation=0;p.embyflow_active_subtitle_index=None
        p.embyflow_srt_v2_loading=False
        p.embyflow_srt_v2_cues=[];p.embyflow_srt_v2_starts=[]
        p.embyflow_srt_v2_download_timer=Timer();p.embyflow_srt_v2_render_timer=Timer()
        p.embyflow_srt_v2_render_timer.callback=[lambda:ns['_embyflow_srt_v4_render_tick'](p)]
        p.embyflow_srt_v2_overlay=None;p.session=types.SimpleNamespace()
    def tearDown(self):
        self.ns['_efseg_cancel'](self.p)
        if self.block is not None:self.block.set()
        self.server.shutdown();self.server.server_close();self.thread.join()
    def start(self):self.ns['_embyflow_srt_v2_start'](self.p,self.stream,'Deutsch',0,False)
    def finish(self):
        deadline=time.monotonic()+3
        while self.p._efseg_state['results'].empty() and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(self.p._efseg_state['results'].empty())
        self.ns['_efseg_poll'](self.p)
        self.p.embyflow_srt_v2_render_timer.fire()
    def test_actual_player_draws_downloaded_segment(self):
        self.p.set_preferred_subtitle_track()
        self.finish()
        self.assertEqual(self.p['external_subtitle_text'].text,'Deutsch 0')
        self.assertTrue(self.p['external_subtitle_text'].visible)
        self.assertEqual(self.p.embyflow_active_subtitle_stream_index,3)
        self.assertEqual(self.calls[0]['StartPositionTicks'],['0'])
        self.assertEqual(self.calls[0]['EndPositionTicks'],['600000000'])
        self.assertFalse(self.downloads)
    def test_prefetch_continues_and_cached_seek_back_draws(self):
        self.start();self.finish()
        self.position=47000;self.ns['_efseg_poll'](self.p);self.finish()
        self.position=62000;self.p.embyflow_srt_v2_render_timer.fire()
        self.assertEqual(self.p['external_subtitle_text'].text,'Deutsch 60000')
        self.position=2000;self.ns['_efseg_poll'](self.p);self.p.embyflow_srt_v2_render_timer.fire()
        self.assertEqual(self.p['external_subtitle_text'].text,'Deutsch 0')
        self.assertEqual(len(self.calls),2)
    def test_far_seek_fetches_current_minute_not_whole_movie(self):
        self.start();self.finish();self.position=602000
        self.ns['_efseg_poll'](self.p);self.finish()
        self.assertEqual(self.p['external_subtitle_text'].text,'Deutsch 600000')
        self.assertEqual(self.calls[-1]['StartPositionTicks'],['6000000000'])
    def test_empty_forced_interval_is_valid(self):
        self.empty=True;self.start();self.finish()
        self.assertFalse(self.p['external_subtitle_text'].visible)
        self.assertEqual(self.p._efseg_state['windows'],[(0,60000)])
    def test_failure_does_not_leave_false_active_check(self):
        self.fail=True;self.start();self.finish()
        self.assertIsNone(self.p._efseg_state)
        self.assertIsNone(self.p.embyflow_active_subtitle_index)
        self.assertFalse(self.p._efseg_timer.running)
    def test_close_cancels_fetch_and_hides(self):
        self.start();state=self.p._efseg_state
        self.p.embyflow_close_subtitle_window()
        self.assertTrue(state['cancel'].is_set())
        self.assertFalse(self.p._efseg_timer.running)
        self.assertFalse(self.p['external_subtitle_text'].visible)
    def test_hd_and_external_and_full_track_delegate(self):
        for change in ('hd','external','full'):
            self.stream.update(IsExternal=False,IsForced=True)
            self.source['MediaStreams'][0].update(Width=3840,Height=2160)
            if change=='hd':self.source['MediaStreams'][0].update(Width=1920,Height=1080)
            if change=='external':self.stream['IsExternal']=True
            if change=='full':self.stream['IsForced']=False
            self.start()
        self.assertEqual(len(self.downloads),3);self.assertFalse(self.calls)
    def test_manual_off_remains_authoritative(self):
        self.p._efut_manual=True;self.p.set_preferred_subtitle_track()
        self.assertFalse(self.calls);self.assertIsNone(getattr(self.p,'_efseg_state',None))
    def test_server_ignoring_absolute_ranges_is_rejected(self):
        response=Mock(status_code=200)
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.iter_content.return_value=[b'1\n00:00:01,000 --> 00:00:03,000\nwrong offset\n']
        fake=types.SimpleNamespace(get=Mock(return_value=response))
        self.ns['requests']=fake
        with self.assertRaises(RuntimeError):self.ns['_efseg_fetch'](['http://example.invalid/Items/a/b/Subtitles/3/stream.srt'],'test',600000,660000,threading.Event())
    def test_cached_window_returns_after_outside_seek(self):
        self.start();self.finish()
        state=self.p._efseg_state
        # Simulate a request in flight so seeking cannot create more workers.
        state['busy']=True;self.position=602000;self.ns['_efseg_poll'](self.p)
        self.assertEqual(self.p.embyflow_srt_v2_cues,[])
        self.position=2000;self.ns['_efseg_poll'](self.p);self.p.embyflow_srt_v2_render_timer.fire()
        self.assertEqual(self.p['external_subtitle_text'].text,'Deutsch 0')
        self.assertEqual(len(self.calls),1)
    def test_seek_does_not_spawn_parallel_requests_or_accept_old_result(self):
        self.block=threading.Event();self.start()
        deadline=time.monotonic()+2
        while not self.calls and time.monotonic()<deadline:time.sleep(.01)
        self.position=602000
        for _ in range(10):self.ns['_efseg_poll'](self.p)
        self.assertEqual(len(self.calls),1)
        self.block.set();self.finish();self.finish()
        self.assertEqual(self.p['external_subtitle_text'].text,'Deutsch 600000')
        self.assertEqual(len(self.calls),2)
    def test_manual_off_cancels_segment_and_stays_off(self):
        self.start();self.finish();state=self.p._efseg_state
        self.p._efut_manual=True
        self.ns['_embyflow_srt_v2_selection_finished'](self.p,('subtitle_off',None,'Aus',None))
        self.assertTrue(state['cancel'].is_set());self.assertIsNone(self.p._efseg_state)
        self.assertFalse(self.p['external_subtitle_text'].visible)
        self.p.set_preferred_subtitle_track();self.assertEqual(len(self.calls),1)
    def test_cache_bounded_and_evicted_seek_reloads(self):
        self.start();self.finish()
        for position in (47000,107000,167000,227000):
            self.position=position;self.ns['_efseg_poll'](self.p);self.finish()
            self.assertLessEqual(len(self.p._efseg_state['segments']),3)
        self.position=2000;self.ns['_efseg_poll'](self.p);self.finish()
        self.assertEqual(self.p['external_subtitle_text'].text,'Deutsch 0')
    def test_source_change_cancels_old_subtitles(self):
        self.start();self.finish();state=self.p._efseg_state
        self.p.media_source_id='different-version';self.ns['_efseg_poll'](self.p)
        self.assertTrue(state['cancel'].is_set());self.assertIsNone(self.p._efseg_state)
        self.assertFalse(self.p['external_subtitle_text'].visible)

if __name__=='__main__':unittest.main()

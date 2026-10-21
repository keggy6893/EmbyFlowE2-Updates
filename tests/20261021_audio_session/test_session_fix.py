import ast
import io
import time
import threading
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from build_session_fix import baseline, fix_source


ORIGINAL = baseline()
FIXED = fix_source(ORIGINAL)
TARGETS = ('_efa2_restart_4097', '_embyflow_v30_send_report_async',
           '_embyflow_seek_async_v17_5_6_report_worker')


class Thread:
    def __init__(self, target, args=(), **kw): self.target=target; self.args=args
    def start(self): self.target(*self.args)


class Timer:
    def start(self, *a): pass
    def stop(self): pass


class Ref:
    def __init__(self, kind, flags, url): self.type=kind; self.url=url
    def setName(self, name): pass


class SessionTests(unittest.TestCase):
    def run_flow(self, source, status=204, simulate_periodic=True):
        posts=[]; services=[]; cleanups=[]
        def post(url, **kwargs):
            posts.append((url, dict(kwargs['json'])))
            return NS(status_code=status, text='')
        p=NS(item={'embyflow_selected_audio_index':2}, position=6000000000,
             playback_info={'server':'https://example.invalid','token':'fake'},
             play_session_id='old-session', title_text='Test film', item_id='42',
             audio_timer=Timer(), seek_fallback_timer=Timer(), initial_big_seek_timer=Timer(),
             paused=False, closed=False)
        p.embyflow_v10_stream_context=lambda: ('https://example.invalid','fake','42','source',2)
        p.emby_report_payload=lambda pos: dict(PlaySessionId=p.play_session_id, PositionTicks=pos,
                                              AudioStreamIndex=p.item['embyflow_selected_audio_index'],
                                              PlayMethod='DirectStream', ItemId='42')
        p.show_overlay=lambda: None; p.update_playback_overlay=lambda: None
        p.cancel_active_encoding=lambda sid: cleanups.append(sid)
        ns=dict(time=time, requests=True, EMBY_SERVER='', AUTH_HEADER='fake',
                uuid4=lambda: NS(hex='new-session'), eServiceReference=Ref,
                embyflow_http_post=post, embyflow_open_log=lambda *a,**kw: io.StringIO(),
                _embyflow_seek_async_v17_5_6_log=lambda msg: None,
                _embyflow_seek_async_v17_5_6_cancel_worker=lambda p,sid,*a: cleanups.append(sid),
                _efguard_play_service=lambda nav,ref: services.append(ref))
        p.session=NS(nav=object())
        tree=ast.parse(source)
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in TARGETS]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'session-regression','exec'),ns)
        p.send_emby_playback_report=lambda endpoint,pos: ns['_embyflow_v30_send_report_async'](p,endpoint,pos)
        with patch('threading.Thread', Thread), patch('time.sleep', lambda seconds: None):
            self.assertTrue(ns['_efa2_restart_4097'](p,p.position,audio_index_override=5))
            # The original caller updated the selected track after restart returned.
            p.item['embyflow_selected_audio_index']=5
            if simulate_periodic:
                for seconds in (10,20,30,40,60):
                    p.send_emby_playback_report('Progress', p.position+seconds*10000000)
        return p, posts, services, cleanups
    def test_published_baseline_reproduces_duplicate_playing(self):
        p,posts,*_=self.run_flow(ORIGINAL)
        playing=[x for x in posts if x[0].endswith('/Playing?reqformat=json')]
        self.assertEqual(len(playing),2)
    def test_fixed_flow_announces_once_through_60_seconds(self):
        p,posts,*_=self.run_flow(FIXED)
        self.assertEqual(len([x for x in posts if x[0].endswith('/Playing?reqformat=json')]),1)
        self.assertEqual(len([x for x in posts if '/Progress?' in x[0]]),6)
        self.assertIn('new-session',p._embyflow_v112_announced_sessions)
    def test_every_report_keeps_selected_audio_and_new_session(self):
        p,posts,*_=self.run_flow(FIXED)
        self.assertTrue(posts)
        for url,payload in posts:
            self.assertEqual(payload['AudioStreamIndex'],5)
            self.assertEqual(payload['PlaySessionId'],'new-session')
            self.assertEqual(payload['PlayMethod'],'DirectStream')
    def test_playing_precedes_first_progress(self):
        p,posts,*_=self.run_flow(FIXED)
        self.assertTrue(posts[0][0].endswith('/Playing?reqformat=json'))
        self.assertIn('/Progress?',posts[1][0])
    def test_rejected_playing_never_sends_progress(self):
        p,posts,*_=self.run_flow(FIXED,status=500)
        self.assertFalse([x for x in posts if '/Progress?' in x[0]])
        self.assertNotIn('new-session',p._embyflow_v112_announced_sessions)
    def test_backend_resume_url_and_old_session_cleanup_retained(self):
        from urllib.parse import urlparse,parse_qs
        p,posts,services,cleanups=self.run_flow(FIXED)
        self.assertEqual(len(services),1); self.assertEqual(services[0].type,4097)
        q=parse_qs(urlparse(services[0].url).query)
        self.assertEqual(q['AudioStreamIndex'],['5']); self.assertEqual(q['StartTimeTicks'],['6000000000'])
        self.assertEqual(cleanups,['old-session'])
        self.assertEqual(p.embyflow_v10_stream_base_ticks,6000000000)


if __name__=='__main__': unittest.main(verbosity=2)

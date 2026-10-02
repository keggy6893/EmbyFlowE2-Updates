import ast
import pathlib
import sys
import types
import threading
import unittest
from unittest.mock import patch

class Label:
    def __init__(self, text=''): self.text=text
    def setText(self,text): self.text=text
class Timer:
    def __init__(self): self.callback=[]; self.running=False
    def start(self,*a): self.running=True
    def stop(self): self.running=False
class Screen(dict):
    def __init__(self,session):
        super().__init__(); self.session=session; self.onClose=[]; self.onLayoutFinish=[]
    def close(self):
        for f in self.onClose: f()
class Detail(Screen):
    def __init__(self,session,data):
        super().__init__(session); self.data=dict(data); self.detail_focus=0
        self._fallback_poll_timer=Timer()
        self.skin='''<screen>
        <eLabel position="1260,320" size="300,70" zPosition="9"/>
        <eLabel position="1260,420" size="300,70" zPosition="9"/>
        <widget name="detail_play_btn" position="1260,320" size="300,70"/>
        <widget name="detail_back_btn" position="1260,420" size="300,70"/>
        <widget name="poster" position="1490,560" size="270,405"/>
        </screen>'''
        self['detail_play_btn']=Label(); self['detail_back_btn']=Label()
        self.play_count=0
    def update_detail_focus(self): pass
    def detail_up(self): self.detail_focus=0
    def detail_down(self): self.detail_focus=1
    def detail_ok(self):
        if self.detail_focus==0: self.play_count+=1
        else: self.close()
class Ref:
    def __init__(self,*args): self.args=args
    def setName(self,name): self.name=name
class Volume:
    muted=True
    @classmethod
    def getInstance(cls): return cls
    @classmethod
    def isMuted(cls): return cls.muted
    @classmethod
    def volumeMute(cls): cls.muted=True
    @classmethod
    def volumeUnMute(cls): cls.muted=False
message=types.ModuleType('Screens.MessageBox')
message.MessageBox=type('MessageBox',(),{'TYPE_INFO':0,'TYPE_ERROR':1})
enigma=types.ModuleType('enigma')
enigma.eServiceReference=Ref; enigma.eDVBVolumecontrol=Volume
sys.modules['Screens.MessageBox']=message; sys.modules['enigma']=enigma
env=dict(Screen=Screen,EmbyFlowDetailScreen=Detail,Label=Label,eTimer=Timer,
         ActionMap=lambda *a: a,sx=lambda x:x,sy=lambda y:y,AUTH_HEADER='auth')
source=pathlib.Path(__file__).with_name('trailer_layer.py').read_text()
ast.parse(source); exec(compile(source,'trailer_layer.py','exec'),env)

class Tests(unittest.TestCase):
    def test_layout_and_navigation(self):
        screen=Detail(None,{'title':'Different Movie','type':'Movie'})
        root=env['_eftr_xml'].fromstring(screen.skin)
        labels=[x for x in root if x.tag=='eLabel']
        self.assertEqual([x.get('position') for x in labels],['1260,280','1260,370'])
        widgets={x.get('name'):x for x in root if x.tag=='widget'}
        for name,y in [('detail_play_btn',280),('detail_back_btn',370),('trailer_button',460)]:
            self.assertEqual(widgets[name].get('position'),'1260,%d'%y)
            self.assertEqual(widgets[name].get('size'),'300,70')
        self.assertEqual(widgets['poster'].get('position'),'1490,560')
        screen.detail_ok(); self.assertEqual(screen.play_count,1)
        screen.detail_down(); screen.detail_down(); self.assertEqual(screen.detail_focus,2)
        called=[]; screen.trailer_begin=lambda:called.append(True)
        screen.detail_ok(); self.assertEqual(called,[True])
        screen.detail_up(); self.assertEqual(screen.detail_focus,1)
        screen.trailer_close()

    def test_audio_unchanged(self):
        screen=Detail(None,{'type':'Audio'})
        self.assertFalse(screen._trailer_enabled)
        self.assertNotIn('trailer_button',screen)
        screen.trailer_close()

    def test_series_parent(self):
        calls=[]
        def get(url,**kwargs):
            calls.append(url)
            data=({'Type':'Episode','SeriesId':'series-42'} if len(calls)==1
                  else {'Type':'Series','RemoteTrailers':[{'Url':'https://youtu.be/series-trailer'}]})
            return types.SimpleNamespace(status_code=200,json=lambda:data)
        env['embyflow_http_get']=get
        result=env['_eftr_lookup']({'id':'episode-7'},('https://emby','token','user'),threading.Event())
        self.assertEqual(result,'https://youtu.be/series-trailer')
        self.assertTrue(calls[1].endswith('/series-42'))

    def test_no_trailer_and_domain(self):
        env['embyflow_http_get']=lambda *a,**k:types.SimpleNamespace(
            status_code=200,json=lambda:{'Type':'Movie'})
        with self.assertRaisesRegex(RuntimeError,'kein YouTube-Trailer'):
            env['_eftr_lookup']({'id':'movie'},('https://emby','token','user'),threading.Event())
        self.assertFalse(env['_eftr_youtube_url']('https://youtube.com.evil.invalid/x'))
        self.assertFalse(env['_eftr_youtube_url']('file:///tmp/video'))
        self.assertTrue(env['_eftr_youtube_url']('https://www.youtube.com/watch?v=x'))

    def test_hls_separate_audio_and_resolution(self):
        video=lambda h,u:dict(protocol='m3u8_native',vcodec='avc1.4D401F',
                              acodec='none',height=h,url=u,tbr=h)
        formats=[video(1080,'https://1080'),video(720,'https://720'),
                 video(360,'https://360'),
                 dict(protocol='m3u8_native',vcodec='none',acodec='unknown',url='https://audio',tbr=128)]
        path,playlist=env['_eftr_select_stream']({'formats':formats})
        self.assertIsNone(path); self.assertIn('https://720',playlist)
        self.assertIn('URI="https://audio"',playlist); self.assertNotIn('1080',playlist)
        with self.assertRaises(RuntimeError):
            env['_eftr_select_stream']({'formats':[video(720,'https://silent')]})

    def test_combined_mp4(self):
        path,playlist=env['_eftr_select_stream']({'formats':[
            dict(vcodec='avc1.4',acodec='mp4a.40.2',height=480,url='https://combined')]})
        self.assertEqual(path,'https://combined'); self.assertIsNone(playlist)

    def test_resolver_checksum(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env['_EFTR_RESOLVER_PATH']=str(pathlib.Path(d)/'yt-dlp')
            class Response:
                def __enter__(self): return self
                def __exit__(self,*a): pass
                def read(self,n): return b'corrupted'
            previous=env['_eftr_urlopen']
            env['_eftr_urlopen']=lambda *a,**k:Response()
            try:
                with self.assertRaisesRegex(RuntimeError,'nicht korrekt'):
                    env['_eftr_ensure_resolver'](threading.Event())
                self.assertFalse(pathlib.Path(env['_EFTR_RESOLVER_PATH']).exists())
            finally: env['_eftr_urlopen']=previous

    def test_player_exit_stops_once_restores_mute(self):
        calls=[]
        nav=types.SimpleNamespace(playService=lambda ref:0,stopService=lambda:calls.append('stop'))
        session=types.SimpleNamespace(nav=nav,open=lambda *a:None)
        Volume.muted=True
        player=env['EmbyFlowTrailerPlayer'](session,'/tmp/trailer.m3u8','Title')
        player.start(); self.assertFalse(Volume.muted)
        player.leave(); player.cleanup()
        self.assertEqual(calls,['stop']); self.assertTrue(Volume.muted)

    def test_cancel_process(self):
        screen=Detail(None,{'title':'Movie','type':'Movie'})
        calls=[]; screen._trailer_process=types.SimpleNamespace(kill=lambda:calls.append('kill'))
        screen.trailer_close()
        self.assertTrue(screen._trailer_cancel.is_set())
        self.assertEqual(calls,['kill'])
        self.assertFalse(screen._trailer_timer.running)

if __name__=='__main__':
    unittest.main()

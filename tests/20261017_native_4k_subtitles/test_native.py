import pathlib,types,unittest,importlib.util
from install import PATCH,patched

class Timer:
    def __init__(self):self.callback=[];self.running=False
    def start(self,*a):self.running=True
    def stop(self):self.running=False
    def fire(self):
        self.running=False
        for callback in self.callback:callback()

class NativeTests(unittest.TestCase):
    def setUp(self):
        root=pathlib.Path(__file__).resolve().parents[2]
        spec=importlib.util.spec_from_file_location('v2',root/'tests/20261017_forced_subtitles_v2/install.py')
        v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(v2)
        class Player(dict):
            set_preferred_subtitle_track=lambda p:None
        self.Player=Player
        self.downloads=[];self.enabled=[];self.disabled=[];self.closed=[]
        Player.embyflow_close_subtitle_window=lambda p:self.closed.append(True)
        def stop(p,invalidate=True):p.embyflow_srt_v2_loading=False
        ns=dict(EmbyFlowMoviePlayer=Player,_embyflow_srt_v2_start=lambda *a:self.downloads.append(a),
            _embyflow_srt_v2_stop=stop,eTimer=Timer,
            _embyflow_srt_v2_connect_timer=lambda p,t,cb,n:t.callback.append(cb),
            _embyflow_srt_v2_is_text_stream=lambda s:s.get('Codec')=='subrip',
            _embyflow_subtitle_flags_0629=lambda s:'Erzw.' if s.get('IsForced') else '')
        # V2 supplies the same active-source inventory and language helpers as the release.
        exec(v2.PATCH,ns);exec(PATCH,ns);self.ns=ns
        self.stream={'Type':'Subtitle','Index':3,'Language':'ger','Codec':'subrip','IsForced':True,'IsExternal':False}
        self.full={'Type':'Subtitle','Index':4,'Language':'ger','Codec':'subrip','IsForced':False,'IsExternal':False}
        self.source={'Id':'active','MediaStreams':[{'Type':'Video','Width':3840,'Height':2160},self.stream,self.full]}
        self.entries=[(2,0,4,0,'ger'),(2,1,4,0,'ger')]
        interface=types.SimpleNamespace(getSubtitleList=lambda:self.entries,
            enableSubtitles=lambda *a:self.enabled.append(a),disableSubtitles=lambda *a:self.disabled.append(a))
        self.p=Player();self.p.item={'MediaSources':[self.source]};self.p.media_source_id='active'
        self.p.stream_url='http://example.invalid/Videos/film/stream.mkv?Static=true'
        self.p.session=types.SimpleNamespace(nav=types.SimpleNamespace(getCurrentService=lambda:types.SimpleNamespace(subtitle=lambda:interface)))
        self.p['state_label']=types.SimpleNamespace(setText=lambda text:None)
        self.p.embyflow_srt_v2_loading=False;self.p.embyflow_active_subtitle_index=None
        self.window=types.SimpleNamespace(instance=object(),show=lambda:None,hide=lambda:None)
        self.p.embyflow_subtitle_window=self.window
        self.p.embyflow_get_subtitle_window=lambda:self.window
    def start(self,stream=None,position=0):self.ns['_embyflow_srt_v2_start'](self.p,stream or self.stream,'Deutsch',position,False)
    def test_native_4k_no_download(self):
        self.start()
        self.assertEqual(len(self.enabled),1);self.assertFalse(self.downloads)
        self.assertEqual(self.enabled[0][1],self.entries[0])
        self.assertEqual(self.p.embyflow_active_subtitle_stream_index,3)
        self.assertEqual(self.source['DefaultSubtitleStreamIndex'],3)
        self.assertFalse(self.p.embyflow_srt_v2_loading)
    def test_hd_keeps_download(self):
        self.source['MediaStreams'][0].update(Width=1920,Height=1080)
        self.start();self.assertFalse(self.enabled);self.assertEqual(len(self.downloads),1)
    def test_external_keeps_download(self):
        self.stream['IsExternal']=True;self.start()
        self.assertFalse(self.enabled);self.assertEqual(len(self.downloads),1)
    def test_unknown_external_keeps_download(self):
        self.stream.pop('IsExternal');self.start();self.assertEqual(len(self.downloads),1)
    def test_transcode_keeps_download(self):
        self.p.stream_url='http://example.invalid/Videos/film/main.m3u8?Static=false'
        self.start();self.assertEqual(len(self.downloads),1)
    def test_full_track_keeps_download(self):
        self.start(self.full,1);self.assertEqual(len(self.downloads),1)
    def test_wait_for_backend(self):
        self.entries=[];self.start();self.assertFalse(self.downloads)
        self.entries=[(2,0,4,0,'ger'),(2,1,4,0,'ger')]
        self.p._efn4_timer.fire();self.assertEqual(len(self.enabled),1)
    def test_mismatch_never_guesses(self):
        self.entries=[(2,0,4,0,'ger')];self.start()
        for _ in range(8):self.p._efn4_timer.fire()
        self.assertFalse(self.enabled);self.assertEqual(len(self.downloads),1)
    def test_language_mismatch_never_guesses(self):
        self.entries[0]=(2,0,4,0,'eng');self.start()
        for _ in range(8):self.p._efn4_timer.fire()
        self.assertFalse(self.enabled)
    def test_stop_disables_native(self):
        self.start();self.ns['_embyflow_srt_v2_stop'](self.p,True)
        self.assertEqual(len(self.disabled),2);self.assertIsNone(self.p._efn4_active)
    def test_stop_cancels_pending(self):
        self.entries=[];self.start();timer=self.p._efn4_timer
        self.ns['_embyflow_srt_v2_stop'](self.p,True)
        self.entries=[(2,0,4,0,'ger'),(2,1,4,0,'ger')];timer.fire()
        self.assertFalse(self.enabled);self.assertFalse(timer.running)
    def test_close_disables_and_delegates(self):
        self.start();self.p.embyflow_close_subtitle_window()
        self.assertEqual(len(self.disabled),2);self.assertEqual(self.closed,[True])
    def test_cached_track_rebinds_window(self):
        class Backend:
            current=0
            owner=None
            def getSubtitleList(inner):return self.entries
            def disableSubtitles(inner,widget):inner.current=-1;inner.owner=None
            def enableSubtitles(inner,widget,entry):
                # Actual early-return condition in openATV serviceMP3.
                if inner.current==entry[1]:return 0
                inner.current=entry[1];inner.owner=widget;return 0
        backend=Backend()
        # Previous test would accept return 0 while no display owner is attached.
        self.assertEqual(backend.enableSubtitles(self.window.instance,self.entries[0]),0)
        self.assertIsNone(backend.owner)
        self.p.session.nav.getCurrentService=lambda:types.SimpleNamespace(subtitle=lambda:backend)
        self.start()
        self.assertIs(backend.owner,self.window.instance)
        self.assertEqual(self.p.embyflow_active_subtitle_stream_index,3)
    def test_backend_error_not_marked_active(self):
        backend=types.SimpleNamespace(getSubtitleList=lambda:self.entries,
            disableSubtitles=lambda widget:None,enableSubtitles=lambda *a:-1)
        self.p.session.nav.getCurrentService=lambda:types.SimpleNamespace(subtitle=lambda:backend)
        self.start();self.assertIsNone(self.p.embyflow_active_subtitle_index)
        self.assertEqual(len(self.downloads),1)
    def test_full_compilation(self):
        root=pathlib.Path(__file__).resolve().parents[2]
        output=patched((root/'EmbyFlowE2_2026101703.py').read_text())
        compile(output,'plugin.py','exec')

if __name__=='__main__':unittest.main()

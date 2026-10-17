import importlib.util,pathlib,types,unittest
from install import PATCH,patched

ROOT=pathlib.Path(__file__).resolve().parents[2]

class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.fallback=[];self.records=[];self.messages=[]
        class Player(dict):
            set_preferred_subtitle_track=lambda p:self.fallback.append(True)
            def show_overlay(p):self.messages.append(True)
        spec=importlib.util.spec_from_file_location('v2',ROOT/'tests/20261017_forced_subtitles_v2/install.py')
        v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(v2)
        ns={'EmbyFlowMoviePlayer':Player};exec(v2.PATCH,ns)
        Player.set_preferred_subtitle_track=lambda p:self.fallback.append(True)
        ns.update(_embyflow_srt_v2_start=lambda *a:self.calls.append(a),_embyflow_srt_v2_language=lambda *a:'Deutsch')
        exec(PATCH,ns);ns['_efsc_record']=lambda *a:self.records.append(a)
        self.ns=ns;self.Player=Player
        self.embedded=dict(Type='Subtitle',Index=3,Language='ger',Codec='subrip',IsForced=True,IsExternal=False)
        self.external=dict(self.embedded,Index=47,IsExternal=True)
        self.source={'Id':'active','DefaultSubtitleStreamIndex':3,'MediaStreams':[dict(Type='Video',Width=3840,Height=2160),self.embedded,self.external]}
        self.p=Player();self.p.item={'MediaSources':[self.source]};self.p.media_source_id='active'
        self.p.embyflow_srt_v2_loading=False;self.p.embyflow_active_subtitle_index=None
        self.p['state_label']=types.SimpleNamespace(setText=lambda text:self.messages.append(text))
    def test_external_replaces_embedded_forced_default(self):
        self.p.set_preferred_subtitle_track()
        self.assertEqual(self.calls[0][1]['Index'],47)
        self.assertEqual(self.calls[0][3],1)
        # No false active checkmark before actual download/activation.
        self.assertIsNone(self.p.embyflow_active_subtitle_index)
    def test_hd_delegates_unchanged(self):
        self.source['MediaStreams'][0].update(Width=1920,Height=1080)
        self.p.set_preferred_subtitle_track();self.assertEqual(self.fallback,[True]);self.assertFalse(self.calls)
    def test_manual_off_respected(self):
        self.p._efut_manual=True;self.p.set_preferred_subtitle_track();self.assertFalse(self.calls)
    def test_loading_does_not_duplicate(self):
        self.p.embyflow_srt_v2_loading=True;self.p.set_preferred_subtitle_track();self.assertFalse(self.calls)
    def test_missing_file_reported_not_synthesized(self):
        self.source['MediaStreams'].remove(self.external)
        self.p.set_preferred_subtitle_track()
        self.assertFalse(self.calls);self.assertFalse(self.fallback)
        self.assertEqual(self.records[0][0],'missing_external_german_forced_srt')
    def test_full_german_default_preserved(self):
        self.embedded['IsForced']=False
        self.p.set_preferred_subtitle_track();self.assertEqual(self.fallback,[True]);self.assertFalse(self.calls)
    def test_foreign_external_not_selected(self):
        self.external['Language']='eng'
        self.p.set_preferred_subtitle_track();self.assertFalse(self.calls)
    def test_external_nonforced_not_selected(self):
        self.external['IsForced']=False
        self.p.set_preferred_subtitle_track();self.assertFalse(self.calls)
    def test_pgs_not_selected(self):
        self.external['Codec']='pgs'
        self.p.set_preferred_subtitle_track();self.assertFalse(self.calls)
    def test_native_test_unhooked(self):
        start=lambda *a:self.calls.append(a)
        stop=lambda *a:None
        close=lambda *a:None
        self.ns.update(_efn4_start_before=start,_efn4_stop_before=stop,_efn4_close_before=close)
        exec(PATCH,self.ns)
        self.assertIs(self.ns['_embyflow_srt_v2_start'],start)
        self.assertIs(self.ns['_embyflow_srt_v2_stop'],stop)
        self.assertIs(self.Player.embyflow_close_subtitle_window,close)
    def test_installs_over_stacked_experiments(self):
        source=(ROOT/'EmbyFlowE2_2026101703.py').read_text()
        for path in ('20261017_subtitle_request_v4','20261017_native_4k_subtitles'):
            spec=importlib.util.spec_from_file_location(path,ROOT/'tests'/path/'install.py')
            m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
            source=m.patched(source)
        result=patched(source)
        self.assertNotIn("kwargs['timeout'] = (5, 15)",result)
        self.assertIn("kwargs['timeout'] = (5, 120)",result)
        compile(result,'plugin.py','exec')
        with self.assertRaises(RuntimeError):patched(result)

if __name__=='__main__':unittest.main()

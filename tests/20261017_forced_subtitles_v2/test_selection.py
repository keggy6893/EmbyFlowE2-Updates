import importlib.util, pathlib, types, unittest
from install import PATCH, patched

class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.timers=[]
        class Player:pass
        self.ns=dict(EmbyFlowMoviePlayer=Player,
            _embyflow_srt_v2_start=lambda *a:self.calls.append(a),
            _embyflow_srt_v2_language=lambda *a:'Deutsch',
            _embyflow_srt_v2_is_text_stream=lambda s:s.get('Codec')=='srt')
        exec(PATCH,self.ns)
        self.p=Player();self.p.media_source_id='active'
        self.stream={'Type':'Subtitle','Index':5,'Language':'ger','IsForced':True,'Codec':'srt'}
        self.p.item={'MediaSources':[
            {'Id':'inactive','DefaultSubtitleStreamIndex':7,'MediaStreams':[]},
            {'Id':'active','DefaultSubtitleStreamIndex':-1,'MediaStreams':[self.stream]}]}
        self.p.embyflow_srt_v2_loading=False;self.p.embyflow_active_subtitle_index=None
        self.p.subtitle_timer=types.SimpleNamespace(start=lambda *a:self.timers.append(a))
    def test_v1_misses_active_source_v2_selects(self):
        path=pathlib.Path(__file__).resolve().parents[1]/'20261017_forced_subtitles/install.py'
        spec=importlib.util.spec_from_file_location('v1',path);v1=importlib.util.module_from_spec(spec);spec.loader.exec_module(v1)
        class OldPlayer:
            set_preferred_subtitle_track=lambda p:None
            subtitle_selection_finished=lambda p,r:None
        ns=dict(self.ns,EmbyFlowMoviePlayer=OldPlayer,
            _embyflow_srt_v2_streams=lambda p:p.item['MediaSources'][0]['MediaStreams'])
        exec(v1.PATCH,ns)
        ns['_efut_auto'](self.p)
        self.assertFalse(self.calls)
        self.p.set_preferred_subtitle_track()
        self.assertEqual(self.calls[0][1]['Index'],5)
    def test_german_variants(self):
        for language in ('ger','deu','de','de-DE','de_AT','German','Deutsch'):
            self.assertTrue(self.ns['_efut2_german']({'Language':language}))
        self.assertFalse(self.ns['_efut2_german']({'Language':'eng','DisplayTitle':'German movie'}))
    def test_default_zero_preserved(self):
        self.stream['Index']=0
        self.p.item['MediaSources'][1]['DefaultSubtitleStreamIndex']=0
        self.p.set_preferred_subtitle_track()
        self.assertEqual(self.calls[0][1]['Index'],0)
    def test_late_streams_retry_bounded(self):
        source=self.p.item['MediaSources'][1];source['MediaStreams']=[]
        for _ in range(10):self.p.set_preferred_subtitle_track()
        self.assertEqual(len(self.timers),4)
        source['MediaStreams']=[self.stream]
        self.p.set_preferred_subtitle_track()
        self.assertEqual(len(self.calls),1)
    def test_missing_active_never_uses_other_source(self):
        self.p.media_source_id='missing'
        self.p.item['MediaSources'][0]['MediaStreams']=[self.stream]
        self.p.set_preferred_subtitle_track();self.assertFalse(self.calls)
    def test_manual_off(self):
        self.p._efut_manual=True
        self.p.set_preferred_subtitle_track();self.assertFalse(self.calls)
    def test_unsupported_bitmap(self):
        self.stream['Codec']='pgs'
        self.p.set_preferred_subtitle_track();self.assertFalse(self.calls)

if __name__=='__main__':unittest.main()

"""Exercise the actual appended matcher without importing Enigma2."""
import ast
import pathlib
import types
from build import build
ROOT=pathlib.Path(__file__).resolve().parents[2]
source=build().read_text()
base_text=(ROOT/'EmbyFlowE2_2026102502.py').read_text()
class Player:
    pass
for name in ('set_preferred_audio_track','open_audio_selection','audio_selection_finished','embyflow_media_streams_by_type','embyflow_apply_confirmed_audio_track'):
    setattr(Player,name,lambda *a:'previous')
ns=dict(EmbyFlowMoviePlayer=Player,_EFA2_OPEN=lambda p:'native-menu',
        _EFA2_SELECT=lambda p,r:'native-select',_DF_APPLY_BEFORE=lambda *a:None,
        _embyflow_rcdev7_static_direct=lambda p:p.direct,
        MessageBox=types.SimpleNamespace(TYPE_INFO=1,TYPE_ERROR=2),RISKY_AUDIO=())
base=ast.parse(base_text)
for node in base.body:
    if isinstance(node,ast.FunctionDef) and node.name in ('audio_stream_text','audio_stream_is_unwanted','audio_stream_score','audio_codec_is_risky','_df_source'):
        exec(ast.get_source_segment(base_text,node),ns)
exec(pathlib.Path(__file__).with_name('runtime.py').read_text(),ns)
logs=[]
ns['_efua_log']=lambda event,**fields:logs.append((event,fields))
class Ref:
    type=4097
    def __str__(self):return 'stable-reference'
class Tracks:
    def __init__(self,descs):self.descs=descs;self.current=0;self.calls=[]
    def getNumberOfTracks(self):return len(self.descs)
    def getCurrentTrack(self):return self.current
    def selectTrack(self,i):self.calls.append(i);self.current=i
class P(Player):
    def __init__(self,langs,streams,direct=True,local=False):
        self.direct=direct;self.play_session_id='session';self.media_source_id='wanted'
        self.item={'MediaSources':[{'Id':'other','MediaStreams':[]},{'Id':'wanted','MediaStreams':streams}]}
        self.playback_info={'item':self.item,'local_file':local}
        self.descs=[dict(e2_index=i,language_key=lang,codec_key='ac3',description='AC3') for i,lang in enumerate(langs)]
        self.tracks=Tracks(self.descs);self.timer_calls=[]
        self.audio_timer=types.SimpleNamespace(start=lambda *x:self.timer_calls.append(x),stop=lambda:None)
        self.session=types.SimpleNamespace(nav=types.SimpleNamespace(getCurrentlyPlayingServiceReference=lambda:Ref(),getCurrentService=lambda:types.SimpleNamespace(audioTracks=lambda:self.tracks)),open=lambda *a,**kw:'message')
    def embyflow_audio_track_descriptor(self,t,i):return self.descs[i]
    def embyflow_audio_language_key(self,s):return {'deu':'de','eng':'en','ger':'de'}.get(s,s)
    def embyflow_audio_codec_key(self,s):return s
    def embyflow_extract_audio_payload(self,r):return r
streams=[dict(Type='Audio',Index=8,Language='deu',Codec='ac3'),dict(Type='Audio',Index=3,Language='eng',Codec='ac3')]
p=P(['en','de'],streams);p.set_preferred_audio_track()
assert p.tracks.calls==[1] and p.item['embyflow_selected_audio_index']==8
assert p.open_audio_selection()=='native-menu'
assert p.audio_selection_finished({'e2_index':1})=='native-select'
p=P(['en','de'],streams);p.embyflow_manual_audio_selected=True;p.set_preferred_audio_track();assert not p.tracks.calls
p=P(['en'],streams);p.set_preferred_audio_track();assert not p.tracks.calls and p.timer_calls
for unused in range(10):p.set_preferred_audio_track()
assert len(p.timer_calls)==7
p=P(['en','de'],streams,direct=False,local=True);p.set_preferred_audio_track();assert p.tracks.calls==[1]
p=P(['en','de'],streams,direct=False);assert p.set_preferred_audio_track()=='previous'
p=P(['en','de'],streams);p._efa2_server_session='session';assert p.set_preferred_audio_track()=='previous'
p._efa2_pending=True;assert p.open_audio_selection()=='message'
assert p.embyflow_media_streams_by_type('Audio')=='previous'
p=P(['en','de'],streams);assert p.embyflow_media_streams_by_type('Audio')==streams
# Native German survives misleading IsForced on an Audio stream, as in 2012.
forced=[dict(Type='Audio',Index=8,Language='ger',Codec='dts',IsForced=True),streams[1]]
p=P(['en','de'],forced);p.set_preferred_audio_track();assert p.tracks.calls==[1]
# Deferred native confirmation retries without declaring success early.
p=P(['en','de'],streams);p.tracks.selectTrack=lambda i:p.tracks.calls.append(i)
p.set_preferred_audio_track();assert p.timer_calls and 'embyflow_selected_audio_index' not in p.item
# Only the four release fields and the appended audio patch may differ.
release=ast.parse(source.split('# EMBYFLOW_UNIVERSAL_DIRECT_AUDIO_V1_20261028')[0])
names={'PLUGIN_VERSION','PLUGIN_BUILD_DATE','PLUGIN_UPDATE_BUILD','PLUGIN_UPDATE_CHANGELOG'}
for tree in (base,release):
    tree.body=[n for n in tree.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
assert ast.dump(base)==ast.dump(release)
ast.parse(source,feature_version=(3,8))
assert 'EMBYFLOW_TRACK_FREEZE_WATCHDOG_V1_20261028' not in source
assert 'EMBYFLOW_LOCAL_TS_NATIVE_SUBTITLES_20261028_V2' not in source
print('PASS: German mapping; manual priority; bounded retries; direct/local/remux routing; pending feedback; source scope; forced audio metadata; deferred confirmation; public AST scope; Python 3.8 syntax.')

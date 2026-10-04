from pathlib import Path
import ast,json,subprocess,sys,tempfile,types,threading
from unittest.mock import Mock
root=Path(__file__).resolve().parents[1]
s=(root/'EmbyFlowE2_Resolver_Dreambox_20261004_0403.py').read_text()
tree=ast.parse(s)
child=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_TRISO_CODE' for t in n.targets))
with tempfile.TemporaryDirectory() as d:
 package=Path(d)/'yt_dlp';package.mkdir()
 (package/'__init__.py').write_text('''
class YoutubeDL:
    def __init__(self,params): self.params=params
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def extract_info(self,url,download=False):
        if 'dead' in url: raise RuntimeError('dead first link')
        if url.startswith('ytsearch'):
            return {'entries':[{'id':'abcdefghijk','title':'Example Film Trailer (2009)','channel':'KinoCheck','duration':120}]}
        return {'title':'Example Film Trailer (2009)','channel':'KinoCheck','duration':120,'url':'https://media.invalid/audio.m4a',
                'formats':[{'protocol':'m3u8_native','height':720,'vcodec':'avc1','acodec':'mp4a','url':'https://media.invalid/video.m3u8'}]}
''')
 meta={'title':'Example Film','original':'','year':'2009','series':False}
 for payload in (
   {'url':'https://www.youtube.com/watch?v=dead','context':[meta,['https://www.youtube.com/watch?v=dead']],'format':'bv*[height<=720]/b'},
   {'url':'https://www.youtube.com/watch?v=abcdefghijk','context':None,'format':'bestaudio[ext=m4a]/bestaudio'}):
    r=subprocess.run([sys.executable,'-c',child,d,json.dumps(payload)],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    out=json.loads(r.stdout);assert out['url']=='https://media.invalid/audio.m4a'
    if payload['context']:
        assert 'TRAILER_LINK_FEHLER' in r.stderr and 'TRAILER_GEFUNDEN' in r.stderr
# A foreign import remains untouched; context reaches the child launcher.
functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
def fn(name,env):
 exec(compile(ast.Module(body=[functions[name]],type_ignores=[]),'test','exec'),env)
 return env[name]
foreign=types.SimpleNamespace(__file__='/other/plugin/yt_dlp/__init__.py')
popen=Mock()
env={'_eftr_sys':types.SimpleNamespace(modules={'yt_dlp':foreign}), '_EFTR_RESOLVER_PATH':'/verified/yt-dlp',
 '_trall_lock':threading.Lock(),'_trall_context':{'url':(meta,['url'])},'_trcache_log':Mock(), '_eftr_subprocess':types.SimpleNamespace(Popen=popen),
 '_TRISO_CODE':child,'_eftr_json':json,'_TRISO_ORIGINAL_POPEN':Mock()}
fn('_triso_popen',env)(['python','/verified/yt-dlp','-f','format','url'],stdout=1)
assert json.loads(popen.call_args.args[0][-1])['context']==[meta,['url']]
assert env['_eftr_sys'].modules['yt_dlp'] is foreign
assert "_efbg_diagnose(data, process.returncode, stderr, 'VIDEO')" in s
print('PASS: real child process retries dead link through matching search, audio resolves in isolation, foreign module preserved and failure logging installed.')

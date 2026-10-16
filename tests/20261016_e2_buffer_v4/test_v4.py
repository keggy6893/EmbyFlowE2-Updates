import ast, pathlib,tempfile,json,time,os,types,sys,hashlib
bridge=pathlib.Path('e2-buffer-test/bridge_v4.py').read_text()
functions={'_efb_enabled','_efb_read_settings','_efb_log','_efb_save','_efb_player_init','_efb_runtime_state','_efb_stats'}
nodes=[n for n in ast.parse(bridge).body if isinstance(n,ast.FunctionDef) and n.name in functions]
class Timer:
 def __init__(self):self.callback=[]
 def start(self,*args):self.args=args
 def stop(self):pass
class Ref:
 def __init__(self,path):self.path=path
 def getPath(self):return self.path
class Nav:
 def getCurrentlyPlayingServiceReference(self):return Ref(self.path)
class Player:
 def __init__(self):
  self.session=types.SimpleNamespace(nav=Nav());self.onClose=[];self.stream_url=''
class Proxy:
 lock=__import__('threading').RLock();routes={}
 def buffered(self):return 8*1024*1024
pkg=types.ModuleType('buffer_test');pkg.__path__=[];sys.modules['buffer_test']=pkg
module=types.ModuleType('buffer_test.embyflow_buffer_v1')
module.eligible=lambda url:'Static=true' in url
sys.modules[module.__name__]=module
with tempfile.TemporaryDirectory() as d:
 ns=dict(__package__='buffer_test',_efb_json=json,time=time,os=os,
  _EFB_SETTINGS=d+'/settings.json',_efb_test_next=False,_efb_proxy=None,
  _efb_original_player_init=lambda self,*a,**kw:None,eTimer=Timer,
  _efb_original_stats=lambda self:{'video':'untouched'})
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'v4','exec'),ns)
 ns['_efb_save'](True,True)
 assert json.loads(pathlib.Path(ns['_EFB_SETTINGS']).read_text())=={'enabled':True,'test_next':True}
 p=Player();ns['_efb_player_init'](p)
 assert p._efb_test_timer.args==(10000,True)
 assert ns['_efb_read_settings']()['test_next'] is False
 ns['_efb_save'](False,True);assert ns['_efb_read_settings']()['test_next'] is False
 p.session.nav.path='http://127.0.0.1:12345/secret/media';ns['_efb_proxy']=Proxy()
 assert ns['_efb_runtime_state'](p)=='RAM 8.0 MiB'
 stats=ns['_efb_stats'](p);assert stats=={'video':'untouched','buffer':'RAM 8.0 MiB'}
 p.session.nav.path='http://example.invalid/stream.mkv?Static=true';ns['_efb_save'](True,False)
 assert ns['_efb_runtime_state'](p)=='Zusatz nicht aktiv'
 p.session.nav.path='http://example.invalid/main.m3u8'
 assert ns['_efb_runtime_state'](p)=='Stream nicht unterstützt'
 # Exact-version upgrade and byte-identical restore, including rollback metadata.
 for name in ('v3','v4'):
  local={'__name__':'test'}
  path='e2-buffer-test/'+('install_e2_buffer_v3.py' if name=='v3' else 'upgrade_e2_buffer_v4.py')
  exec(pathlib.Path(path).read_text(),local)
  root=pathlib.Path(d)/'plugin';root.mkdir(exist_ok=True)
  for k,f in [('ROOT',''),('TARGET','plugin.py'),('STATE','embyflow_buffer_install_v3.json'),('HELPER','embyflow_buffer_v1.py')]:local[k]=root/f
  if name=='v3':local['TARGET'].write_bytes(pathlib.Path('e2-buffer/plugin.py').read_bytes())
  sys.argv=['installer'];local['main']()
 sys.argv=['installer','--restore'];local['main']()
 assert local['TARGET'].read_bytes()==pathlib.Path('e2-buffer/plugin.py').read_bytes()
print('PASS: durable one-shot test, native runtime state (no Webif), stats preservation, V3 upgrade, original rollback.')

import ast,os,tempfile,threading,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'EmbyFlowE2_LCD_Fanart_20261004_0404.py').read_text()
compile(s,'plugin.py','exec')
tree=ast.parse(s)
names={'_efimg3_copy','_efimg3_clear','_efimg4_backdrop'}
code='\n\n'.join(ast.get_source_segment(s,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names)
with tempfile.TemporaryDirectory() as folder:
 logs=[];calls=[]
 env=dict(os=os,_efimg3_shutil=shutil,_efimg3_dir=folder,_efimg3_lock=threading.RLock(),_efimg3_log=logs.append)
 exec(code,env)
 state={'cancel':threading.Event()}
 env['_efimg3_active']=state
 original=b'\xff\xd8'+b'ORIGINAL_UNDARKENED'*30
 class Response:
  status_code=200
  content=original
 def get(url,**kwargs):
  calls.append(url)
  return Response()
 env['embyflow_http_get']=get;env['AUTH_HEADER']='test'
 env['_efimg4_backdrop'](state,('https://example.invalid','token','user'),('movie1',))
 assert Path(folder,'Backdrop.jpg').read_bytes()==original
 assert calls==['https://example.invalid/Items/movie1/Images/Backdrop/0']
 assert not list(Path(tempfile.gettempdir()).glob('embyflow-lcd-original-*.jpg'))
 # Film switch: an old download cannot replace the new film's image.
 next_state={'cancel':threading.Event()}
 env['_efimg3_active']=next_state
 env['_efimg4_backdrop'](state,('https://example.invalid','token','user'),('movie1',))
 assert Path(folder,'Backdrop.jpg').read_bytes()==original
 # Close while response is in flight: no files may reappear.
 def late(url,**kwargs):
  state['cancel'].set();env['_efimg3_clear']()
  return Response()
 env['_efimg3_active']=state;env['embyflow_http_get']=late
 env['_efimg4_backdrop'](state,('https://example.invalid','token','user'),('movie1',))
 assert not list(Path(folder).iterdir())
 # Missing backdrop: never substitute the dark TV cache.
 state={'cancel':threading.Event()};env['_efimg3_active']=state
 class Missing:
  status_code=404
  content=b''
 env['embyflow_http_get']=lambda *a,**k: Missing()
 env['_efimg4_backdrop'](state,('https://example.invalid','token','user'),('movie1',))
 assert not list(Path(folder).iterdir())
 assert "'image_ids': tuple(dict.fromkeys((item_id, source_id)))" in s
print('PASS: original JPEG bytes, correct item endpoint, film switch, late response after close, missing image and temporary file cleanup')

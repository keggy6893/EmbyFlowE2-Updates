from pathlib import Path
import ast,json,threading,time,types,unittest
from concurrent.futures import ThreadPoolExecutor
import requests
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'EmbyFlowE2_ServerGuard_20261005_0503.py'

class GuardTests(unittest.TestCase):
 def setUp(self):
  self.now=1000.0;self.calls=[];self.status=200;self.headers={};self.payload={}
  self.env={'requests':requests,'time':time,'json':json,'__name__':'guard_test'}
  exec((ROOT/'release_tools/server_guard_0503.inc.py').read_text(),self.env)
  self.env['_efguard_clock']=lambda:self.now
  self.transport=patch.object(requests.Session,'send',lambda session,request,**kw:self.send(session,request,**kw));self.transport.start()
 def tearDown(self):self.transport.stop()
 def send(self,session,request,**kwargs):
  self.calls.append((request.method,request.url,kwargs))
  r=requests.Response();r.status_code=self.status;r.headers.update(self.headers)
  r._content=json.dumps(self.payload).encode();r._content_consumed=True;r.request=request;r.url=request.url
  return r
 def get(self,url='https://emby.test/Items/1'):
  return self.env['requests'].get(url)
 def login(self):
  return self.env['requests'].post('https://emby.test/Users/AuthenticateByName',json={'Username':'u','Pw':'secret'})
 def test_403_all_methods_and_sessions_other_host_unaffected(self):
  original=requests.Session
  self.status=403
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.get()
  self.status=200
  for method in ('get','post','delete'):
   with self.assertRaises(self.env['EmbyFlowServerPaused']):getattr(self.env['requests'],method)('http://emby.test:8096/emby/Items/2')
  with self.env['requests'].Session() as session:
   with self.assertRaises(self.env['EmbyFlowServerPaused']):session.get('https://emby.test/Images')
  self.get('https://other.test/Items');self.assertEqual(len(self.calls),2)
  self.assertIs(requests.Session,original)
  self.assertIn('HTTP 403',self.env['_efguard_notice'])
 def test_429_retry_after_and_expiry(self):
  self.status=429;self.headers={'Retry-After':'600'}
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.get()
  self.now+=599
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.get()
  self.now+=1;self.status=200;self.get();self.get()
  self.assertEqual(len(self.calls),3)
 def test_http_date_retry_after(self):
  from email.utils import formatdate
  self.status=429;self.headers={'Retry-After':formatdate(time.time()+700,usegmt=True)}
  with self.assertRaises(self.env['EmbyFlowServerPaused']):self.get()
  self.assertGreater(self.env['_efguard_servers']['emby.test']['until']-self.now,690)
 def test_login_backoff_and_success_reset(self):
  self.status=401
  for delay in (60,120,240,480,900,900):
   with self.assertRaises(RuntimeError):self.login()
   state=next(iter(self.env['_efguard_logins'].values()))
   self.assertEqual(state['until']-self.now,delay)
   calls=len(self.calls)
   with self.assertRaises(self.env['EmbyFlowServerPaused']):self.login()
   self.assertEqual(len(self.calls),calls)
   self.now+=delay
  self.status=200;self.payload={'AccessToken':'token','User':{'Id':'u'}}
  self.login();self.assertEqual(state['failures'],0)
  self.assertFalse(self.calls[-1][2]['allow_redirects'])
 def test_parallel_failed_logins_only_one_request(self):
  self.status=401
  def worker(_):
   try:self.login()
   except RuntimeError:pass
  with ThreadPoolExecutor(max_workers=12) as pool:list(pool.map(worker,range(30)))
  self.assertEqual(len(self.calls),1)
 def test_half_open_single_probe(self):
  self.status=403
  with self.assertRaises(RuntimeError):self.get()
  self.now+=300;self.status=200
  ready=threading.Event();done=threading.Event();base=self.send
  def slow(session,request,**kwargs):
   ready.set();self.assertTrue(done.wait(3));return base(session,request,**kwargs)
  with patch.object(requests.Session,'send',slow):
   with ThreadPoolExecutor(max_workers=1) as pool:
    future=pool.submit(self.get);self.assertTrue(ready.wait(3))
    try:
     with self.assertRaises(self.env['EmbyFlowServerPaused']):self.get()
    finally:done.set()
    future.result()
  self.assertNotIn('emby.test',self.env['_efguard_servers'])
 def test_central_auth_parallel_success_uses_cache(self):
  source=RELEASE.read_text();tree=ast.parse(source)
  original=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_emby_auth')
  self.env.update(EMBY_SERVER='https://emby.test',EMBY_USERNAME='u',EMBY_PASSWORD='pw',
                  AUTH_HEADER='safe',EMBY_AUTH_CACHE={},embyflow_http_post=self.env['requests'].post,
                  EMBYFLOW_V18_AUTH_LOCK=threading.RLock(),main=lambda *a,**k:None)
  exec(ast.get_source_segment(source,original),self.env)
  exec((ROOT/'release_tools/server_guard_ui_0502.inc.py').read_text(),self.env)
  self.env['_embyflow_v20_cached_auth_valid']=lambda:bool(self.env['EMBY_AUTH_CACHE'].get('token'))
  self.payload={'AccessToken':'token','User':{'Id':'u'}}
  with ThreadPoolExecutor(max_workers=12) as pool:
   result=list(pool.map(lambda _:self.env['get_emby_auth'](True),range(30)))
  self.assertEqual(len(self.calls),1);self.assertTrue(all(r[1]=='token' for r in result))
 def test_404_does_not_block_correct_emby_path(self):
  self.status=404
  self.assertEqual(self.login().status_code,404)
  state=next(iter(self.env['_efguard_logins'].values()))
  self.assertEqual(state['failures'],0);self.assertEqual(state['until'],0)
  self.status=200;self.payload={'AccessToken':'token','User':{'Id':'u'}}
  self.env['requests'].post('https://emby.test/emby/Users/AuthenticateByName',json={'Username':'u','Pw':'secret'})
  self.assertEqual(len(self.calls),2)
 def test_non_auth_statuses_do_not_backoff(self):
  for status in (302,404,500,503):
   self.status=status;self.assertEqual(self.login().status_code,status)
   state=next(iter(self.env['_efguard_logins'].values()))
   self.assertEqual(state['failures'],0);self.assertEqual(state['until'],0)
 def test_200_without_token_and_malformed_json_backoff(self):
  self.status=200;self.payload={}
  with self.assertRaises(RuntimeError):self.login()
  state=next(iter(self.env['_efguard_logins'].values()))
  self.assertEqual(state['until']-self.now,60)
 def test_transport_error_does_not_count_as_auth_failure(self):
  def fail(session,request,**kwargs):raise requests.ConnectionError('test')
  with patch.object(requests.Session,'send',fail):
   with self.assertRaises(requests.ConnectionError):self.login()
  state=next(iter(self.env['_efguard_logins'].values()))
  self.assertEqual(state['failures'],0)
 def test_gui_notice_once_on_gui_timer(self):
  self.env.update(get_emby_auth=lambda *a:None,main=lambda *a,**k:None)
  exec((ROOT/'release_tools/server_guard_ui_0502.inc.py').read_text(),self.env)
  dialog=type('Dialog',(),{'__module__':'guard_test'})()
  calls=[]
  session=types.SimpleNamespace(current_dialog=dialog,dialog_stack=[],open=lambda *a,**k:calls.append(a))
  self.env.update(_efguard_gui_session=session,MessageBox=types.SimpleNamespace(TYPE_INFO=1),
                  _efguard_gui_timer=types.SimpleNamespace(stop=lambda:None))
  self.env['_efguard_notice']='Server-Anfragen pausiert (HTTP 403).'
  self.env['_efguard_gui_tick']();self.env['_efguard_gui_tick']()
  self.assertEqual(len(calls),1);self.assertIn('403',calls[0][1])
 def test_real_local_transport_redirect_and_block(self):
  from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
  self.transport.stop()
  counts=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    counts.append(self.path)
    self.send_response(302 if self.path=='/redirect' else 403)
    if self.path=='/redirect':self.send_header('Location','/blocked')
    self.end_headers();self.wfile.write(b'blocked')
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   url='http://127.0.0.1:%d'%server.server_port
   with self.assertRaises(self.env['EmbyFlowServerPaused']):self.get(url+'/redirect')
   with self.assertRaises(self.env['EmbyFlowServerPaused']):self.get(url+'/again')
   self.assertEqual(counts,['/redirect','/blocked'])
  finally:server.shutdown();server.server_close();thread.join()
 def test_release_integration(self):
  source=RELEASE.read_text();compile(source,str(RELEASE),'exec');tree=ast.parse(source)
  self.assertNotIn('get_emby_auth(force=True)',source)
  self.assertIn('_V18Pool(max_workers=8)',source)
  scans=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='start_nas_scan']
  self.assertEqual(len(scans),1)
  wizard=next(n for n in tree.body if isinstance(n,ast.ClassDef) and any(isinstance(m,ast.FunctionDef) and m.name=='_candidate_urls' for m in n.body))
  login=next(n for n in wizard.body if isinstance(n,ast.FunctionDef) and n.name=='login')
  self.assertFalse(any(isinstance(n,ast.For) for n in ast.walk(login)))
  posts=[n for n in ast.walk(login) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='embyflow_http_post']
  self.assertEqual(len(posts),1)

if __name__=='__main__':unittest.main()

import ast,io,json,os,re,tempfile,types,unittest
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]/'EmbyFlowE2_Security_20261005_1907.py'
class SecurityTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.env=dict(os=os,io=io,json=json,re=re,config=types.SimpleNamespace(embyflow=types.SimpleNamespace(password=types.SimpleNamespace(value='private-secret'))))
  source=SOURCE.read_text();tree=ast.parse(source)
  for node in tree.body:
   if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in ('embyflow_sanitize_log_text','_EmbyFlowSafeLog','_embyflow_private_log','write_json_file'):
    text=ast.get_source_segment(source,node).replace("'/tmp/embyflow-private-logs'",repr(self.temp.name+'/logs'))
    exec(text,self.env)
 def test_redaction(self):
  f=self.env['embyflow_sanitize_log_text']
  for value,secret in [('?api_key=abc&x=1','abc'),('{"AccessToken": "abc xyz"}','abc xyz'),("{'password': 'abc xyz'}",'abc xyz'),('password=abc','abc'),('https://bob:abc@example.test','bob:abc'),('failure private-secret','private-secret')]:
   self.assertNotIn(secret,f(value))
 def test_private_logs(self):
  with self.env['_embyflow_private_log']('/tmp/error.log','w') as log:log.write('token=private')
  p=Path(self.temp.name)/'logs/error.log'
  self.assertEqual(p.stat().st_mode&0o777,0o600);self.assertEqual(p.parent.stat().st_mode&0o777,0o700)
  self.assertNotIn('private',p.read_text())
 def test_symlink_refused(self):
  directory=Path(self.temp.name)/'logs';directory.mkdir();target=Path(self.temp.name)/'victim';target.write_text('preserve');(directory/'error.log').symlink_to(target)
  with self.assertRaises(OSError):self.env['_embyflow_private_log']('/tmp/error.log','w')
  self.assertEqual(target.read_text(),'preserve')
 def test_atomic_private_json(self):
  p=Path(self.temp.name)/'data.json';self.assertTrue(self.env['write_json_file'](p,{'token':'abc'}))
  self.assertEqual(p.stat().st_mode&0o777,0o600);self.assertEqual(json.loads(p.read_text()),{'token':'abc'})
 def test_tls_bypass_rejected_before_send(self):
  source=SOURCE.read_text();node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_efguard_send')
  exec(ast.get_source_segment(source,node),self.env)
  with self.assertRaises(ValueError):self.env['_efguard_send'](None,None,verify=False)
if __name__=='__main__':unittest.main()

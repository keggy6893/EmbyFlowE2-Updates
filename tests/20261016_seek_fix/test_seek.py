import ast, pathlib, types, unittest
SOURCE=pathlib.Path(__file__).resolve().parents[2]/'EmbyFlowE2_2026101602.py'
class Timer:
 def __init__(self):self.callback=[];self.starts=[]
 def start(self,*args):self.starts.append(args)
 def stop(self):pass
class Player:
 duration_ticks=1000*10000000; closed=False
 def __init__(self,accepted=True):self.calls=[];self.accepted=accepted
 def current_position_ticks(self):return 100*10000000
 def show_overlay(self):pass
 def embyflow_seek_to_chapter(self,target):self.calls.append(target);return self.accepted
class SeekTests(unittest.TestCase):
 def setUp(self):
  self.clock=10.; self.legacy=[]
  names={'_embyflow_seek_burst_v17_5_5_'+s for s in ['timer','reset','queue','commit']}
  names.add('_embyflow_rcdev7_native_seek_now')
  tree=ast.parse(SOURCE.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
  self.ns={'time':types.SimpleNamespace(time=lambda:self.clock,monotonic=lambda:self.clock),'eTimer':Timer,'EMBYFLOW_SEEK_BURST_MS_V17_5_5':1200,'_embyflow_seek_burst_v17_5_5_log':lambda *a:None,'_embyflow_rcdev7_log':lambda *a:None,'_EMBYFLOW_SEEK_V17_5_2_ORIGINAL_RELATIVE_SECONDS':lambda *a:self.legacy.append(a)}
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'seek','exec'),self.ns)
 def queue(self,p,s):return self.ns['_embyflow_seek_burst_v17_5_5_queue'](p,s,'number_direction')
 def commit(self,p):self.ns['_embyflow_seek_burst_v17_5_5_commit'](p)
 def test_burst_coalesces(self):
  p=Player()
  for _ in range(5):self.assertTrue(self.queue(p,30))
  self.assertEqual(p.calls,[]);self.commit(p)
  self.assertEqual(p.calls,[250*10000000]);self.assertEqual(self.legacy,[])
 def test_rejected_seek_never_calls_legacy(self):
  p=Player(False);self.queue(p,30);self.commit(p)
  self.assertEqual(len(p.calls),1);self.assertEqual(self.legacy,[])
 def test_second_burst_waits(self):
  p=Player();self.queue(p,30);self.commit(p)
  self.queue(p,30);self.queue(p,30);self.commit(p)
  self.assertEqual(len(p.calls),1);self.assertTrue(p._embyflow_seek_burst_pending_v17_5_5)
  self.clock+=3.1;self.commit(p);self.assertEqual(len(p.calls),2)
 def test_target_clamped(self):
  p=Player();self.queue(p,-1000);self.commit(p);self.assertEqual(p.calls,[0])
 def test_unseekable_backend_never_receives_seek(self):
  calls=[];seek=types.SimpleNamespace(isCurrentlySeekable=lambda:0,seekTo=lambda t:calls.append(t))
  p=types.SimpleNamespace(session=types.SimpleNamespace(nav=types.SimpleNamespace(getCurrentService=lambda:types.SimpleNamespace(seek=lambda:seek))))
  self.assertFalse(self.ns['_embyflow_rcdev7_native_seek_now'](p,10000000));self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()

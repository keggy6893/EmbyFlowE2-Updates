import unittest,hashlib,urllib.request,urllib.error,threading
from pathlib import Path
from tempfile import TemporaryDirectory
from server import _EFHCServer,_efhc_range
class ServerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=TemporaryDirectory();cls.path=Path(cls.tmp.name)/'original.ts';cls.data=bytes(range(256))*8192;cls.path.write_bytes(cls.data);cls.digest=hashlib.sha256(cls.data).digest();cls.logs=[]
  cls.server=_EFHCServer(str(cls.path),lambda e,**kw:cls.logs.append((e,kw)))
 @classmethod
 def tearDownClass(cls):
  cls.server.close();cls.server.thread.join(2);assert not cls.server.thread.is_alive();assert hashlib.sha256(cls.path.read_bytes()).digest()==cls.digest;cls.tmp.cleanup()
 def request(self,range=None,method='GET',url=None):
  return urllib.request.urlopen(urllib.request.Request(url or self.server.url,headers={'Range':range} if range else {},method=method),timeout=3)
 def test_loopback_only(self):self.assertEqual(self.server.httpd.server_address[0],'127.0.0.1')
 def test_full_get_identical_original_bytes(self):
  with self.request() as r:self.assertEqual(r.status,200);self.assertEqual(r.read(),self.data)
 def test_head_does_not_send_video(self):
  with self.request(method='HEAD') as r:self.assertEqual(int(r.headers['Content-Length']),len(self.data));self.assertEqual(r.read(),b'')
 def test_seek_range_exact_bytes_and_headers(self):
  with self.request('bytes=1000-1999') as r:
   self.assertEqual(r.status,206);self.assertEqual(r.headers['Content-Range'],'bytes 1000-1999/%d'%len(self.data));self.assertEqual(r.read(),self.data[1000:2000])
 def test_open_range(self):
  with self.request('bytes=2000000-') as r:self.assertEqual(r.read(),self.data[2000000:])
 def test_suffix_range(self):
  with self.request('bytes=-200') as r:self.assertEqual(r.read(),self.data[-200:])
 def test_past_end_is_416(self):
  with self.assertRaises(urllib.error.HTTPError) as cm:self.request('bytes=9999999-')
  self.assertEqual(cm.exception.code,416);self.assertEqual(cm.exception.headers['Content-Range'],'bytes */%d'%len(self.data))
 def test_invalid_ranges(self):
  for v in ('bytes=10-2','bytes=-0','bytes=','bytes=0-1,3-4','items=1-2'):
   with self.subTest(v=v),self.assertRaises(urllib.error.HTTPError) as cm:self.request(v)
   self.assertEqual(cm.exception.code,416)
 def test_cannot_request_other_file(self):
  for suffix in ('/../etc/passwd','?file=/etc/passwd','/other.ts'):
   with self.subTest(suffix=suffix),self.assertRaises(urllib.error.HTTPError) as cm:self.request(url=self.server.url+suffix)
   self.assertEqual(cm.exception.code,404)
 def test_post_cannot_write(self):
  with self.assertRaises(urllib.error.HTTPError) as cm:self.request(method='POST')
  self.assertEqual(cm.exception.code,501)
 def test_parallel_ranges(self):
  errors=[]
  def work(i):
   try:
    with self.request('bytes=%d-%d'%(i*100,i*100+99)) as r:assert r.read()==self.data[i*100:i*100+100]
   except Exception as e:errors.append(e)
  threads=[threading.Thread(target=work,args=(i,)) for i in range(4)]
  for t in threads:t.start()
  for t in threads:t.join()
  self.assertEqual(errors,[])
 def test_empty_file_bounds(self):
  self.assertEqual(_efhc_range(None,0),(0,-1,False))
  with self.assertRaises(ValueError):_efhc_range('bytes=0-',0)
if __name__=='__main__':unittest.main()

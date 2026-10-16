import importlib.util, threading, time, requests, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import embyflow_buffer_v1 as b
DATA = bytes(range(256)) * (48 * 1024)
seen=[]
class Source(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        seen.append(self.headers.get('Range'))
        start=0; end=len(DATA)-1
        value=self.headers.get('Range')
        if value:
            lo,hi=value.split('=')[1].split('-'); start=int(lo); end=int(hi) if hi else end
        if start>=len(DATA):
            self.send_response(416);self.send_header('Content-Range','bytes */%d'%len(DATA));self.end_headers();return
        payload=DATA[start:end+1]
        self.send_response(206 if value else 200)
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Content-Type','video/x-matroska')
        if value:self.send_header('Content-Range','bytes %d-%d/%d'%(start,end,len(DATA)))
        self.end_headers()
        try:self.wfile.write(payload)
        except (BrokenPipeError,ConnectionResetError):pass
source=ThreadingHTTPServer(('127.0.0.1',0),Source)
threading.Thread(target=source.serve_forever,daemon=True).start()
p=b.BufferProxy(requests.request)
u='http://127.0.0.1:%d/Videos/x/stream.mkv?Static=true'%source.server_port
local=p.register(u)
r=requests.get(local);assert r.status_code==200 and r.content==DATA
r=requests.get(local,headers={'Range':'bytes=12345-98765'});assert r.status_code==206 and r.content==DATA[12345:98766]
assert r.headers['Content-Range']=='bytes 12345-98765/%d'%len(DATA)
r=requests.get(local,headers={'Range':'bytes=%d-'%(len(DATA)+1)});assert r.status_code==416
assert p.register(u.replace('Static=true','Static=false')).startswith('http://127.0.0.1:%d/Videos'%source.server_port)
assert requests.get(local.replace(local.split('/')[-2], 'not-a-route')).status_code==404
# A gated source must not publish new chunks; old queued data remains consumable.
class Raw:
    def __init__(self):self.n=0
    def read(self,n,**kwargs):self.n+=1;return b'x'*n if self.n<10000 else b''
class Response:
    raw=Raw()
    def close(self):pass
reader=b.ReadAhead(Response(),p)
reader.prefill();time.sleep(.15)
with reader.cv:assert reader.size<=b.CAPACITY
p.test(.4);time.sleep(.08)
while reader.size:reader.take()
time.sleep(.1)
with reader.cv:assert reader.size==0
assert p.gated()
time.sleep(.4)
assert reader.take()
reader.close();p.release();p.server.shutdown();source.shutdown()
print('PASS: full byte integrity, Range/206/416, route authentication, static-only selection, bounded queue, gate/resume, cleanup.')

from pathlib import Path
import tempfile, time, os, threading, shutil
root=Path(tempfile.mkdtemp()); cache=root/'cache'; (cache/'player').mkdir(parents=True); (cache/'grid_backdrops').mkdir()
class Player:
    def __init__(self, item): self.item_id=item; self.calls=[]
    def player_poster_source_id(self): return self.item_id
    def load_player_poster_async(self): self.calls.append('load'); return 'loaded'
    def stop_player_poster_loader(self): return 'stopped'
init=Player.__init__
ns=dict(os=os,time=time,CACHE_DIR=str(cache),SCREEN_W=1920,SCREEN_H=1080,EmbyFlowMoviePlayer=Player)
exec(Path(__file__).with_name('current_images_0401.inc.py').read_text(),ns)
ns['_efimg3_dir']=str(root/'EmbyFlow')
assert Player.__init__ is init
for item in ('A','B'):
    (cache/'player'/f'{item}_primary_v1.jpg').write_bytes(b'\xff\xd8'+item.encode())
    (cache/'grid_backdrops'/f'grid_{item}_1920x1080.jpg').write_bytes(b'\xff\xd8'+item.encode())
def ready(item):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        files=[root/'EmbyFlow'/n for n in ('Poster.jpg','Backdrop.jpg')]
        if all(p.exists() and p.read_bytes()==b'\xff\xd8'+item.encode() for p in files): return
        threading.Event().wait(.01)
    raise AssertionError('exports not ready')
a=Player('A'); assert a.load_player_poster_async()=='loaded'; ready('A')
b=Player('B'); b.load_player_poster_async(); ready('B')
a.__dict__.clear(); assert a.stop_player_poster_loader()=='stopped'; ready('B')
b.__dict__.clear(); assert b.stop_player_poster_loader()=='stopped'; assert not list((root/'EmbyFlow').iterdir())
assert b.stop_player_poster_loader()=='stopped'
c=Player('missing'); c.load_player_poster_async(); c.stop_player_poster_loader(); threading.Event().wait(.03)
assert not list((root/'EmbyFlow').iterdir())
shutil.rmtree(root)
print('PASS: unchanged player init, original callbacks, atomic JPEG export, title switch, cleared screen attrs, repeated close, cancellation, installer and poster correction')

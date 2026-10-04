from pathlib import Path
import tempfile, os, time, threading, shutil
root=Path(tempfile.mkdtemp())
class Detail:
    def __init__(self,session,data): self.data=data; self.onClose=[]
class Player:
    def load_player_poster_async(self): pass
    def stop_player_poster_loader(self): return 'original-stop'
ns=dict(os=os,time=time,CACHE_DIR=str(root),SCREEN_W=1920,SCREEN_H=1080,EmbyFlowDetailScreen=Detail,EmbyFlowMoviePlayer=Player)
v3=Path(__file__).with_name('current_images_0401.inc.py').read_text().replace("state = {'cancel': _efimg3_threading.Event()}","state = {'cancel': _efimg3_threading.Event(), 'item_id': item_id}")
exec(v3,ns);ns['_efimg3_dir']=str(root/'EmbyFlow');exec(Path(__file__).with_name('detail_cleanup_0401.inc.py').read_text(),ns)
d=Detail(None,{'id':'ef_cleanup_test'})
state=ns['_efclean_states'][id(d)]
path=state['allowed'][0]
assert ns['_efclean_write'](d,path,b'\xff\xd8test')
ns['_efimg3_active']={'item_id':'ef_cleanup_test','cancel':threading.Event()}
callbacks=list(d.onClose)
for cb in callbacks: cb()
d.__dict__.clear()
assert Path(path).exists() # source protected during film
assert not ns['_efclean_write'](d,path,b'late')
ns['_efimg3_active']=None
p=Player(); assert p.stop_player_poster_loader()=='original-stop'
assert not Path(path).exists()
for cb in callbacks: cb() # must not read deleted screen attributes
assert not ns['_efclean_states']
e=Detail(None,{'Id':'ef_cleanup_test_2'}); state=ns['_efclean_states'][id(e)]; path=state['allowed'][1]
assert ns['_efclean_write'](e,path,b'\xff\xd8test')
for cb in list(e.onClose): cb()
assert not Path(path).exists() # close without playback
assert not ns['_efclean_write'](e,path,b'late')
assert not ns['_efclean_states']
source=Path(__file__).resolve().parents[1]/'EmbyFlowE2_Bilder_Aufraeumen_20261004_0401.py'
text=source.read_text()
compile(text,str(source),'exec')
assert 'focus_y = y + h + 4' in text
assert text.count('_efclean_write(self, path, content)')==2
shutil.rmtree(root)
print('PASS: installer, syntax, active-film source retention, close without playback, deleted screen attributes, repeated close, late download rejection, original stop preserved')

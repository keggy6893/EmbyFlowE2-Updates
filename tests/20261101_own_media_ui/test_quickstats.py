import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import types

ROOT=Path(__file__).resolve().parent
def load(filename):
    spec=importlib.util.spec_from_file_location(filename,ROOT/filename)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
installer=load('EmbyFlowE2_Schnellinfo_Schneller_V1_20261031.py')
original=(ROOT.parents[1] / 'EmbyFlowE2_2026102801.py').read_text(encoding='utf-8')
tree=ast.parse(original)
v16=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EmbyFlowLocalSourcesScreenV16')
v17=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EmbyFlowLocalSourcesScreenV17')
rescan=next(n for n in v16.body if isinstance(n,ast.FunctionDef) and n.name=='rescan_stats')
layout=next(n for n in v17.body if isinstance(n,ast.FunctionDef) and n.name=='layout_ready')
class Thread:
    def __init__(self,target,**kw):self.target=target
    def start(self):self.target()
class Timer:
    def start(self,*args):pass
class Label:
    def __init__(self):self.text='old'
    def setText(self,t):self.text=t
class Screen(dict):
    def __init__(self,sources):
        super().__init__();self.sources=sources;self.stats_running=False;self.stats_result=None;self.closed_sources_v16=False
        self['status']=Label();self.apply_timer=Timer()
    def cleanup(self):self.closed_sources_v16=True
    def apply_async_results(self):
        if self.stats_result is not None:self.stats_running=False

visited_old=[];visited_new=[]
def walk(path):
    for row in os.walk(path):visited_old.append(row[0]);yield row
def scandir(path):visited_new.append(path);return os.scandir(path)
fake_os=types.SimpleNamespace(**{k:getattr(os,k) for k in ('path','sep')},walk=walk,scandir=scandir)
def series(root,path):return os.path.relpath(path,root).split(os.sep)[0].replace('_',' ').strip()
ns=dict(os=fake_os,time=time,EmbyFlowLocalSourcesScreenV16=Screen,EmbyFlowLocalSourcesScreenV17=Screen,
        EMBYFLOW_LOCAL_LIBRARY_SKIP_DIRS_V3={'cache'},EMBYFLOW_LOCAL_VIDEO_EXTENSIONS={'.ts','.mkv','.mp4'},EMBYFLOW_LOCAL_SOURCE_MAX_SCAN_FILES_V16=50000,
        _embyflow_v16_source_is_inside=lambda root,p:p==root or p.startswith(root+os.sep),embyflow_local_v3_series_name=series,_embyflow_v16_log=lambda t:None)
exec(compile(ast.Module(body=[rescan],type_ignores=[]),'<original-rescan>','exec'),ns)
old=ns['rescan_stats']
exec(installer.RUNTIME,ns)
ns['_efqs_threading']=types.SimpleNamespace(Thread=Thread,Event=threading.Event)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve()
    for directory,n in [('Filme',11),('Serien/A_Show/Staffel1',3),('Serien/B_Show/Staffel2',4),('Doku',2),('Sonstige',1),('.hidden',2),('cache',2)]:
        d=root/directory;d.mkdir(parents=True)
        for i in range(n):(d/('Film%d.ts'%i)).write_bytes(b'1234567890')
    (root/'Filme/poster.jpg').write_bytes(b'xx')
    sources=[dict(path=str(root/'Filme'),mode='movies'),dict(path=str(root/'Serien'),mode='series'),dict(path=str(root),mode='mixed'),dict(path=str(root/'Doku'),mode='documentary'),dict(path=str(root/'Filme'),mode='mixed')]
    # Original's local import uses sys.modules: provide only a deterministic scheduler.
    module=types.ModuleType('threading');module.Thread=Thread
    real_threading=sys.modules['threading'];sys.modules['threading']=module
    try:
        screen=Screen(sources);old(screen);baseline=screen.stats_result
    finally:sys.modules['threading']=real_threading
    screen=Screen(sources);ns['_efqs_rescan'](screen);fast=screen.stats_result
    keys=('movies','series','episodes','docs','size','truncated')
    assert {k:fast[k] for k in keys}==baseline,(fast,baseline)
    assert fast['movies']==11 and fast['series']==2 and fast['episodes']==7 and fast['docs']==2
    assert len(visited_new)==len(set(visited_new)),visited_new
    assert len(visited_new)<len(visited_old),(visited_old,visited_new)
    assert fast['skipped_subtrees']==3
    print('PASS: exact original totals; folder visits reduced from %d to %d (fixture)'%(len(visited_old),len(visited_new)))
    cancel=threading.Event();cancel.set();assert ns['_efqs_scan'](sources,cancel) is None
    ns['EMBYFLOW_LOCAL_SOURCE_MAX_SCAN_FILES_V16']=2
    capped=ns['_efqs_scan'](sources,threading.Event());assert capped['truncated'] and capped['scan_files']==2
    ns['EMBYFLOW_LOCAL_SOURCE_MAX_SCAN_FILES_V16']=50000
    empty=Screen([]);ns['_efqs_rescan'](empty);assert empty.stats_result['size']==0
    screen=Screen(sources);screen.stats_running=True;ns['_efqs_rescan'](screen);assert screen._efqs_pending==sources
    screen.cleanup();assert screen.closed_sources_v16
print('PASS: cap, cancellation, no sources, queued refresh, cleanup')

current=original
for f in ('EmbyFlowE2_Ordnerdialog_Textfix_20261031.py','EmbyFlowE2_Quellendialog_Textfix_V2_20261031.py','EmbyFlowE2_Quelleninfo_V1_20261031.py','EmbyFlowE2_Quellen_Picons_V1_20261031.py'):
    current=load(f).transform(current)
updated=installer.transform(current);newtree=ast.parse(updated)
newv17=next(n for n in newtree.body if isinstance(n,ast.ClassDef) and n.name==v17.name)
newlayout=next(n for n in newv17.body if isinstance(n,ast.FunctionDef) and n.name=='layout_ready')
class Base:
    @staticmethod
    def layout_ready(screen):screen.loaded=True
state={'timestamp':1,'stats':{'movies':11}}
layoutns=dict(EmbyFlowLocalSourcesScreenV16=Base,read_json_file=lambda *a:state,time=time,EMBYFLOW_LOCAL_SOURCES_STATS_FILE_V16='',EMBYFLOW_LOCAL_SOURCES_STATS_TTL_V17=300,_embyflow_v16_log=lambda t:None)
exec(compile(ast.Module(body=[newlayout],type_ignores=[]),'<layout>','exec'),layoutns)
screen=Screen([])
for key in ('stat_movies','stat_series','stat_episodes','stat_docs','stat_size'):screen[key]=Label()
screen.refresh=lambda:None;screen.rescan_stats=lambda:setattr(screen,'scan_requested',True)
layoutns['layout_ready'](screen)
assert screen.scan_requested and screen['stat_movies'].text=='old'
state.clear();layoutns['layout_ready'](screen);assert screen['stat_movies'].text=='...'
oldclasses=[n for n in ast.parse(current).body if isinstance(n,ast.ClassDef)]
newclasses=[n for n in newtree.body if isinstance(n,ast.ClassDef)]
for a,b in zip(oldclasses,newclasses):
    if a.name!=v17.name:assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
oldfuncs={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(current).body if isinstance(n,ast.FunctionDef)}
newfuncs={n.name:ast.dump(n,include_attributes=False) for n in newtree.body if isinstance(n,ast.FunctionDef)}
assert all(newfuncs[k]==v for k,v in oldfuncs.items())
try:installer.transform(updated);raise AssertionError('repeat accepted')
except ValueError:pass
with tempfile.TemporaryDirectory() as tmp:
    target=Path(tmp)/'plugin.py';target.write_bytes(current.encode())
    result=subprocess.run([sys.executable,str(ROOT/'EmbyFlowE2_Schnellinfo_Schneller_V1_20261031.py'),'--apply','--path',str(target)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert target.read_bytes()==updated.encode() and next(Path(tmp).glob('*.bak')).read_bytes()==current.encode()
print('PASS: old cached numbers remain visible, missing cache shows pending, previous patches/player unchanged, actual install and exact backup')

import ast
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
p=ROOT/'EmbyFlowE2_Kachelfokus_V1_20261101.py'
spec=importlib.util.spec_from_file_location('fix',p);fix=importlib.util.module_from_spec(spec);spec.loader.exec_module(fix)
original=(ROOT.parents[1] / 'EmbyFlowE2_2026102801.py').read_text(encoding='utf-8')

def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/name)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
for name in ('EmbyFlowE2_Ordnerdialog_Textfix_20261031.py', 'EmbyFlowE2_Quellendialog_Textfix_V2_20261031.py', 'EmbyFlowE2_Quelleninfo_V1_20261031.py', 'EmbyFlowE2_Quellen_Picons_V1_20261031.py', 'EmbyFlowE2_Schnellinfo_Schneller_V1_20261031.py'):
    original=load(name).transform(original)

updated=fix.transform(original)
oldtree,newtree=ast.parse(original),ast.parse(updated)
oldfuncs={n.name:ast.dump(n,include_attributes=False) for n in oldtree.body if isinstance(n,ast.FunctionDef)}
newfuncs={n.name:ast.dump(n,include_attributes=False) for n in newtree.body if isinstance(n,ast.FunctionDef)}
assert all(newfuncs[k]==v for k,v in oldfuncs.items())
for a,b in zip((n for n in oldtree.body if isinstance(n,ast.ClassDef)),(n for n in newtree.body if isinstance(n,ast.ClassDef))):
    if a.name!='EmbyFlowLocalSourcesScreenV17':assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
    else:
        methods=lambda c:{n.name:ast.dump(n,include_attributes=False) for n in c.body if isinstance(n,ast.FunctionDef)}
        assert methods(a)==methods(b)
def skin(tree):
    scope={'scale_skin':lambda s:s}
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in ('_EMBYFLOW_V16_CARD_SKIN','_EMBYFLOW_V16_MANAGER_ROWS_SKIN') for x in n.targets):exec(compile(ast.Module(body=[n],type_ignores=[]),'<constants>','exec'),scope)
    c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EmbyFlowLocalSourcesScreenV17')
    n=next(n for n in c.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='skin' for x in n.targets))
    return ET.fromstring(eval(compile(ast.Expression(n.value),'<skin>','eval'),scope))
before,after=skin(oldtree),skin(newtree)
fill=next(e for e in after if e.get('name')=='source_selection_fill')
assert fill.get('zPosition')=='2' and fill.get('size')=='200,302'
assert len(after)==len(before)+1
for e in after:
    name=e.get('name','')
    if name.startswith('card_bg'):assert e.get('backgroundColor')=='#0D2138'
    elif name!='source_selection_fill':assert (e.tag,e.attrib,(e.text or '').strip()) in [(x.tag,x.attrib,(x.text or '').strip()) for x in before]
class Widget:
    def __init__(self,*args):self.instance=self;self.visible=False;self.position=None
    def move(self,p):self.position=p
    def show(self):self.visible=True
    def hide(self):self.visible=False
class Screen(dict):
    def __init__(self):super().__init__();self.sources=[{}]*4;self.selected_index=0;self.card_offset=0;self.focus_zone_v17='cards';self.colors=[]
    def refresh(self):self.old_refresh=True
    def _set_bg_color(self,name,color):self.colors.append((name,color))
ns=dict(EmbyFlowLocalSourcesScreenV17=Screen,Label=Widget,EFP=lambda *p:p)
exec(fix.RUNTIME,ns);s=Screen()
for i in (0,1,2,3,4,0):
    s.selected_index=i;s.refresh();assert s['source_selection_fill'].position==(205+i*216,330) and s['source_selection_fill'].visible
for zone in ('add','edit','remove'):
    s.focus_zone_v17=zone;s.refresh();assert not s['source_selection_fill'].visible
s.focus_zone_v17='cards';s.sources=[{}]*8;s.card_offset=4;s.selected_index=8;s.refresh();assert s['source_selection_fill'].position==(1069,330)
s.sources=[];s.refresh();assert not s['source_selection_fill'].visible
s._set_bg_color('card_bg0','#12355C');assert not s.colors
s._set_bg_color('mgr_bg0','#102B48');assert len(s.colors)==1
try:fix.transform(updated);raise AssertionError('repeat accepted')
except ValueError:pass
with tempfile.TemporaryDirectory() as temp:
    target=Path(temp)/'plugin.py';target.write_bytes(original.encode())
    r=subprocess.run([sys.executable,str(p),'--apply','--path',str(target)],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert target.read_bytes()==updated.encode() and next(Path(temp).glob('*.bak')).read_bytes()==original.encode()
print('PASS: syntax/XML, original methods/player/layout preserved, one fill follows 5 tiles and scrolling, action/empty hiding, exact backup and actual installer')

import ast
import base64
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
installer = load(ROOT / 'EmbyFlowE2_Quellen_Picons_V1_20261031.py')
original = (ROOT.parents[1] / 'EmbyFlowE2_2026102801.py').read_text(encoding='utf-8')
sourceinfo = load(ROOT / 'EmbyFlowE2_Quelleninfo_V1_20261031.py')
current = sourceinfo.transform(original)
# Preserve the two already-installed dialog fixes, too.
for filename in ('EmbyFlowE2_Ordnerdialog_Textfix_20261031.py', 'EmbyFlowE2_Quellendialog_Textfix_V2_20261031.py'):
    current = load(ROOT / filename).transform(current)
updated = installer.transform(current)
tree0, tree1 = ast.parse(current), ast.parse(updated)
def existing_functions(tree):
    return {n.name: ast.dump(n, include_attributes=False) for n in tree.body if isinstance(n, ast.FunctionDef)}
oldfuncs, newfuncs = existing_functions(tree0), existing_functions(tree1)
assert all(newfuncs[k] == v for k, v in oldfuncs.items())
for cls, newer in zip((n for n in tree0.body if isinstance(n, ast.ClassDef)), (n for n in tree1.body if isinstance(n, ast.ClassDef))):
    assert cls.name == newer.name
    if cls.name != 'EmbyFlowLocalAddSourceScreenV18':
        assert ast.dump(cls, include_attributes=False) == ast.dump(newer, include_attributes=False)
    else:
        methods = lambda c: {n.name: ast.dump(n, include_attributes=False) for n in c.body if isinstance(n, ast.FunctionDef)}
        assert methods(cls) == methods(newer)
        skinassign = next(n for n in newer.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'skin' for t in n.targets))
        skin = ET.fromstring(ast.literal_eval(skinassign.value.args[0]))
        assert len([e for e in skin if e.get('name') == 'source_card_fill']) == 1
        for i, x in enumerate((222,500,778,1056)):
            icon = next(e for e in skin if e.get('name') == 'card_icon%d' % i)
            assert icon.get('position') == '%d,298' % (x+73) and icon.get('size') == '112,112'
        assert all(int(e.get('zPosition','0')) >= 5 for e in skin if e.tag == 'eLabel' and e.get('text'))
for invalid in (updated, current.replace('class EmbyFlowLocalAddSourceScreenV18(', 'class MissingAddSource(',1)):
    try:
        installer.transform(invalid)
        raise AssertionError('Guard failed')
    except ValueError:
        pass
print('PASS: complete plugin syntax, XML/layers, prior patches, all original methods and player code unchanged, drift/repeat guards')

class Widget:
    def __init__(self,*args): self.instance=self; self.visible=False; self.file=None
    def setPixmapFromFile(self,path): self.file=path
    def setScale(self,value): self.scale=value
    def move(self,pos): self.pos=pos
    def resize(self,size): self.size=size
    def show(self): self.visible=True
    def hide(self): self.visible=False
class Screen(dict):
    def __init__(self):
        super().__init__();self.locations=[];self.focus_zone='cards';self.card_index=0
        for i in range(4):
            self['card_icon%d'%i]=Widget();self['storage_icon%d'%i]=Widget()
    def refresh_locations(self): self.refresh_called=True; self.apply_focus()
    def layout_ready(self): self.layout_called=True; self.refresh_locations();self.apply_focus()
    def apply_focus(self): self.focus_called=True
ns=dict(EmbyFlowLocalAddSourceScreenV18=Screen,Label=Widget,os=os,PLUGIN_PATH='/plugin',EFP=lambda *p:p,EFS=lambda *p:p,
        _EMBYFLOW_V18_ADD_CARD_POSITIONS=[(x,286) for x in (222,500,778,1056)])
exec(installer.RUNTIME,ns)
screen=Screen()
screen.locations=[dict(path='/media/hdd',icon='drive.png'),dict(path='/media/usb',icon='drive.png'),dict(path='/media/autofs/Test',icon='nas.png')]
screen.layout_ready()
assert screen.layout_called and screen.refresh_called and screen.focus_called
assert all(screen['card_icon%d'%i].visible for i in range(4))
assert [Path(screen['card_icon%d'%i].file).stem for i in range(4)]==['disk_usb','nas_search','nas_address','folder_link']
assert [Path(screen['storage_icon%d'%i].file).stem for i in range(3)]==['disk','usb','network']
assert not screen['storage_icon3'].visible
for i,x in enumerate((222,500,778,1056)):
    screen.card_index=i;screen.apply_focus()
    assert screen['source_card_fill'].visible and screen['source_card_fill'].pos==(x+3,289)
screen.focus_zone='storage';screen.apply_focus();assert not screen['source_card_fill'].visible
screen.locations=[];screen.refresh_locations();assert not any(screen['storage_icon%d'%i].visible for i in range(4))
print('PASS: all 7 icon mappings, initial layout, refresh, selection fill follows all 4 cards and hides outside cards, empty list')

with tempfile.TemporaryDirectory() as temp:
    target=Path(temp)/'plugin.py';target.write_bytes(current.encode('utf-8'))
    done=subprocess.run([sys.executable,str(ROOT/'EmbyFlowE2_Quellen_Picons_V1_20261031.py'),'--apply','--path',str(target)],capture_output=True,text=True)
    assert done.returncode==0,done.stderr
    assert target.read_bytes()==updated.encode('utf-8')
    assert next(Path(temp).glob('*.bak')).read_bytes()==current.encode('utf-8')
    for name,encoded in installer.ASSETS.items():
        assert (Path(temp)/'assets/source_setup_v1'/name).read_bytes()==base64.b64decode(encoded)
    again=subprocess.run([sys.executable,str(ROOT/'EmbyFlowE2_Quellen_Picons_V1_20261031.py'),'--apply','--path',str(target)],capture_output=True,text=True)
    assert again.returncode!=0 and target.read_bytes()==updated.encode('utf-8')
print('PASS: actual installer, byte-exact backup and 7 PNG files, atomic plugin write, second install safely rejected')

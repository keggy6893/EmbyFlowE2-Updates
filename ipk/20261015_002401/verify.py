from pathlib import Path
import ast,json,hashlib,subprocess,tarfile,io,base64,tempfile,os
from PIL import Image
w=Path('EmbyFlowE2-IPK-release');m=json.loads((w/'release.json').read_text());ipk=w/m['filename']
assert hashlib.sha256(ipk.read_bytes()).hexdigest()==m['sha256']
assert subprocess.check_output(['ar','t',str(ipk)]).decode().split()==['debian-binary','control.tar.gz','data.tar.gz']
data={}
for part in ['control','data']:
 raw=subprocess.check_output(['ar','p',str(ipk),part+'.tar.gz'])
 with tarfile.open(fileobj=io.BytesIO(raw)) as t:
  for p in t:
   assert p.isfile() and '..' not in Path(p.name).parts and not p.name.startswith('/')
   data[(part,p.name.removeprefix('./'))]=t.extractfile(p).read()
prefix='usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/'
manifest=json.loads(data['data',prefix+'PACKAGE-MANIFEST.json'])
for p,h in manifest['files'].items():assert hashlib.sha256(data['data',p]).hexdigest()==h
original=ast.parse(Path('EmbyFlowE2-installed/plugin.py').read_text());new=ast.parse(data['data',prefix+'plugin.py'])
allowed={'PLUGIN_VERSION','PLUGIN_BUILD_DATE','PLUGIN_UPDATE_BUILD','_EMBYFLOW_V9_ASSET_DIR','_EMBYFLOW_AUDIO_GRADIENT_CACHE'}
def normalize(t):
 for n in t.body:
  if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in allowed for x in n.targets):n.value=ast.Constant(None)
 return ast.dump(t)
assert normalize(original)==normalize(new)
pre=data['control','preinst'].decode();inner=pre.split("<<'PYCHECK'\n")[1].split('\nPYCHECK')[0];ast.parse(inner)
p=subprocess.run(['sh',str(w/'control/preinst')],capture_output=True);assert p.returncode==1 and b'Installation abgebrochen' in p.stderr
ns={'os':os}
tree=ast.parse(data['data',prefix+'plugin.py'])
assets=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='_EMBYFLOW_V9_ASSETS' for x in n.targets))
for name,b in assets.items():assert data['data',prefix+'assets/login/'+name]==base64.b64decode(b)
for (part,name),b in data.items():
 if part=='data' and name.endswith(('.png','.jpg')):Image.open(io.BytesIO(b)).verify()
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_embyflow_v9_install_assets')
with tempfile.TemporaryDirectory() as d:
 ns.update(_EMBYFLOW_V9_ASSET_DIR=d,_EMBYFLOW_V9_ASSETS=assets)
 exec(compile(ast.Module(body=[fn],type_ignores=[]),'login','exec'),ns)
 assert ns['_embyflow_v9_install_assets']()
 for name,b in assets.items():assert (Path(d)/name).read_bytes()==base64.b64decode(b)
 (Path(d)/next(iter(assets))).unlink();assert ns['_embyflow_v9_install_assets']()
for name in ['compat','stream_strategy','skin_utils','item_types']:assert data['data',prefix+name+'.pyc'][:4].hex()==m['python_magic']
assert len([1 for p,n in data if p=='data'])==m['file_count']
print('PASS: package, payload hashes, exact source delta, installer ABI rejection, login recovery, graphics, helper ABI. No receiver installation performed.')

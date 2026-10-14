from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import ast,base64,hashlib,io,tarfile,gzip,shutil,subprocess,json

work=Path('EmbyFlowE2-IPK-release').resolve()
installed=Path('EmbyFlowE2-installed').resolve()
now=datetime.now(ZoneInfo('Europe/Berlin'));stamp=now.strftime('%Y%m%d_%H%M%S')
version=now.strftime('%Y.%m.%d-r%Y%m%d%H%M%S')
root=work/'root';plugin=root/'usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2'
plugin.mkdir(parents=True,exist_ok=True)
source=(installed/'plugin.py').read_text();tree=ast.parse(source)
login=None
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_EMBYFLOW_V9_ASSETS' for t in node.targets):login=ast.literal_eval(node.value)
assert login is not None and len(login)==7
# Preserve exactly the installed release, changing only build identity and fixed-art paths.
old='_EMBYFLOW_V9_ASSET_DIR = "/tmp/embyflow_v9_assets"'
new='_EMBYFLOW_V9_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "login")'
assert source.count(old)==1;source=source.replace(old,new)
old='_EMBYFLOW_AUDIO_GRADIENT_CACHE = "/tmp/embyflow_audio_backdrops/gradient_overlay_v1.png"'
new='_EMBYFLOW_AUDIO_GRADIENT_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "audio_gradient_overlay_v1.png")'
assert source.count(old)==1;source=source.replace(old,new)
source=source.replace('PLUGIN_VERSION = "2026-RCDEV-TEST-20261014"',f'PLUGIN_VERSION = "2026-RCDEV-IPK-{stamp}"',1)
source=source.replace('PLUGIN_BUILD_DATE = "14.10.2026"',f'PLUGIN_BUILD_DATE = "{now.strftime("%d.%m.%Y %H:%M:%S")}"',1)
source=source.replace('PLUGIN_UPDATE_BUILD = 2026101401','PLUGIN_UPDATE_BUILD = 2026101501',1)
(plugin/'plugin.py').write_text(source)
# Allowlisted runtime files only: no archives, personal accounts or stale plugin bytecode.
for name in ['__init__.py','plugin.png','keymap.xml','emby_config.py','disney_search.py','theme_media_manager.py','compat.pyc','stream_strategy.pyc','skin_utils.pyc','item_types.pyc']:
 shutil.copyfile(installed/name,plugin/name)
for directory in ['assets','audio_assets','images/audio_controls']:
 for p in (installed/directory).rglob('*'):
  if p.is_file() and p.suffix.lower() in ['.png','.jpg','.jpeg']:
   target=plugin/p.relative_to(installed);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
for name,encoded in login.items():
 assert '/' not in name and name.endswith('.png')
 target=plugin/'assets/login'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(encoded))
# Build the fixed audio veil from the installed function, with only its destination replaced.
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_embyflow_build_audio_gradient_overlay')
import os
namespace={'os':os,'_EMBYFLOW_AUDIO_GRADIENT_CACHE':str(plugin/'assets/audio_gradient_overlay_v1.png')}
exec(compile(ast.Module(body=[function],type_ignores=[]),'<installed-audio-gradient>','exec'),namespace)
assert namespace['_embyflow_build_audio_gradient_overlay']()
# Preserve original source credentials only if all legacy defaults are empty.
config=ast.parse((plugin/'emby_config.py').read_text())
for node in config.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['EMBY_SERVER','EMBY_USERNAME','EMBY_PASSWORD'] for t in node.targets):
  assert isinstance(node.value,ast.Constant) and not node.value.value
helper_names=['compat.pyc','stream_strategy.pyc','skin_utils.pyc','item_types.pyc']
magic=(plugin/helper_names[0]).read_bytes()[:4]
assert all((plugin/name).read_bytes()[:4]==magic for name in helper_names)
control=work/'control';control.mkdir(exist_ok=True)
(control/'control').write_text(f'''Package: enigma2-plugin-extensions-embyflowe2
Version: {version}
Section: extra
Priority: optional
Architecture: all
Maintainer: EmbyFlowE2
Depends: enigma2, python3-core, python3-requests, python3-pillow
Description: EmbyFlowE2 current VU snapshot {stamp}
 Complete installed plugin snapshot, persistent login artwork and audio veil.
 Contains receiver helper bytecode ABI {magic.hex()}; preinst verifies compatibility.
 Build timestamp Europe/Berlin: {now.isoformat(timespec='seconds')}.
''')
(control/'conffiles').write_text('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/emby_config.py\n')
preinst='''#!/bin/sh
set -eu
if [ -n "${D:-}" ]; then exit 0; fi
python3 - <<'PYCHECK'
import importlib.util,sys
expected=bytes.fromhex("EXPECTED_HEX")
if importlib.util.MAGIC_NUMBER != expected:
    sys.stderr.write("EmbyFlowE2: Python-Bytecode passt nicht zur VU-Sicherung. Installation abgebrochen.\\n")
    sys.exit(1)
PYCHECK
'''.replace('EXPECTED_HEX',magic.hex())
(control/'preinst').write_text(preinst)
postinst='''#!/bin/sh
set -eu
if [ -n "${D:-}" ]; then exit 0; fi
plugin=/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2
# Only stale compiled copies of plugin.py; helper modules are retained.
rm -f "$plugin/plugin.pyc" "$plugin/plugin.py.pyc"
if [ -d "$plugin/__pycache__" ]; then
    find "$plugin/__pycache__" -maxdepth 1 -type f -name 'plugin.*.pyc' -exec rm -f {} \\;
fi
python3 -m py_compile "$plugin/plugin.py"
echo 'EmbyFlowE2 installiert. GUI-Neustart bei Gelegenheit manuell ausfuehren.'
'''
(control/'postinst').write_text(postinst)
for name in ['preinst','postinst']:
 (control/name).chmod(0o755);subprocess.run(['sh','-n',str(control/name)],check=True)
checks={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name != 'PACKAGE-MANIFEST.json'}
(plugin/'PACKAGE-MANIFEST.json').write_text(json.dumps({'timestamp':now.isoformat(timespec='seconds'),'source_sha256':hashlib.sha256((installed/'plugin.py').read_bytes()).hexdigest(),'python_magic':magic.hex(),'files':checks},indent=2)+'\n')
def archive(folder,target):
 with open(target,'wb') as out:
  with gzip.GzipFile(filename='',fileobj=out,mode='wb',mtime=int(now.timestamp())) as gz:
   with tarfile.open(fileobj=gz,mode='w',format=tarfile.GNU_FORMAT) as tar:
    for path in sorted(folder.rglob('*')):
     if not path.is_file():continue
     raw=path.read_bytes();info=tarfile.TarInfo('./'+str(path.relative_to(folder)))
     info.size=len(raw);info.mode=0o755 if path.name in ['preinst','postinst'] and folder==control else 0o644
     info.uid=info.gid=0;info.uname=info.gname='root';info.mtime=int(now.timestamp())
     tar.addfile(info,io.BytesIO(raw))
archive(control,work/'control.tar.gz');archive(root,work/'data.tar.gz')
(work/'debian-binary').write_bytes(b'2.0\n')
ipk=work/f'enigma2-plugin-extensions-embyflowe2_{version}_all.ipk'
subprocess.run(['ar','rcs',str(ipk),'debian-binary','control.tar.gz','data.tar.gz'],cwd=work,check=True)
metadata={'timestamp':stamp,'version':version,'filename':ipk.name,'sha256':hashlib.sha256(ipk.read_bytes()).hexdigest(),'size':ipk.stat().st_size,'python_magic':magic.hex(),'file_count':len(checks)+1}
(work/'release.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata,indent=2))

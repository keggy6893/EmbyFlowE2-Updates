from pathlib import Path
import ast, gzip, hashlib, io, json, tarfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tests/20261031_rc26'
OUT.mkdir(exist_ok=True)
PREFIX='usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/'
URL='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/tests/20261031_rc26/'
def parts(raw):
    assert raw[:8]==b'!<arch>\n'
    result={}; pos=8
    while pos<len(raw):
        h=raw[pos:pos+60]; n=h[:16].decode().strip().rstrip('/'); size=int(h[48:58])
        result[n]=raw[pos+60:pos+60+size]; pos+=60+size+(size%2)
    return result
def unpack(raw):
    with tarfile.open(fileobj=io.BytesIO(raw)) as t:
        return {x.name.removeprefix('./'):t.extractfile(x).read() for x in t if x.isfile()}
def pack(files,scripts=()):
    b=io.BytesIO()
    with gzip.GzipFile(filename='',mode='wb',fileobj=b,mtime=1793444400) as g:
        with tarfile.open(fileobj=g,mode='w',format=tarfile.GNU_FORMAT) as t:
            for n,data in sorted(files.items()):
                x=tarfile.TarInfo('./'+n);x.size=len(data);x.mode=0o755 if n in scripts else 0o644;x.mtime=1793444400
                x.uname=x.gname='root'; t.addfile(x,io.BytesIO(data))
    return b.getvalue()
def ar(files):
    b=b'!<arch>\n'
    for n,data in files.items():
        h=f'{n+"/":<16}{1793444400:<12}{0:<6}{0:<6}{100644:<8}{len(data):<10}`\n'.encode()
        assert len(h)==60
        b+=h+data+(b'\n' if len(data)%2 else b'')
    return b
base=(ROOT/'ipk/20261015_002401/enigma2-plugin-extensions-embyflowe2_2026.10.15-r20261015002401_all.ipk').read_bytes()
assert hashlib.sha256(base).hexdigest()=='dcb75997a559b7e868b270c1dc03b4e2574f79c15b25a70a47dec7508c13acfc'
bp=parts(base); data=unpack(bp['data.tar.gz']);control=unpack(bp['control.tar.gz'])
old=json.loads(data.pop(PREFIX+'PACKAGE-MANIFEST.json'))
assert set(old['files'])==set(data)
for n,h in old['files'].items(): assert hashlib.sha256(data[n]).hexdigest()==h
src=(ROOT/'EmbyFlowE2_2026102801.py').read_text(encoding='utf-8')
assert hashlib.sha256(src.encode()).hexdigest()=='a99ae4ce9756abf9a32c826bba23d44406b409bf28caf96bfe4e37a8cab06d7e'
assert 'import py_compile' not in src
for a,b in {
    '_EMBYFLOW_V9_ASSET_DIR = "/tmp/embyflow_v9_assets"':'_EMBYFLOW_V9_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "login")',
    '_EMBYFLOW_AUDIO_GRADIENT_CACHE = "/tmp/embyflow_audio_backdrops/gradient_overlay_v1.png"':'_EMBYFLOW_AUDIO_GRADIENT_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "audio_gradient_overlay_v1.png")',
    'EmbyFlowE2-Updates/refs/heads/main/update.json':'EmbyFlowE2-Updates/main/tests/20261031_rc26/update.json',
}.items():
    assert src.count(a)==1;src=src.replace(a,b,1)
for rc in (1,2):
    candidate=src.replace("PLUGIN_VERSION = '2026-RCDEV-TEST-20261028-DIRECT-AUDIO'",f"PLUGIN_VERSION = '2026-RC26{'.1' if rc == 2 else ''}'",1).replace('PLUGIN_UPDATE_BUILD = 2026102801',f'PLUGIN_UPDATE_BUILD = {2026103100+rc}',1).replace("PLUGIN_BUILD_DATE = '28.10.2026'","PLUGIN_BUILD_DATE = '31.10.2026'",1)
    compile(candidate,'plugin.py','exec');ast.parse(candidate,feature_version=(3,8))
    (OUT/f'plugin_RC26{'.1' if rc == 2 else ''}.py').write_text(candidate,encoding='utf-8',newline='\n')
rc1=(OUT/'plugin_RC26.py').read_bytes();rc2=(OUT/'plugin_RC26.1.py').read_bytes()
data[PREFIX+'plugin.py']=rc1
control['control']=b'Package: enigma2-plugin-extensions-embyflowe2\nVersion: 2026.10.31-rc26\nSection: extra\nPriority: optional\nArchitecture: all\nMaintainer: EmbyFlowE2\nDepends: enigma2, python3-core, python3-requests, python3-pillow\nDescription: EmbyFlowE2 RC26 with built-in syntax validation\n Python helper ABI 2b0e0d0a; checked by preinst.\n'
oldpost=b'python3 -m py_compile "$plugin/plugin.py"'
newpost=b'''python3 - "$plugin/plugin.py" <<'PYSYNTAX'
import sys
with open(sys.argv[1], "rb") as handle:
    compile(handle.read(), sys.argv[1], "exec", dont_inherit=True)
PYSYNTAX'''
assert control['postinst'].count(oldpost)==1
control['postinst']=control['postinst'].replace(oldpost,newpost)
assert b'py_compile' not in control['postinst']
data[PREFIX+'PACKAGE-MANIFEST.json']=(json.dumps(dict(build=2026103101,version='2026-RC26',python_magic='2b0e0d0a',files={n:hashlib.sha256(v).hexdigest() for n,v in data.items()}),indent=2)+'\n').encode()
packed={'debian-binary':b'2.0\n','control.tar.gz':pack(control,('preinst','postinst')),'data.tar.gz':pack(data)}
result=ar(packed)
assert parts(result)==packed
assert unpack(parts(result)['data.tar.gz'])==data
assert unpack(parts(result)['control.tar.gz'])==control
filename='enigma2-plugin-extensions-embyflowe2_2026.10.31-rc26_all.ipk'
(OUT/filename).write_bytes(result)
manifest=dict(version='2026-RC26.1',build=2026103102,channel='rcdev',target='plugin.py',artifact_type='plugin_py',download=URL+'plugin_RC26.1.py',sha256=hashlib.sha256(rc2).hexdigest(),changelog=['Update-Test fuer Anskar: sichtbarer Wechsel von RC26 auf RC26.1.','Syntaxpruefung ueber eingebautes compile(); kein optionales py_compile erforderlich.'])
(OUT/'update.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
meta=dict(filename=filename,sha256=hashlib.sha256(result).hexdigest(),size=len(result),version='2026-RC26',build=2026103101,python_magic='2b0e0d0a',helper_bytecode_files=4)
(OUT/'release.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
(OUT/'SHA256SUMS').write_text(meta['sha256']+'  '+filename+'\n',encoding='utf-8')
print(json.dumps(meta,indent=2))

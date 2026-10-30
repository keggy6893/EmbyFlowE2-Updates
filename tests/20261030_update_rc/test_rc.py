import ast,builtins,hashlib,io,json,os,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
OUT=Path(__file__).resolve().parent
SRC=(OUT/'plugin_UPDATE_RC1.py').read_text(encoding='utf-8')
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.live=self.root/'plugin.py';self.live.write_bytes(b'ORIGINAL=True\n')
        self.new=(OUT/'plugin_UPDATE_RC2.py').read_bytes();self.record=[]
    def load(self,fail=False):
        nodes=[n for n in ast.parse(SRC).body if isinstance(n,ast.FunctionDef) and n.name in ('_embyflow_update_install_plugin','_embyflow_update_check_python_source')]
        for n in nodes:
            for child in ast.walk(n):
                if isinstance(child,ast.Constant) and isinstance(child.value,str) and child.value.startswith('/tmp/embyflow_update_'):child.value=str(self.root/Path(child.value).name)
        def mark(*a):
            if fail:raise RuntimeError('metadata failure')
            self.record.append(a)
        ns=dict(os=os,PLUGIN_PATH=str(self.root),_embyflow_update_read_url=lambda *a:self.new,EMBYFLOW_UPDATE_ARTIFACT_MAX_BYTES=10000000,EMBYFLOW_UPDATE_ALLOWED_INITIAL_HOSTS=(),_embyflow_update_payload_identity_ok=lambda b:True,_embyflow_update_mark_installed=mark)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'updater','exec'),ns)
        return ns['_embyflow_update_install_plugin']
    def manifest(self):
        m=json.loads((OUT/'update.json').read_text());m['installable']=True;return m
    def blocked(self):
        orig=builtins.__import__
        def imp(n,*a,**k):
            if n=='py_compile':raise ModuleNotFoundError(n)
            return orig(n,*a,**k)
        return patch('builtins.__import__',imp)
    def test_rc1_installs_real_rc2_without_py_compile(self):
        install=self.load()
        with self.blocked():r=install(self.manifest())
        self.assertTrue(r['ok']);self.assertEqual(self.live.read_bytes(),self.new)
        self.assertEqual(Path(r['backup']).read_bytes(),b'ORIGINAL=True\n')
    def test_bad_hash_preserves_plugin(self):
        m=self.manifest();m['sha256']='0'*64
        with self.blocked(),self.assertRaises(RuntimeError):self.load()(m)
        self.assertEqual(self.live.read_bytes(),b'ORIGINAL=True\n')
    def test_bad_syntax_preserves_plugin(self):
        self.new=b'def broken(:\n';m=self.manifest();m['sha256']=hashlib.sha256(self.new).hexdigest()
        with self.blocked(),self.assertRaises(RuntimeError):self.load()(m)
        self.assertEqual(self.live.read_bytes(),b'ORIGINAL=True\n')
    def test_metadata_failure_rolls_back(self):
        with self.blocked(),self.assertRaises(RuntimeError):self.load(True)(self.manifest())
        self.assertEqual(self.live.read_bytes(),b'ORIGINAL=True\n')
    def test_validation_never_executes_source(self):
        self.new=b'raise RuntimeError("do not execute")\n';m=self.manifest();m['sha256']=hashlib.sha256(self.new).hexdigest()
        with self.blocked():self.assertTrue(self.load()(m)['ok'])
    def test_package_install_syntax_uses_builtin(self):
        # Read actual control archive and execute its Python validation snippet.
        raw=next(OUT.glob('*.ipk')).read_bytes();pos=8
        while pos<len(raw):
            h=raw[pos:pos+60];size=int(h[48:58]);n=h[:16].decode().strip().rstrip('/');b=raw[pos+60:pos+60+size];pos+=60+size+size%2
            if n=='control.tar.gz':
                with tarfile.open(fileobj=io.BytesIO(b)) as t:post=t.extractfile('./postinst').read().decode()
        self.assertNotIn('py_compile',post)
        snippet=post.split("<<'PYSYNTAX'\n",1)[1].split('\nPYSYNTAX',1)[0]
        with self.blocked(),patch('sys.argv',['-',str(OUT/'plugin_UPDATE_RC1.py')]):exec(snippet,{})
    def test_five_checks_retained_and_versions_visible(self):
        self.assertEqual(SRC.count('_embyflow_update_check_python_source('),6)
        for rc in (1,2):
            s=(OUT/f'plugin_UPDATE_RC{rc}.py').read_text(encoding='utf-8');self.assertIn(f"PLUGIN_VERSION = '2026-UPDATE-RC{rc}'",s)
            self.assertIn('tests/20261030_update_rc/update.json',s);ast.parse(s,feature_version=(3,8))
if __name__=='__main__':unittest.main(verbosity=2)

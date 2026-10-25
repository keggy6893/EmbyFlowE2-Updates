import ast,tempfile,unittest
from pathlib import Path
from repair_core import patched,HELPER
ROOT=Path(__file__).parents[2]
class Tests(unittest.TestCase):
 def test_supported_old_releases_preserve_all_other_code(self):
  for name in ('EmbyFlowE2_BOOTSTRAP_V2_20260919.py','EmbyFlowE2_2026101805.py'):
   with self.subTest(name=name):
    source=(ROOT/name).read_text();result=patched(source)
    tree=ast.parse(source);node=next(n for n in tree.body if getattr(n,'name',None)=='_embyflow_update_install_plugin')
    newtree=ast.parse(result);new=next(n for n in newtree.body if getattr(n,'name',None)=='_embyflow_update_install_plugin')
    self.assertNotIn('py_compile',ast.get_source_segment(result,new))
    self.assertEqual(sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_embyflow_update_builtin_syntax' for n in ast.walk(new)),5)
    for t in (tree,newtree):t.body=[n for n in t.body if getattr(n,'name',None)!='_embyflow_update_install_plugin']
    self.assertEqual(ast.dump(tree),ast.dump(newtree));self.assertEqual(patched(result),result)
 def test_published_fixed_updater_unchanged(self):
  s=(ROOT/'EmbyFlowE2_2026102402.py').read_text() if (ROOT/'EmbyFlowE2_2026102402.py').is_file() else Path('/workspace/anskar-dreamone-release/EmbyFlowE2_2026102402.py').read_text()
  self.assertEqual(patched(s),s)
 def test_local_compatibility_repair_unchanged(self):
  source=(ROOT/'EmbyFlowE2_2026101805.py').read_text()
  replacement='    class py_compile:\n        @staticmethod\n        def compile(path, **kwargs):\n            with open(path, "rb") as handle:\n                compile(handle.read(), path, "exec", dont_inherit=True)\n'
  source=source.replace('    import py_compile\n',replacement,1);self.assertEqual(patched(source),source)
 def test_bad_check_count_rejected(self):
  source=(ROOT/'EmbyFlowE2_2026101805.py').read_text().replace('py_compile.compile(stage_plugin, doraise=True)','pass')
  with self.assertRaises(RuntimeError):patched(source)
 def test_unexpected_arguments_rejected(self):
  source=(ROOT/'EmbyFlowE2_2026101805.py').read_text().replace('py_compile.compile(stage_plugin, doraise=True)','py_compile.compile(stage_plugin, doraise=False)')
  with self.assertRaises(RuntimeError):patched(source)
 def test_helper_uses_builtin_compile_without_executing_input(self):
  ns={};exec('def factory():\n'+HELPER+'    return _embyflow_update_builtin_syntax\n',ns);check=ns['factory']()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'source.py';sentinel=Path(d)/'executed';p.write_text('open('+repr(str(sentinel))+',"w").write("bad")');check(str(p));self.assertFalse(sentinel.exists())
   p.write_text('def invalid(')
   with self.assertRaises(SyntaxError):check(str(p))
 def test_missing_file_raises(self):
  ns={};exec('def factory():\n'+HELPER+'    return _embyflow_update_builtin_syntax\n',ns)
  with self.assertRaises(OSError):ns['factory']()('/nonexistent/embyflow/source.py')
if __name__=='__main__':unittest.main()

import importlib.util,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('diag',Path(__file__).with_name('collect.py'));diag=importlib.util.module_from_spec(spec);spec.loader.exec_module(diag)
class Tests(unittest.TestCase):
 def test_plain_and_encoded_urls_redacted(self):
  for url in ('http://host/video?api_key=secret','http%3a//host/video?api_key=secret','https%3A%2F%2Fhost/video?token=secret'):
   result=diag.clean('Playing '+url+' end');self.assertNotIn('secret',result);self.assertNotIn('host',result)
 def test_separate_credentials_redacted(self):
  for field in ('api_key','AccessToken','X-Emby-Token','authorization','password','token'):
   self.assertNotIn('secret',diag.clean(field+': secret'))
 def test_tail_bounded_and_drops_partial_line(self):
  with TemporaryDirectory() as tmp:
   p=Path(tmp)/'file';p.write_text('123456\nabc\ndef\n');self.assertEqual(diag.tail(p,7),'def\n')
 def test_excerpts_have_context_and_redact(self):
  with TemporaryDirectory() as tmp:
   p=Path(tmp)/'file';p.write_text('before\nselectTrack 1\nhttp://host/key?api_key=secret\nafter\nnoise\n')
   result='\n'.join(diag.debug_excerpt(p));self.assertIn('selectTrack 1',result);self.assertNotIn('secret',result);self.assertIn('before',result)
 def test_no_control_shell_or_network_calls(self):
  source=Path(diag.__file__).read_text();self.assertNotIn('subprocess',source);self.assertNotIn('urllib',source);self.assertNotIn('requests.',source);self.assertNotIn("open(path, 'w'",source)
 def test_missing_diagnostics_handled(self):
  with patch.object(diag,'decoder_paths',return_value=[]),patch.object(diag,'debug_files',return_value=[]),patch.object(diag,'current_comparison'),patch('builtins.print') as out:
   diag.main();self.assertTrue(any('FERTIG' in str(c) for c in out.call_args_list))
if __name__=='__main__':unittest.main()

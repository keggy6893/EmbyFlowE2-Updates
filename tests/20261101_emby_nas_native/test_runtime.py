import ast
import builtins
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
ns = {'_ebnt_os': os, '_ebnt_log': lambda *a, **k: None}
source=(ROOT/'runtime.py').read_text(encoding='utf-8')
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_ebnt_resolve')
exec(compile(ast.Module(body=[node],type_ignores=[]),'resolver','exec'),ns)

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.mount = self.root/'Action'
        self.mount.mkdir()
        self.file = self.mount/'2012 (2009)'/'2012 (2009).ts'
        self.file.parent.mkdir()
        self.file.write_bytes(b'test movie content')
        self.rows = 'nas:/Action /mounted\\040action nfs4 rw 0 0\n'
        self.info = {'url': 'http://example.invalid/stream.ts', 'item': {
            'Id': 'emby-id', 'Type': 'Movie', 'Name': '2012',
            'MediaSources': [{'Id': 'a', 'Path': '/pi/Action/2012 (2009)/2012 (2009).ts', 'Size': self.file.stat().st_size}]}}
    def tearDown(self):
        self.temp.cleanup()
    def resolve(self):
        realpath=os.path.realpath
        def mapped(path):
            normalized=str(path).replace('\\','/')
            prefix='/media/autofs/Action'
            if normalized.startswith(prefix+'/'):
                return realpath(self.mount.joinpath(*normalized[len(prefix)+1:].split('/')))
            return str(self.mount) if normalized in ('/mounted action','/media/autofs/Action') else realpath(path)
        def opened(path,*args,**kwargs):
            if path=='/proc/mounts': return io.StringIO(self.rows)
            if path=='/etc/auto.network': return io.StringIO(getattr(self,'maptext',''))
            if path=='/etc/enigma2/embyflow_local_sources.json':
                import json
                return io.StringIO(json.dumps(getattr(self,'config',{'sources':[]})))
            raise OSError('unexpected path')
        with patch.object(builtins,'open',side_effect=opened), patch.object(os.path,'realpath',side_effect=mapped):
            return ns['_ebnt_resolve'](self.info)
    def test_idle_configured_autofs(self):
        self.rows=''
        self.config={'sources':[{'path':'/media/autofs/Action','enabled':True}]}
        self.assertEqual(self.resolve()[0][0],str(self.file))
    def test_disabled_source(self):
        self.rows=''
        self.config={'sources':[{'path':'/media/autofs/Action','enabled':False}]}
        self.assertIsNone(self.resolve()[0])
    def test_local_source_excluded(self):
        self.rows=''
        self.config={'sources':[{'path':'/media/usb'}]}
        self.assertIsNone(self.resolve()[0])
    def test_corrupt_configuration(self):
        self.config=[]
        self.assertIsNotNone(self.resolve()[0])
    def test_idle_image_autofs_map(self):
        self.rows='/etc/auto.network /media/autofs autofs rw 0 0\n'
        self.maptext='Action -fstype=nfs,rw,nolock 192.0.2.1:/volume1/Action\n'
        self.assertEqual(self.resolve()[0][0],str(self.file))
    def test_autofs_map_comments_and_invalid_keys(self):
        self.rows='/etc/auto.network /media/autofs autofs rw 0 0\n'
        self.maptext='# Action -fstype=nfs host:/Action\n../Action -fstype=nfs host:/Action\n* -fstype=nfs host:/Action\nAction -fstype=ext4 host:/Action\n'
        self.assertIsNone(self.resolve()[0])
    def test_idle_smb_autofs_map(self):
        self.rows='/etc/auto.network /media/autofs autofs rw 0 0\n'
        self.maptext='Action -fstype=cifs,credentials=/private/file ://nas/Action\n'
        self.assertIsNotNone(self.resolve()[0])
    def test_nfs_nested(self):
        self.assertEqual(self.resolve()[0][0], str(self.file))
    def test_smb_windows_path(self):
        self.rows = self.rows.replace('nfs4', 'cifs')
        self.info['item']['MediaSources'][0]['Path'] = r'Z:\Action\2012 (2009)\2012 (2009).ts'
        self.assertEqual(self.resolve()[0][0], str(self.file))
    def test_direct_root(self):
        direct = self.mount/self.file.name
        self.file.rename(direct)
        self.assertEqual(self.resolve()[0][0], str(direct))
    def test_no_mount(self):
        self.rows = ''
        self.assertIsNone(self.resolve()[0])
    def test_size_mismatch(self):
        self.info['item']['MediaSources'][0]['Size'] += 1
        self.assertIsNone(self.resolve()[0])
    def test_ambiguous_files(self):
        (self.mount/self.file.name).write_bytes(self.file.read_bytes())
        self.assertIsNone(self.resolve()[0])
    def test_multiple_versions(self):
        self.info['item']['MediaSources'].append(dict(self.info['item']['MediaSources'][0], Id='b'))
        self.assertIsNone(self.resolve()[0])
        self.info['url'] += '?MediaSourceId=b'
        self.assertEqual(self.resolve()[0][1]['Id'], 'b')
    def test_traversal(self):
        self.info['item']['MediaSources'][0]['Path'] = '/Action/../2012 (2009).ts'
        self.assertEqual(self.resolve()[1], 'invalid-server-path')
    def test_unsupported_transport(self):
        self.info['local_file'] = True
        self.assertEqual(self.resolve()[1], 'not-remote')
        del self.info['local_file']
        self.info['item']['MediaSources'][0]['Path'] = '/movie.mkv'
        self.assertEqual(self.resolve()[1], 'server-source-not-ts')
    def test_same_input_untouched(self):
        import copy
        before = copy.deepcopy(self.info)
        self.resolve()
        self.assertEqual(self.info, before)
    def test_mount_escape(self):
        self.mount.rename(self.root/'Action Films')
        self.mount = self.root/'Action Films'
        self.rows = 'nas:/Action /mounted\\040action cifs rw 0 0\n'
        self.assertIsNotNone(self.resolve()[0])
    def test_installer_scope(self):
        installer={'__name__':'test_import'}
        exec((ROOT/'installer.py').read_text(encoding='utf-8'),installer)
        base=(ROOT.parent/'20261101_embylocal/plugin_TEST1.py').read_text(encoding='utf-8')
        after=installer['transform'](base)
        self.assertTrue(after.startswith(base.rstrip()))
        compile(after,'full-plugin','exec')
        with self.assertRaises(ValueError): installer['transform'](after)
        with self.assertRaises(ValueError): installer['transform']('pass')
    def test_complete_installer_on_public_audio_basis(self):
        installer={'__name__':'test_import'}
        exec((ROOT/'installer.py').read_text(encoding='utf-8'),installer)
        base=(ROOT.parents[1]/'EmbyFlowE2_2026102801.py').read_text(encoding='utf-8')
        after=installer['transform'](base)
        self.assertTrue(after.startswith(base.rstrip()))
        self.assertEqual(after.count('def _eftsh_launch('),1)
        self.assertEqual(after.count('def _ebnt_launch('),1)
        self.assertIn('# EMBYFLOW_TS_SUBTITLE_STATE_FIX_END',after)
        compile(after,'full-public-plugin','exec')
        ast.parse(after,feature_version=(3,8))
    def test_incomplete_native_rejected(self):
        installer={'__name__':'test_import'}
        exec((ROOT/'installer.py').read_text(encoding='utf-8'),installer)
        base=(ROOT.parents[1]/'EmbyFlowE2_2026102801.py').read_text(encoding='utf-8')
        with self.assertRaises(ValueError):
            installer['transform'](base+'\ndef _eftw_partial(): pass\n')
    def test_upgrade_only_resolver(self):
        installer={'__name__':'test_import'}
        exec((ROOT/'installer.py').read_text(encoding='utf-8'),installer)
        base=(ROOT.parent/'20261101_embylocal/plugin_TEST1.py').read_text(encoding='utf-8')
        before=base.rstrip()+'\n\n'+installer['RUNTIME']
        node=next(n for n in ast.parse(before).body if isinstance(n,ast.FunctionDef) and n.name=='_ebnt_resolve')
        lines=before.splitlines(keepends=True)
        lines[node.lineno-1:node.end_lineno]=[installer['OLD_RESOLVER']+'\n']
        before=''.join(lines)
        after=installer['transform'](before)
        changes=[getattr(a,'name','') for a,b in zip(ast.parse(before).body,ast.parse(after).body) if ast.dump(a)!=ast.dump(b)]
        self.assertEqual(changes,['_ebnt_resolve'])
        compile(after,'full-upgraded-plugin','exec')
        with self.assertRaises(ValueError): installer['transform'](after)

if __name__ == '__main__': unittest.main(verbosity=2)

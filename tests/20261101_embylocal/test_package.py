import ast
import builtins
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('embylocal_build', HERE / 'build.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
raw = (HERE / build.FILENAME).read_bytes()
members = build.ar_parts(raw)
data = build.unpack(members['data.tar.gz']); control = build.unpack(members['control.tar.gz'])
source = data[build.PREFIX + 'plugin.py'].decode()
tree = ast.parse(source)


class Tests(unittest.TestCase):
    def test_manifest_and_resources(self):
        manifest = json.loads(data[build.PREFIX + 'PACKAGE-MANIFEST.json'])
        self.assertEqual(set(manifest['files']), set(data) - {build.PREFIX + 'PACKAGE-MANIFEST.json'})
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256(data[name]).hexdigest(), digest)
        self.assertEqual(len(data), 55)
        for dirname, count in [('source_setup_v1', 7), ('local_source_picons_20261026', 7), ('local_folder_grid_20261026', 2), ('local_sources_v16', 8)]:
            icons = [v for n, v in data.items() if '/assets/' + dirname + '/' in n]
            self.assertEqual(len(icons), count)
            self.assertTrue(all(v.startswith(b'\x89PNG\r\n\x1a\n') for v in icons))

    def test_no_receiver_configuration_or_http_trial(self):
        self.assertTrue(all(n.startswith(build.PREFIX) for n in data))
        self.assertNotIn('EMBYFLOW_DEBUG_LOGS = True', source)
        self.assertNotIn('_efua_vu_remote_audio_trial', source)
        self.assertNotIn('_eftsh_install_comparison', source)
        self.assertNotIn('EMBYFLOW_LOCAL_SKYFALL_DETAIL_V1_BEGIN', source)
        self.assertNotIn('EMBYFLOW_GERMAN_FORCED_AUTO_POLICY_BEGIN', source)
        for needle in (b'192.168.1.107', b'192.168.1.11', b'C:\\Users\\bumse', b'29416.iovagy.org', b'GoM6893'):
            self.assertFalse(any(needle in value for value in data.values()), needle)
        self.assertIn(build.PREFIX + 'emby_config.py', control['conffiles'].decode())

    def test_complete_syntax_and_helper_abi(self):
        compile(source, 'plugin.py', 'exec')
        ast.parse(source, feature_version=(3, 8))
        helpers = [v for n, v in data.items() if n.endswith('.pyc')]
        self.assertEqual(len(helpers), 4)
        self.assertTrue(all(v[:4].hex() == '2b0e0d0a' for v in helpers))
        for value in data.values():
            if value.startswith(b'#!/usr/bin/env python'):
                compile(value, '<package-source>', 'exec')

    def test_preinstall_rejects_different_abi_and_preserves_backup_order(self):
        script = control['preinst'].decode()
        python = script.split("<<'PYCHECK'\n", 1)[1].split('\nPYCHECK', 1)[0]
        with patch.object(importlib.util, 'MAGIC_NUMBER', bytes.fromhex('2b0e0d0a')):
            exec(python, {})
        with patch.object(importlib.util, 'MAGIC_NUMBER', b'BAD!'), self.assertRaises(SystemExit) as error:
            exec(python, {})
        self.assertEqual(error.exception.code, 1)
        self.assertLess(script.index('PYCHECK\nplugin='), script.index('tar -czf'))
        self.assertIn('umask 077', script)
        self.assertIn('/etc/enigma2/embyflow-backups', script)

    def test_postinstall_without_optional_compile_module(self):
        script = control['postinst'].decode()
        python = script.split("<<'PYSYNTAX'\n", 1)[1].split('\nPYSYNTAX', 1)[0]
        real_import = builtins.__import__
        def blocked(name, *args, **kwargs):
            if name == 'py_compile':
                raise ModuleNotFoundError(name)
            return real_import(name, *args, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'plugin.py'; path.write_bytes(source.encode())
            with patch.object(sys, 'argv', ['-', str(path)]), patch('builtins.__import__', blocked):
                exec(python, {})
        self.assertNotIn('killall', script)
        self.assertNotIn('init 4', script)
        self.assertNotIn('\nreboot', script)
        self.assertIn('manuell', script)

    def test_native_routing_and_http_passthrough(self):
        names = ('_eftsh_path', '_eftsh_launch')
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        calls = []
        class Ref:
            def __init__(self, *args): self.args = args
            def setName(self, title): self.title = title
        namespace = dict(eServiceReference=Ref, _EFTSH_OPEN=lambda *args: calls.append(args) or args)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<native-launch>', 'exec'), namespace)
        original = object(); info = {'local_file': True, 'url': '/media/net/NAS/2012.ts'}
        routed = namespace['_eftsh_launch']('session', original, '2012', info['url'], info)
        self.assertEqual(routed[1].args, (1, 0, info['url']))
        self.assertEqual(routed[4]['local_service_type'], 1)
        self.assertNotIn('local_service_type', info)
        for url, flags in [('http://server/video.ts', {'local_file': False}), ('https://server/video.ts', {'local_file': True}), ('/media/usb/film.mkv', {'local_file': True}), ('relative.ts', {'local_file': True})]:
            result = namespace['_eftsh_launch']('session', original, 'film', url, flags)
            self.assertIs(result[1], original)
            self.assertIs(result[4], flags)

    def test_navigation_is_visible_and_not_duplicated(self):
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_eflocal_entries')
        ns = {}; exec(compile(ast.Module(body=[node], type_ignores=[]), '<navigation>', 'exec'), ns)
        entries = [('Start', {}), ('Einstellungen', {'_direct_action_ref12': 'settings'})]
        rows = ns['_eflocal_entries'](entries)
        self.assertEqual(rows[1], ('Emby Local', {'_direct_action_ref12': 'local_usb'}))
        self.assertEqual(ns['_eflocal_entries'](rows), rows)
        self.assertEqual(len(entries), 2)

    def test_own_subtitle_menu_is_preserved(self):
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_eftu_menu')
        text = ast.get_source_segment(source, node)
        self.assertIn('EmbyFlowTrackSelectionScreen', text)
        self.assertNotIn('SubtitleSelection', text)
        self.assertIn('EmbyFlowMoviePlayer.open_subtitle_selection = _eftu_menu', source)

    def test_package_metadata_matches(self):
        meta = json.loads((HERE / 'release.json').read_text())
        self.assertEqual(meta['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(meta['version'], build.VERSION)
        self.assertFalse(meta['hardware_confirmed'])
        self.assertIn('PLUGIN_VERSION = ' + repr(build.VERSION), source)
        self.assertIn('PLUGIN_UPDATE_BUILD = ' + str(build.BUILD), source)
        self.assertIn('EmbyFlowLocalSourcesScreenV17', source)
        self.assertIn('EmbyFlowLocalAddSourceScreenV18', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)

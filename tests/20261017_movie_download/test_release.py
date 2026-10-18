"""Check release identity and the actual previous build's updater installation."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DownloadReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = (ROOT / 'EmbyFlowE2_2026101802.py').read_bytes()
        cls.manifest = (ROOT / 'update.json').read_bytes()
        cls.release_tree = ast.parse(cls.data)
        cls.base_tree = ast.parse((ROOT / 'EmbyFlowE2_2026101704.py').read_text())

    def namespace(self, temporary_directory):
        names = {'_embyflow_update_https_url', '_embyflow_update_normalize_manifest',
                 '_embyflow_update_payload_identity_ok', '_embyflow_update_install_plugin'}
        nodes = [node for node in self.base_tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        # Isolate the original updater's fixed /tmp staging and backup paths.
        class IsolatePaths(ast.NodeTransformer):
            def visit_Constant(self, node):
                if isinstance(node.value, str) and node.value.startswith('/tmp/embyflow_'):
                    return ast.copy_location(ast.Constant(os.path.join(temporary_directory, Path(node.value).name)), node)
                return node
        tree = IsolatePaths().visit(ast.Module(body=copy.deepcopy(nodes), type_ignores=[]))
        self.marked = []
        namespace = dict(json=json, re=re, os=os, PLUGIN_PATH=temporary_directory,
                         EMBYFLOW_UPDATE_CHANNEL='rcdev',
                         EMBYFLOW_UPDATE_ALLOWED_INITIAL_HOSTS=('raw.githubusercontent.com',),
                         EMBYFLOW_UPDATE_ARTIFACT_MAX_BYTES=16*1024*1024,
                         _embyflow_update_read_url=lambda *args: self.data,
                         _embyflow_update_mark_installed=lambda *args: self.marked.append(args))
        exec(compile(ast.fix_missing_locations(tree), 'previous_updater.py', 'exec'), namespace)
        return namespace

    def test_release_metadata_and_hash_match(self):
        manifest = json.loads(self.manifest)
        assignments = {node.targets[0].id: ast.literal_eval(node.value)
                       for node in self.release_tree.body
                       if isinstance(node, ast.Assign) and len(node.targets) == 1 and
                       isinstance(node.targets[0], ast.Name) and
                       node.targets[0].id in ('PLUGIN_VERSION', 'PLUGIN_UPDATE_BUILD', 'PLUGIN_BUILD_DATE')}
        self.assertEqual(assignments['PLUGIN_UPDATE_BUILD'], 2026101802)
        self.assertEqual(assignments['PLUGIN_UPDATE_BUILD'], manifest['build'])
        self.assertEqual(assignments['PLUGIN_VERSION'], manifest['version'])
        self.assertEqual(assignments['PLUGIN_BUILD_DATE'], '18.10.2026')
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), manifest['sha256'])

    def test_release_is_reproducible_and_uses_exact_receiver_tested_code(self):
        spec = importlib.util.spec_from_file_location('release_builder', ROOT / '.github/build_download_2026101802.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.build_source().encode(), self.data)
        directory = ROOT / 'tests/20261017_pgs_native'
        suffix = '\n\n' + (directory / 'patch.py').read_text() + '\n\n' + (directory / 'auto.py').read_text()
        self.assertIn(suffix, self.data.decode())
        self.assertIn(b'_efdl_engine', self.data)
        for name in ('engine.py', 'dialogs.py', 'ui.py', 'library.py'):
            content = (ROOT / 'tests/20261017_movie_download' / name).read_text()
            if name == 'engine.py':
                self.assertIn(repr(content), self.data.decode())
            elif name == 'ui.py':
                self.assertIn(content.replace("            self.events.put(('done', path))", "            _efdl_library_save(path, self.item, self.data)\n            self.events.put(('done', path))"), self.data.decode())
            else:
                self.assertIn(content, self.data.decode())
        self.assertNotIn(b'EMBYFLOW_ATV76_DETAIL_LAYOUT', self.data)
        self.assertNotIn(b'EMBYFLOW_LAYOUT_DIAG', self.data)

    def test_previous_updater_accepts_and_installs_release_with_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            namespace = self.namespace(tmp)
            normalized = namespace['_embyflow_update_normalize_manifest'](self.manifest)
            self.assertTrue(normalized['installable'])
            self.assertTrue(namespace['_embyflow_update_payload_identity_ok'](self.data))
            target = Path(tmp) / 'plugin.py'
            previous = (ROOT / 'EmbyFlowE2_2026101704.py').read_bytes()
            target.write_bytes(previous)
            target.chmod(0o640)
            result = namespace['_embyflow_update_install_plugin'](normalized)
            self.assertTrue(result['ok'])
            self.assertEqual(target.read_bytes(), self.data)
            self.assertEqual(Path(result['backup']).read_bytes(), previous)
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
            self.assertEqual(self.marked, [(normalized['version'], 2026101802)])

    def test_hash_failure_leaves_installed_plugin_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            namespace = self.namespace(tmp)
            normalized = namespace['_embyflow_update_normalize_manifest'](self.manifest)
            normalized['sha256'] = '0' * 64
            target = Path(tmp) / 'plugin.py'
            target.write_text('# existing plugin\n')
            with self.assertRaises(RuntimeError): namespace['_embyflow_update_install_plugin'](normalized)
            self.assertEqual(target.read_text(), '# existing plugin\n')
            self.assertEqual(self.marked, [])

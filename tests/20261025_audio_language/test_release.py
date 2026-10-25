import ast
import hashlib
import unittest
from pathlib import Path
from build import build, BUILD, VERSION, BASE_SHA

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = (ROOT / 'EmbyFlowE2_2026102501.py').read_bytes()
        cls.release = build().read_bytes()
        cls.runtime = (HERE / 'runtime.py').read_text()

    def test_baseline_and_exact_runtime(self):
        self.assertEqual(hashlib.sha256(self.base).hexdigest(), BASE_SHA)
        self.assertEqual(self.release.decode().count('# EMBYFLOW_ACTIVE_AUDIO_LANGUAGE_V1_BEGIN'), 1)
        self.assertTrue(self.release.decode().endswith(self.runtime))

    def test_only_identity_and_appended_repair_change(self):
        baseline = ast.parse(self.base)
        release = ast.parse(self.release.decode().split('# EMBYFLOW_ACTIVE_AUDIO_LANGUAGE_V1_BEGIN')[0])
        names = {'PLUGIN_VERSION', 'PLUGIN_BUILD_DATE', 'PLUGIN_UPDATE_BUILD', 'PLUGIN_UPDATE_CHANGELOG'}
        for tree in (baseline, release):
            tree.body = [n for n in tree.body if not (isinstance(n, ast.Assign) and
                         any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
        self.assertEqual(ast.dump(baseline), ast.dump(release))

    def test_release_identity_and_python38_syntax(self):
        tree = ast.parse(self.release, feature_version=(3, 8))
        values = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
                  if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id in ('PLUGIN_VERSION', 'PLUGIN_UPDATE_BUILD')}
        self.assertEqual(values['PLUGIN_VERSION'], VERSION)
        self.assertEqual(values['PLUGIN_UPDATE_BUILD'], BUILD)

    def test_only_display_methods_are_wrapped(self):
        tree = ast.parse(self.runtime)
        targets = [n.targets[0].attr for n in tree.body
                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Attribute)]
        self.assertEqual(targets, ['tester_osd_selected_streams', 'show_overlay', 'update_playback_overlay'])
        self.assertNotIn('selectTrack(', self.runtime)
        self.assertNotIn('seekTo(', self.runtime)
        self.assertNotIn('playService(', self.runtime)

    def test_reproducible_release(self):
        self.assertEqual(build().read_bytes(), self.release)


if __name__ == '__main__':
    unittest.main()

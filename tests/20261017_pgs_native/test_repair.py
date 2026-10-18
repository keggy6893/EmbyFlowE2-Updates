import ast
from pathlib import Path
import unittest

from repair_parent import repaired, NEW_MARKER

HERE = Path(__file__).resolve().parent


class RepairTests(unittest.TestCase):
    def setUp(self):
        # V1 used the standalone display as native output parent.
        self.original_patch = (HERE / 'patch.py').read_text().replace(
            NEW_MARKER + '\n', '', 1).replace(
            "    widget = getattr(self, 'instance', None)",
            "    widget = getattr(window, 'instance', None)", 1)
        self.base = (HERE.parent.parent / 'EmbyFlowE2_2026101704.py').read_text()

    def test_exact_v1_artifact_changes_only_parent_and_marker(self):
        original = self.base + '\n' + self.original_patch
        result = repaired(original)
        self.assertTrue(result.startswith(self.base))
        expected = original.replace('# EMBYFLOW_PGS_NATIVE_LOCAL_V1',
            '# EMBYFLOW_PGS_NATIVE_LOCAL_V1\n' + NEW_MARKER, 1)
        before, marker, tail = expected.partition('# EMBYFLOW_PGS_NATIVE_LOCAL_V1')
        expected = before + marker + tail.replace(
            "    widget = getattr(window, 'instance', None)",
            "    widget = getattr(self, 'instance', None)", 1)
        self.assertEqual(result, expected)
        with self.assertRaises(RuntimeError): repaired(result)

    def test_missing_v1_or_ambiguous_parent_rejected(self):
        with self.assertRaises(RuntimeError): repaired(self.base)
        with self.assertRaises(RuntimeError): repaired(self.base + self.original_patch + self.original_patch)

    def test_new_patch_and_repaired_patch_have_identical_ast(self):
        repaired_patch = repaired(self.original_patch)
        self.assertEqual(ast.dump(ast.parse(repaired_patch)), ast.dump(ast.parse((HERE / 'patch.py').read_text())))


if __name__ == '__main__':
    unittest.main()

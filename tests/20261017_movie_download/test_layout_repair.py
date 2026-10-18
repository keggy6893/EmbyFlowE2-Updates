from historical import source as historical_source
from pathlib import Path
import unittest
from repair_layout import patched, METHOD

class LayoutRepairTests(unittest.TestCase):
    def test_full_v6_becomes_built_v7(self):
        before=historical_source(6)
        after=historical_source(7)
        self.assertEqual(patched(before),after)
    def test_repeat_repair_keeps_every_byte(self):
        source=historical_source(7)
        self.assertEqual(patched(source),source)
    def test_unexpected_layout_rejected(self):
        source=historical_source(6)
        source=source.replace('    def cleanup(self):\n','    def unknown_cleanup(self):\n')
        with self.assertRaises(ValueError):patched(source)

if __name__=='__main__':unittest.main()

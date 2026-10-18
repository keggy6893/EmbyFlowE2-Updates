from historical import source as historical_source
import ast
from pathlib import Path
import tempfile
import unittest

from install_quota import patched, install

HERE = Path(__file__).resolve().parent


class QuotaInstallerTests(unittest.TestCase):
    def test_actual_v8_with_pgs_is_updated_without_losing_pgs_or_local_code(self):
        original = historical_source(8)
        suffix = '\n' + (HERE.parent / '20261017_pgs_native/patch.py').read_text()
        suffix += '\n' + (HERE.parent / '20261017_pgs_native/auto.py').read_text()
        source = original + suffix + '\n# keep receiver-local addition\n'
        engine = (HERE / 'engine.py').read_text()
        result = patched(source, engine)
        self.assertTrue(result.endswith(suffix + '\n# keep receiver-local addition\n'))
        start = result.index('exec(compile(', result.index('import types as _efdl_types'))
        embedded = ast.parse(result[start:result.index('\n', start)]).body[0].value.args[0].args[0].value
        self.assertEqual(embedded, engine)
        self.assertEqual(patched(result, engine), result)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'plugin.py'; path.write_text(source); path.chmod(0o640)
            install(path, engine)
            self.assertEqual(path.read_text(), result)
            self.assertEqual(next(path.parent.glob('*.vor-dl-limit5-*')).read_text(), source)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_missing_download_test_is_rejected(self):
        with self.assertRaises(RuntimeError): patched('PLUGIN_NAME="EmbyFlow E2"', 'pass')

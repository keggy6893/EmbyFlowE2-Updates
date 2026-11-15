"""Isolated tests: no receiver and no changes to production updater."""
import hashlib
import importlib.util
import pathlib
import tempfile
import unittest

LIB = pathlib.Path(__file__).resolve().parents[1] / "tools" / "transactional_bundle.py"
spec = importlib.util.spec_from_file_location("transactional_bundle", LIB)
transaction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transaction)


def checks(files):
    return {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = pathlib.Path(self.folder.name)
        (self.root / "plugin.py").write_bytes(b"ORIGINAL PLUGIN\n")
        (self.root / "keep.txt").write_bytes(b"KEEP")

    def test_success(self):
        files = {"plugin.py": b"version = 2\n", "refactor_modules/utils.py": b"def f(): return 3\n"}
        self.assertEqual(transaction.install_bundle(self.root, files, checks(files)), 2)
        self.assertEqual((self.root / "plugin.py").read_bytes(), files["plugin.py"])
        self.assertEqual((self.root / "refactor_modules/utils.py").read_bytes(), files["refactor_modules/utils.py"])
        self.assertEqual((self.root / "keep.txt").read_bytes(), b"KEEP")

    def test_sha_mismatch_changes_nothing(self):
        files = {"plugin.py": b"version = 2\n"}
        with self.assertRaises(transaction.BundleError):
            transaction.install_bundle(self.root, files, {"plugin.py": "0" * 64})
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"ORIGINAL PLUGIN\n")

    def test_syntax_error_changes_nothing(self):
        files = {"plugin.py": b"def invalid(\n"}
        with self.assertRaises(transaction.BundleError):
            transaction.install_bundle(self.root, files, checks(files))
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"ORIGINAL PLUGIN\n")

    def test_rollback_existing_and_new(self):
        files = {"plugin.py": b"version = 2\n", "refactor_modules/utils.py": b"x=1\n"}
        with self.assertRaises(OSError):
            transaction.install_bundle(self.root, files, checks(files), fail_after=2)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"ORIGINAL PLUGIN\n")
        self.assertFalse((self.root / "refactor_modules/utils.py").exists())

    def test_rollback_existing_after_first(self):
        files = {"plugin.py": b"version = 2\n", "refactor_modules/utils.py": b"x=1\n"}
        with self.assertRaises(OSError):
            transaction.install_bundle(self.root, files, checks(files), fail_after=1)
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"ORIGINAL PLUGIN\n")

    def test_path_traversal_rejected(self):
        for name in ("../escape.py", "/tmp/escape.py", "a/../../escape.py", "a\\..\\escape.py", "foo//bar.py"):
            with self.subTest(name=name):
                files = {name: b"x=1\n"}
                with self.assertRaises(transaction.BundleError):
                    transaction.install_bundle(self.root, files, checks(files))
        self.assertEqual((self.root / "plugin.py").read_bytes(), b"ORIGINAL PLUGIN\n")

    def test_symlink_rejected(self):
        (self.root / "fake").symlink_to(self.root, target_is_directory=True)
        files = {"fake/evil.py": b"x=1\n"}
        with self.assertRaises(transaction.BundleError):
            transaction.install_bundle(self.root, files, checks(files))


if __name__ == "__main__":
    unittest.main(verbosity=2)

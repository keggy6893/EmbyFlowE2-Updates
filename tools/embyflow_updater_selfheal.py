"""In-process syntax-check recovery for the EmbyFlowE2 updater.

Call ensure_syntax_checker() before an updater imports py_compile.
On stripped Enigma2 images this provides the needed syntax-check API
using Python's built-in compile(), without modifying the installed plugin.
"""

import sys
import types


def ensure_syntax_checker():
    """Return True if the missing py_compile compatibility shim is installed."""
    try:
        import py_compile  # noqa: F401
        return False
    except ImportError as error:
        if getattr(error, "name", None) not in (None, "py_compile"):
            raise

    if "py_compile" in sys.modules:
        raise RuntimeError("py_compile exists but cannot be imported safely")

    module = types.ModuleType("py_compile")

    class PyCompileError(Exception):
        pass

    def check_source(file, cfile=None, dfile=None, doraise=False, optimize=-1,
                     invalidation_mode=None, quiet=0):
        try:
            with open(file, "rb") as handle:
                source = handle.read()
            compile(source, dfile or file, "exec", dont_inherit=True)
        except (SyntaxError, UnicodeError, OSError, ValueError) as error:
            if doraise:
                raise PyCompileError(str(error))
            if not quiet:
                print("Syntaxcheck failed for %s: %s" % (file, error))
            return None
        # Syntax check only: no .pyc is written.
        return cfile or file

    module.PyCompileError = PyCompileError
    module.compile = check_source
    sys.modules["py_compile"] = module
    return True

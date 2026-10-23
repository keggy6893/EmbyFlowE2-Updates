"""Prepare an updater repair; an already broken updater cannot bootstrap itself."""
from pathlib import Path
import ast

HELPER = '''
def _embyflow_update_check_python_source(path):
    # Validate without executing source or requiring the optional py_compile
    # package. Normal Python import manages the bytecode cache after restart.
    with open(path, "rb") as handle:
        source = handle.read()
    compile(source, path, "exec", dont_inherit=True)


'''


def repair(source):
    start = source.index('def _embyflow_update_install_plugin(manifest):')
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == '_embyflow_update_install_plugin')
    lines = source.splitlines(keepends=True)
    original = ''.join(lines[node.lineno - 1:node.end_lineno])
    fixed = original.replace('    import py_compile\n', '')
    import re
    fixed, count = re.subn(r'py_compile\.compile\((\w+), doraise=True\)',
                           r'_embyflow_update_check_python_source(\1)', fixed)
    if count != 5 or fixed == original:
        raise ValueError('Unexpected updater layout')
    result = source.replace(original, HELPER + fixed, 1)
    ast.parse(result, feature_version=(3, 8))
    return result


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    source = (root / 'EmbyFlowE2_2026102201.py').read_text(encoding='utf-8')
    result = repair(source)
    (root / 'updater_compile_candidate.py').write_text(result, encoding='utf-8', newline='\n')
    print('Prepared updater repair. Not installed or published.')

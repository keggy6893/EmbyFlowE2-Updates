"""Repair existing layout helper functions without changing other local features."""
import ast
from pathlib import Path
import os
import shutil
import tempfile
import time


def patch(source, runtime):
    compile(source, 'existing_plugin.py', 'exec')
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if '_efl_plan' not in functions:
        if '_efl_detail_layout' in functions:
            raise RuntimeError('Unvollstaendiger Layout-Test. Nichts geaendert.')
        for required in ('class EmbyFlowDetailScreen', 'EMBYFLOW_CINEMA_POLISH_V2_20261013', 'EMBYFLOW_DETAIL_TEXT_SPACE_V4_20261013'):
            if required not in source:
                raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
        result = source + '\n\n' + runtime
    else:
        wanted = ('_efl_plan', '_efl_detail_layout')
        snippets = {}
        for node in ast.parse(runtime).body:
            if isinstance(node, ast.FunctionDef) and node.name in wanted:
                snippets[node.name] = ast.get_source_segment(runtime, node) + '\n'
        if not all(name in functions for name in wanted):
            raise RuntimeError('Layoutfunktion fehlt. Nichts geaendert.')
        lines = source.splitlines(keepends=True)
        for name in sorted(wanted, key=lambda name: functions[name].lineno, reverse=True):
            node = functions[name]
            lines[node.lineno-1:node.end_lineno] = [snippets[name]]
        result = ''.join(lines)
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, runtime):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad. Nichts geaendert.')
    source = path.read_text()
    result = patch(source, runtime)
    if source == result:
        print('Layout-Test V2 bereits vorhanden.', flush=True)
        return False
    backup = str(path) + '.vor-layout-v2-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits. Nichts geaendert.')
    shutil.copy2(path, backup)
    fd, name = tempfile.mkstemp(prefix='plugin.py.layout-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(result)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copystat(path, name)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print('Layout-Test V2 installiert. Sicherung:', backup, flush=True)
    return True

#!/usr/bin/env python3
"""Generate a modular RC26.9 candidate without modifying the official plugin.

The candidate requires refactor_modules/local_media_utils.py alongside it.
It is NOT compatible with the existing single-file plugin.py updater yet.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'plugin_2026111523.py'
OUTPUT = ROOT / 'refactor_candidates' / 'plugin_rc269_modular.py'
MOVED = ('embyflow_local_human_size', 'embyflow_local_clean_title')


def build():
    source = SOURCE.read_text(encoding='utf-8')
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    found = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in MOVED}
    assert set(found) == set(MOVED), 'Functions to extract not found exactly once'
    for name in MOVED:
        matches = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
        assert len(matches) == 1, f'Ambiguous function: {name}'
    for node in sorted(found.values(), key=lambda x: x.lineno, reverse=True):
        # Explicit absolute import works if the helper package is placed with plugin.py.
        lines[node.lineno - 1:node.end_lineno] = [
            'from refactor_modules.local_media_utils import %s\n' % node.name
        ]
    result = ''.join(lines)
    compile(result, str(OUTPUT), 'exec')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(result, encoding='utf-8')
    return OUTPUT


if __name__ == '__main__':
    print('CANDIDATE:', build())

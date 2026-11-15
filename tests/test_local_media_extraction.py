#!/usr/bin/env python3
"""Behavior checks: original RC26.9 functions versus extracted module."""
import ast
import importlib.util
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin_2026111523.py'
MODULE = ROOT / 'refactor_modules' / 'local_media_utils.py'
NAMES = ('embyflow_local_human_size', 'embyflow_local_clean_title')


def load_original():
    tree = ast.parse(PLUGIN.read_text(encoding='utf-8'))
    nodes = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in NAMES]
    assert len(nodes) == 2
    ns = {'os': os}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<rc269-functions>', 'exec'), ns)
    return ns


def load_module():
    spec = importlib.util.spec_from_file_location('embyflow_local_media_utils', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_equivalence():
    original, extracted = load_original(), load_module()
    sizes = [None, 0, 1, 10, 1023, 1024, 1025, 10**6, 10**9, 10**15, -1, 'not_a_number', '2048', {}, []]
    titles = ['', None, '/movie/James_Bond_007.ts', '/x/movie.mkv', 'C:/test/my_film.ts', 'file_without_extension', '_', 14, '/path/.hidden']
    for val in sizes:
        assert original[NAMES[0]](val) == getattr(extracted,NAMES[0])(val), ('size',val)
    for val in titles:
        assert original[NAMES[1]](val) == getattr(extracted,NAMES[1])(val), ('title',val)
    old = ast.parse(PLUGIN.read_text(encoding='utf-8'))
    new = ast.parse(MODULE.read_text(encoding='utf-8'))
    for name in NAMES:
        a = next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name)
        b = next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name==name)
        assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False), name
    print('FUNCTION EQUIVALENCE PASS')


def test_candidate():
    subprocess.check_call([sys.executable, str(ROOT/'tools'/'build_modular_candidate.py')])
    candidate = ROOT/'refactor_candidates'/'plugin_rc269_modular.py'
    tree = ast.parse(candidate.read_text(encoding='utf-8'))
    assert not any(isinstance(n,ast.FunctionDef) and n.name in NAMES for n in tree.body)
    imports = [n for n in tree.body if isinstance(n,ast.ImportFrom) and n.module=='refactor_modules.local_media_utils']
    imported = {alias.name for n in imports for alias in n.names}
    assert imported==set(NAMES)
    print('MODULAR CANDIDATE PASS (syntax only; receiver test outstanding)')


if __name__ == '__main__':
    test_equivalence()
    test_candidate()

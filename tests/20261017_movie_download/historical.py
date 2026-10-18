"""Exact historical installer inputs, stored as deltas against the public base."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def source(version):
    fixture = json.loads((HERE / 'fixtures' / ('v%d.json' % version)).read_text())
    base = (HERE.parents[1] / 'EmbyFlowE2_2026101704.py').read_text()
    assert hashlib.sha256(base.encode()).hexdigest() == fixture['base_sha256']
    lines = base.splitlines(keepends=True)
    for start, end, replacement in reversed(fixture['edits']):
        lines[start:end] = [replacement]
    result = ''.join(lines)
    assert hashlib.sha256(result.encode()).hexdigest() == fixture['sha256']
    return result

"""Build a reviewable receiver-test candidate; never publish update.json."""
from pathlib import Path
import ast
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_SHA256 = '742aa17708e7ff3a204665980a8195708a68420b925394226e9fbd7408ed5ef2'


def build(baseline, output):
    data = baseline.read_bytes()
    if hashlib.sha256(data).hexdigest() != BASE_SHA256:
        raise RuntimeError('Published LCD baseline mismatch')
    source = data.decode('utf-8')
    changes = {
        'PLUGIN_VERSION = "2026-RCDEV-TEST-20261020-LCD-CONTENT-TIME"':
            'PLUGIN_VERSION = "2026-RCDEV-TEST-20261021-AUDIO-LOCAL-CANDIDATE"',
        'PLUGIN_UPDATE_BUILD = 2026102001': 'PLUGIN_UPDATE_BUILD = 2026102101',
        'PLUGIN_BUILD_DATE = "20.10.2026"': 'PLUGIN_BUILD_DATE = "21.10.2026"',
    }
    for old, new in changes.items():
        if source.count(old) != 1: raise RuntimeError('Baseline identity mismatch')
        source = source.replace(old, new, 1)
    source += '\n\n' + (HERE / 'audio_runtime.py').read_text(encoding='utf-8')
    ast.parse(source, feature_version=(3, 8))
    compile(source, str(output), 'exec')
    output.write_bytes(source.encode('utf-8'))
    return hashlib.sha256(output.read_bytes()).hexdigest()


if __name__ == '__main__':
    baseline = ROOT / 'EmbyFlowE2_2026102001.py'
    if not baseline.exists(): baseline = HERE / 'base.py'
    output = HERE / 'EmbyFlowE2_2026102101_candidate.py'
    print(output.name, build(baseline, output))

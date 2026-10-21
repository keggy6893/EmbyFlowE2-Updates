from pathlib import Path
import ast
import hashlib

HERE = Path(__file__).resolve().parent
BASE_SHA = '742aa17708e7ff3a204665980a8195708a68420b925394226e9fbd7408ed5ef2'


def build():
    baseline = HERE / 'base.py'
    if not baseline.exists():
        baseline = HERE.parents[1] / 'EmbyFlowE2_2026102001.py'
    raw = baseline.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise RuntimeError('Published LCD baseline mismatch')
    source = raw.decode('utf-8')
    for old, new in [
        ('PLUGIN_VERSION = "2026-RCDEV-TEST-20261020-LCD-CONTENT-TIME"', 'PLUGIN_VERSION = "2026-RCDEV-TEST-20261021-RECEIVER-AUDIO-4097"'),
        ('PLUGIN_UPDATE_BUILD = 2026102001', 'PLUGIN_UPDATE_BUILD = 2026102102'),
        ('PLUGIN_BUILD_DATE = "20.10.2026"', 'PLUGIN_BUILD_DATE = "21.10.2026"'),
    ]:
        if source.count(old) != 1:
            raise RuntimeError('Baseline identity mismatch: ' + old)
        source = source.replace(old, new, 1)
    source += '\n\n' + (HERE / 'restart_4097.py').read_text(encoding='utf-8')
    source += '\n\n' + (HERE / 'audio_4097.py').read_text(encoding='utf-8')
    ast.parse(source, feature_version=(3, 8))
    compile(source, 'EmbyFlowE2_2026102102.py', 'exec')
    artifact = HERE / 'EmbyFlowE2_2026102102.py'
    artifact.write_bytes(source.encode('utf-8'))
    print(artifact.name, hashlib.sha256(artifact.read_bytes()).hexdigest())


if __name__ == '__main__':
    build()

"""Reproduce the receiver-confirmed SRT size on the public download release."""
from pathlib import Path
import hashlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026-RCDEV-TEST-20261018-SRT58'
BUILD = 2026101803
ARTIFACT = 'EmbyFlowE2_2026101803.py'
SRT_CHANGE = 'Groessere SRT-Untertitel standardmaessig: Schriftgroesse 58 bei Full HD, automatisch 39 bei HD, mit schwarzer Kontur und mehr Platz fuer mehrere Zeilen. Darstellung am Receiver bestaetigt; kein Zusatzbefehl erforderlich.'
BASE_MANIFEST = ROOT / 'tests/20261017_movie_download/update_2026101802.json'
CHANGELOG = [SRT_CHANGE] + json.loads(BASE_MANIFEST.read_text())['changelog']


def build_source():
    source = (ROOT / 'EmbyFlowE2_2026101802.py').read_text()
    baseline = json.loads(BASE_MANIFEST.read_text())
    if hashlib.sha256(source.encode()).hexdigest() != baseline['sha256']:
        raise RuntimeError('Download baseline checksum mismatch')
    spec = importlib.util.spec_from_file_location('srt_readable_installer', ROOT / 'install-srt-readable.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    source = helper.patched(source)
    replacements = {
        'PLUGIN_VERSION = ' + json.dumps(baseline['version']): 'PLUGIN_VERSION = ' + json.dumps(VERSION),
        'PLUGIN_UPDATE_BUILD = 2026101802': 'PLUGIN_UPDATE_BUILD = ' + str(BUILD),
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise RuntimeError('Unexpected baseline identity: ' + old)
        source = source.replace(old, new, 1)
    lines = source.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line.startswith('PLUGIN_UPDATE_CHANGELOG = ')]
    if len(indices) != 1:
        raise RuntimeError('Unexpected changelog assignment')
    lines[indices[0]] = 'PLUGIN_UPDATE_CHANGELOG = ' + repr('|'.join(CHANGELOG)) + '\n'
    source = ''.join(lines)
    compile(source, ARTIFACT, 'exec')
    return source


def main():
    source = build_source()
    (ROOT / ARTIFACT).write_text(source)
    manifest = dict(version=VERSION, build=BUILD, channel='rcdev', target='plugin.py',
                    artifact_type='plugin_py',
                    download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/' + ARTIFACT,
                    sha256=hashlib.sha256(source.encode()).hexdigest(), changelog=CHANGELOG)
    (ROOT / 'update.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(ARTIFACT, manifest['sha256'])


if __name__ == '__main__':
    main()

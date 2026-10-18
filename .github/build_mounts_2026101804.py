"""Numbered HDD/USB mount recognition on the confirmed SRT58 release."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026-RCDEV-TEST-20261018-MOUNTS'
BUILD = 2026101804
ARTIFACT = 'EmbyFlowE2_2026101804.py'
BASE_MANIFEST = ROOT / 'tests/20261018_srt_readable/update_2026101803.json'
CHANGELOG = ['Downloadziele und lokale Downloads erkennen jetzt auch nummerierte Laufwerke wie /media/hdd2 und /media/usb2. Laufwerke erscheinen mit ihrem Einhaengenamen und ihrer Speicherkapazitaet. Nicht eingehaengte Verzeichnisse, interner Flash und doppelte Datentraeger werden ausgelassen.'] + json.loads(BASE_MANIFEST.read_text())['changelog']


def build_source():
    source = (ROOT / 'EmbyFlowE2_2026101803.py').read_text()
    baseline = json.loads(BASE_MANIFEST.read_text())
    if hashlib.sha256(source.encode()).hexdigest() != baseline['sha256']:
        raise RuntimeError('Baseline checksum mismatch')
    for old, new in {
        'PLUGIN_VERSION = ' + json.dumps(baseline['version']): 'PLUGIN_VERSION = ' + json.dumps(VERSION),
        'PLUGIN_UPDATE_BUILD = 2026101803': 'PLUGIN_UPDATE_BUILD = 2026101804',
        'Keine beschreibbare, eingehaengte HDD/USB unter /media/hdd oder /media/usb.': 'Kein beschreibbarer, eingehaengter HDD-/USB-Speicher gefunden.',
        'Keine fertigen Downloads gefunden.\\nSpeicherorte: /media/hdd/movie/EmbyFlow und /media/usb/movie/EmbyFlow': 'Keine fertigen Downloads gefunden.\\nSpeicherorte: movie/EmbyFlow auf eingehaengten HDD-/USB-Laufwerken.',
    }.items():
        if source.count(old) != 1:
            raise RuntimeError('Unexpected baseline: ' + old)
        source = source.replace(old, new, 1)
    lines = source.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line.startswith('PLUGIN_UPDATE_CHANGELOG = ')]
    if len(indices) != 1:
        raise RuntimeError('Unexpected changelog')
    lines[indices[0]] = 'PLUGIN_UPDATE_CHANGELOG = ' + repr('|'.join(CHANGELOG)) + '\n'
    source = ''.join(lines) + '\n\n' + (ROOT / 'tests/20261018_download_mounts/runtime.py').read_text()
    compile(source, ARTIFACT, 'exec')
    return source


if __name__ == '__main__':
    source = build_source()
    (ROOT / ARTIFACT).write_text(source)
    manifest = dict(version=VERSION, build=BUILD, channel='rcdev', target='plugin.py', artifact_type='plugin_py',
                    download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/' + ARTIFACT,
                    sha256=hashlib.sha256(source.encode()).hexdigest(), changelog=CHANGELOG)
    (ROOT / 'update.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(ARTIFACT, manifest['sha256'])

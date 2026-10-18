"""Release the receiver-confirmed AV1 playback fallback for downloads."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026-RCDEV-TEST-20261018-AV1-DOWNLOAD-PLAY'
BUILD = 2026101805
ARTIFACT = 'EmbyFlowE2_2026101805.py'
BASE_MANIFEST = ROOT / 'tests/20261018_download_mounts/update_2026101804.json'
CHANGELOG = ['AV1 aus Downloads: kompatible Online-Wiedergabe ueber den urspruenglichen Emby-Server. Bild und Ton bei Die Wuestenratten am Receiver bestaetigt. Titel-ID, Titelname und Typ werden vor dem Start geprueft; keine unscharfe Titelsuche.',
             'AV1-Fallback braucht Serververbindung und passende Wiedergaberechte. Die HDD-Datei bleibt unveraendert. Andere lokale Formate behalten den bisherigen Offline-Wiedergabeweg; keine zusaetzliche Downloadzaehlung.'] + json.loads(BASE_MANIFEST.read_text())['changelog']


def build_source():
    source = (ROOT / 'EmbyFlowE2_2026101804.py').read_text()
    baseline = json.loads(BASE_MANIFEST.read_text())
    if hashlib.sha256(source.encode()).hexdigest() != baseline['sha256']:
        raise RuntimeError('Baseline checksum mismatch')
    for old, new in {
        'PLUGIN_VERSION = ' + json.dumps(baseline['version']): 'PLUGIN_VERSION = ' + json.dumps(VERSION),
        'PLUGIN_UPDATE_BUILD = 2026101804': 'PLUGIN_UPDATE_BUILD = 2026101805',
    }.items():
        if source.count(old) != 1:
            raise RuntimeError('Unexpected baseline identity')
        source = source.replace(old, new, 1)
    lines = source.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line.startswith('PLUGIN_UPDATE_CHANGELOG = ')]
    if len(indices) != 1:
        raise RuntimeError('Unexpected changelog assignment')
    lines[indices[0]] = 'PLUGIN_UPDATE_CHANGELOG = ' + repr('|'.join(CHANGELOG)) + '\n'
    source = ''.join(lines) + '\n\n' + (ROOT / 'tests/20261018_download_av1/runtime.py').read_text()
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

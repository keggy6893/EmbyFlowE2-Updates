"""Build the receiver-tested PGS code on the previous published RCDEV payload."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026-RCDEV-TEST-20261018-PGS-AUTO'
BUILD = 2026101801
ARTIFACT = 'EmbyFlowE2_2026101801.py'
CHANGELOG = [
    'PGS-Test mit Player 4097: Eingebettete PGS-Bilduntertitel werden direkt im sichtbaren EmbyFlow-Playerfenster angezeigt.',
    'Ohne Emby-Vorgabe wird eine deutsche erzwungene PGS-Spur automatisch gewaehlt, wenn keine passende erzwungene Textspur vorhanden ist. Eine vorhandene Emby-Spurauswahl hat Vorrang.',
    'Manuelle Auswahl und Untertitel aus bleiben waehrend der Wiedergabe erhalten. Bisherige SRT- und 4K-Abschnittsuntertitel bleiben enthalten.',
    'Bestaetigt auf Vu+ Duo4K SE mit openATV 8.0.1: deutsche volle und erzwungene PGS, Spulen/Fortsetzen im manuellen Test sowie Automatik bei 2012 in 4K.',
    'Bekannt und offen: Bei einem SD-Film fehlt die automatische Auswahl; Spurliste und Forced-Metadaten stehen noch aus. Keine Zusage fuer alle Filme, Boxen, externe SUP-Dateien oder Transcoding.',
    'Das separate Standbildproblem beim wiederholten Tonspurwechsel auf DM One ist damit nicht als behoben bestaetigt. Der lokale Filmdownload-Test ist kein Bestandteil dieses Updates.',
]


def build_source():
    source = (ROOT / 'EmbyFlowE2_2026101704.py').read_text()
    replacements = {
        'PLUGIN_VERSION = "2026-RCDEV-TEST-20261017-4K-UT-SEGMENTS"': 'PLUGIN_VERSION = ' + json.dumps(VERSION),
        'PLUGIN_UPDATE_BUILD = 2026101704': 'PLUGIN_UPDATE_BUILD = ' + str(BUILD),
        'PLUGIN_BUILD_DATE = "17.10.2026"': 'PLUGIN_BUILD_DATE = "18.10.2026"',
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise RuntimeError('Unexpected release baseline: ' + old)
        source = source.replace(old, new, 1)
    lines = source.splitlines(keepends=True)
    found = [i for i, line in enumerate(lines) if line.startswith('PLUGIN_UPDATE_CHANGELOG = ')]
    if len(found) != 1:
        raise RuntimeError('Unexpected changelog assignment')
    lines[found[0]] = 'PLUGIN_UPDATE_CHANGELOG = ' + repr('|'.join(CHANGELOG)) + '\n'
    source = ''.join(lines)
    directory = ROOT / 'tests/20261017_pgs_native'
    source += '\n\n' + (directory / 'patch.py').read_text()
    source += '\n\n' + (directory / 'auto.py').read_text()
    compile(source, 'plugin.py', 'exec')
    return source


def main():
    source = build_source()
    (ROOT / ARTIFACT).write_text(source)
    digest = hashlib.sha256(source.encode()).hexdigest()
    manifest = dict(version=VERSION, build=BUILD, channel='rcdev', target='plugin.py',
                    artifact_type='plugin_py',
                    download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/' + ARTIFACT,
                    sha256=digest, changelog=CHANGELOG)
    (ROOT / 'update.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(ARTIFACT)
    print('SHA256:', digest)


if __name__ == '__main__':
    main()

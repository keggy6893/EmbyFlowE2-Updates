"""Publish the optional movie/episode downloads on the public PGS baseline."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026-RCDEV-TEST-20261018-DOWNLOADS-LIMIT5'
BUILD = 2026101802
ARTIFACT = 'EmbyFlowE2_2026101802.py'
CHANGELOG = [
    'Optionaler Film-/Folgen-Download: In den erweiterten Einstellungen in Spalte zwei einschalten und mit Gruen speichern; standardmaessig aus.',
    'Sichtbarer Herunterladen-Button bei Filmen und einzelnen Serienfolgen. Vorher werden die Emby-Benutzerfreigabe und die gewaehlte Originaldatei geprueft. Nicht erlaubt oder nicht pruefbar sperrt den Download.',
    'HDD-/USB-Auswahl mit freiem und gesamtem Speicher, Dateigroesse und 512 MiB Reserve. Ein Download gleichzeitig; Abbruch entfernt die Teildatei nach Ende des laufenden Lesevorgangs.',
    'Gemeinsames Tageslimit: maximal fuenf Filme oder einzelne Folgen pro Receiver-Installation. Heute X von 5 und verbleibende Plaetze sind sichtbar; Neustart oder Benutzerwechsel setzt den Zaehler nicht zurueck.',
    'Downloads erscheint unter Updates, wenn die Downloadfunktion aktiviert ist. Fertige lokale Dateien lassen sich dort mit OK ueber EmbyFlow/4097 abspielen; Wiedergabe verbraucht keinen Downloadplatz.',
    'Bisherige PGS-/SRT-/4K-Untertitel bleiben enthalten. Downloadoberflaeche und Speicher-/Limiteranzeige wurden vom Nutzer bestaetigt; die neue lokale Uebersicht braucht weitere Receivertests.',
    'Testgrenzen: kein Download-Fortsetzen, keine Warteschlange und keine externen Untertitel. Das Downloadfenster bleibt waehrend der Uebertragung offen. Separater Sprachtest und experimentelle ATV-7.6-Layoutaenderungen sind nicht enthalten.',
]


def build_source():
    directory = ROOT / 'tests/20261017_movie_download'
    sys.path.insert(0, str(directory))
    try:
        spec = importlib.util.spec_from_file_location('movie_download_builder', directory / 'build.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = module.build_source()
    finally:
        sys.path.pop(0)
    replacements = {
        'PLUGIN_VERSION = "2026-LOCAL-TEST-DOWNLOAD-LIMIT5"': 'PLUGIN_VERSION = ' + json.dumps(VERSION),
        'PLUGIN_UPDATE_BUILD = 2026101801': 'PLUGIN_UPDATE_BUILD = ' + str(BUILD),
        'Film-Download (lokaler Test)': 'Film-/Folgen-Download (Test)',
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise RuntimeError('Unexpected download baseline: ' + old)
        source = source.replace(old, new, 1)
    lines = source.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line.startswith('PLUGIN_UPDATE_CHANGELOG = ')]
    if len(indices) != 1:
        raise RuntimeError('Unexpected changelog assignment')
    lines[indices[0]] = 'PLUGIN_UPDATE_CHANGELOG = ' + repr('|'.join(CHANGELOG)) + '\n'
    result = ''.join(lines)
    compile(result, 'plugin.py', 'exec')
    return result


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

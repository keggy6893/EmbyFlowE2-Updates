"""Refresh the displayed language from the active native audio track."""
import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = '6d6b2508197aa6a9b961752a95077bd4d7b2a11f218606bff5efca7607e72cd8'
BUILD = 2026102502
VERSION = '2026-RCDEV-TEST-20261025-AUDIO-LABEL'
CHANGES = ['Sprachanzeige in der Infobar: Die Sprache der tatsaechlich aktiven nativen Tonspur hat Vorrang vor Start- und Standardmetadaten, auch auf Octagon SF8008 Supreme und anderen Receivern.', 'Die Infobar wird beim Oeffnen und bei sichtbarer laufender Aktualisierung aufgefrischt. Dadurch wird auch ein erst nach dem Menueschliessen bestaetigter Tonspurwechsel angezeigt. Keine neue Timer-Schleife.', 'Reine Anzeigekorrektur: keine Aenderung an Tonspurwahl, Wiedergabestart, Serveranfragen, Pausenzustand oder Spruengen. Unbekannte native Sprachdaten behalten die bisherige Metadaten-Anzeige; fremde Dienste werden nicht ausgewertet.', 'Lokaler Taste-9-Fix aus Build 2026102501 sowie Modal-Guard-, DreamOne- und Updater-Korrekturen bleiben enthalten.', 'Anskars Standbild beim HTTP/GStreamer-Tonspurwechsel und das noch nicht genauer beschriebene Verhalten nach Taste 9 sind damit nicht als behoben bestaetigt.']


def build():
    raw = (ROOT / 'EmbyFlowE2_2026102501.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise RuntimeError('Public baseline checksum mismatch')
    source = raw.decode('utf-8')
    runtime = (Path(__file__).parent / 'runtime.py').read_text()
    if 'EMBYFLOW_ACTIVE_AUDIO_LANGUAGE_V1_BEGIN' in source:
        raise RuntimeError('Audio display repair already present')
    values = dict(PLUGIN_VERSION=VERSION, PLUGIN_BUILD_DATE='25.10.2026',
                  PLUGIN_UPDATE_BUILD=BUILD, PLUGIN_UPDATE_CHANGELOG='|'.join(CHANGES))
    tree = ast.parse(source)
    lines = source.splitlines(True)
    edits = []
    for key, value in values.items():
        nodes = [n for n in tree.body if isinstance(n, ast.Assign) and
                 any(isinstance(t, ast.Name) and t.id == key for t in n.targets)]
        if len(nodes) != 1:
            raise RuntimeError('Ambiguous release identity: ' + key)
        n = nodes[0]
        edits.append((n.lineno - 1, n.end_lineno, key + ' = ' + repr(value) + '\n'))
    for start, end, text in sorted(edits, reverse=True):
        lines[start:end] = [text]
    result = ''.join(lines).rstrip() + '\n\n' + runtime
    ast.parse(result, feature_version=(3, 8))
    compile(result, 'plugin.py', 'exec')
    target = ROOT / ('EmbyFlowE2_%d.py' % BUILD)
    target.write_bytes(result.encode())
    return target


if __name__ == '__main__':
    print(build())

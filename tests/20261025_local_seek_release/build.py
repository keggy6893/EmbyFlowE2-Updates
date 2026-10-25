"""Add the confirmed local seek repair to the immutable public release."""
import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = 'cb4dfb686d8a9345fc724581bd12f01d8d6e78c5e8d94db61bc2671065b59b12'
BUILD = 2026102501
VERSION = '2026-RCDEV-TEST-20261025-LOCAL-SEEK'
CHANGES = [
    'Lokale USB-/HDD-/NAS-Dateien: Taste 9, Kapitelspruenge und die beiden Restart-Einstiege verwenden den aktiven nativen Dateidienst. Kein Emby-HTTP-Neustart und kein Backendwechsel fuer lokale Spruenge.',
    'Spruenge pruefen die aktive eigene Datei, beachten die native Laufzeit und lassen Pause sowie Tonspur unveraendert. Bei abgelehntem Sprung erfolgt kein Neustart vom Filmanfang.',
    'Der lokale Skyfall-TS-Vergleich wurde auf der Vu+ mit Tonspurwechsel und Taste 9 vom Nutzer bestaetigt. EMC wird als Referenz fuer den nativen Dateidienst verwendet; EMC muss nicht installiert sein.',
    'Modal-Guard-Absturzkorrektur, bisheriger DreamOne-Tonspur-Teststand und Updater ohne py_compile-Abhaengigkeit aus Build 2026102402 bleiben enthalten.',
    'Grenze: Anskars Standbild beim Tonspurwechsel ueber HTTP/GStreamer ist weiterhin offen. Dieser Build ist keine bestaetigte Loesung dieses Decoderproblems. Server-Streams behalten den bisherigen Sprungpfad.',
]


def build():
    raw = (ROOT / 'EmbyFlowE2_2026102402.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise RuntimeError('Public baseline checksum mismatch')
    source = raw.decode('utf-8')
    runtime = (Path(__file__).parent / 'runtime.py').read_text()
    if 'EMBYFLOW_LOCAL_SEEK_V1_BEGIN' in source:
        raise RuntimeError('Local seek repair already present')
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

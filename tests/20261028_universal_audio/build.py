"""Build the direct-audio update from the unchanged published baseline."""
import ast
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE_SHA = 'a5144f7359dc6863c280d0db11183c002b6d39b5d8e1039c16dcb46dc2de2f56'
BUILD = 2026102801
VERSION = '2026-RCDEV-TEST-20261028-DIRECT-AUDIO'
CHANGES = ['Direkte Wiedergabe: erkannte deutsche Decoder-Tonspuren werden receiverunabhaengig bevorzugt; manuelle Tonwahl bleibt vorrangig.', 'GRUEN oeffnet bei direkter Wiedergabe die nativen Tonspuren. Sprach- und Codec-Zuordnung erfolgen anhand der aktiven Filmversion.', 'Serverseitige Tonwechsel und Transcoding behalten den vorhandenen Weg; bei laufendem Tonwechsel erscheint eine Meldung statt eines stummen Abbruchs.', 'Bestaetigt vom Nutzer: 2012 in 1080p startet auf Vu+ Duo 4K SE mit OpenATV auf Deutsch DTS 5.1; GRUEN zeigt Deutsch und Englisch korrekt.', 'Lokale Tests bestanden. Weitere Receiver und Anskars bisheriger HTTP-Standbildfall sind mit diesem Test nicht als behoben bestaetigt.']

def build():
    raw = (ROOT / 'EmbyFlowE2_2026102502.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise RuntimeError('Public baseline checksum mismatch')
    source = raw.decode('utf-8')
    values = dict(PLUGIN_VERSION=VERSION, PLUGIN_BUILD_DATE='28.10.2026',
                  PLUGIN_UPDATE_BUILD=BUILD, PLUGIN_UPDATE_CHANGELOG='|'.join(CHANGES))
    lines = source.splitlines(True)
    tree = ast.parse(source)
    edits = []
    for key, value in values.items():
        nodes = [n for n in tree.body if isinstance(n, ast.Assign) and
                 any(isinstance(t, ast.Name) and t.id == key for t in n.targets)]
        if len(nodes) != 1:
            raise RuntimeError('Ambiguous release identity: ' + key)
        node = nodes[0]
        edits.append((node.lineno-1, node.end_lineno, key+' = '+repr(value)+'\n'))
    for start, end, text in sorted(edits, reverse=True):
        lines[start:end] = [text]
    runtime = (HERE / 'runtime.py').read_text()
    result = ''.join(lines).rstrip()+'\n\n'+runtime
    ast.parse(result, feature_version=(3, 8))
    compile(result, 'plugin.py', 'exec')
    target = ROOT / ('EmbyFlowE2_%d.py' % BUILD)
    target.write_bytes(result.encode('utf-8'))
    return target

if __name__ == '__main__':
    print(build())

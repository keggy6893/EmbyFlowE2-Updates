"""Publish the isolated genre adjustment on the latest public audio/LCD baseline."""
import ast,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
COMMIT='c761aeb5c4f6258fb85d9977a679d1f270e8fd06'
BASE='EmbyFlowE2_2026102104.py'
BASE_SHA='fe79ab4fdc7e60809224bdc5a5d7d9b2ae8c7b9ff75026a8e105151375d76b5c'
ARTIFACT='EmbyFlowE2_2026102105.py'
BUILD=2026102105
VERSION='2026-RCDEV-TEST-20261021-GENRE-SPACING'
CHANGELOG=[
 'Detailansicht: Nur die Genrezeile (Action, Komoedie usw.) sitzt hoeher und erscheint warmgelb. Inhaltsangabe, Beschreibung, Titel, Info-Badges und Poster behalten ihre bisherigen Positionen.',
 'Keine neuen Serverabfragen und keine Aenderung an Navigation oder Wiedergabe durch die Genre-Korrektur.',
 'Basis ist Teststand 2026102104: HD-Detailansicht, LCD-Zeitfix und aktueller 4097-Tonspur-Sitzungstest bleiben enthalten. Die Hardwarebestaetigung des Tonspurtests und der UT-Test stehen weiter aus.',
 'Gezielt lokal geprueft: Nur Genreposition und Genrefarbe im Detail-Layout geaendert; Gesamtplugin fuer Python 3.8 kompilierbar.'
]
def baseline():
    raw=subprocess.check_output(['git','show',COMMIT+':'+BASE],cwd=ROOT)
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA:raise RuntimeError('Published baseline mismatch')
    return raw.decode()
def build_source():
    source=baseline();tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_efbad_init')
    code=ast.get_source_segment(source,node)
    for old,new in [('sy(442)','sy(400)'),("'foregroundColor':'#CFD5DD'","'foregroundColor':'#F2C94C'")]:
        if code.count(old)!=1:raise RuntimeError('Genre field mismatch')
        code=code.replace(old,new,1)
    lines=source.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=[code+'\n'];source=''.join(lines)
    for old,new in [('PLUGIN_VERSION = "2026-RCDEV-TEST-20261021-AUDIO-SESSION-4097"','PLUGIN_VERSION = '+json.dumps(VERSION)),('PLUGIN_UPDATE_BUILD = 2026102104','PLUGIN_UPDATE_BUILD = '+str(BUILD))]:
        if source.count(old)!=1:raise RuntimeError('Build identity mismatch')
        source=source.replace(old,new,1)
    lines=source.splitlines(keepends=True)
    indexes=[i for i,line in enumerate(lines) if line.startswith('PLUGIN_UPDATE_CHANGELOG = ')]
    if len(indexes)!=1:raise RuntimeError('Changelog mismatch')
    lines[indexes[0]]='PLUGIN_UPDATE_CHANGELOG = '+repr('|'.join(CHANGELOG))+'\n';source=''.join(lines)
    ast.parse(source,feature_version=(3,8));compile(source,ARTIFACT,'exec');return source
if __name__=='__main__':
    source=build_source();(ROOT/ARTIFACT).write_text(source)
    manifest=dict(version=VERSION,build=BUILD,channel='rcdev',target='plugin.py',artifact_type='plugin_py',download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+ARTIFACT,sha256=hashlib.sha256(source.encode()).hexdigest(),changelog=CHANGELOG)
    (Path(__file__).parent/'update.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(ARTIFACT,manifest['sha256'])

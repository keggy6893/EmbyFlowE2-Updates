"""LCD-only test update built from the last published artifact, not private features."""
from pathlib import Path
import ast,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1].parents[0]
HERE=Path(__file__).resolve().parent
BUILD=2026102001
VERSION='2026-RCDEV-TEST-20261020-LCD-CONTENT-TIME'
ARTIFACT='EmbyFlowE2_2026102001.py'
BASE_HASH='dba656338542079ea137296a85b0ca3f07d8c1ee57930548737fb040b12cd4b5'
BASE_FILE='EmbyFlowE2_2026101805.py'
CHANGELOG=[
 'LCD-Testupdate fuer Receiver: interne Frontdisplays und 7-Segment-Anzeigen verwenden EmbyFlows Filmlaenge und korrigierte absolute Abspielposition wie die TV-Infobar.',
 'Kompatible, bereits geladene LCD4linux-Renderer erhalten dieselbe Filmzeit nur waehrend der zugehoerigen EmbyFlow-Wiedergabe. Keine Aenderung von LCD4linux-Dateien oder Einstellungen und keine globale Seek-Manipulation.',
 'Unbekannte LCD4linux-Renderer werden nicht angepasst. Ein begrenztes lokales Zeitprotokoll hilft bei abweichenden Versionen. Keine weiteren Serverabfragen fuer die Displayanzeige.',
 'Lokal geprueft: Zeitumrechnung, Fortsetzen/Streamneustart, Pause, Filmende, Live-TV-/Fremdplayer-Abgrenzung und oeffentlicher LCD4linux-Referenzrenderer. Zgemma H17 TWIN, Gigablue UHD Quad Pro und Mutant HD51 sind noch auf den Receivern zu bestaetigen.',
 'Basis ist der veroeffentlichte Stand 2026101805. Dieses Update ergaenzt ausschliesslich den Display-Zeitfix.'
]

def build_source():
    data=(ROOT/BASE_FILE).read_bytes()
    if hashlib.sha256(data).hexdigest()!=BASE_HASH:raise RuntimeError('Published baseline mismatch')
    source=data.decode()
    old_version='2026-RCDEV-TEST-20261018-AV1-DOWNLOAD-PLAY'
    for old,new in [('PLUGIN_VERSION = '+json.dumps(old_version),'PLUGIN_VERSION = '+json.dumps(VERSION)),('PLUGIN_UPDATE_BUILD = 2026101805','PLUGIN_UPDATE_BUILD = '+str(BUILD)),('PLUGIN_BUILD_DATE = "18.10.2026"','PLUGIN_BUILD_DATE = "20.10.2026"')]:
        if source.count(old)!=1:raise RuntimeError('Baseline identity mismatch')
        source=source.replace(old,new,1)
    lines=source.splitlines(True)
    positions=[i for i,line in enumerate(lines) if line.startswith('PLUGIN_UPDATE_CHANGELOG = ')]
    if len(positions)!=1:raise RuntimeError('Changelog assignment mismatch')
    lines[positions[0]]='PLUGIN_UPDATE_CHANGELOG = '+repr('|'.join(CHANGELOG))+'\n'
    source=''.join(lines)+'\n\n'+(HERE/'runtime.py').read_text()
    ast.parse(source,feature_version=(3,8));compile(source,ARTIFACT,'exec')
    return source

if __name__=='__main__':
    source=build_source();(ROOT/ARTIFACT).write_text(source)
    manifest=dict(version=VERSION,build=BUILD,channel='rcdev',target='plugin.py',artifact_type='plugin_py',download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+ARTIFACT,sha256=hashlib.sha256(source.encode()).hexdigest(),changelog=CHANGELOG)
    (HERE/'update.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(ARTIFACT,manifest['sha256'])

"""Build a narrowly scoped public DreamOne receiver trial on build 2301."""
import ast,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'EmbyFlowE2_2026102301.py'
EXPECTED='7cf7dcee1b14d5ad65504698e0cfdb29579ebe716f6fd9eeeb9f673665348ae8'
VERSION='2026-RCDEV-TEST-20261024-DREAMONE-NATIVE-AUDIO'
BUILD=2026102401
CHANGES=[
 'DreamOne (dreamone/dmone), Enigma2/4097: Tonspuren der laufenden Datei direkt im Player wechseln. Der Tonspurwechsel startet keine neue HLS-/Remux-Sitzung und setzt die Filmposition nicht zurueck.',
 'DreamOne: Deutsch wird nach Bereitstellung der nativen Tonspuren anhand der tatsaechlich erkannten Sprache gewaehlt. Manuelle Sprachwahl bleibt bis zum Filmende erhalten. Eine nicht verfuegbare deutsche Player-Spur wird nicht als ausgewaehlt ausgegeben.',
 'DreamOne: Haken und Infobar werden nach bestaetigtem nativen Spurwechsel aktualisiert; die aktive Filmversion bleibt massgeblich. Originalton wird durch diesen Wechsel nicht in AAC-Stereo umgewandelt.',
 'Gezielter Receiver-Test fuer Anskar. MKV/TS, Bild-/Tonstabilitaet und Langzeitwiedergabe muessen auf der DreamOne bestaetigt werden. Lokale Tests sind kein Nachweis, dass das gemeldete Stocken behoben ist.',
 'Andere Receiver behalten ihren bisherigen Tonspurpfad. Updater-Syntaxpruefung ohne py_compile, LCD-Zeitfix, Genre-Abstand und HD-Layout aus 2026102301 bleiben erhalten. Keine privaten Such-/Wunschbox-/Download-Testaenderungen enthalten.'
]
def build():
 raw=BASE.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('Wrong immutable 2301 baseline')
 source=raw.decode('utf-8');tree=ast.parse(source);lines=source.splitlines(True)
 replacements={'PLUGIN_VERSION':VERSION,'PLUGIN_BUILD_DATE':'24.10.2026','PLUGIN_UPDATE_BUILD':BUILD,'PLUGIN_UPDATE_CHANGELOG':'|'.join(CHANGES)}
 changes=[]
 for key,value in replacements.items():
  nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets)]
  if len(nodes)!=1:raise RuntimeError('Ambiguous release identity: '+key)
  n=nodes[0];changes.append((n.lineno-1,n.end_lineno,key+' = '+repr(value)+'\n'))
 for a,b,text in sorted(changes,reverse=True):lines[a:b]=[text]
 runtime=(Path(__file__).parent/'runtime.py').read_text()
 result=''.join(lines).rstrip()+'\n\n'+runtime
 ast.parse(result,feature_version=(3,8));compile(result,'plugin.py','exec')
 target=ROOT/'EmbyFlowE2_2026102401.py';target.write_bytes(result.encode('utf-8'));return target
if __name__=='__main__':print(build())

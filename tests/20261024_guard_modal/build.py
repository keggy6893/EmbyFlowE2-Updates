"""Change only the proven modal-notification crash and release identity."""
import ast,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXPECTED='920f7d93442cf64bd3bb838d2dc0b8f4b8ffbcc70dcec909d1b7eafb91fc62a2'
VERSION='2026-RCDEV-TEST-20261024-MODAL-GUARD'
BUILD=2026102402
CHANGES=[
 'Absturzkorrektur fuer das Crashlog vom 24.10.2026: Der Hinweis-Timer _efguard_gui_tick oeffnet kein modales Fenster mehr, waehrend die Enigma2-Sitzung keinen ausfuehrenden Dialog hat.',
 'Waehrend eines Bildschirm-/Playerwechsels bleibt der Hinweis vorgemerkt. Eine Ausnahme beim Oeffnen darf Enigma2 nicht beenden; ein neuerer Hinweis wird beim erneuten Vormerken nicht ueberschrieben.',
 'Gezielte Korrektur des Pluginfehlers "Modal open are allowed only from a screen which is modal". FF_ERROR ist damit nicht als exteplayer3-Absturz eingeordnet. Keine Aenderung an Player-Auswahl, Suchfunktionen, Tonspurwechsel, Stream-URLs oder Server-Abbruchregeln.',
 'DreamOne-Teststand 2026102401 bleibt enthalten. Stocken und Sprachwechsel sind damit weiterhin nicht als auf Hardware behoben bestaetigt. Kein weiterer Hardwaretest von Anskar fuer die Analyse dieses belegten Dialogfehlers angefordert.',
 'Lokale Regression: Originalabsturz reproduziert, Dialog-Uebergaenge und parallele Hinweise geprueft; sonstiger Plugin-Code bleibt erhalten.'
]
def build():
 raw=(ROOT/'EmbyFlowE2_2026102401.py').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('Wrong immutable 2401 baseline')
 source=raw.decode('utf-8');tree=ast.parse(source);lines=source.splitlines(True)
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_efguard_gui_tick']
 if len(nodes)!=1:raise RuntimeError('Guard tick is ambiguous')
 n=nodes[0];changes=[(n.lineno-1,n.end_lineno,(Path(__file__).parent/'runtime.py').read_text())]
 values={'PLUGIN_VERSION':VERSION,'PLUGIN_BUILD_DATE':'24.10.2026','PLUGIN_UPDATE_BUILD':BUILD,'PLUGIN_UPDATE_CHANGELOG':'|'.join(CHANGES)}
 for key,value in values.items():
  matches=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets)]
  if len(matches)!=1:raise RuntimeError('Release identity ambiguous: '+key)
  n=matches[0];changes.append((n.lineno-1,n.end_lineno,key+' = '+repr(value)+'\n'))
 for a,b,text in sorted(changes,reverse=True):lines[a:b]=[text]
 result=''.join(lines);ast.parse(result,feature_version=(3,8));compile(result,'plugin.py','exec')
 target=ROOT/'EmbyFlowE2_2026102402.py';target.write_bytes(result.encode('utf-8'));return target
if __name__=='__main__':print(build())

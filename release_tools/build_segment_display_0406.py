from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
base=root/'EmbyFlowE2_Menu_20261004_0405.py'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='45ed397f77f4349ac5ae16f9d4e8e5253244c97226b67d2ab92706158f3038d1'
s=base.read_text().replace('PLUGIN_UPDATE_BUILD = 2026100405','PLUGIN_UPDATE_BUILD = 2026100406').replace('2026-RCDEV-MENU-20261004','2026-RCDEV-SEGMENTDISPLAY-20261004')
s+='\n'+(root/'release_tools/segment_display_0406.inc.py').read_text()
compile(s,'plugin.py','exec')
target=root/'EmbyFlowE2_Segmentdisplay_20261004_0406.py';target.write_text(s)
m=json.loads((root/'update.json').read_text())
m.update(version='2026-RCDEV-SEGMENTDISPLAY-20261004',build=2026100406,download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
m['changelog']=['Optionales Boxdisplay: eigene einzeilige Restzeitanzeige HHMM fuer von openATV erkannte 7-Segment-Displays','Kein direkter Geraetezugriff; normale Enigma2-Summary und Timer-Aufraeumung','Grafikdisplays behalten ihre bisherige Anzeige; unbekannte Laufzeit zeigt ----','Alle Aenderungen aus 0405 enthalten; automatische Tests bestanden, SF8008-Hardwaretest steht aus']
(root/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print(m['sha256'])

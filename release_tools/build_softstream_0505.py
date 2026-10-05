from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
s=(root/'EmbyFlowE2_PlayerGuard_20261005_0504.py').read_text()
s=s[:s.index('# EMBYFLOW_PLAYER_GUARD_0504_START')]+(root/'release_tools/softstream_0505.inc.py').read_text()
s=s.replace('2026-RCDEV-PLAYERGUARD-20261005','2026-RCDEV-SOFTSTREAM-20261005',1)
compile(s,'plugin.py','exec')
p=root/'EmbyFlowE2_Softstream_20261005_0505.py';p.write_text(s)
m=json.loads((root/'update.json').read_text())
m.update(version='2026-RCDEV-SOFTSTREAM-20261005',build=2026100505,
 download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+p.name,
 sha256=hashlib.sha256(p.read_bytes()).hexdigest(),changelog=[
 'Securitycheck by Paul',
 'Native Streamfehler pausieren nur weitere Streamstarts; Browsen und Poster bleiben verfuegbar',
 'Erster Streamfehler ohne Pause, zweiter innerhalb 120 Sekunden mit 60 Sekunden Pause, dritter mit 300 Sekunden Pause',
 'HTTP 403/429 pausiert weiterhin alle Anfragen an den Host; 404-Login-Fix und Neuheiten enthalten',
 'Lokal getestet; native HTTP-Statuscodes und interne Reconnects weiterhin nicht vollstaendig kontrollierbar'])
(root/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print('Build',m['build'],m['sha256'])

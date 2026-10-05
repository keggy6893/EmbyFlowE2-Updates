from pathlib import Path
import ast,json,hashlib
root=Path(__file__).resolve().parents[1]
s=(root/'EmbyFlowE2_ServerGuard_20261005_0503.py').read_text()
s=s.replace('2026-RCDEV-SERVERGUARD404-20261005','2026-RCDEV-PLAYERGUARD-20261005',1)
# Generic native errors have no HTTP status; never label them as HTTP 403.
anchor="def _efguard_message(status, remaining):\n"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''    if status == 'Streamfehler':
        return ('Server-Anfragen nach Streamfehler pausiert. Noch %d Sekunden. '
                'HTTP-Status nicht verfuegbar. Securitycheck by Paul' %
                max(1, int(_efguard_math.ceil(remaining))))
''',1)
source=s.encode('utf-8');lines=source.splitlines(keepends=True);offsets=[0]
for line in lines:offsets.append(offsets[-1]+len(line))
changes=[]
for node in ast.walk(ast.parse(s)):
 if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='playService':
  start=offsets[node.lineno-1]+node.col_offset
  end=offsets[node.end_lineno-1]+node.end_col_offset
  f_end=offsets[node.func.end_lineno-1]+node.func.end_col_offset
  rest=source[f_end:end].lstrip()
  assert rest.startswith(b'(')
  nav=ast.get_source_segment(s,node.func.value)
  replacement=('_efguard_play_service('+nav+', ').encode()+rest[1:]
  changes.append((start,end,replacement))
for start,end,replacement in sorted(changes,reverse=True):source=source[:start]+replacement+source[end:]
s=source.decode()+'\n'+(root/'release_tools/player_guard_0504.inc.py').read_text()
compile(s,'plugin.py','exec')
p=root/'EmbyFlowE2_PlayerGuard_20261005_0504.py';p.write_text(s)
m=json.loads((root/'update.json').read_text())
m.update(version='2026-RCDEV-PLAYERGUARD-20261005',build=2026100504,
 download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+p.name,
 sha256=hashlib.sha256(p.read_bytes()).hexdigest(),changelog=[
 'Securitycheck by Paul',
 'Alle vom Plugin ausgeloesten Streamstarts/-neustarts beachten die Host-Pause',
 'Laufenden Stream bei erkannter Host-Sperre stoppen; native Startfehler und vorzeitiges EOF mit bekannter Laufzeit loesen 5 Minuten Pause aus',
 'Native HTTP-Statuscodes/interne Reconnects nicht vollstaendig sichtbar oder kontrollierbar; keine zusaetzlichen Testanfragen an den Server',
 '404-Login-Fix, Neuheiten und Anbieterlinks enthalten; lokale Tests, kein Zugriff auf Bennies Server'])
(root/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print('Prepared',m['build'],'guarded playService call sites:',len(changes))

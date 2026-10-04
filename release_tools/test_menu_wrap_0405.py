from pathlib import Path
import ast,re,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
s=(root/'EmbyFlowE2_Menu_20261004_0405.py').read_text()
compile(s,'plugin.py','exec')
tree=ast.parse(s)
tags=re.findall(r'<widget name="(?:side_sub_\d+|nav_focus_marker)"[^>]*?/>',s)
assert len(tags)==19 and all(ET.fromstring(t).get('noWrap')=='1' for t in tags)
node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_sidebar_display_label_v24')
ns={};exec(ast.get_source_segment(s,node),ns);f=ns[node.name]
assert f(None,'Science Fiction & Fantasy',20)=='Sci-Fi & Fantasy'
assert f(None,'Serien',20)=='Serien'
assert f(None,'A'*40,20)=='A'*19+'…'
print('PASS: 18 single-line menu rows, focus label, short and long category labels and syntax')

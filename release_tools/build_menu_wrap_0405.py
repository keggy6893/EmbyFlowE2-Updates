from pathlib import Path
import re,json,hashlib
root=Path(__file__).resolve().parents[1]
base=root/'EmbyFlowE2_LCD_Fanart_20261004_0404.py'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='f80f6c2c2cd0deb322847f744daf255d44c8b079791e42677fddf194379d3f39'
s=base.read_text()
pattern=r'<widget name="(?:side_sub_\d+|nav_focus_marker)"[^>]*?/>'
def nowrap(m):
    tag=m.group()
    assert 'noWrap=' not in tag
    return tag.replace(' />',' noWrap="1" />')
s,count=re.subn(pattern,nowrap,s)
assert count==19,count
old='        value = str(text or "").strip()\n        if len(value) <= max_chars:'
new='        value = str(text or "").strip()\n        if value.casefold() == "science fiction & fantasy":\n            value = "Sci-Fi & Fantasy"\n        if len(value) <= max_chars:'
assert s.count(old)==1
s=s.replace(old,new).replace('PLUGIN_UPDATE_BUILD = 2026100404','PLUGIN_UPDATE_BUILD = 2026100405').replace('2026-RCDEV-LCD-FANART-20261004','2026-RCDEV-MENU-20261004')
compile(s,'plugin.py','exec')
target=root/'EmbyFlowE2_Menu_20261004_0405.py';target.write_text(s)
m=json.loads((root/'update.json').read_text())
m.update(version='2026-RCDEV-MENU-20261004',build=2026100405,download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
m['changelog']=['Menue: einzeilige Kategorien verhindern abgeschnittene Zeichen einer zweiten Zeile','Science Fiction & Fantasy wird im Menue als Sci-Fi & Fantasy angezeigt; Bibliotheksname und ID bleiben erhalten','LCD-Fanart und Resolver-Fixes aus 0404 enthalten']
(root/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print(m['sha256'])

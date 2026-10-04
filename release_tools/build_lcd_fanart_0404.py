from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
base=root/'EmbyFlowE2_Resolver_Dreambox_20261004_0403.py'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='af3851c39eb9a256dc2da4682a2697735a66b40260c940e3812efb93ef4880e8'
s=base.read_text()
old="        state = {'cancel': _efimg3_threading.Event(), 'item_id': item_id}"
new="        state = {'cancel': _efimg3_threading.Event(), 'item_id': item_id,\n                 'auth': tuple(get_emby_auth() or ()),\n                 'image_ids': tuple(dict.fromkeys((item_id, source_id)))}"
assert s.count(old)==1
s=s.replace(old,new).replace('PLUGIN_UPDATE_BUILD = 2026100403','PLUGIN_UPDATE_BUILD = 2026100404').replace('2026-RCDEV-RESOLVER-20261004','2026-RCDEV-LCD-FANART-20261004')
s+='\n'+(root/'release_tools/lcd_fanart_0404.inc.py').read_text()
compile(s,'plugin.py','exec')
target=root/'EmbyFlowE2_LCD_Fanart_20261004_0404.py'
target.write_text(s)
m=json.loads((root/'update.json').read_text())
m.update(version='2026-RCDEV-LCD-FANART-20261004',build=2026100404,download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
m['changelog']=['LCD: ungedunkeltes Emby-Backdrop statt dunklem TV-Cachebild','Exportnamen Poster.jpg und Backdrop.jpg unveraendert','Bilder nur waehrend Wiedergabe; spaete Antworten nach Filmende verworfen','0403 Resolver-Fixes enthalten; automatisiert getestet, Box-Test steht aus']
(root/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print(m['sha256'])

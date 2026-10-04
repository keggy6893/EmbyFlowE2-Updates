from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parents[1]
base=root/'EmbyFlowE2_GroessereSchrift_20261003_0304.py'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='37c9b9e2d16aff75aff93b947d8d2068df66a5fe17c89352704ba32f435cee4a'
s=base.read_text(encoding='utf-8')
changes=[('                focus_y = y + h + 15','                focus_y = y + h + 4'),
('PLUGIN_VERSION = "2026-RCDEV-LESBARKEIT-20261003"','PLUGIN_VERSION = "2026-RCDEV-BILDER-20261004"'),
('PLUGIN_UPDATE_BUILD = 2026100304','PLUGIN_UPDATE_BUILD = 2026100401'),
('            with open(path + ".tmp", "wb") as handle:\n                handle.write(content)\n            os.rename(path + ".tmp", path)', '            if not _efclean_write(self, path, content):\n                return'),
('                    with open(path + ".tmp", "wb") as handle:\n                        handle.write(content)\n                    os.rename(path + ".tmp", path)', '                    if not _efclean_write(self, path, content):\n                        return')]
for old,new in changes:
    assert s.count(old)==1,old
    s=s.replace(old,new,1)
images=(root/'release_tools/current_images_0401.inc.py').read_text()
old="        state = {'cancel': _efimg3_threading.Event()}"
assert images.count(old)==1
images=images.replace(old,"        state = {'cancel': _efimg3_threading.Event(), 'item_id': item_id}",1)
s+='\n'+images+'\n'+(root/'release_tools/detail_cleanup_0401.inc.py').read_text()
compile(s,'plugin.py','exec')
target=root/'EmbyFlowE2_Bilder_Aufraeumen_20261004_0401.py';target.write_text(s,encoding='utf-8')
m=json.loads((root/'update.json').read_text())
m.update(version='2026-RCDEV-BILDER-20261004',build=2026100401,download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
m['changelog']=[
'Waehrend der Wiedergabe: vorhandene JPEG-Bilder unter /tmp/EmbyFlow/Poster.jpg und /tmp/EmbyFlow/Backdrop.jpg; beim Stoppen automatisch entfernt',
'Temporaere Detailposter und Backdrops werden nach Schliessen der Detailseite aufgeraeumt; Bilder des laufenden Films bleiben geschuetzt',
'Keine neuen Bilddownloads fuer den Export; dauerhafter Poster-Cache bleibt erhalten',
'Gelber Auswahlstrich auf der Startseite liegt unter dem Poster statt im Filmtitel',
'Bildwechsel Skyfall/Fallout, Filmstart, Stoppen und Aufraeumen lokal auf VU+ Duo 4K SE mit openATV 8.0 getestet',
'Groessere Schrift, optionales Boxdisplay und Trailer-Funktionen aus Build 2026100304 enthalten']
(root/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print('Built 2026100401:',m['sha256'])

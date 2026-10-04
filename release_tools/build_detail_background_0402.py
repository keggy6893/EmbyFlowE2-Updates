from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
base=root/'EmbyFlowE2_Bilder_Aufraeumen_20261004_0401.py'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='5d4a270712f97acdacd78df9d057d720d89761feeb12caab5efadaf1184c517c'
s=base.read_text()
for old,new in [
('PLUGIN_VERSION = "2026-RCDEV-BILDER-20261004"','PLUGIN_VERSION = "2026-RCDEV-DETAIL-HINTERGRUND-20261004"'),
('PLUGIN_UPDATE_BUILD = 2026100401','PLUGIN_UPDATE_BUILD = 2026100402'),
('        theme_file = _FALLOUT_2018_LOCAL_THEME_FILE','        theme_file = ""  # external detail background replaces local experiment')]:
 assert s.count(old)==1,old
 s=s.replace(old,new,1)
s+='\n'+(root/'release_tools/detail_background_0402.inc.py').read_text()
compile(s,'plugin.py','exec')
target=root/'EmbyFlowE2_Detail_Hintergrund_20261004_0402.py';target.write_text(s)
m=json.loads((root/'update.json').read_text())
m.update(version='2026-RCDEV-DETAIL-HINTERGRUND-20261004',build=2026100402,download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
m['changelog']=[
'Hintergrundmedien nur auf der Detailseite; Posteruebersicht startet keine Musik oder Videos',
'Erweiterte Einstellungen > Blau/Musik: Hoch/Runter waehlt Video mit Musik-Fallback, Musik und Backdrop oder Aus; Gruen speichert',
'Video nutzt die vorhandene Online-Trailersuche ohne eigenen API-Key und unabhaengig von ThemeVideos beim Anbieter',
'Ohne Video: ThemerrDB-Musik anhand vorhandener TMDB-Metadaten, sofern verfuegbar; sonst nur Backdrop',
'Abbruch bei Filmstart und Verlassen; spaete Hintergrund-Ergebnisse starten keine Wiedergabe',
'Bilder-Export, Bereinigung, Posterstrich, Schrift und optionales Boxdisplay aus 0401 bleiben enthalten',
'Automatisierte Pruefung; neue Hintergrundfunktion noch nicht auf Receiver getestet']
(root/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print('Built 2026100402',m['sha256'])

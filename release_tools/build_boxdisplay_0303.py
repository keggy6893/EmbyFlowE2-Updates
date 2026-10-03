from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
source = root / 'EmbyFlowE2_TrailerQuellen_20261003_0302.py'
assert hashlib.sha256(source.read_bytes()).hexdigest() == 'eaaa904a3de7bb4c311a3037b5fde67323ab07748f2ac306181beec74d2f3df7'
s = source.read_text(encoding='utf-8')
anchor = 'config.embyflow.cache_enabled = ConfigYesNo(default=True)'
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + '\nconfig.embyflow.box_display = ConfigYesNo(default=False)', 1)
anchor = '            getConfigListEntry("Poster-Cache", config.embyflow.cache_enabled),'
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + '\n            getConfigListEntry("Boxdisplay: Titel und Wiedergabezeiten", config.embyflow.box_display),', 1)
s += '\n\n' + (root / 'release_tools/boxdisplay_0303.inc.py').read_text(encoding='utf-8')
s += '\n\n' + (root / 'release_tools/boxdisplay_settings_0303.inc.py').read_text(encoding='utf-8')
compile(s, 'plugin.py', 'exec')
target = root / 'EmbyFlowE2_Boxdisplay_20261003_0303.py'
target.write_text(s, encoding='utf-8')
manifest = json.loads((root / 'update.json').read_text())
manifest.update(version='2026-RCDEV-BOXDISPLAY-20261003', build=2026100303,
                download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/' + target.name,
                sha256=hashlib.sha256(target.read_bytes()).hexdigest())
manifest['changelog'] = [
    'Optionales Boxdisplay: Erweiterte Einstellungen > Wiedergabe & Diagnose > Boxdisplay; standardmaessig aus, mit Gruen speichern',
    'Filmtitel weiss, 2 Pixel groesser und mit kraeftiger Schriftkontur',
    'Wiedergabe/Pause, schmaler Fortschrittsbalken, vergangene Zeit/Gesamtlaufzeit und Restzeit',
    'Lokal auf VU+ Duo 4K SE mit openATV 8.0 getestet; Rueckkehr zur TV-Anzeige bestaetigt',
    'Darstellung auf weiteren Boxen noch zu testen; keine LCD4linux-Anbindung enthalten',
    'Trailer-Suche, Ersatzquellen, Vorladen und Fehlercache aus Build 2026100302 bleiben enthalten'
]
(root / 'update.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Built optional boxdisplay 2026100303:', manifest['sha256'])

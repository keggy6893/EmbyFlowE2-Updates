# EmbyFlowE2 – openATV-Übergabe

RC26.5 Login Fix Test · Build `2026111411` · Paketversion `2026.11.14.1-r1411`

EmbyFlowE2 verbindet Enigma2 mit Emby. Dieser Stand enthält den gemeinsamen AutoFS/NAS-Resolver, die Filmaktionen „Fortsetzen“ und „Von vorn abspielen“ sowie die Speicherung der Anmeldung pro Server-Slot.

## Quellstand und Paket

- `src/EmbyFlowE2/` enthält Plugin, Python-Begleitdateien, Keymap und Ressourcen. Die Ressourcen und einige Begleitdateien stammen aus dem UPDATE-RC1-IPK vom 30.10.2026.
- `CI/build.sh` baut das Test-IPK mit Python 3 und `dpkg-deb`. Auf dem Build-Rechner aus dem Projektordner `sh CI/build.sh` ausführen. Das Ergebnis liegt in `dist/`.
- Das Test-IPK wird aus `src/EmbyFlowE2/` gebaut. Die Plugin-Dateien des bisherigen Test-IPK wurden byteweise mit diesem Quellordner verglichen.
- `emby_config.py` enthält leere Standardwerte und ist im Paket als Konfigurationsdatei deklariert.

Der veröffentlichte Plugin-Quellstand für den bestehenden Test-Updater liegt im [Commit a2b858b](https://github.com/keggy6893/EmbyFlowE2-Updates/tree/a2b858bd6a96fc641eaf1c28ca66c08396f72fc8/tests/20261114_universal_release). Die mitgelieferte `plugin.py` entspricht dessen geprüftem Download (SHA-256: `e0c2a4be1aaee77f8bf3deaaf984f24dde92473994ae266382dbed8b9e1c2d6a`). Der GitHub-Buttonpfad ist für Boxen eingerichtet, die bereits dieses RC26.5-Testmanifest verwenden.

## Teststand

| Geprüft | Ergebnis |
|---|---|
| VU+ Duo 4K SE, openATV 8.0.1, Build 2026111410 | Paketupgrade vom Plugin-Build 2026111402, Start, bisheriger Server online und Tonspurwechsel Deutsch → Englisch. Das Skript hat die alte `emby_config.py` nach dem Paketupgrade zurückkopiert. |
| Build 2026111411 | Manifest und Download über HTTPS abgeglichen, SHA-256 und Python-Syntax geprüft. Der Loginfix ist im bestehenden RC26.5-Testkanal verfügbar. |

## Vor der Feed-Freigabe

- Build 2026111411 über den Update-Button installieren. Server 1 → Server 2 → Server 1 nach GUI-Neustart prüfen und den Tonspurwechsel erneut testen.
- Neuinstallation sowie Upgrade einer älteren RC per Paketmanager auf dem Receiver prüfen. Dabei muss die bestehende Konfiguration ohne manuelles Zurückkopieren erhalten bleiben.
- Die vier älteren Bytecode-Module `compat`, `item_types`, `skin_utils` und `stream_strategy` fehlen im Paket. RC26.5 verwendet dafür eingebaute Ersatzpfade. Deren Laufzeitverhalten bei frischer Installation ist noch zu prüfen. Optionale Integrationen separat prüfen.
- Projektlizenz und Rechte an den Ressourcen klären. Der Stand ist zur technischen Durchsicht vorbereitet.
- „Weiterschauen“ ist offen. Die gespeicherte Position in der Detailansicht und die Anzeige in der Startliste müssen separat geprüft werden.

Für den offiziellen Feed ist der Paketmanager der vorgesehene Updateweg. Das lokal gebaute IPK ist ein Testpaket. Die Quellstruktur orientiert sich an ArdMediathek. Ein offizielles Build-Rezept und eine Aufnahme in den Feed stehen noch aus.

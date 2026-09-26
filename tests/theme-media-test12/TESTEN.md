# EmbyFlowE2 ThemeMedia Test12 – Test für Tester

**Voraussetzung:** Auf der Box läuft exakt WatchParty QR Test11 (`plugin.py` SHA256 `362a4131f5fad14991a670f086c16010fef550e6e6d3bb697a31a63f2944dab9`). Bei einem anderen Stand stoppt das Installationsskript ohne Änderung. Test12 nicht als allgemeines Update ausrollen.

## Installation unter Windows

1. Dieses Tester-ZIP vollständig entpacken. Die enthaltene `EmbyFlowE2_ThemeMedia_Test12.zip` und `Install-Test12.ps1` müssen im selben Ordner liegen.
2. PowerShell in diesem Ordner öffnen und ausführen:

   `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-Test12.ps1`

   Wenn die Box eine andere IP hat, `-Box 192.168.1.11` entsprechend ändern.
3. Das Skript prüft ZIP und Dateien, legt eine dauerhafte Sicherung direkt im Plugin-Ordner an, prüft Python-Syntax und startet die Box neu. Bei abweichendem Plugin-Stand wird nichts überschrieben.

## Test

1. In EmbyFlow ein Film- oder Serienplakat auswählen und mindestens 3 Sekunden dort bleiben. Bei vorhandenem Theme sollte Ton einsetzen.
2. Plakat wechseln oder Ansicht schließen: Theme muss stoppen und der vorherige Ton zurückkehren.
3. Mit mehreren Titeln testen. Ohne auf Emby hinterlegtes Theme greift ThemerrDB nur bei vorhandener TMDB-ID und installiertem `yt-dlp`. Wenn für einen Titel kein Theme existiert, ist Stille erwartbar.
4. Notieren: Titel, Uhrzeit, ob Ton startet/stoppt und ob die Navigation während der Suche flüssig bleibt.

**Grenzen:** Auf realer Box noch nicht getestet. Trailer sind technisch im Manager vorbereitet, aber nicht als Taste in EmbyFlow vorhanden. Watch Party ist im zugrunde liegenden Test11-Plugin enthalten.

**Paket-SHA256:** `cabb7fbf95885e419b8db335400f07603274d4226ae80e8a6f2d2e58441ff399`

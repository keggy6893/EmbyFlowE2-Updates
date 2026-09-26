# EmbyFlowE2 ThemeMedia Test12

Testpaket für Theme-Songs auf Basis von WatchParty QR Test11. Nicht über den automatischen Updater verteilen; Box-Laufzeittest steht aus.

- Emby ThemeSongs zuerst; ThemerrDB nur ohne Server-Theme und mit TMDB-ID sowie `yt-dlp`.
- Die Abfrage läuft im vorhandenen Hintergrund-Worker der Poster-Auswahl.
- Trailer-Zugriff ist im Manager vorbereitet, ohne Schaltfläche im Plugin.
- Die bestehende WatchParty aus Test11 bleibt im Paket.

ZIP SHA256: `cabb7fbf95885e419b8db335400f07603274d4226ae80e8a6f2d2e58441ff399`

Installation nur nach Prüfung des vorhandenen `plugin.py` SHA256 `362a4131f5fad14991a670f086c16010fef550e6e6d3bb697a31a63f2944dab9`. Vor Austausch eine Sicherung erstellen und beide Python-Dateien mit `python3 -m py_compile` prüfen.

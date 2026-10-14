# EmbyFlowE2 - freiwilliger Teststand 20261014_091749

Basis: Checkpoint 20261014_083450, Commit 712e9285.

Enthalten:
- Aktuelle plugin.py, identisch mit dem installierten Stand der Entwickler-VU.
- Sechs UI-Grafiken im plugininternen Ordner assets.
- Lokale USB-Bond-Themes standardmaessig deaktiviert.
- Marineblauer Favoriten-Dialog mit Aufloesungsangaben aus Video-Metadaten.
- Fehlende Aufloesungsangaben werden im Hintergrund vom Emby-Server angefordert.

Installation fuer bestehende EmbyFlowE2-Installationen:
1. Bisherigen Plugin-Ordner sichern.
2. EmbyFlowE2/plugin.py und die sechs Dateien aus EmbyFlowE2/assets
   in /usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/ uebertragen.
   Die Unterordnerstruktur assets muss erhalten bleiben.
3. GUI neu starten, sobald keine Aufnahme laeuft.

Dies ist ein Ergaenzungspaket fuer bestehende Installationen,
kein vollstaendiger Erstinstaller und kein automatisches Update.

Zu testen:
- Favoriten: Varianten-Auswahl, Aufloesungen, OK und EXIT.
- Film-, Episoden- und Serienansichten samt Grafiken.
- Theme-Musik, Theme-Video und Fanart vom eigenen Emby-Server.
- Verhalten ohne Theme-Dateien und beim Verlassen der Detailseite.

Pruefstand:
Python-Syntax und Datei-Pruefsummen geprueft.
Dialog-Darstellung, Bedienung und Server-Themes noch nicht
durch einen abgeschlossenen Laufzeittest bestaetigt.

Bekannte Einschraenkungen:
Favoritengruppierung nach Titel/Jahr ist eine Heuristik.
Favorit entfernen entfernt bisher nur den ersten Gruppeneintrag.
Bei mehreren MediaSources eines Eintrags zeigt der neue Dialog
die hoechste in dessen Video-Metadaten gefundene Aufloesung.

Der automatische Update-Kanal und die Buildnummer bleiben unveraendert.
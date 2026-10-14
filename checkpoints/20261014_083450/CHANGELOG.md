# EmbyFlowE2 – Entwicklungsstand vom 14.10.2026, 08:34:50

Dieser Ordner sichert den aus der VU exportierten Stand unverändert. Er ist ein Entwicklungscheckpoint, kein neuer freigegebener Auto-Update-Build.

## Gesammelte Änderungen vom 13.–14. Oktober

- Neue Film-Detailseite: großer Titel, Poster rechts, breite Inhaltsangabe mit Seitenwechsel, abgerundete dunkle Buttons und türkisfarbene Auswahl.
- Informationsplaketten für vorhandene Bewertung, Jahr, Laufzeit, Altersfreigabe, Bildauflösung, Audioformat, Kanäle und Untertitel. Voraussichtliche Endzeit daneben.
- Land, Regie, Filmstudio und Darsteller unter der Beschreibung; Anzeige abhängig von den Serverdaten.
- Mehr Platz für die Inhaltsangabe und angepasste vertikale Positionen.
- Angepasste Hintergrundverläufe; marineblauer Film-/Episoden-Verlauf und separater vertikaler Serien-Verlauf.
- Serienübersicht im Stil der Film-Detailseite, ohne zusätzliche Staffel-Posterreihe. Hauptaktion „Staffel wählen“, daneben Trailer und Zurück.
- Staffel-Auswahl mit bis zu acht sichtbaren Einträgen pro Seite, ohne leere Zusatzfelder und mit mittig ausgerichteten Beschriftungen.
- Alphabetleiste in der Episodenübersicht ausgeblendet.
- Trailerbutton auf Episoden-Detailseiten entfernt; Serien-Trailer bleibt auf der Serienübersicht.
- Fehlgeschlagene Serien-Trailersuche zeigt „Nicht verfügbar“ im Button statt eines zusätzlichen Informationsfensters.
- Nach angeforderter Film-Trailersuche startet ein später gefundenes Ergebnis automatisch, wenn der Trailerbutton noch ausgewählt ist. Bei anderer Auswahl wird das Ergebnis bereitgehalten.
- Favoriten-Titel mit Platz für zwei Zeilen. Filmtitel haben Posterbreite, Serien behalten mehr Breite.
- Favoriten werden für Movie/Series nach normalisiertem Titel und gleichem Jahr gruppiert. Unterschiedliche Emby-IDs bleiben beim Öffnen als Varianten erreichbar. Servereinträge werden nicht gelöscht.
- Detail-Hintergrund-Auswahl für Video oder Musik mit Fanart; Video hat Vorrang, Musik ist der vorgesehene Ersatz. Lautstärke über Fernbedienung.
- Lokale Bond-Theme-Tests und Layout-Callback-Korrektur sind im exportierten Code enthalten.

## Dateien und Prüfung

- `plugin.py`: unveränderter Receiverexport, SHA256 `fff3cc49be99c3b62e2a22a42d2b4c763e038c340d3f436641f0a3bcbc03d6f9`.
- `assets/`: sechs mitgelieferte UI-Grafiken.
- Originale Export-ZIP und `SHA256SUMS.txt`; das Manifest verwendet Windows-Pfadtrenner.
- Alle sieben Prüfsummen des Exportmanifests stimmen. Python-Syntax wurde mit AST geprüft.
- Screenshots dokumentieren die Detailseiten und Favoritenansicht. Vollständige Enigma2-Laufzeit-, Wiedergabe- und andere Receiver-Tests wurden hier nicht durchgeführt.

## Noch für eine allgemeine Veröffentlichung zu bearbeiten

Der Code enthält lokale Theme-Overrides und erwartet Grafiken unter `/media/usb/EmbyFlowThemeLocalTest/`. Die Grafiken gehören beim aktuellen Teststand dorthin; die Export-ZIP ist kein automatischer Installer. Theme-Mediendateien sind nicht im Paket enthalten. Für eine allgemeine Version müssen UI-Assets in einen plugininternen Pfad und die lokalen Theme-Overrides in einen optionalen Testmodus überführt werden. Die Theme-API des eigenen Emby-Servers wurde in dieser Sitzung nicht praktisch bestätigt.

„Favorit entfernen“ entfernt weiterhin nur den ersten Eintrag einer Gruppe; andere Varianten können beim erneuten Laden wieder erscheinen. Gruppierung nach Titel/Jahr ist eine Heuristik, keine garantierte Identitätsprüfung. Die bestehende Buildnummer und die Update-Manifeste wurden nicht verändert.

# Marineblauer lokaler USB-/HDD-Ordnerbrowser

Dieses lokale Werkzeug ersetzt die alte schwarze Verzeichnisliste unterhalb
der Quellenuebersicht durch ein 3x3-Kartenraster. Marineblau `#0C1827` ist der
Hintergrund des gesamten Screens. Karten, Icons, die Quellenbezeichnung,
aktueller Pfad und der Detailbereich rechts sind Teil des neuen Browser-Skins.
Die USB-/HDD-Quellenuebersicht selbst bleibt erhalten.

Bei vorhandenen bekannten Medienordnern zeigt die Standardansicht diese und
Videodateien zuerst. **Gelb** blendet alle weiteren Ordner ein; es wird nichts
geloescht und die gescannte Liste nicht veraendert. Ohne erkannte Medienordner
bleiben alle Ordner sichtbar. Bei einem Verzeichniswechsel beginnt die Ansicht
wieder mit Medienordnern. Dateinamen bleiben erhalten; die textuellen
`[Ordner]`-/`[Video]`-Praefixe entfallen zugunsten der Symbole.

Die vorhandenen Methoden fuer Einlesen, Oeffnen, Root-Grenzen, Zurueck und
Dateiwiedergabe werden nicht ersetzt. Nur Darstellung, Auswahlzuordnung und
Rasternavigation werden angepasst. Aktuelle Skyfall-Detailseite, Picons der
Quellenuebersicht und Player-Korrekturen bleiben ausserhalb dieses Zusatzes.

Das Werkzeug enthaelt die benoetigten Ordner-/Videosymbole als PNG. Es legt
sie unter `assets/local_folder_grid_20261026` ab, sichert die installierte
Plugin-Datei und fordert nach der Aenderung einen GUI-Neustart an. Ein spaeteres
regulaeres Vollupdate kann den lokalen Zusatz ersetzen.

16 lokale Tests pruefen Skin/Marineblau, Filter und unveraenderte Eintraege,
unbekannte Ordnernamen, Ordner-/Dateiauswahl, Root-Grenzen, Raster-Navigation,
leere und laufende Scans, Seitenwechsel, PNGs und lokale Installation/Sicherung.
Die sortierte Ansicht wird bei der Navigation wiederverwendet und erst nach
neuen Scan-Ergebnissen oder Filterwechsel erneut aufgebaut.
`preview.png` zeigt Beispielordner, keinen Receiver-Screenshot.
Die Darstellung auf der Vu ist noch nicht bestaetigt.

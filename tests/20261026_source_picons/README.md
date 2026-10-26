# Lokale Quellen-Picons, 26.10.2026

Das separate Werkzeug `tools/install-local-source-picons-20261026.py` ergaenzt
die vorhandene USB-/HDD-Uebersicht um lokale Quellenbilder. Es ist kein neues
allgemeines Plugin-Update. Es ergaenzt ausschliesslich `_show_icon()` des
bestehenden Quellen-Dashboards und legt sieben eigene PNG-Dateien unter
`assets/local_source_picons_20261026` im Plugin-Ordner ab.

Filme, Serien, USB/HDD, Aufnahmen und die virtuelle Kachel Alle Medien bekommen
eigene, farblich passende Symbole. Dokumentationen und gemountete Netzwerkquellen
haben ebenfalls eigene Picons. Die Quellenkarten zeigen diese mit 112x112
Bildpunkten in Full HD; die vorhandenen Skalierungshelfer passen kleinere
Aufloesungen an. Die Quellenverwaltung rechts behaelt ihre bisherigen kleinen
Bildflaechen. Beschriftungen, Fokus und restliches Layout bleiben erhalten.

`build_assets.py` erzeugt die eigenen PNGs und eine Komponenten-Vorschau mit
Pillow. `preview.png` ist eine Entwurfsvorschau und kein Screenshot von der Vu.
Auf dem Receiver ist fuer diese Picons kein Pillow, Bilddownload oder
Metadatenabruf erforderlich: Die geprueften Bilder sind im Werkzeug enthalten.

Vor der Plugin-Aenderung wird die installierte Datei gesichert. Die GUI wird
anschliessend neu gestartet. Wiederholter Aufruf repariert auch fehlende eigene
Picons, ohne das Plugin erneut zu aendern. Ein regulaeres Vollupdate kann den
lokalen Anzeigezusatz ersetzen; es werden keine Einstellungen, Filme, Poster
oder Quellenlisten geloescht oder ersetzt.

14 lokale Tests: Bilder/Transparenz, Kategoriezuordnung inklusive Alle Medien,
vererbte Dashboard-Bildfunktion, Kartengroesse und Quellenverwaltung, fehlende
Bilder/Decoderfehler, unveraenderte Quellen und Player-Funktionen, Sicherung,
Wiederholung, Symlink-Abbruch und Wiederanlauf nach fehlgeschlagenem Austausch.
Die Darstellung auf der tatsaechlichen Box ist noch nicht bestaetigt.

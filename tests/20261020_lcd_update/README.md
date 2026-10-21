# den LCD-Zeit – Testupdate 2026102001

Verteilung über den vorhandenen EmbyFlow-RCDEV-Updater. Basis ist ausschließlich
veröffentlichter Build 2026101805 mit geprüfter SHA256; private Such-, Theme- und
Wunschbox-Versuche werden nicht übernommen. Der vom Nutzer gelieferte volle
Pluginstand wurde zur Analyse gelesen und unverändert belassen.

## Ursache im Code / Fix

Die eigenen Front-/Segment-Summaries lesen bisher rohe Service-PTS. Die richtige
TV-Infobar verwendet `duration_ticks` und `current_position_ticks()` (absolute
Inhaltsposition, einschließlich Streamneustart/Fortsetzen, 10 Millionen Ticks/s).
Die Summaries verwenden jetzt diese gleiche Inhaltszeit; die Ganzzahlumrechnung
nach 90-kHz-PTS lautet `ticks * 9 // 1000`. Ohne gültige Dauer/Position erscheinen
Platzhalter. Playback-, Seek-, Subtitle- und TV-Overlay-Methoden bleiben fachlich
unverändert; der vorhandene Overlay-Takt veröffentlicht nur einen Zeitschnappschuss.

Für das externe LCD4linux wird ausschließlich die bereits geladene Funktion
`LCD4linuxPIC(self, session)` im Speicher adaptiert. Vorher wird der kompilierte
Renderer strukturell geprüft: verschachteltes `putProgress`, Zugriff auf
`Llength`/`Lposition`, Umrechnungskonstante 90000. Das funktioniert auch ohne
installierte plugin.py, solange die bekannte Rendererstruktur in plugin.pyc
vorliegt. Unbekannte Strukturen bleiben unangetastet und werden protokolliert.

Ein Render-Proxy liefert nur die beiden Zeitfelder aus dem EmbyFlow-Schnappschuss.
Der gemeinsame LCD4linux-Servicecache wird nie überschrieben. Die Werte gelten
nur bei passender Sitzung und vollständiger aktueller Service-Referenz; dabei
wird der bestehende EmbyFlow-Puffer-Proxy über seine Besitzprüfung berücksichtigt.
Schnappschüsse verfallen nach drei Sekunden und werden beim Schließen gelöscht.
Live-TV, fremde Player und Musik-Casting verwenden weiter den Originalrenderer.
Keine Änderung an getCurrentService/getLength/getPlayPosition und kein Schreiben
auf Display-Geräte oder an LCD4linux-Konfiguration. Keine Serverabfragen.

## Nachweise und Grenzen

`python -m unittest discover -s tests/20261020_lcd_update -p 'test_*.py' -q`

21 Tests: Einheiten, absolute Position nach Streamneustart, Pause, Filmende,
ungültige Zeiten, Metadatenfallback, Lebenszyklus, Fremdservice/Session, Pufferbesitz,
interne Anzeigen, isolierter Render-Proxy, unveränderter LCD4linux-Cache,
Cast/Live-TV, Ablauf, unbekannter Renderer und idempotente Registrierung.

Zusätzlich wird der echte öffentliche LCD4linux-Renderer r36 anhand des
unveränderlichen Commits 4d4bde2651a25bf9570be58182af8f6ad64b29d9 überprüft.
Gesamte Quelldatei SHA256:
`9d4774c9c9285b343d8e897096a79449b8ab7a9538093fda7f8747a4e874c288`.
Der Referenzcode wird nur zum Testen geladen und nicht mit dem Update gebündelt.
LCD4linux-Quelle/Lizenz: joergm6, NPOSL-3.0, siehe Originalkopf.

Installiertes r40 und konkrete Zgemma/Gigablue/Mutant-Hardware wurden hier nicht
ausgeführt. Die strukturelle Laufzeitprüfung verhindert blindes Patchen eines
abweichenden Renderers. Die Anzeige auf den Geräten muss nach dem Update
bestätigt werden. Das Bild +179 min allein belegt keine tatsächliche Filmrestzeit.

Begrenztes Diagnoseprotokoll: `/tmp/embyflow-display-time.log`; enthält Zeitwerte
und Registrierungsstatus, keine URLs, Tokens oder Titel. Maximal ein Eintrag je
Kategorie alle 30 Sekunden, Dateigröße etwa 64 KiB. Dieses Protokoll erlaubt die
Unterscheidung zwischen fehlender Rendererkompatibilität und falschen Laufzeiten,
ohne weitere Diagnoseinstallation.

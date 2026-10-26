# Lokale Wiederherstellung des Skyfall-Einstiegs

`tools/restore-local-skyfall-20261026.py` ist ein separates Werkzeug fuer die
lokale Vu-Testinstallation, kein allgemeines Plugin-Update. Der Updater-Kanal
und die Server-Mediathek werden dadurch nicht geaendert.

Das Werkzeug verlangt die vorhandene, nicht leere Originaldatei
`/media/usb/Filme/James Bond 007 - Skyfall (2012).ts`. Es sichert die installierte
`plugin.py` und ergaenzt den bisherigen lokalen Einstieg samt Detailseite.
Vorhandene Player-Korrekturen und Einstellungen bleiben erhalten. Filmdaten
kommen nur aus vorhandenen lokalen Caches und Bildern. Es werden keine
Server-Metadaten abgerufen und keine Filme kopiert oder heruntergeladen.

Bei einer Aenderung wird die GUI neu gestartet; Wiederholung ist ohne
Aenderung und Neustart moeglich. Ein spaeteres regulaeres Vollupdate der
`plugin.py` kann diesen lokalen Zusatz erneut ersetzen.

21 lokale Tests pruefen Detailseite, originalen lokalen TS-Playerpfad,
Navigation inklusive Hintergrund-Neuaufbau, Erhalt der bisherigen
Player-Korrekturen und Quellenliste sowie Sicherung und Fehlerbehandlung.
Es wurde hier keine Installation auf der Vu ausgefuehrt.

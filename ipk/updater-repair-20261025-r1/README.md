# EmbyFlowE2: einmalige Updater-Reparatur

Dieses Zusatzpaket behebt "No module named 'py_compile'" im bereits
installierten EmbyFlowE2. Es ersetzt nicht das vollstaendige Plugin und
installiert keine Python-Bytecode-Helfer oder Zugangsdaten.

Installation ohne Telnet:

1. Das IPK von GitHub herunterladen und per Dateitransfer nach /tmp auf die Box kopieren.
2. In der Softwareverwaltung des Images "Lokale Erweiterungen installieren"
   oeffnen, /tmp waehlen und dieses IPK installieren. Menunamen koennen abweichen.
3. Nach erfolgreicher Installation die GUI manuell neu starten.
4. EmbyFlowE2 > Updates > Update pruefen verwenden.

Das Paket legt vor der Aenderung eine Sicherung neben plugin.py an:
plugin.py.vor-updater-only-<Datum-Uhrzeit>-<Prozessnummer>.
Es aendert ausschliesslich den erkannten alten Updater. Alle fuenf
Syntaxpruefungen bleiben aktiv und verwenden das eingebaute compile().
Einstellungen, Zugangsdaten, Suche und Wiedergabecode werden nicht ersetzt.
Ein bereits reparierter Updater bleibt unveraendert.

Bei unbekanntem Updater oder einem Fehler meldet die Paketinstallation einen
Fehler. Dann nicht von einer erfolgreichen Reparatur ausgehen; Ausgabe sichern.
Das Paket stoppt oder startet weder Enigma2 noch den Receiver. Es braucht
keinen Netzwerkzugriff und kein python3-compile. Nach dem GUI-Neustart laeuft
der korrigierte Updater. Deinstallation dieses Zusatzpakets entfernt nur die
Reparaturdateien und macht die Korrektur im Plugin nicht rueckgaengig.

Ein spaeteres regulaeres Plugin-Update ersetzt die ganze plugin.py durch den
veroeffentlichten Stand. Private lokale Erweiterungen sind darin nicht
automatisch enthalten.

Lokal mit echten alten Plugin-Quellen und simuliertem Paketablauf geprueft.
Eine Installation auf einem Receiver wurde hier nicht durchgefuehrt.

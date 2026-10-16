# EmbyFlowE2 – getesteter Pufferstand vom 16.10.2026

Dieser Checkpoint enthält die vollständige PY aus dem installierten V4-Test sowie die benötigte Hilfsdatei. Er ist für bestehende EmbyFlowE2-Installationen gedacht und ersetzt kein vollständiges IPK.

## Dateien

- `plugin.py`: vollständiger zusammengeführter Stand, SHA256 siehe SHA256SUMS.
- `embyflow_buffer_v1.py`: benötigte Puffer-Hilfsdatei; gehört neben die PY in den Plugin-Ordner.
- `COMMUNITY.md`: fünf Zeilen zur Weitergabe.
- `SHA256SUMS`: Prüfsummen beider Python-Dateien.

Beide Python-Dateien gehören zusammen nach `/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/`. Vor einer manuellen Übernahme vorhandene Installation sichern. Vorhandene Assets und weitere Plugin-Module werden weiterhin benötigt und sind nicht Teil dieses Quellcode-Checkpoints. Keine Benutzerkonfiguration, Zugangsdaten oder laufenden Testvormerkungen sind enthalten.

## Verhalten

Der Stabilitätsmodus ist ohne gespeicherte Aktivierung aus. Erweiterte Einstellungen öffnen, in der mittleren Spalte nach unten zu Stabilitätsmodus oder Puffertest navigieren und Änderungen mit Grün speichern. Der vorhandene Einstieg und die Schriftgrößen bleiben erhalten. Sechs sichtbare Zeilen scrollen durch insgesamt acht Optionen in der mittleren Spalte.

Nur statische HTTP(S)-Videostreams mit `/Videos/.../stream.*` und `Static=true` werden gepuffert. HLS, DASH, Transcoding, Audio und andere Endpunkte sind ausgenommen. Ein lokaler HTTP-Proxy bindet ausschließlich an Loopback, erhält die ursprünglichen HTTP-Bereichsanfragen und verwendet den vorhandenen Requests-Serverguard. Es gibt keine zusätzlichen Wiederholungsversuche im Proxy und keine vollständige Filmdatei auf dem Datenträger.

Vor der Ausgabe werden zunächst bis zu 4 MiB vorgeladen; die begrenzte Warteschlange hält bis zu 16 MiB pro Anfrage. Höchstens zwei Anfragen werden gleichzeitig angenommen. Diese Begrenzung betrifft die eigenen Warteschlangen, nicht den gesamten Speicherbedarf des Players oder der Netzwerkbibliotheken. Eine feste Reserve in Sekunden wird nicht zugesichert. Auf der getesteten VU wurde ein ungefähr zwei Sekunden langer Spinner beim Start beobachtet und vom Nutzer akzeptiert; das ist keine allgemeine Zeitgarantie.

Der vorgemerkte Test wird gespeichert und beim nächsten Filmstart einmalig verbraucht. Die Anzeige wartet auf mindestens 8 MiB Proxyreserve, hält dann neue Daten für 15 Sekunden zurück und gibt das Nachladen automatisch frei. Vorhandene Daten werden weiter ausgegeben. Zurück schließt die Testanzeige und gibt die Sperre vorzeitig frei.

Der Buffer-Eintrag unter Qualität & Stats liest den aktiven Dienst direkt aus Enigma2 und zeigt beispielsweise `RAM 16.0 MiB`. Diagnose `/tmp/embyflow_buffer_status_v4.json` enthält Statusfelder ohne Stream-URLs, Titel oder Zugangsdaten.

## Prüfung und Grenzen

- Lokale HTTP-Tests: vollständige Datenintegrität, Range/206/416, geschützte Loopback-Route, Warteschlangenbegrenzung, Sperre/Fortsetzung und Aufräumen.
- Einstellungsprüfung: originale Skin-XML, Zeilengrenzen, Erreichbarkeit aller Optionen, automatisches Scrollen, Delegation bisheriger Aktionen und Speichern erst mit Grün.
- Installationsprüfung: Syntax des vollständigen Plugins, exakte Versionsprüfung, V3-zu-V4-Update, Sicherung und bytegenauer Rückweg.
- Praxistest am 16.10.2026: VU+ Duo 4K SE, normaler 4097-Player; Nutzer bestätigte durchgehendes Bild und Ton während der 15 Sekunden. Screenshot zeigt anschließend 16.0 MiB Reserve.
- Nicht bestätigt: echte Verbindungsabbrüche mit automatischem Wiederverbinden, dauerhafte Unterversorgung, sämtliche Codecs/Spulszenarien und andere Receiver.

Die versionierten Installations- und Rückwegskripte stehen unter `tests/20261016_e2_buffer_v3/` und `tests/20261016_e2_buffer_v4/`. Sie prüfen den jeweils erwarteten Vorzustand. Die frühere V1-Menüvorschaltung wurde verworfen und ist in dieser vollständigen PY nicht enthalten.

Der bestehende automatische Updatekanal in `update.json` wurde durch diesen Checkpoint nicht umgestellt. Ein einzelnes PY-Update ohne Hilfsdatei wäre unvollständig.

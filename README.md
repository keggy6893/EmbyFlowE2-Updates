# EmbyFlowE2-Updates
Update repository for EmbyFlow E2

## Build 2026100801

Die Neuheitenübersicht zeigt sechs Spalten und zwölf Poster pro Seite. Die rechte Vorschau mit Bild und Beschreibung entfällt; die vollständige Detailseite öffnet sich mit OK. Unter den Postern stehen Jahr und Titelart: Film, Serie, Doku oder Doku-Serie. Die Doku-Zuordnung verwendet die Genres des Emby-Servers. Titel nutzen zwei Zeilen mit einer Kürzung bei längeren Namen; ein zusätzlicher automatischer Zeilenumbruch ist deaktiviert.

Die dunklen Hintergrundflächen sind auf Marineblau `#0C1827` vereinheitlicht. Auf der Detailseite bleibt die Fläche deckend, auch wenn ein Hintergrundbild oder Video geladen wird.

### Trailer

Trailer bleiben optional und standardmäßig ausgeschaltet. Aktivierung unter **Erweiterte Einstellungen → Wiedergabe & Diagnose → Trailer aktivieren (Erprobung)**; mit Grün speichern. Der Resolver nutzt das Systempaket yt-dlp ab Version 2026.08.19. Die Reihenfolge bleibt: Emby-Anbieterlinks, KinoCheck, gefilterte YouTube-Ersatzsuche. KinoCheck berücksichtigt Trailer und danach Teaser; die YouTube-Suche prüft Titel, Filmjahr und Länge. Quellen und Ablehnungsgründe erscheinen im Trailer-Log.

Auf der VU+ Duo 4K SE scheiterte ein gültiger YouTube-Trailer durch den zuvor eingestellten AdGuard-Familien-DNS. Nach Umstellung auf DNS ohne erzwungenen YouTube-Restricted-Mode bestätigte der Benutzer Bild und Ton. Das ist eine Netzwerk-Einstellung und kein Teil des Plugin-Updates. Der Benutzer berichtet, dass etwa 95 Prozent seiner Trailer-Tests funktionieren; dies ist keine allgemeine Erfolgsquote. Eine Startzeit von vier Sekunden wird nicht zugesichert.

### Prüfung

Python-Syntax, Skin-XML, 6×2-Layout, Navigation und Titelart-Zuordnung wurden lokal mit simulierten Enigma2-Komponenten geprüft. Der Benutzer bestätigte Marineblau, die Posterübersicht und den Schriftfix auf seiner Box. Andere Receiver und sämtliche Wiedergabeszenarien sind damit nicht geprüft.

Die hochgeladene Box-PY vom 8. Oktober und die anschließend bestätigten Änderungen bilden die Grundlage dieses Builds. Bestehende Sicherheitskorrekturen bleiben enthalten.

## Entwicklungsstand vom 14.10.2026

[Receiver-Checkpoint mit PY, Grafiken und Original-ZIP](checkpoints/20261014_083450/) · [Gesammelte Änderungen und Einschränkungen](checkpoints/20261014_083450/CHANGELOG.md)

Der Export enthält lokale Theme-Tests und USB-Pfade. Er ist als Entwicklungsstand gesichert; der Auto-Update-Kanal bleibt beim bisherigen Build.

## Getesteter E2-Pufferstand vom 16.10.2026

[Zusammengeführte vollständige PY, benötigte Hilfsdatei und Prüfbericht](checkpoints/20261016_1545_buffer_v4/) · [Community-Text](checkpoints/20261016_1545_buffer_v4/COMMUNITY.md)

Optionaler RAM-Puffer für statische Direktstreams, scrollbare mittlere Einstellungsspalte, dauerhafte Testvormerkung und Pufferstatus direkt im Player. Auf der VU+ Duo 4K SE wurde der 15-Sekunden-Puffertest mit durchgehendem Bild und Ton bestätigt. Für weitere Receiver und echte Verbindungsabbrüche liegt keine Bestätigung vor. Der bestehende Auto-Update-Kanal wird mit diesem Checkpoint nicht umgestellt.

## Auto-Update 2026101601

Der rcdev-Updatekanal stellt jetzt den E2-Pufferstand V4 bereit. Die Update-PY enthaelt die unveraenderte Hilfsdatei aus dem Checkpoint und stellt sie beim GUI-Neustart mit SHA256-Pruefung und atomarem Dateiaustausch neben plugin.py bereit. Bestehende Einstellungen bleiben erhalten; ohne gespeicherte Aktivierung ist der Stabilitaetsmodus aus. Keine neue IPK. Echte Verbindungsabbrueche und Wiederverbindung sind weiterhin ungeprueft.

## Auto-Update 2026101701 – deutsche Forced-Textuntertitel

Auf Basis von Build 2026101603: Ohne gesetzten Untertitel-Standard wird eine deutsche, als Forced/erzwungen gekennzeichnete Textspur automatisch gestartet. Eine vorhandene Serverauswahl bleibt erhalten. Manuelle Auswahl einschließlich „Untertitel aus“ verhindert eine erneute automatische Auswahl während dieses Players. Ein vom Server gesetzter Aus-Index (-1) schließt diese Forced-Automatik nicht aus.

Nach einem Verbindungsabbruch beim Untertitel-Download erfolgt einmalig ein Versuch über eine frische Verbindung. Serverguard und TLS-Zertifikatsprüfung bleiben aktiv; Zertifikatsfehler werden nicht wiederholt.

Der Benutzer bestätigte deutsche Untertitel in der gezeigten fremdsprachigen Szene von „Mayday“ auf VU+ Ultimo 4K mit openATV 8.0.1. Das bestätigt weder sämtliche Filmszenen noch PGS-Bilduntertitel oder andere Receiver. Elf lokale Prüfungen decken Auswahl, Ausschalten, Download-Abbruch, SRT-Verarbeitung und Aktivierung mit den originalen Player-Funktionen ab.

Der optionale manuelle Installer und die Tests stehen unter `tests/20261017_forced_subtitles/`. Das automatische Update enthält den Fix bereits; der Installer ist dafür nicht zusätzlich nötig.

## Auto-Update 2026101702 – Untertitel V2, aktive Filmversion

Automatik und Textrenderer verwenden die aktive MediaSource gemeinsam. Die bisherige Auswahl konnte Spuren der ersten Filmversion verwenden, obwohl das Menü die aktive Version zeigte. Aktivieren und Ausschalten schreiben den Standardindex der aktiven Version. Deutsche Sprachvarianten wie de-DE/de_AT werden erkannt; fehlende Metadaten werden mit höchstens vier verzögerten Timeraufrufen erneut geprüft. Ein vorhandener Standardindex einschließlich 0 bleibt maßgeblich, manuelle Auswahl bleibt wirksam. Der Download-Neuversuch aus V1 bleibt erhalten.

Neun V2-Prüfungen umfassen die mit V1 reproduzierte Quellenverwechslung, HTTP-Download/Parsing/Aktivierung/Ausschalten mit originalen Player-Funktionen und mehrere Filmversionen. Die V1-Suite umfasst weitere elf Prüfungen. Nach dem V2-Test schickte der Benutzer einen Screenshot mit deutschem Untertitel in einer weiteren Filmszene auf VU+ Ultimo 4K mit openATV 8.0.1. Ob dieser automatisch oder manuell aktiviert wurde, wurde nicht separat bestätigt. Keine Zusage für sämtliche Filme, PGS-Bilduntertitel oder andere Receiver.

Der Auto-Update-Kanal enthält V1 und V2 vollständig; die manuellen Testinstaller sind dafür nicht zusätzlich erforderlich.

## Auto-Update 2026101703 – Untertitel V3, leere Downloads

Nach dem gemeldeten Fehler „Leere Untertiteldatei“ mit installiertem V2 verwendet V3 für Untertiteldateien frische geschützte Requests-Verbindungen statt des Metadaten-Pools/-Caches und normale Kompressionsaushandlung. Eine leere HTTP-200-Antwort oder ein Verbindungsabbruch erlaubt höchstens einen weiteren Versuch pro Pfad. Danach können die bereits im Repository verwendeten Videos-Pfade für denselben Film, dieselbe Filmversion und dieselbe Spur verwendet werden. Es wird keine andere oder vollständige Untertitelspur ersatzweise eingeschaltet. Liefert der Server auf allen Pfaden keine Daten, bleibt der Fehler sichtbar.

Die V2-Auswahl und der vorhandene SRT-Renderer bleiben enthalten. Zertifikatsfehler sowie HTTP-Zugriffs-/Rate-Limit-Antworten werden vom Download-Helfer nicht erneut versucht; TLS-Prüfung und Serverguard bleiben aktiv. Die Diagnose `/tmp/embyflow_ut_v3.jsonl` enthält nur Zeit, Versuchsnummer, HTTP-Status, Datenmenge und Ergebnistyp, keine URLs oder Zugangsdaten.

Sechs lokale V3-Tests decken leere Antworten, begrenzte Versuche, Zertifikats-/Zugriffsfehler und den originalen Download-Worker mit echtem lokalen HTTP ab. V1 und V2 haben zusätzlich elf beziehungsweise neun Prüfungen. V3 wird auf ausdrücklichen Wunsch im rcdev-Kanal bereitgestellt; der Receiver-Test auf der Ultimo 4K / openATV 8.0.1 steht noch aus. Keine Zusage für sämtliche Filme oder PGS-Bilduntertitel.

## Auto-Update 2026101704 – automatische 4K-Forced-Untertitel in Abschnitten

Eingebettete deutsche Forced-Textuntertitel werden bei der aktiven 4K-Filmversion über die dokumentierte Emby-API in 60-Sekunden-Abschnitten mit absoluten Zeitstempeln angefordert. Das vermeidet die Anforderung einer vollständigen SRT-Datei vor der Anzeige. Ob der Server die Abschnittsanforderung effizient bearbeitet, hängt weiterhin vom Server ab. Der bestehende playerinterne Text-Renderer zeichnet die geladenen Dialoge. Kein Administratorzugang und keine separate SRT auf dem Server erforderlich.

Der nächste Abschnitt wird 15 Sekunden vor Ablauf des geladenen Bereichs angefordert. Bis zu drei Abschnitte bleiben im RAM. Spulen fordert bei Bedarf den aktuellen Bereich an, verwirft veraltete Ergebnisse und erzeugt pro Wiedergabezustand nur eine laufende Abschnittsanfrage. Manuelles Ausschalten, Schließen und Filmversionswechsel beenden die Verarbeitung. HD, externe, anderssprachige und nicht-erzwungene Untertitel verwenden den vorherigen Download-Weg. Der frühere native Decoder-Test ist nicht Teil dieses Releasepfads. TLS-Zertifikatsprüfung und Serverguard bleiben aktiv.

**Receiver-Bestätigung des Benutzers, VU+ Ultimo 4K mit openATV 8.0.1:** „Mayday“ in 4K zeigt die deutschen Untertitel automatisch und synchron, mit ungefähr 30 Sekunden Startverzögerung. „Tenzig“ in 4K zeigt sie automatisch sofort und synchron; auch nach weiterem Abspielen wurde funktionierender Betrieb bestätigt. Dies ist keine Zusage für sämtliche Filme, Server, andere Receiver oder PGS-Bilduntertitel. Die Startverzögerung bei „Mayday“ bleibt eine bekannte Einschränkung.

Vierzehn lokale Abschnittstests prüfen unter anderem tatsächliche Textausgabe mit originalem Renderer und echtem lokalem HTTP, Nachladen, verschiedene Spulwege, Cache-/Anfragebegrenzung, Ausschalten, Versionswechsel, Fehler und absolute Zeitstempel. Die Quelltexte und der optionale manuelle Testinstaller stehen unter `tests/20261017_subtitle_segments/`. Das Auto-Update enthält den getesteten Abschnittscode bereits vollständig; der Testinstaller ist dafür nicht zusätzlich erforderlich. Diagnose: `/tmp/embyflow_subtitle_segments.jsonl` enthält nur Zeitbereiche, Status, Daten-/Dialoganzahl und Fehlerklassen ohne URLs oder Zugangsdaten.

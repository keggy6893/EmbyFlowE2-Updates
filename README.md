# EmbyFlowE2-Updates
Update repository for EmbyFlow E2

## Aktueller RCDEV-Test: Build 2026102502 – Sprachanzeige

Ueber **EmbyFlow → Updates → Update pruefen → Update installieren** verfuegbar.
Danach GUI neu starten. Die Infobar liest die Sprache der aktiven nativen
Tonspur und aktualisiert ihren Text beim Oeffnen und waehrend sie sichtbar ist,
auch auf Nicht-DreamOne-Boxen wie der SF8008 Supreme. Fehlende native
Sprachdaten verwenden weiter die vorhandenen Metadaten.

Tonspurwahl und Spruenge bleiben unveraendert. Der lokale Taste-9-Fix aus
2026102501 und die bisherigen Korrekturen bleiben enthalten. Kein auf Hardware
bestaetigter Fix fuer Anskars HTTP-Standbild oder das Verhalten nach Taste 9.
[Anzeigekorrektur und Tests](tests/20261025_audio_language/).

## Vorheriger RCDEV-Test: Build 2026102501 – lokale Dateispruenge

Ueber **EmbyFlow → Updates → Update pruefen → Update installieren** verfuegbar.
Nach erfolgreicher Installation die GUI neu starten.

Enthaelt den lokalen Taste-9-/Kapitel-Fix: Spruenge in lokalen Dateien verwenden
wie beim EMC-Vergleich den aktiven nativen Dateidienst. Kein Emby-HTTP-Neustart
und kein Backendwechsel fuer lokale Spruenge. Pause und Tonspur bleiben erhalten.
Die bisherigen Modal-Guard-, DreamOne- und Updater-Korrekturen sind enthalten.

**Anskars Standbild beim HTTP/GStreamer-Tonspurwechsel ist weiterhin offen.**
Die lokale Bestaetigung auf der Vu+ ist keine Bestaetigung fuer diesen Fall.
[Umfang und Pruefungen](tests/20261025_local_seek_release/).

## Update-Fehler: No module named 'py_compile'

**Einfacher Weg ueber den vorhandenen Image-Feed, ohne Telnet:**

1. Im Browser das OpenWebif der betroffenen Box oeffnen.
2. Unter **Einstellungen → Pakete** nach `python3-compile` suchen und das
   Standardpaket installieren, sofern es im Image-Feed angeboten wird.
3. Danach in EmbyFlow das normale Update erneut installieren und nach dessen
   erfolgreichem Abschluss die GUI neu starten.

Das Paket stellt dem alten Updater das fehlende Standardmodul zur Verfuegung.
Der danach installierte neue Updater verwendet bereits das eingebaute
`compile()` und braucht dieses Zusatzmodul kuenftig nicht mehr.
Die Verfuegbarkeit im jeweiligen Receiver-Feed wurde hier nicht geprueft.
Die normale Installation ueber die Paketverwaltung loest Abhaengigkeiten auf;
keine fremde `py_compile.py` aus einer anderen Python-Version kopieren.

Quellen: [OpenEmbedded Python-Paketaufteilung](https://github.com/openembedded/openembedded-core/blob/master/meta/recipes-devtools/python/python3/python3-manifest.json),
[OpenWebif Paketverwaltung](https://github.com/E2OpenPlugins/e2openplugin-OpenWebif/blob/master/plugin/controllers/views/responsive/ajax/settings.tmpl)
und [Installationscontroller](https://github.com/E2OpenPlugins/e2openplugin-OpenWebif/blob/master/plugin/controllers/ipkg.py).

**Alternative, falls das Standardpaket im Feed fehlt: Reparatur-IPK ohne Telnet:**
[Reparatur-IPK herunterladen](https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/65995374ea529924da652d29189e2fecbde123d8/ipk/updater-repair-20261025-r1/enigma2-plugin-extensions-embyflowe2-updater-repair_2026.10.25-r1_all.ipk),
nach `/tmp` auf die Box kopieren, in der Softwareverwaltung als lokale
Erweiterung installieren und danach die GUI manuell neu starten.
Das Zusatzpaket repariert ausschliesslich den vorhandenen Updater. Es ersetzt
keine komplette Plugin-Version und enthaelt keine versionsgebundenen
Python-Bytecode-Helfer.
[Paketinhalt, Sicherung und Installationshinweise](ipk/updater-repair-20261025-r1/README.md).

Der ueber `update.json` angebotene Build 2026102502 enthaelt bereits den
Updater-Fix aus Build 2026102301: Alle fuenf Syntaxpruefungen verwenden das
eingebaute `compile()`. Das zusaetzliche Python-Paket ist dafuer nicht noetig.
Installationen mit funktionierendem Updater beziehen diese Korrektur ueber
**Updates → Update pruefen → Update installieren**.

**Bereits blockierte alte Installationen koennen sich nicht allein durch ein
GitHub-Update reparieren.** Ihr installierter Updater importiert `py_compile`
noch vor dem ersten Abruf der neuen Plugin-Datei. Eine neue Manifest-Version,
ein anderes Downloadformat oder ein Reparaturskript im Repo aendern den bereits
laufenden alten Code nicht. Es gibt dort keinen vorgelagerten Reparatur-Hook.

Fuer diese Installationen liegt die einmalige lokale Reparatur in
[`tools/repair-updater-only-20261025.py`](tools/repair-updater-only-20261025.py).
Das Reparatur-IPK fuehrt sie ausserhalb des blockierten Updaters mit
`--no-restart` aus; danach ist der manuelle GUI-Neustart erforderlich.
Beim direkten Skriptaufruf ohne diesen Parameter wird der GUI-Neustart
automatisch angefordert. Die Reparatur sichert die
installierte Datei, ersetzt ausschliesslich die fuenf Syntaxpruefungen im
erkannten alten Updater. Beim direkten Aufruf wird auch bei fehlgeschlagenem
Stoppen oder Aufraeumen der Wiederanlauf versucht.
Ein bereits reparierter Updater bleibt unveraendert, ohne GUI-Neustart.
Danach funktionieren kuenftige Updates wieder ueber das Plugin-Menue.

Die Reparatur fuehrt selbst kein vollstaendiges Plugin-Update aus. Ein spaeteres
regulaeres Update ersetzt dagegen die gesamte `plugin.py`; private lokale
Erweiterungen sind im veroeffentlichten Build nicht automatisch enthalten.
Lokale Regressionen simulieren fehlendes `py_compile`, Installation, Sicherung,
Wiederanlauf und Fehlerfaelle. Eine Receiver-Pruefung wird damit nicht behauptet.

## Frueherer RCDEV-Test: Build 2026101802 – Downloads mit Tageslimit

Der eingebaute Updater bietet diesen Test unter **Updates → Update pruefen** an.
Nach Installation die GUI neu starten. Unter **Erweiterte Einstellungen →
Wiedergabe & Diagnose → Film-/Folgen-Download (Test)** einschalten und mit Gruen
speichern. Standard ist AUS. Bei Filmen und einzelnen Folgen erscheint dann
**Herunterladen**. Der Anbieter muss Downloads fuer den Emby-Benutzer erlauben;
bei Ablehnung oder unklarer Freigabe bleibt der Start gesperrt.

Die Zielauswahl zeigt freien und gesamten HDD-/USB-Speicher sowie Dateigroesse
und Reserve. Gemeinsam hoechstens **fuenf Filme oder einzelne Folgen pro Tag**
und Receiver-Installation; der Zaehler ist in den Downloadfenstern sichtbar.
Fertige Dateien stehen unter **Downloads**, direkt unter Updates. Der Eintrag
erscheint nur bei aktivierter Downloadfunktion. OK spielt lokal mit 4097 ab.
Lokale Wiedergabe verbraucht keinen Downloadplatz.

Ein Download gleichzeitig; das Downloadfenster muss offen bleiben. Kein
Download-Fortsetzen, keine Warteschlange und kein Download externer Untertitel.
Anbieterpruefung, Platzkontrollen, Abbruch und Tageszaehler sind lokal getestet.
Der Nutzer bestaetigte Downloadoberflaeche, Speicher- und Limiteranzeige;
die neue Uebersicht benoetigt weitere Receivertests.
[Code, Tests und technische Grenzen](tests/20261017_movie_download/).

Die PGS-/SRT-/4K-Untertitelfunktionen aus Build 2026101801 sind enthalten.
Dieses Update ersetzt die gesamte plugin.py mit Sicherung durch den Updater.
Der separate lokale Sprachtest und die experimentellen ATV-7.6-Layoutversuche
sind nicht enthalten und werden bei einem Update ersetzt.

## Vorheriger RCDEV-Test: Build 2026101801 – PGS automatisch mit 4097

Der eingebaute Updater bietet den PGS-Test ueber **Update pruefen** an. Nach der
Installation die GUI neu starten und den Film frisch oeffnen. Ein zusaetzlicher
manueller PGS-Installer ist nicht erforderlich.

Eingebettete PGS-Bilduntertitel werden an das sichtbare EmbyFlow-Playerfenster
gebunden. Ohne Emby-Vorgabe wird eine deutsche erzwungene PGS-Spur automatisch
ausgewaehlt, sofern keine passende erzwungene Textspur vorhanden ist. Emby-Vorgabe,
manuelle Spurwahl und manuelles Ausschalten haben Vorrang. Der bisherige SRT-
und 4K-Abschnittscode bleibt enthalten. Der Player bleibt 4097.

Auf Vu+ Duo4K SE mit openATV 8.0.1 wurden volle/erzwungene deutsche PGS,
Spulen/Fortsetzen im manuellen Test sowie die Automatik bei **2012 in 4K** vom
Nutzer bestaetigt. **Offen:** Bei einem SD-Film fehlt die automatische Auswahl;
Spur-/Forced-Metadaten stehen noch aus. Keine Zusage fuer alle Filme oder Receiver.
Das Standbildproblem beim wiederholten Tonspurwechsel auf DM One ist damit nicht
als behoben bestaetigt.

Dieser fruehere Build enthielt den Download-Test noch nicht.
[PGS-Code, Tests und genaue Grenzen](tests/20261017_pgs_native/).

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

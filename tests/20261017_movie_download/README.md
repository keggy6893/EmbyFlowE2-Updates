# Film-/Folgen-Download – RCDEV-Test 2026101802

Der bisher lokale Stand V11 wird mit Build 2026101802 ueber den RCDEV-Updater
bereitgestellt. Enthalten sind der sichtbare Downloadbutton, Anbieterpruefung,
Kapazitaetsanzeige, Tageslimit mit Anzeige und die lokale Downloaduebersicht.
Die Option heisst im Release **Film-/Folgen-Download (Test)** und bleibt
standardmaessig aus. **Downloads** erscheint bei Aktivierung unter Updates.
Die folgenden Abschnitte dokumentieren die Entwicklung vor dieser Freigabe;
damalige Hinweise auf eine fehlende Veroeffentlichung gelten fuer die jeweiligen
historischen Zwischenstaende.

Release reproduzieren: `python3 .github/build_download_2026101802.py`.
Tests: `python3 -m unittest discover -s tests/20261017_movie_download -p 'test_*.py'`
(Python mit Requests). Die historischen Installer-Eingaben stehen als
SHA256-gepruefte Deltas unter `fixtures/`; keine externen lokalen Dateien noetig.
Der Releasebuilder setzt die Manifest-URL zunaechst auf main; bei der
Veroeffentlichung wird sie auf den unveraenderlichen Artefakt-Commit gesetzt.

Die neue Downloaduebersicht braucht weitere Receivertests. Externe Untertitel,
Warteschlange und Download-Fortsetzen sind nicht enthalten. Der Player bleibt
4097. Keine Aenderung am offenen GigaBlue-Layoutproblem oder Sprachtest.

## Historischer lokaler Test

Basis v9: veröffentlichter PGS-/UT-Build 2026101801; kein Manifest- oder Releasewechsel.
Erzeugen: `/workspace/.embyflow-venv/bin/python tests/20261017_movie_download/build.py`.
Artefakt: `/workspace/local-artifacts/EmbyFlowE2_movie_download_LOCAL_v10.py`.
Tests: `/workspace/.embyflow-venv/bin/python -m unittest discover -s tests/20261017_movie_download -p 'test_*.py'`.

In den erweiterten Einstellungen in der zweiten Spalte „Wiedergabe & Diagnose“ bis „Film-Download (lokaler Test)“ scrollen, einschalten (standardmäßig aus) und mit Grün speichern. Es gibt neun Optionen mit sechs sichtbaren Zeilen. Ohne Grün bleibt der bisher gespeicherte Wert erhalten. Anschließend im Film-Detailbild den sichtbaren Button „↓ Herunterladen“ mit Hoch/Runter auswählen und OK drücken. Mit aktivem Trailer steht er zwischen Trailer und Zurück; ohne Trailer zwischen Abspielen und Zurück. Bei ausgeschalteter Option und bei Serienepisoden bleiben Button und Navigation unverändert. Filmversion wählen, eingehängte HDD/USB wählen und Größe/freien Platz/Zieldatei bestätigen. Ziel ist `movie/EmbyFlow` auf `/media/hdd` oder `/media/usb`; keine Ausweichablage im internen Flash. Zusätzlich zur Dateigröße sind 512 MiB Reserve erforderlich.

Die Oberfläche fragt die Emby-Benutzerrichtlinie `EnableContentDownloading` ab und verweigert ohne explizite Erlaubnis den Start. Der Server prüft zusätzlich den Originaldownload-Endpunkt `/Items/{Id}/Download` mit der gewählten `MediaSourceId`. Es werden keine Streams transkodiert und keine Berechtigungen umgangen. TLS und vorhandener Requests-Serverguard bleiben aktiv. Weiterleitungen werden im lokalen Test abgelehnt; Tokens werden weder protokolliert noch gespeichert.

Ein Download gleichzeitig. Fortschritt über GUI-Timer, HTTP und Schreiben im Hintergrund. Das Downloadfenster muss offen bleiben; EXIT/ROT bricht ab und entfernt die temporäre Datei, sobald der laufende Lesevorgang zurückkehrt (HTTP-Lesezeitlimit 30 Sekunden). Erst ein vollständig geladener Film erhält seinen endgültigen Namen; vorhandene Dateien bleiben erhalten. Unbekannte Größen, Größenabweichungen, ungeeignete Formate und fehlender Platz führen zum Abbruch. Absturz/Stromausfall kann versteckte `.embyflow-*.part`-Dateien hinterlassen.

Bewusste Grenzen dieses ersten Tests: kein Fortsetzen, keine Downloadwarteschlange, keine externen Untertitel, keine eigene Offline-Bibliothek. Originaldatei bewahrt die enthaltenen Ton-/UT-Spuren; lokale automatische Forced-UT-Auswahl ist damit nicht zugesichert. Abspielen nach Abschluss über den normalen lokalen Dateiplayer. Keine Behauptung eines erfolgreichen Tests an echter Ultimo-Hardware oder einem echten Emby-Downloadserver.

62 lokale Tests: Originalbytes und gewählte Version über echten lokalen HTTP-Server, Fortschritt, Abbruch/Teildateibereinigung, HTTP403, Redirect ohne Tokenweitergabe, Platzmangel vor und während Download, bestehende Datei, Größenabweichung, Einzeldownload, sichere Dateinamen sowie fehlender Datenträger, EXIT, abgelehnte Bestätigung und Abschlussanzeige mit Enigma2-Stubs. Zusätzlich werden die tatsächlich generierten Einstellungsfunktionen ausgeführt: neunte Option in Spalte zwei, Scrollposition und Fokus, Navigation aller vorhandenen Optionen, Umschalten ohne vorzeitiges Speichern und Übernahme erst bei erfolgreichem Grün-Speichern. Button-Tests prüfen beide Trailerzustände, Positionen ohne Überlappung, Navigation, Download per OK, unverändertes Abspielen/Zurück, deaktivierten Zustand und Episoden. Gesamtes generiertes Plugin syntaktisch kompiliert. Receiverprüfung auf Ultimo 4K/openATV 8.0.1 steht aus.

## Dialogstil v4

Versionsauswahl, Zielauswahl, Downloadbestätigung und Fortschrittsanzeige sind eigene rahmenlose EmbyFlow-Dialoge, angelehnt an den vorhandenen Qualitätsdialog: Navy #0C1827, Cyan #26DFF5, Markenname und eigene Fernbedienungshinweise. Keine ChoiceBox oder MessageBox des Systemskins im Downloadablauf. Lange ausgewählte Versionsnamen werden unter der Liste umgebrochen vollständig dargestellt. Die Bestätigung bietet zunächst Abbrechen; Größen- und Zielangaben bleiben vor dem Start sichtbar. Tests prüfen Dialogklasse im Versionsablauf, Pagerückgabe der richtigen Filmversion, Langnamenumbruch, Abbruch, sichere Bestätigungsvorgabe, Skinpalette/-rahmen und Fortschrittsbalken. Echtes Enigma2-Rendering muss auf dem Receiver geprüft werden.

## Filigrane Dialoge v5

Kompakte Breite 1120 statt 1280 Pixel bei 1080p; die Höhe passt sich der Anzahl sichtbarer Einträge an (ein Film etwa 418 Pixel statt 900). Ruhige dunkle Auswahlfläche und nur ein 2-Pixel-Cyan-Akzent, kleinere Typografie, schmale Trennlinie und 4-Pixel-Fortschrittsbalken. Filmversionen zeigen Qualität/Codec/Container links und die Größe separat rechts, der vollständige Versionsname steht in einer leisen Detailfläche darunter. Zusätzliche Tests prüfen adaptive Höhe, getrennte Größenanzeige, Fokusakzent und Layoutgrenzen. Receiverdarstellung der v5 steht aus.

## v6 – freigegebener Kartenentwurf und sichtbare Anbieterprüfung

Abgerundete Navy-Karten mit Cyan-Auswahlkontur, eingebetteten Download-/Auswahlsymbolen, Qualitäts-Badges und EMBY/FLOW-Farben. Die kleinen PNG-Assets sind in der einzelnen Test-Python-Datei enthalten und werden lokal nach /tmp entpackt; auf dem Receiver sind weder Pillow noch zusätzliche Pakete nötig.

Vor der Versionsauswahl fragt der Worker die Benutzerrichtlinie beim Emby-Server ab. Nur ein explizites JSON-Boolean `EnableContentDownloading: true` ist eine Freigabe. Ein explizites `false` wird als „Nicht erlaubt“, eine fehlende Antwort, Netzwerkfehler oder ein unklarer Wert als „Nicht prüfbar“ angezeigt; beide Zustände blockieren die Versionsauswahl und den Start. Eine zusätzlich vom Film gemeldete Ablehnung `CanDownload: false` wird berücksichtigt. Vor dem eigentlichen Dateiabruf wird die Benutzerrichtlinie erneut abgefragt (ohne lokalen Cache). Eine zwischenzeitlich entzogene Freigabe stoppt den Download. Der finale Download-Endpunkt kann weiterhin ablehnen; HTTP403 überschreibt dann den zuvor positiven UI-Status. Die Anzeige bestätigt die vom Server gemeldete Benutzerfreigabe, keine pauschale Vertrags-/Anbieterfreigabe und keine Garantie für sämtliche Filmversionen. Es findet kein Film-Download allein durch die Berechtigungsprüfung statt.

50 lokale Download-, Ablauf-, Layout- und Berechtigungstests bestehen; Berechtigungsfälle einschließlich realem lokalem HTTP sind enthalten. Gesamtes Test-Plugin kompiliert. Vorschau aus denselben XML-Geometrien, Texten und eingebetteten Assets: `/workspace/local-artifacts/EmbyFlowE2_movie_download_v6_preview.png`, erzeugbar mit `python3 tests/20261017_movie_download/render_preview.py` (Pillow auf der Build-Maschine). Dies ist ein lokales Rendering und kein Receiver-Screenshot.

## v7 – Receiver-Crash beim Öffnen des Downloads

Die Datei `20261017-193553-enigma2-crash.log` zeigt den Aufruf `_efdl_detail_ok` → `EmbyFlowLocalDownloadScreen` → `Screen.createGUIScreen` Zeile 366 und `TypeError: exec() arg 1 must be a string, bytes or code object`. Ursache war der einfache Lambda-Callback in `onLayoutFinish`. openATV 8.0 akzeptiert dort gebundene Methoden oder ausführbaren Quelltext; siehe https://github.com/openatv/enigma2/blob/8.0/lib/python/Screens/Screen.py#L364 . Der Callback ist jetzt die gebundene Methode `_efdl_layout`. Der Test mit dem originalen Dispatcher-Verhalten reproduzierte vor der Korrektur exakt den gemeldeten TypeError und besteht mit der Korrektur. Ein weiterer Test reproduziert den Fehler mit einem einfachen Lambda weiterhin gezielt.

Das ältere Log `20261017-163224-enigma2-crash.log` enthält einen unabhängigen `IndexError` in `E2EmbyClient/EmbyPlayer.py::__setSubtitleTrack` sowie fehlende `MovieBarInfo`-Skin-Konverter. Dieser fremde Plugin-Code wird durch die Reparatur nicht geändert. Design, Anbieterprüfung und veröffentlichter UT-Code bleiben in v7 gegenüber v6 unverändert. 56 lokale Download-/Berechtigungs-/Layout-/Reparaturtests bestehen. Der optionale lokale Reparaturhelfer `repair_layout.py` bewahrt den installierten Restcode, legt vor der Änderung eine Sicherung an und ersetzt atomar; die reguläre v7-Datei enthält die Reparatur bereits. Receiverbestätigung der Reparatur steht aus.

## v8 – Speicheranzeige bereits in der Zielauswahl

Jedes HDD-/USB-Ziel erhält beim Öffnen der Auswahl eine echte Kapazitätsabfrage. Rechts steht der freie Speicher, unter dem Namen die Gesamtkapazität. Im Detailbereich bleiben Pfad, Filmgröße, 512-MiB-Reserve und das Ergebnis der Platzprüfung sichtbar. Unzureichender oder nicht prüfbarer Platz sperrt die Übernahme per OK. Die Dateipfade der Auswahl bleiben unverändert. Vor und während der Übertragung prüfen die bestehenden Kontrollen den Platz erneut; die Anzeige ist eine Momentaufnahme beim Öffnen.

Sechs neue Tests decken freie/gesamte Kapazität, Film-/Reserveanzeige, zu wenig Platz, fehlgeschlagene Kapazitätsabfrage, exakte Reservegrenze, Abfragen für beide Laufwerke im wirklichen Auswahlablauf und eine reale lokale Datenträgerabfrage ab (62 Tests insgesamt). Das Bildschirmdesign wurde dem Benutzer zuerst als Vorschau mit klar gekennzeichneten Beispielwerten gezeigt. Keine Veröffentlichung auf Git und keine direkte Receiverprüfung durch die Cloud.

## v9 – zusammen fünf Filme oder einzelne Serienfolgen pro Tag

Das Limit gilt gemeinsam für alle Emby-Server und Benutzer dieser lokalen
Installation. Jede Folge zählt einzeln; ganze Serien/Staffeln werden nicht als
ein Download angeboten. Der bekannte Downloadbutton ist nun auch bei einzelnen
Folgen verfügbar. Die Anbieterfreigabe wird weiterhin vor jedem Start geprüft.

Der Zähler liegt dauerhaft unter `/etc/enigma2/embyflow-download-quota.json`,
mit Dateirechten 0600, atomarem Austausch und Dateisperre während eines Transfers.
Er enthält nur Kalendertage und Anzahlen, keine URLs, Zugangsdaten oder Filmtitel.
Die Box-Uhr bestimmt den Tag. GUI-/Receiver-Neustart, Server- und Benutzerwechsel
setzen das Limit nicht zurück. Frühere Tagesstände bleiben erhalten, auch bei
einer zurückgestellten Uhr. Ein defekter oder nicht schreibbarer Zähler sperrt
neue Downloads, statt das Limit zu umgehen.

Ein Platz wird vor dem Dateiabruf dauerhaft reserviert und bei normalem Fehler
oder Abbruch zurückgegeben. Nach einem Prozess-/Stromabsturz bleibt er vorsichtig
gezählt, weil Dateiveröffentlichung und Zähler nicht gemeinsam transaktional
gespeichert werden können. Die Reservierung zählt zum Starttag, auch über
Mitternacht hinweg. Der sechste Dateiabruf wird vor HTTP/Teildatei blockiert.

Dies ist ein lokales Clientlimit, keine serverseitige Sperre über mehrere
Receiver, Images oder neu installierte Systeme hinweg. Es wird nicht auf Git
oder im regulären RCDEV-Update veröffentlicht. `install_quota.py` ergänzt die
installierte lokale Downloadversion mit Sicherung und erhält vorhandene PGS-
Ergänzungen. `build_quota.py` erzeugt dafür einen eigenständigen Direktinstaller.

## v10 – sichtbarer Tageszaehler

Versionen, Speicherziele, Bestaetigung und Fortschritt zeigen in Cyan:
„Heute X von 5 · noch Y verfügbar“. Bei fuenf belegten Plaetzen steht
„Heute 5 von 5 · Tageslimit erreicht“ in Warnfarbe. Ein nicht lesbarer Zaehler
wird als „Tageslimit nicht prüfbar · kein Download möglich“ angezeigt, niemals
als fuenf freie Plaetze. Reservierungen laufender Downloads sind eingeschlossen.

Die Auswahlfenster aktualisieren sekündlich, das Fortschrittsfenster bei seinen
bestehenden Abfragen. Die Statusabfrage liest nur die atomar gespeicherte Datei
und wartet nicht auf die Transfer-Sperre. Tageswechsel und Rueckgabe eines
abgebrochenen Downloads werden dadurch sichtbar. Keine Zaehler-Neuanlage durch
die Anzeige; ein reines Oeffnen oder eine Installation setzt den Stand nicht
zurueck.

Die Layoutvorschau wurde vor der Umsetzung gezeigt und vom Benutzer als
„sehr gut“ bestaetigt. Beispielwerte sind keine Receiver-Messung. Der Installer
`install_quota_display.py` ergaenzt v8 oder v9 mit Quota und Anzeige, erhaelt PGS
und fertigt eine Sicherung an. `build_quota_display.py` erzeugt den einzelnen
Direktinstaller. 83 lokale Tests bestehen; Receiver-Test der neuen Anzeige steht
noch aus. Kein Git-/RCDEV-Release dieser lokalen Downloadfunktion.
# Lokale Downloadübersicht V11 (unveröffentlicht)

`library.py` zeigt fertige Videos aus `movie/EmbyFlow` auf tatsächlich
eingehängten HDD-/USB-Datenträgern. Die Suche läuft im Hintergrund; BLAU lädt
neu. Teildateien, versteckte Dateien, leere Dateien und Symlinks werden
ausgelassen. Schreibgeschützte Datenträger dürfen gelesen werden.

OK startet die Originaldatei über EmbyFlow mit Dienst 4097, vorhandenen lokalen
Fortsetzungsdaten und der bestehenden lokalen Medienanalyse. Die Übersicht
fragt weder Anbieterfreigabe noch Tageskontingent ab. Wiedergabe verbraucht
keinen Downloadplatz. Neue Downloads erhalten optional eine kleine JSON-Datei
mit Titel/Folgenangaben, ohne Zugangsdaten; vorhandene Videos werden auch ohne
diese Datei angezeigt. Externe Untertitel werden weiterhin nicht mitgeladen.

`build_library.py` erzeugt einen atomaren Zusatzinstaller mit vorheriger
Sicherung für die lokale Downloadversion. `build.py` erzeugt V11 vollständig.
Der Einstieg erscheint direkt unter Updates, ausschließlich bei aktivierter
Downloadfunktion. Nach Rückkehr aus den Einstellungen wird er aktualisiert.
Noch nicht auf der Box getestet oder veröffentlicht.
`render_preview.py --library` rendert die tatsächliche
Übersicht mit Beispieldaten für eine lokale Designprüfung.


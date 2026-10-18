# PGS-Untertitel mit 4097 – Teststand

EmbyFlow kann eingebettete PGS-Bilduntertitel direkt im Player 4097 anzeigen.
Die Ausgabe wird an das sichtbare EmbyFlow-Playerfenster gebunden. Eine von Emby
vorgegebene Untertitelspur hat Vorrang. Ohne Vorgabe bleibt vorhandener deutscher
Forced-SRT-Text auf seinem bisherigen Weg; andernfalls wird eine deutsche
erzwungene PGS-Spur automatisch eingeschaltet. Manuelles Aus und manuelle
Spurwahl haben innerhalb der Wiedergabe Vorrang.

## Bisher bestaetigt

Vu+ Duo4K SE, openATV 8.0.1 vom 16.10.2026, Enigma2
`8.0.1+git35909+fd5aeae0+fd5aeae9fd-r1`, keine ServiceApp-Umleitung:

- Deutsche vollstaendige und erzwungene PGS-Spuren manuell sichtbar.
- Spulen/Fortsetzen im manuellen PGS-Test vom Nutzer als funktionierend bestaetigt.
- Automatische PGS-Auswahl bei **2012 in 4K** vom Nutzer bestaetigt.
- **Offen:** Bei einem SD-Film fehlt der Haken. Spurliste/Codec/Forced-Metadaten
  liegen dafuer noch nicht vor. Keine Zusage fuer alle Filme, Aufloesungen oder Boxen.

Das separate Problem mit wiederholtem Tonspurwechsel/Standbild auf der DM One
ist durch diesen PGS-Test nicht als behoben bestaetigt.

## Installation zum Testen

Voraussetzung: EmbyFlow mit aktivem MediaSource-UT-Fix, zum Beispiel Build
2026101704. Der einzelne Installer **install_test.py** enthaelt beide Patches;
er benoetigt keine weiteren heruntergeladenen Dateien und keine neuen Pakete.
Nach dem Herunterladen auf die Box ausfuehren:

```sh
python3 /tmp/install_test.py
```

Der Installer sichert `plugin.py` mit Zeitstempel, prueft die Syntax, erhaelt
Dateirechte und ersetzt die Datei atomar. Lokale Ergaenzungen wie der noch
unveroeffentlichte Filmdownload bleiben erhalten. Vorhandene PGS-V1/V2-Tests
werden ergaenzt; bei bereits vollstaendig installiertem Test bleibt alles wie es
ist. Eine unpassende Basis wird vor einer Aenderung abgelehnt.

Danach GUI neu starten, den Film frisch oeffnen und keine Untertitel manuell
auswaehlen. An einer bekannten fremdsprachigen Szene pruefen. Danach Off,
manuelle Spurwahl, Spulen/Fortsetzen und bisherige SRT-Filme gegenpruefen.
Fuer SD bitte Aufloesung, Codec und Forced-Kennzeichnung der Spurliste melden.

Der urspruengliche Zweig `test/pgs-4097` enthaelt nur den manuellen Installer.
Auf `main` ist derselbe Laufzeitcode jetzt als RCDEV-Build **2026101801** im
eingebauten Updater verfuegbar. Fuer dieses Update ist kein zusaetzlicher
PGS-Installer erforderlich. Anders als der ergaenzende Einzelinstaller ersetzt
das regulaere Update die gesamte plugin.py; der lokale Filmdownload-Test ist
im RCDEV-Build nicht enthalten.

## Technische Grenzen und Pruefung

Nur eingebettete PGS im HTTP-Originalstream mit `Static=true`, aktivem 4097 und
einer vollstaendig zuordenbaren nativen Spurliste werden verwendet. Ordinal,
Codec und Sprache muessen passen. Emby-Streamindizes sind keine nativen PIDs.
Externe SUP-Dateien, fehlende/native Teilinventare und Transcoding sind nicht
abgedeckt. Ein akzeptierter Aufruf allein beweist noch keine sichtbare Ausgabe.
Die Automatik wartet hoechstens acht Versuche auf die native Spurliste, ohne
Video-/Audio-Neustart. Der SRT- und 4K-Segmentpfad bleibt bestehen.

Backend-Referenzen zum genauen Image-Quellstand:

- [PGS-Subtyp und Parser](https://github.com/openatv/enigma2/blob/fd5aeae9fd/lib/service/servicemp3.h)
- [Native PGS-Ausgabe und Spurliste](https://github.com/openatv/enigma2/blob/fd5aeae9fd/lib/service/servicemp3.cpp)
- [Untertitel-Widget am uebergebenen Elternfenster](https://github.com/openatv/enigma2/blob/fd5aeae9fd/lib/python/python_service.i)

```sh
python -m unittest discover -s tests/20261017_pgs_native -p 'test_*.py'
python -m unittest discover -s tests/20261017_subtitle_segments -p 'test_*.py'
```

`build_test.py` erzeugt den eigenstaendigen Installer reproduzierbar aus
`test_installer_template.py`, `patch.py` und `auto.py`. Die kleineren Installer
und Reparaturskripte bleiben fuer die vorherigen lokalen Testschritte enthalten.

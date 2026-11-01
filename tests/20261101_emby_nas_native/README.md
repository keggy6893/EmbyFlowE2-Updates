# Normale Emby-Auswahl: native TS-Wiedergabe vom NAS

## Bestaetigter Stand vom 01.11.2026

Auf einer VU+ Duo 4K SE mit openATV 8.0.1 und SMB-Freigabe:

- Skyfall und 2012 starten aus der normalen Emby-Bibliothek direkt vom NAS.
- Deutsch/Englisch in beide Richtungen unter einer Sekunde ohne Spinner.
- Stoppen, erneutes Oeffnen und Fortsetzen wurden bestaetigt.
- Die Diagnose bestaetigt Servicetyp 1, eine eindeutige lokale Datei und
  uebereinstimmende Dateigroesse.

Die Zuordnung nutzt keine Boxmodell-Liste und keinen festen NAS-Pfad.
Dreambox One, weitere Receiver und NFS sind fuer diesen normalen Emby-Einstieg
noch nicht auf Hardware bestaetigt. Lokale Tests decken NFS- und SMB-Pfade ab.
Das ist keine Freigabe fuer alle Boxen oder Container.

## Voraussetzungen

Eine kompatible Pluginbasis mit nativem lokalen TS- und Tonspurweg, etwa das
[EmbyLocal TEST1-Paket](../20261101_embylocal/). Der Installer kontrolliert den
Player-Einstieg und bricht bei abweichender Grundlage ab.

Das NAS muss im Receiver eingerichtet sein. Aktive CIFS/NFS/NFS4-Mounts werden
aus `/proc/mounts` gelesen. Fuer noch nicht aktive autofs-Freigaben werden auch
aktivierte Netzwerkquellen in `/etc/enigma2/embyflow_local_sources.json` genutzt.
Eine solche Quelle kann einmal unter Eigene Medien eingerichtet werden;
anschliessend wird zum Abspielen die normale Emby-Bibliothek benutzt.
Der Fix richtet keine Freigaben ein und speichert keine Zugangsdaten.

## Installation per Telnet / SSH

Als root eine Zeile ausfuehren:

```sh
wget -O /tmp/embyflow-nas-native-install.sh https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/tests/20261101_emby_nas_native/install.sh && sh /tmp/embyflow-nas-native-install.sh && reboot
```

Der Shell-Installer enthaelt seinen Python-Code. Kein separates PY/ZIP muss
heruntergeladen werden. Er prueft die komplette Python-Syntax mit dem
eingebauten `compile()` (kein optionales `py_compile` erforderlich), erstellt
und verifiziert eine datierte Sicherung und ersetzt die Datei atomar.
Die genaue Sicherungsdatei wird ausgegeben. Bereits installierte lokale
NAS-Testwege werden nicht ueberschrieben; auf der bestaetigten VU ist keine
erneute Installation erforderlich.

## Zuordnung und Grenzen

Nur entfernte Emby-Filme mit einer eindeutig gewaehlten TS-Medienquelle und
bekannter Dateigroesse kommen fuer diesen Weg infrage. Unter maximal 16
Netzwerkquellen werden der exakte Dateiname und bis zu vier abschliessende
Pfadbestandteile ausprobiert. Es findet kein rekursiver Bibliotheksscan statt.
Genau ein lokaler Treffer mit passender Dateigroesse ist erforderlich.
Gleicher Name und gleiche Groesse sind kein kryptografischer Inhaltsvergleich.

Fehlende, anders benannte, zu tief verschachtelte oder mehrdeutige Dateien
verwenden den vorherigen HTTP-Weg. MKV, Episoden und andere Wiedergabewege
werden nicht auf diesen TS-Dienst umgestellt. Die vorhandene Oberflaeche und
das eigene Untertitelmenue werden nicht ersetzt; Untertitelverhalten dieses
NAS-Weges wurde hier nicht umfassend auf Hardware geprueft.

Der Emby-Item bleibt mit seiner entfernten ID und den vorhandenen Metadaten
erhalten. Nur der Wiedergabetransport wechselt. Das bisherige Reporting wird
weiterverwendet; eine separate Pruefung aller serverseitigen Gesehen-Zaehler
steht noch aus. Nicht erreichbare NAS-Systeme koennen Dateizugriffe durch
Kernel-Mount-Timeouts verzoegern.

## Testen und Diagnose

Nach Neustart direkt ueber die normale Emby-Bibliothek starten, ohne vorher
den NAS-Ordner zu oeffnen. DE/EN/DE, Stoppen und Fortsetzen pruefen.

```sh
tail -n 12 /tmp/embyflow-emby-nas-test1.log
```

`NAS_NATIVE_START` mit `service_type: 1` bestaetigt den NAS-Weg.
`HTTP_FALLBACK` nennt den Ablehnungsgrund. Die gezielte Diagnose funktioniert
auch bei abgeschalteten allgemeinen Debuglogs und protokolliert keine
Stream-URLs oder Zugangsdaten.

## Lokale Pruefungen

```sh
python3 tests/20261101_emby_nas_native/test_runtime.py
```

16 Tests fuer NFS/SMB-Pfade, inaktive konfigurierte autofs-Quellen,
Mount-Escapes, Dateigroessen, Mehrdeutigkeit, Quellenauswahl, deaktivierte oder
ungueltige Konfiguration, HTTP-Fallback und den Installer auf der
veroeffentlichten Pluginbasis. Die bestaetigten Runtime-Funktionen sind
gegenueber dem VU-Test unveraendert; nur Installation und Dokumentation wurden
zusammengefasst. Der regulaere Updatekanal wird durch diesen Commit nicht
veraendert.

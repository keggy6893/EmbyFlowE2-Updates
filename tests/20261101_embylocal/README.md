# Vollstaendiges EmbyLocal-Testpaket fuer Anskar

**Version:** 2026-EMBYLOCAL-TEST1, Build 2026110101.
**Testziel:** Dreambox One mit openATV 8.0.1.
**Status:** lokal geprueftes Testpaket; Installation und Wiedergabe auf Anskars
Dreambox One sind noch nicht bestaetigt.

## Download und Installation

[Vollstaendiges Test-IPK herunterladen](enigma2-plugin-extensions-embyflowe2_2026.11.01-embylocal1_all.ipk)

1. IPK auf den Receiver kopieren und mit der lokalen Paketinstallation des
   Images installieren. Es ersetzt die vorhandene EmbyFlowE2-Paketinstallation.
2. Nach erfolgreicher Installation die Benutzeroberflaeche manuell neu starten.
3. EmbyFlow muss die Version **2026-EMBYLOCAL-TEST1** anzeigen.
4. Im Hauptmenue **Emby Local** oeffnen. Unter **Eigene Medien** eine Quelle
   hinzufuegen. Bereits im Image eingebundene NAS-Ordner ueber **Bereits
   eingebundene Quelle** auswaehlen. Alternativ die NAS-Suche/manuelle
   NAS-Einrichtung testen. Es werden keine NAS-Adressen vorgegeben.
5. Eine lokale TS-Aufnahme von USB oder dem eingebundenen NAS starten.
   Deutsch zu Englisch und zurueck testen; anschliessend Pause, Fortsetzen,
   Spruenge und Rueckkehr zum Fernsehen pruefen. Falls Untertitel vorhanden
   sind, das eigene EmbyFlow-Untertitelmenue pruefen.

Ein Emby-HTTP-Stream ist kein gleichwertiger Test dieses lokalen Dateiweges.
Fuer MKV und andere Nicht-TS-Dateien bleibt der vorherige Wiedergabeweg erhalten.

## Paketumfang

Das IPK enthaelt die komplette Plugin-Datei, die vorhandenen Hilfsmodule und
saemtliche fuer diesen Stand benoetigten Paketgrafiken (55 Dateien insgesamt):

- Oeffentliche Pluginbasis `EmbyFlowE2_2026102801.py` mit ihrem reparierten
  Updater; kein optionales `py_compile` fuer Syntaxpruefungen erforderlich.
- Sichtbarer Einstieg **Emby Local**, Quellenverwaltung fuer lokale und
  eingebundene Netzwerkordner, vorhandene SMB/NFS-Einrichtung und NAS-Suche.
- Quellen-Picons, Ordner-/Video-Kacheln und lokale Aufnahmeinformationen.
- Die sechs geprueften UI-Installer vom 01.11.2026 sind bereits integriert;
  sie muessen nicht separat angewendet werden.
- Native Dateiwiedergabe fuer als lokal markierte absolute `.ts`-Pfade mit
  Servicetyp 1. HTTP/HTTPS und andere Dateitypen bleiben beim bisherigen Weg.
- Vorhandene lokale TS-Untertitelbruecke mit eigenem EmbyFlow-Auswahlmenue,
  separater Untertitelflaeche und Ausschaltstatus. Der fruehere globale
  EMC-/InfoBar-Vergleichshook ist entfernt.

Kein privater kompletter Boxexport, keine NAS-/Server-/Kontodaten, kein
festgelegter Testfilm, kein persoenlicher Skyfall-Detaildialog, kein
VU-spezifischer HTTP-Tonwechselversuch und keine verworfene Quelleninfo V2.
Der allgemeine `update.json`-Kanal wird durch diese Veroeffentlichung nicht
veraendert. Dies ist keine automatische Verteilung an alle Nutzer.

## Sicherung und Kompatibilitaet

Vor dem Ersetzen wird die bestehende Plugin-Installation unter
`/etc/enigma2/embyflow-backups/embylocal-test1-<Zeit>-<PID>.tar.gz` gesichert.
Die Sicherung hat private Dateirechte. Vorhandene `emby_config.py` bleibt
Paket-Konfigurationsdatei; die Einstellungen unter `/etc/enigma2` werden nicht
mitgeliefert oder ersetzt. Ein GUI-Neustart erfolgt erst manuell nach Erfolg.

Vier vorhandene Hilfsmodule liegen nur als Bytecode vor. Ihre Python-Magic ist
`2b0e0d0a` (Python 3.13). **Das Image allein beweist keine passende Python-ABI.**
`preinst` prueft diese vor Sicherung/Installation und lehnt eine Abweichung ab.
`Architecture: all` bedeutet deshalb keine beliebige Python-Kompatibilitaet.
Die ABI-Pruefung nicht umgehen; bei Ablehnung die Meldung zurueckgeben.

## Pruefungen und Grenzen

Neun lokale Pakettests pruefen Manifest/Dateihashes, alle Grafikgruppen,
vollstaendige Python-Syntax einschliesslich Python-3.8-Syntaxniveau des Plugins,
Hilfsmodul-ABI und deren Ablehnung, fehlendes `py_compile`, lokale TS-Auswahl,
unveraenderte HTTP/HTTPS-/MKV-Weiterleitung, sichtbaren und eindeutigen
Navigationseintrag sowie Erhalt des eigenen Untertitelmenues. Der Archivinhalt
wird nach dem Packen vollstaendig verglichen; der Build ist reproduzierbar.
Die vier bestehenden UI-Testsuiten sind separat unter
[`../20261101_own_media_ui/`](../20261101_own_media_ui/) dokumentiert.

Der Shell-Syntaxlauf mit Git-Bash war in der eingeschraenkten Windows-Umgebung
durch einen Betriebssystem-Zugriffsfehler blockiert. Die Python-Abschnitte der
Installationsskripte wurden separat ausgefuehrt; die Shell-Skripte liegen zur
Pruefung als `preinst.sh` und `postinst.sh` bei. Das ist keine bestaetigte
opkg-Installation oder native Decoderpruefung auf der Dreambox.

Der Benutzer bestaetigte lokale NAS-/TS-Tonwechsel mit Skyfall und 2012 (2009)
auf Vu+ Duo 4K SE/openATV 8.0.1 in unter einer Sekunde ohne Spinner. Auf
Dreambox One sind diese Zeiten sowie NAS-Suche und Untertitel noch offen.
Sichtbar eingebrannter Text kann nicht ueber das Untertitelmenue ausgeschaltet
werden; eine fehlende TS-Untertitelspur wird durch das Paket nicht erzeugt.

## Reproduktion

Aus dem Repository-Hauptverzeichnis:

```sh
python tests/20261101_embylocal/build.py
python tests/20261101_embylocal/test_package.py
sh -n tests/20261101_embylocal/preinst.sh
sh -n tests/20261101_embylocal/postinst.sh
```

Der Build verwendet ausschliesslich die vorhandene oeffentliche Pluginbasis,
die anhand ihrer SHA256 gepruefte vollstaendige IPK vom 15.10.2026, die
veroeffentlichten sechs UI-Installer und die hier abgelegten generischen
Lokalmodule/Grafiken. `release.json` und `SHA256SUMS` beschreiben das IPK.

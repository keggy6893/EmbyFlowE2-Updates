# Eigene Medien: gepruefte Oberflaechenkorrekturen

Stand: 01.11.2026. Diese optionalen Installer sichern und korrigieren eine
vorhandene EmbyFlowE2-Installation. Es wird keine neue Komplettversion und keine
Umstellung des regulaeren Updatekanals veroeffentlicht.

## Enthalten

| Installer | Aenderung | Pruefstand |
| --- | --- | --- |
| `EmbyFlowE2_Ordnerdialog_Textfix_20261031.py` | Ordnernamen, Pfad und Hinweis oberhalb des deckenden Hintergrunds anzeigen | Syntax und Anzeigeebenen geprueft; anschliessende Ordnerauswahl am Receiver dokumentiert |
| `EmbyFlowE2_Quellendialog_Textfix_V2_20261031.py` | Pfad, Name-/Typ-Felder und Hinweis im Abschlussdialog sichtbar machen | Syntax und Anzeigeebenen geprueft; hinzugefuegte NAS-Quelle am Receiver angezeigt |
| `EmbyFlowE2_Quelleninfo_V1_20261031.py` | Rechte Spalte zeigt Informationen zur gewaehlten Quelle | Auf Vu+ angezeigt; zaehlt direkt enthaltene Videos/Unterordner, keine rekursive Bibliothekszahl |
| `EmbyFlowE2_Quellen_Picons_V1_20261031.py` | Vier Auswahl-Picons, kleinere Speicherort-Symbole und bewegliche Auswahlflaeche beim Hinzufuegen einer Quelle | Installation auf Vu+ bestaetigt; Zuordnung, XML und Fokus lokal geprueft |
| `EmbyFlowE2_Schnellinfo_Schneller_V1_20261031.py` | Gespeicherte Zahlen beim Hintergrundscan sichtbar lassen; ueberlappende Ordner nicht wiederholt durchlaufen | Im exportierten Receiverstand enthalten; lokale Zaehlergleichheit geprueft; neue Laufzeit auf Hardware noch nicht gemessen |
| `EmbyFlowE2_Kachelfokus_V1_20261101.py` | Eine einzige Auswahlflaeche statt Farbwechsel an fuenf Kachelhintergruenden | Benutzer meldete nach Installation `passt`; Auswahl/Scrollen/Aktionsfokus lokal geprueft |

Receiverbasis der Rueckmeldungen: Vu+ Duo 4K SE mit openATV 8.0.1.
Keine pauschale Hardwarebestaetigung fuer andere Boxen oder Images.

## Grenzen und bewusst nicht enthaltene Versuche

- Die Quelleninfo V2 ist **nicht enthalten**. Der Standardordner fuer Aufnahmen
  war auf dem Testreceiver leer; die Meldung mit null Dateien war korrekt.
  Die quellenuebergreifende Aufnahmeansicht und der Inhalt eines einzelnen
  Quellordners sind unterschiedliche Umfaenge. Die leere Quelle wurde entfernt.
- Keine Aenderung von Wiedergabe, Tonspur-/Untertitelwahl, NAS-Zugangsdaten,
  Freigaben, Mounts oder automatischer Netzwerksuche.
- Der HTTP-Tonwechselversuch fuer die Vu+ ist nicht Teil dieser UI-Korrekturen.
  Lokale TS-Wiedergabe vom eingebundenen NAS wurde mit Skyfall und 2012 (2009)
  vom Benutzer mit DE/EN-Wechseln unter einer Sekunde ohne Spinner bestaetigt.
  Daraus folgt keine entsprechende Zusage fuer HTTP oder andere Receiver.
- Die Quelleninfo zaehlt direkt im gewaehlten Ordner; die Schnellinfo liest die
  eingerichteten Quellen rekursiv. Die beiden Zahlen muessen nicht gleich sein.
- Die schnellere Statistik speichert `scan_ms`, `scan_files`, `scan_folders`
  und `skipped_subtrees` neben den bestehenden Zaehlern. Diese Werte beschreiben
  den letzten fertigen Scan. Gespeicherte Zahlen koennen waehrend eines neuen
  Scans den vorherigen Stand zeigen.

## Anwendung

Nur auf einer gesicherten Installation mit den erwarteten V16/V17/V18-Ansichten
anwenden. Die Installer brechen bei einem abweichenden Zielaufbau ab. Fuer die
uebliche Installation liegt die Zieldatei unter
`/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py`.

Die sechs Dateien enthalten keine Zugangsdaten und keine persoenliche
Receiver-Konfiguration. Insbesondere werden keine privaten kompletten
`plugin.py`-Exporte veroeffentlicht.

Die beiden Textfixes werden mit `python3 DATEINAME.py` angewendet. Die anderen
vier Installer pruefen ohne Parameter nur und schreiben mit `--apply`.
Bei Bedarf zuerst Quelleninfo V1 und danach die weiteren Korrekturen anwenden.
Bereits installierte Fixes nicht nochmals anwenden. Nach erfolgreicher Anwendung
die Benutzeroberflaeche bzw. den Receiver neu starten.

Jeder Installer erstellt vor der Aenderung eine zeitgestempelte, gepruefte
Sicherung neben der Zieldatei und ersetzt die Plugin-Datei atomar. Die gesamte
Python-Datei wird mit dem eingebauten `compile()` geprueft. Das optionale Modul
`py_compile`/Paket `python3-compile` ist dafuer nicht erforderlich.

Die sieben PNGs liegen zusaetzlich unter `source_picons_v1/`; der Picon-Installer
enthaelt dieselben Bilder eingebettet und benoetigt keinen separaten Download.
`make_source_picons.ps1` erzeugt die Grafiken unter Windows mit System.Drawing.

## Reproduzierbare lokale Pruefung

Aus dem Repository-Hauptverzeichnis, mit Python 3:

```sh
python tests/20261101_own_media_ui/test_source_info.py
python tests/20261101_own_media_ui/test_source_picons.py
python tests/20261101_own_media_ui/test_quickstats.py
python tests/20261101_own_media_ui/test_card_focus.py
```

Die Tests verwenden den vorhandenen oeffentlichen Stand
`EmbyFlowE2_2026102801.py`, pruefen die Installer einzeln und in Kombination und
fuehren keinen Plugin-Code auf einem Receiver aus. Sie umfassen vollstaendige
Syntax, Skin-XML, Ebenen und Positionen, unveraenderte Player-/Bestandsmethoden,
Auswahlwechsel, Cache und veraltete Worker-Ergebnisse, Zaehlergleichheit,
Abbruch/Scanlimit, Picon-Zuordnung sowie echten Dateiaustausch und exakte
Sicherungen in temporaeren Ordnern.

Im synthetischen Statistiktest blieben die Zaehler gleich und die Anzahl
besuchter Ordner sank von 17 auf 9. Das ist ein Testbestand, keine gemessene
Laufzeit oder garantierte Beschleunigung auf dem Receiver.

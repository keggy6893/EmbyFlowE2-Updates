# Build 2026102502: Sprache der aktiven Tonspur in der Infobar

Die Infobar speichert ihren Badge-Text beim Playerstart. Der bisherige
zusaetzliche Refresh beim Oeffnen war auf DreamOne beschraenkt. Auf anderen
Receivern konnte deshalb Deutsch stehen bleiben, obwohl Englisch lief.

Die Korrektur aktualisiert die Anzeige beim Oeffnen und ueber die bestehende
Aktualisierung der sichtbaren Infobar. Der aktive native Tonspurindex und dessen
Sprachkennung haben Vorrang vor den Startmetadaten. Noch nicht vollzogene
Umschaltungen werden nicht vorzeitig als neue Sprache angezeigt.

Die aktive Dienstreferenz muss zum Player gehoeren. Fehlende oder unbekannte
native Sprachinformationen behalten die bisherige Metadaten-Anzeige. Das ist
eine Grenze der Anzeige, keine Bestaetigung der tatsaechlichen Sprache in
solchen Faellen. Ein einspuriger Serverstream mit korrekten ausgewaehlten
Sprachmetadaten behaelt diese, wenn der native Dienst keine Sprache meldet.

Der Zusatz veraendert nur Anzeigeinformationen: keine Tonspurwahl, keine
Serveranfragen, kein Seek, kein Neustart und keine neue Timer-Schleife.
Die bisherige Basis 2026102501 bleibt bis auf Release-Kennung und diesen
Anzeigezusatz unveraendert, einschliesslich des lokalen Taste-9-Fixes.

17 lokale Tests: alter Nicht-DreamOne-Fehlerpfad, echte Badge- und
Sprachparsermethoden, mehrfache Wechsel, verzoegerter Wechsel, fremde Dienste,
unbekannte Sprachkennung, verborgene Infobar, Fehlerfaelle und Releaseumfang.
Keine Hardwarebestaetigung fuer die SF8008 Supreme behauptet.
Anskars HTTP-Tonspur-/Sprungproblem ist damit nicht als behoben eingestuft.

[Nachtraeglicher EMC-Quellcodevergleich und verbleibende Grenzen](EMC_REFERENCE.md).

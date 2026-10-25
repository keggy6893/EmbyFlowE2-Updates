# Build 2026102501: lokale Spruenge ueber den aktiven Dateidienst

Basis ist ausschliesslich der oeffentliche Build 2026102402 mit unveraenderter
Modal-Guard- und DreamOne-Korrektur. Hinzu kommen der bereits separat verteilte
lokale Seek-Wrapper und die neue Release-Kennung. Private Testinstallationen,
HTTP-Vergleichswerkzeuge und Untertitelversuche werden nicht hineinkopiert.

Bei `playback_info.local_file` gehen Kapitelspruenge und beide
Restart-Einstiege an `seekTo()` des aktiven eigenen Dateidienstes. Die aktive
Referenz und der Dateipfad muessen zum Player gehoeren. Unseekbare Dienste,
fremde Dateien und abgelehnte Spruenge loesen keinen Server-Neustart aus.
Pause und Tonspur werden nicht geaendert. Die native Laufzeit begrenzt das Ziel.
Server-Streams behalten ihre bisherigen Sprungpfade.

EMC dient als Referenz fuer den nativen Dateidienst; es ist keine Abhaengigkeit.
Der Nutzer bestaetigte den lokalen Skyfall-TS-Vergleich auf der Vu+ mit
Tonspurwechsel und Taste 9. Das ist keine Bestaetigung fuer DreamOne-HTTP-Streams.
Anskars Standbild beim HTTP/GStreamer-Tonspurwechsel bleibt offen.

`python3 build.py` erzeugt den Build reproduzierbar aus der SHA256-geprueften
oeffentlichen Basis. Die 15 Tests pruefen den lokalen Fehlerpfad, die nativen
Spruenge und Ablehnungen, unveraenderte Server-Pfade, den exakt bereits
veroeffentlichten Wrapper und den unveraenderten restlichen Plugin-Code.

# Trailer: No module named 'yt_dlp'

## Bestaetigter Fix

Beim Trailerstart meldete EmbyFlow auf einer VU+ Duo 4K SE mit openATV 8.0.1:
`No module named 'yt_dlp'`.

Die Installation von `python3-yt-dlp` aus dem konfigurierten Image-Feed behob
den Fehler. Installiert wurde Version **2026.10.26**; der Benutzer bestaetigte
anschliessend die funktionierende Trailerwiedergabe. Der Feed installierte
auch seine Abhaengigkeiten, darunter `python3-yt-dlp-ejs` und `quickjs`.

## Eine Zeile per Telnet / SSH als root

```sh
wget -O /tmp/embyflow-ytdlp-install.sh https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/tests/20261101_trailer_ytdlp/install.sh && sh /tmp/embyflow-ytdlp-install.sh && reboot
```

Der Shell-Installer protokolliert die installierten Pakete vor und nach der
Installation unter `/etc/enigma2/embyflow-dependency-backups/`. Er aktualisiert
die Paketlisten, installiert ausschliesslich das genannte Paket samt den vom
Feed aufgeloesten Abhaengigkeiten und prueft den Modulstart sowie die vom
vorliegenden EmbyFlow-Resolver geforderte Mindestversion 2026.08.19.
Kein allgemeines `opkg upgrade`, kein pip und kein Austausch der Plugin-Datei.
Nur bei erfolgreicher Installation und Pruefung folgt im obigen Befehl der
Neustart. Danach denselben Trailer erneut starten.

Andere Images und deren Feed-Angebot sind nicht auf Hardware bestaetigt.
Dieser Fix behebt die fehlende Abhaengigkeit; er garantiert nicht, dass jeder
Trailer bei YouTube verfuegbar oder auf jedem Receiver abspielbar ist.
Der regulaere EmbyFlow-Updatekanal bleibt unveraendert.

# HTTP-Tonspurwechsel: vorhandene native Spuren bevorzugen

Optionaler, auf einer VU+ Duo 4K SE mit openATV 8.0.1 getesteter Fix. Beim Film **6 Underground** über Emby/HTTP verursachte der bisherige Remote-Tonwechsel ein kurzes Standbild. Nach Installation wurde der Tonwechsel als funktionierend bestätigt; das Log zeigt `http-native-first` und `audio_menu` mit `native: true`.

Wenn der bestehende Player den Stream bereits als nativ nutzbar erkennt und mindestens zwei Tonspuren meldet, bleibt die vorhandene native Tonspurauswahl zuständig. Der zusätzliche Remote-Copy-Testweg wird dann übersprungen. Bei fehlenden nativen Spuren bleibt der bisherige Rückfallweg erhalten. Die vorhandene Begrenzung dieses Testwegs auf VU+ Duo 4K SE bleibt bestehen. Andere Boxen sind durch diesen Test nicht als geprüft anzusehen.

## Installation

Voraussetzung: Eine Pluginbasis mit genau einer Funktion `_efua_vu_remote_audio_trial` im erwarteten Stand. Abweichende und bereits gepatchte Versionen werden ohne Änderung abgelehnt. Der Installer ergänzt gezielt diese Funktion, prüft die vollständige Python-Syntax, erstellt und kontrolliert eine Sicherung und ersetzt die Datei atomar. Der bestehende NAS-Wiedergabeweg bleibt erhalten.

Ein Befehl im Receiver-Terminal; nach erfolgreicher Installation startet die Box neu:

```sh
wget -O /tmp/embyflow-http-native-install.sh https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/tests/20261102_http_native_audio/install.sh && sh /tmp/embyflow-http-native-install.sh && reboot
```

Auf der bereits erfolgreich getesteten Box ist keine erneute Installation nötig. Dies ist ein optionaler Installer, kein neues IPK und keine Änderung am regulären automatischen Updatekanal.

## Prüfung

```sh
python3 -m unittest discover -s tests/20261102_http_native_audio
```

Die isolierten Tests prüfen die Routingentscheidung bei zwei, einer und keiner nativen Spur, nicht nativen Sitzungen, anderen Boxen, lokalen NAS-Dateien, Service-Typen und Track-Fehlern. Dazu kommen Syntax, Änderungsumfang und Ablehnung unbekannter beziehungsweise bereits gepatchter Grundlagen. Sie ersetzen keine Wiedergabetests auf weiterer Hardware.

Zur Kontrolle nach einem Tonwechsel: `/tmp/embyflow-audio-universal.log`. Erwartet wird `http-native-first` bei mindestens zwei nativen Spuren. `HTTP_FALLBACK` im separaten NAS-Log bezeichnet den normalen HTTP-Wiedergabeweg, falls keine passende lokale TS-Datei verwendet wird.

## Rücknahme

Der Installer gibt den vollständigen Sicherungspfad aus (`plugin.py.before_http_native_….bak`). Zur Rücknahme Enigma2 stoppen, genau diese Sicherung auf `plugin.py` zurückspielen und Enigma2 wieder starten. Keine ältere Sicherung anhand eines Platzhalters auswählen: Nachträgliche andere Änderungen würden ebenfalls zurückgenommen.

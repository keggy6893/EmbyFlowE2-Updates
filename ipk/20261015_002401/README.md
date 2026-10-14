# EmbyFlowE2 – aktueller VU-Stand

Zeitstempel Europe/Berlin: 20261015_002401.
Paket: `enigma2-plugin-extensions-embyflowe2_2026.10.15-r20261015002401_all.ipk`
SHA256: `dcb75997a559b7e868b270c1dc03b4e2574f79c15b25a70a47dec7508c13acfc`

Basis ist die hochgeladene installierte VU-Sicherung. Enthält die vorhandenen Laufzeitmodule und Grafiken, sieben dauerhaft gepackte Anmeldegrafiken sowie den festen Audioverlauf. Diese festen Ressourcen liegen im Plugin, nicht mehr in /tmp. Temporäre Downloads, Caches und Diagnoseprotokolle bleiben temporär. Es wird kein /tmp-Verzeichnis gelöscht. Optionale Grafiken, die bereits in der Sicherung fehlen, wurden nicht erfunden.

Keine Zugangsdaten enthalten. Vorhandene geänderte emby_config.py wird als Konfigurationsdatei behandelt. Kein automatischer GUI-Neustart. Vier nur kompiliert vorhandene Hilfsmodule erfordern dieselbe Python-Bytecode-ABI wie die Sicherung (2b0e0d0a); preinst prüft dies vor Installation. Architektur all bedeutet hier keine freie Python-Versionskompatibilität.

Geprüft: ar/tar-Struktur, alle Nutzdaten-Prüfsummen, exakt fünf erlaubte Quelltext-Zuweisungsänderungen, Shell-/Python-Syntax, Ablehnung abweichender Python-ABI, Anmeldegrafik-Wiederherstellung und Bildintegrität. Kein Installationstest auf der VU durchgeführt. Der automatische Updatekanal wurde nicht verändert.

Reproduktion: build_ipk.py erwartet den entpackten Originalstand als EmbyFlowE2-installed neben dem Verzeichnis EmbyFlowE2-IPK-release; benötigt Python mit Pillow, tar/ar und sh. verify.py prüft das Ergebnis. Originalarchiv enthält alte Sicherungen und wird nicht veröffentlicht.

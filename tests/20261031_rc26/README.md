# EmbyFlowE2 RC26 fuer Anskar

Vollstaendige IPK mit repariertem Updater und Installationsskript, ohne Abhaengigkeit von py_compile/python3-compile. Basis ist der oeffentliche Pluginstand 2026102801; Ressourcen stammen aus der geprueften vollstaendigen IPK vom 15.10.2026.

1. enigma2-plugin-extensions-embyflowe2_2026.10.31-rc26_all.ipk ueber die lokale Paketinstallation des Receivers installieren.
2. Nach erfolgreicher Installation die Benutzeroberflaeche neu starten. EmbyFlow zeigt 2026-RC26, Build 2026103101.
3. EmbyFlow -> Updates: pruefen und 2026-RC26.1 installieren.
4. Benutzeroberflaeche erneut starten. EmbyFlow muss 2026-RC26.1, Build 2026103102 anzeigen.

RC26.1 unterscheidet sich nur durch Versions- und Buildkennung. Dieser echte Dateiaustausch dient dem Nachweis des Updatewegs. Es wird ein eigener Testkanal verwendet; das allgemeine update.json bleibt unveraendert. Kein SSH-/Telnet-Fix und kein zusaetzliches Compile-Paket erforderlich. Keine automatischen GUI-Neustarts. Bestehende Einstellungen werden nicht ersetzt, emby_config.py bleibt conffile.

Wichtig: Vier vorhandene Hilfsmodule liegen nur als Bytecode vor. Das Paket erfordert Python-Magic 2b0e0d0a (Python 3.13); preinst lehnt eine andere ABI ab. Architecture all bedeutet deshalb keine beliebige Python-Kompatibilitaet. Eine Installation auf Anskars Receiver ist noch nicht bestaetigt.

Pruefungen: Sieben RC26-Tests mit blockiertem py_compile (echter RC26-zu-RC26.1-Dateiaustausch, Hashfehler, Syntaxfehler, Rollback, keine Ausfuehrung des Updatecodes, Installationspruefung, Versionsanzeige), zehn bestehende Updater-Regressionstests, Python-3.8-Syntax des Plugins, Shell-Syntax beider Installationsskripte, Ressourcen-/Paketmanifest-Hashes, Bilddateien und Archiv-Roundtrip.

Reproduzieren: python3 tests/20261031_rc26/build_rc.py und python3 tests/20261031_rc26/test_rc.py. Das Buildskript erzeugt eine main-Downloadadresse; das veroeffentlichte Manifest wird auf einen unveraenderlichen Payload-Commit gepinnt.

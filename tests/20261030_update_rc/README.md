# EmbyFlowE2 UPDATE-RC1 / UPDATE-RC2

Vollstaendige Test-IPK fuer Anskar. Basis: oeffentlicher Stand 2026102801 und anhand SHA256 gepruefte Paketressourcen vom 15.10.2026.

1. IPK nach /tmp kopieren und ueber die lokale Paketinstallation des Images installieren.
2. Nach erfolgreicher Installation die GUI manuell neu starten. Das Plugin muss 2026-UPDATE-RC1 anzeigen.
3. Im Plugin Updates oeffnen, Update pruefen und UPDATE-RC2 installieren.
4. Nach erfolgreichem Update die GUI erneut starten. Das Plugin muss 2026-UPDATE-RC2 anzeigen.

Kein Telnet-Fix erforderlich. Installation und Updater verwenden eingebautes compile(); kein python3-compile/py_compile erforderlich. Syntaxpruefungen und SHA256-Pruefung bleiben aktiv. Keine automatische GUI-Neustartaktion. Der regulaere update.json-Kanal bleibt unveraendert; diese RCs verwenden ausschliesslich das hier liegende Testmanifest.

Das Paket enthaelt vier vorhandene Bytecode-Hilfsmodule der bisherigen VU-Basis (Python-Magic 2b0e0d0a). preinst lehnt eine abweichende Python-ABI vor Installation ab. Architecture all bedeutet keine beliebige Python-Kompatibilitaet. Vorhandene emby_config.py bleibt conffile. Keine Receiver-Zugangsdaten oder privaten lokalen Erweiterungen enthalten.

Lokal geprueft: sieben Regressionstests, tatsaechlicher RC1-zu-RC2-Dateiaustausch bei gesperrtem py_compile, defekte Syntax, falscher Hash, Rollback, Nichtausfuehrung heruntergeladenen Codes, Installations-Syntaxpruefung, fuenf erhaltene Updater-Pruefungen, Python-3.8-Syntax, Paket-/Ressourcen-Hashes und Archiv-Roundtrip. Receiverinstallation noch nicht getestet. Ein Shell-Syntaxlauf konnte unter der eingeschraenkten Windows-Umgebung nicht ausgefuehrt werden.

Reproduktion im Repository: python tests/20261030_update_rc/build_rc.py, danach python tests/20261030_update_rc/test_rc.py. Das Buildskript erzeugt zunaechst ein Testmanifest mit main-Download; die veroeffentlichte Manifest-Datei pinnt RC2 auf einen unveraenderlichen Commit bei gleicher SHA256.

"""Build a source-only repair add-on; never replace a user's whole plugin."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026.10.25-r1'
PACKAGE = 'enigma2-plugin-extensions-embyflowe2-updater-repair'
DIRECTORY = ROOT / 'ipk' / 'updater-repair-20261025-r1'
INSTALL_DIR = 'usr/share/embyflow-updater-repair/'
README = '''# EmbyFlowE2: einmalige Updater-Reparatur

Dieses Zusatzpaket behebt "No module named 'py_compile'" im bereits
installierten EmbyFlowE2. Es ersetzt nicht das vollstaendige Plugin und
installiert keine Python-Bytecode-Helfer oder Zugangsdaten.

Installation ohne Telnet:

1. Das IPK von GitHub herunterladen und per Dateitransfer nach /tmp auf die Box kopieren.
2. In der Softwareverwaltung des Images "Lokale Erweiterungen installieren"
   oeffnen, /tmp waehlen und dieses IPK installieren. Menunamen koennen abweichen.
3. Nach erfolgreicher Installation die GUI manuell neu starten.
4. EmbyFlowE2 > Updates > Update pruefen verwenden.

Das Paket legt vor der Aenderung eine Sicherung neben plugin.py an:
plugin.py.vor-updater-only-<Datum-Uhrzeit>-<Prozessnummer>.
Es aendert ausschliesslich den erkannten alten Updater. Alle fuenf
Syntaxpruefungen bleiben aktiv und verwenden das eingebaute compile().
Einstellungen, Zugangsdaten, Suche und Wiedergabecode werden nicht ersetzt.
Ein bereits reparierter Updater bleibt unveraendert.

Bei unbekanntem Updater oder einem Fehler meldet die Paketinstallation einen
Fehler. Dann nicht von einer erfolgreichen Reparatur ausgehen; Ausgabe sichern.
Das Paket stoppt oder startet weder Enigma2 noch den Receiver. Es braucht
keinen Netzwerkzugriff und kein python3-compile. Nach dem GUI-Neustart laeuft
der korrigierte Updater. Deinstallation dieses Zusatzpakets entfernt nur die
Reparaturdateien und macht die Korrektur im Plugin nicht rueckgaengig.

Ein spaeteres regulaeres Plugin-Update ersetzt die ganze plugin.py durch den
veroeffentlichten Stand. Private lokale Erweiterungen sind darin nicht
automatisch enthalten.

Lokal mit echten alten Plugin-Quellen und simuliertem Paketablauf geprueft.
Eine Installation auf einem Receiver wurde hier nicht durchgefuehrt.
'''
POSTINST = b'''#!/bin/sh
set -eu
# Offline image construction defers configuration to the receiver.
if [ -n "${D:-}${IPKG_INSTROOT:-}" ]; then exit 0; fi
python3 /usr/share/embyflow-updater-repair/repair.py --no-restart
echo 'EmbyFlowE2: Updater geprueft/repariert. Bitte GUI jetzt manuell neu starten.'
'''


def build():
    spec = importlib.util.spec_from_file_location('ipk_common', ROOT / 'ipk/build_current.py')
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    source = (ROOT / 'tools/repair-updater-only-20261025.py').read_bytes()
    compile(source, 'repair.py', 'exec')
    control = {
        'control': (
            'Package: ' + PACKAGE + '\nVersion: ' + VERSION + '\n'
            'Section: extra\nPriority: optional\nArchitecture: all\n'
            'Maintainer: EmbyFlowE2\nDepends: enigma2, python3-core\n'
            'Description: Repair installed EmbyFlowE2 updater without py_compile\n'
            ' Source-only add-on; preserves existing plugin features and settings.\n'
            ' No automatic GUI restart. Restart GUI manually after installation.\n'
        ).encode(),
        'postinst': POSTINST,
    }
    data = {INSTALL_DIR + 'repair.py': source,
            INSTALL_DIR + 'README.md': README.encode()}
    subprocess.run(['sh', '-n'], input=POSTINST, check=True)
    DIRECTORY.mkdir(exist_ok=True)
    parts = {'debian-binary': b'2.0\n',
             'control.tar.gz': common.packed(control, ('postinst',), 1792886400),
             'data.tar.gz': common.packed(data, (), 1792886400)}
    filename = PACKAGE + '_' + VERSION + '_all.ipk'
    ipk = DIRECTORY / filename
    for name, content in parts.items():
        (DIRECTORY / name).write_bytes(content)
    try:
        # Rebuild from scratch so a stale ar member cannot survive.
        if ipk.exists():
            ipk.unlink()
        subprocess.run(['ar', 'rcsD', filename, *parts], cwd=DIRECTORY, check=True)
        assert common.read_part(ipk, 'data') == data
        assert common.read_part(ipk, 'control') == control
        assert subprocess.check_output(['ar', 't', str(ipk)]).decode().split() == list(parts)
    finally:
        for name in parts:
            (DIRECTORY / name).unlink()
    metadata = dict(package=PACKAGE, version=VERSION, filename=filename,
                    sha256=hashlib.sha256(ipk.read_bytes()).hexdigest(),
                    source_sha256=hashlib.sha256(source).hexdigest(),
                    size=ipk.stat().st_size, automatic_gui_restart=False,
                    replaces_full_plugin=False, bytecode_files=0)
    (DIRECTORY / 'release.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (DIRECTORY / 'SHA256SUMS').write_text(metadata['sha256'] + '  ' + filename + '\n')
    (DIRECTORY / 'README.md').write_text(README)
    return ipk


if __name__ == '__main__':
    print(build())

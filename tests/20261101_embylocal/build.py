"""Reproducible complete EmbyLocal test package from the public plugin and resources."""
from pathlib import Path
import ast
import base64
import calendar
import gzip
import hashlib
import importlib.util
import io
import json
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIXES = ROOT / 'tests/20261101_own_media_ui'
PREFIX = 'usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/'
VERSION = '2026-EMBYLOCAL-TEST1'
BUILD = 2026110101
FILENAME = 'enigma2-plugin-extensions-embyflowe2_2026.11.01-embylocal1_all.ipk'
STAMP = calendar.timegm((2026, 11, 1, 4, 0, 0))
BASE = ROOT / 'ipk/20261015_002401/enigma2-plugin-extensions-embyflowe2_2026.10.15-r20261015002401_all.ipk'


def ar_parts(raw):
    assert raw.startswith(b'!<arch>\n')
    result = {}; position = 8
    while position < len(raw):
        header = raw[position:position + 60]
        size = int(header[48:58]); name = header[:16].decode().strip().rstrip('/')
        result[name] = raw[position + 60:position + 60 + size]
        position += 60 + size + size % 2
    return result


def unpack(raw):
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        return {entry.name.removeprefix('./'): archive.extractfile(entry).read()
                for entry in archive if entry.isfile()}


def pack(files, executable=()):
    result = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=result, mtime=STAMP) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.GNU_FORMAT) as archive:
            for name, content in sorted(files.items()):
                entry = tarfile.TarInfo('./' + name)
                entry.size = len(content); entry.mode = 0o755 if name in executable else 0o644
                entry.mtime = STAMP; entry.uname = entry.gname = 'root'
                archive.addfile(entry, io.BytesIO(content))
    return result.getvalue()


def ar(files):
    result = b'!<arch>\n'
    for name, content in files.items():
        header = f'{name+"/":<16}{STAMP:<12}{0:<6}{0:<6}{100644:<8}{len(content):<10}`\n'.encode()
        assert len(header) == 60
        result += header + content + (b'\n' if len(content) % 2 else b'')
    return result


def installer(name):
    spec = importlib.util.spec_from_file_location(name, FIXES / name)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def build():
    raw = BASE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'dcb75997a559b7e868b270c1dc03b4e2574f79c15b25a70a47dec7508c13acfc'
    parts = ar_parts(raw); data = unpack(parts['data.tar.gz']); control = unpack(parts['control.tar.gz'])
    old_manifest = json.loads(data.pop(PREFIX + 'PACKAGE-MANIFEST.json'))
    assert set(old_manifest['files']) == set(data)
    assert all(hashlib.sha256(data[n]).hexdigest() == h for n, h in old_manifest['files'].items())
    source = (ROOT / 'EmbyFlowE2_2026102801.py').read_text(encoding='utf-8')
    assert hashlib.sha256(source.encode()).hexdigest() == 'a99ae4ce9756abf9a32c826bba23d44406b409bf28caf96bfe4e37a8cab06d7e'
    replacements = {
        "PLUGIN_VERSION = '2026-RCDEV-TEST-20261028-DIRECT-AUDIO'": "PLUGIN_VERSION = '" + VERSION + "'",
        "PLUGIN_BUILD_DATE = '28.10.2026'": "PLUGIN_BUILD_DATE = '01.11.2026'",
        'PLUGIN_UPDATE_BUILD = 2026102801': 'PLUGIN_UPDATE_BUILD = ' + str(BUILD),
        '_EMBYFLOW_V9_ASSET_DIR = "/tmp/embyflow_v9_assets"': '_EMBYFLOW_V9_ASSET_DIR = os.path.join(PLUGIN_PATH, "assets", "login")',
        '_EMBYFLOW_AUDIO_GRADIENT_CACHE = "/tmp/embyflow_audio_backdrops/gradient_overlay_v1.png"': '_EMBYFLOW_AUDIO_GRADIENT_CACHE = os.path.join(PLUGIN_PATH, "assets", "audio_gradient_overlay_v1.png")',
    }
    for before, after in replacements.items():
        assert source.count(before) == 1, before
        source = source.replace(before, after, 1)
    source, count = re.subn(r'^PLUGIN_UPDATE_CHANGELOG = .*$',
        "PLUGIN_UPDATE_CHANGELOG = 'Emby Local Test: USB- und NAS-Quellen, Quelleninformationen und Picons.|Lokale TS-Dateien verwenden den nativen Dateidienst; der HTTP-Wiedergabeweg bleibt erhalten.|Schnellinfo und Kachelauswahl korrigiert. Dreambox One mit openATV 8.0.1 ist das Testziel; die Hardwarebestaetigung steht aus.'",
        source, count=1, flags=re.MULTILINE)
    assert count == 1
    for name in ('local_nav.inc.py', 'source_picons.inc.py', 'folder_grid.inc.py', 'recording_info.inc.py', 'native_local_ts.inc.py'):
        source = source.rstrip() + '\n\n' + (OUT / name).read_text(encoding='utf-8').rstrip() + '\n'
    names = ('EmbyFlowE2_Ordnerdialog_Textfix_20261031.py',
             'EmbyFlowE2_Quellendialog_Textfix_V2_20261031.py',
             'EmbyFlowE2_Quelleninfo_V1_20261031.py',
             'EmbyFlowE2_Quellen_Picons_V1_20261031.py',
             'EmbyFlowE2_Schnellinfo_Schneller_V1_20261031.py',
             'EmbyFlowE2_Kachelfokus_V1_20261101.py')
    for name in names:
        source = installer(name).transform(source)
    assert 'import py_compile' not in source
    assert '_efua_vu_remote_audio_trial' not in source
    assert '_eftsh_install_comparison' not in source
    compile(source, 'plugin.py', 'exec'); ast.parse(source, feature_version=(3, 8))
    data[PREFIX + 'plugin.py'] = source.encode('utf-8')
    for path in sorted((OUT / 'assets').rglob('*.png')):
        data[PREFIX + 'assets/' + path.relative_to(OUT / 'assets').as_posix()] = path.read_bytes()
    picons = installer('EmbyFlowE2_Quellen_Picons_V1_20261031.py')
    for name, encoded in picons.ASSETS.items():
        data[PREFIX + 'assets/source_setup_v1/' + name] = base64.b64decode(encoded, validate=True)
    # The legacy chooser also uses this directory; no image is left dependent on a VU export.
    aliases = {'folder': 'folder_grid', 'drive': 'drive', 'nas': 'network', 'globe_v18': 'network',
               'tv': 'recordings', 'doc': 'documentary', 'kids': 'movies', 'gear': 'all'}
    for target, origin in aliases.items():
        path = 'assets/local_folder_grid_20261026/folder.png' if origin == 'folder_grid' else 'assets/local_source_picons_20261026/' + origin + '.png'
        data[PREFIX + 'assets/local_sources_v16/' + target + '.png'] = data[PREFIX + path]
    control['control'] = (f'Package: enigma2-plugin-extensions-embyflowe2\nVersion: 2026.11.01-embylocal1\nSection: extra\nPriority: optional\nArchitecture: all\nMaintainer: EmbyFlowE2\nDepends: enigma2, python3-core, python3-requests, python3-pillow\nDescription: Complete EmbyLocal TEST1 for openATV 8.0.1\n Local NAS/USB source UI and native TS playback; Python helper ABI checked.\n').encode()
    control['preinst'] = b'''#!/bin/sh
set -eu
if [ -n "${D:-}" ]; then exit 0; fi
python3 - <<'PYCHECK'
import importlib.util, sys
if importlib.util.MAGIC_NUMBER != bytes.fromhex("2b0e0d0a"):
    sys.stderr.write("EmbyLocal TEST1: Python-ABI stimmt nicht mit den enthaltenen Hilfsmodulen ueberein. Installation abgebrochen.\\n")
    sys.exit(1)
PYCHECK
plugin=/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2
if [ -d "$plugin" ]; then
    umask 077
    destination=/etc/enigma2/embyflow-backups
    mkdir -p "$destination"
    chmod 700 "$destination"
    backup="$destination/embylocal-test1-$(date +%Y%m%d-%H%M%S)-$$.tar.gz"
    tar -czf "$backup" -C "$plugin" .
    echo "EmbyLocal-Sicherung: $backup"
fi
'''
    control['postinst'] = b'''#!/bin/sh
set -eu
if [ -n "${D:-}" ]; then exit 0; fi
plugin=/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2
python3 - "$plugin/plugin.py" <<'PYSYNTAX'
import sys
with open(sys.argv[1], "rb") as handle:
    compile(handle.read(), sys.argv[1], "exec", dont_inherit=True)
PYSYNTAX
rm -f "$plugin/plugin.pyc" "$plugin/plugin.py.pyc"
if [ -d "$plugin/__pycache__" ]; then
    find "$plugin/__pycache__" -maxdepth 1 -type f -name 'plugin.*.pyc' -exec rm -f {} \\;
fi
echo 'EmbyLocal TEST1 installiert. Benutzeroberflaeche jetzt manuell neu starten.'
'''
    # Existing account settings remain conffiles; never include /etc receiver settings.
    assert PREFIX + 'emby_config.py' in control['conffiles'].decode()
    data[PREFIX + 'PACKAGE-MANIFEST.json'] = (json.dumps(dict(build=BUILD, version=VERSION,
        python_magic='2b0e0d0a', files={n: hashlib.sha256(v).hexdigest() for n, v in sorted(data.items())}), indent=2) + '\n').encode()
    members = {'debian-binary': b'2.0\n', 'control.tar.gz': pack(control, ('preinst', 'postinst')), 'data.tar.gz': pack(data)}
    result = ar(members)
    assert ar_parts(result) == members
    assert unpack(members['data.tar.gz']) == data
    (OUT / FILENAME).write_bytes(result)
    (OUT / 'plugin_TEST1.py').write_bytes(data[PREFIX + 'plugin.py'])
    for name in ('preinst', 'postinst'):
        (OUT / (name + '.sh')).write_bytes(control[name])
    meta = dict(filename=FILENAME, sha256=hashlib.sha256(result).hexdigest(), size=len(result),
                version=VERSION, build=BUILD, python_magic='2b0e0d0a', files=len(data),
                hardware_target='Dreambox One / openATV 8.0.1', hardware_confirmed=False)
    (OUT / 'release.json').write_bytes((json.dumps(meta, indent=2) + '\n').encode())
    (OUT / 'SHA256SUMS').write_bytes((meta['sha256'] + '  ' + FILENAME + '\n').encode())
    return meta


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))

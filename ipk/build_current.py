"""Repackage the verified VU resources with the exact current public release."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import ast
import gzip
import hashlib
import io
import json
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'ipk/20261015_002401'
PREFIX = 'usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/'


def read_part(ipk, part):
    raw = subprocess.check_output(['ar', 'p', str(ipk), part + '.tar.gz'])
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for item in archive:
            if not item.isfile() or item.name.startswith('/') or '..' in Path(item.name).parts:
                raise ValueError('Unexpected archive member')
            result[item.name.removeprefix('./')] = archive.extractfile(item).read()
    return result


def packed(files, scripts, epoch):
    output = io.BytesIO()
    with gzip.GzipFile(filename='', fileobj=output, mode='wb', mtime=epoch) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.GNU_FORMAT) as archive:
            for name, data in sorted(files.items()):
                item = tarfile.TarInfo('./' + name)
                item.size = len(data)
                item.mode = 0o755 if name in scripts else 0o644
                item.uid = item.gid = 0
                item.uname = item.gname = 'root'
                item.mtime = epoch
                archive.addfile(item, io.BytesIO(data))
    return output.getvalue()


def build():
    now = datetime.now(ZoneInfo('Europe/Berlin'))
    stamp = now.strftime('%Y%m%d_%H%M%S')
    version = now.strftime('%Y.%m.%d-r%Y%m%d%H%M%S')
    directory = ROOT / 'ipk' / stamp
    directory.mkdir()
    baseline = json.loads((BASE / 'release.json').read_text())
    old_ipk = BASE / baseline['filename']
    if hashlib.sha256(old_ipk.read_bytes()).hexdigest() != baseline['sha256']:
        raise ValueError('Baseline IPK checksum mismatch')
    data = read_part(old_ipk, 'data')
    control = read_part(old_ipk, 'control')
    old_manifest = json.loads(data.pop(PREFIX + 'PACKAGE-MANIFEST.json'))
    assert set(old_manifest['files']) == set(data)
    for name, expected in old_manifest['files'].items():
        assert hashlib.sha256(data[name]).hexdigest() == expected
    assert all(name.startswith(PREFIX) for name in data)
    assert not any(name.endswith(('.log', '.ini', '.bak')) or '/__pycache__/' in name for name in data)
    manifest = json.loads((ROOT / 'update.json').read_text())
    original = (ROOT / ('EmbyFlowE2_%d.py' % manifest['build'])).read_bytes()
    assert hashlib.sha256(original).hexdigest() == manifest['sha256']
    source = original.decode()
    for old, new in {
        '_EMBYFLOW_V9_ASSET_DIR = "/tmp/embyflow_v9_assets"': '_EMBYFLOW_V9_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "login")',
        '_EMBYFLOW_AUDIO_GRADIENT_CACHE = "/tmp/embyflow_audio_backdrops/gradient_overlay_v1.png"': '_EMBYFLOW_AUDIO_GRADIENT_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "audio_gradient_overlay_v1.png")',
    }.items():
        assert source.count(old) == 1
        source = source.replace(old, new, 1)
    compile(source, 'plugin.py', 'exec')
    data[PREFIX + 'plugin.py'] = source.encode()
    config = ast.parse(data[PREFIX + 'emby_config.py'])
    defaults = {node.targets[0].id: ast.literal_eval(node.value) for node in config.body
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    assert all(defaults[key] == '' for key in ('EMBY_SERVER', 'EMBY_USERNAME', 'EMBY_PASSWORD'))
    helpers = ['compat.pyc', 'stream_strategy.pyc', 'skin_utils.pyc', 'item_types.pyc']
    assert all(data[PREFIX + name][:4].hex() == baseline['python_magic'] for name in helpers)
    control['control'] = (f'Package: enigma2-plugin-extensions-embyflowe2\nVersion: {version}\n'
        'Section: extra\nPriority: optional\nArchitecture: all\nMaintainer: EmbyFlowE2\n'
        'Depends: enigma2, python3-core, python3-requests, python3-pillow\n'
        f'Description: EmbyFlowE2 build {manifest["build"]}, clean VU package\n'
        f' Timestamp Europe/Berlin: {now.isoformat(timespec="seconds")}\n'
        f' Python helper ABI {baseline["python_magic"]}; checked before installation.\n').encode()
    # Keep the existing ABI guard and no-restart postinst. No settings are exported.
    assert baseline['python_magic'].encode() in control['preinst']
    for name in ('preinst', 'postinst'):
        subprocess.run(['sh', '-n'], input=control[name], check=True)
    package_manifest = dict(timestamp=now.isoformat(timespec='seconds'), build=manifest['build'],
                            source_sha256=manifest['sha256'], python_magic=baseline['python_magic'],
                            files={name: hashlib.sha256(raw).hexdigest() for name, raw in data.items()})
    data[PREFIX + 'PACKAGE-MANIFEST.json'] = (json.dumps(package_manifest, indent=2) + '\n').encode()
    parts = {'debian-binary': b'2.0\n', 'control.tar.gz': packed(control, ('preinst', 'postinst'), int(now.timestamp())),
             'data.tar.gz': packed(data, (), int(now.timestamp()))}
    for name, raw in parts.items():
        (directory / name).write_bytes(raw)
    filename = f'enigma2-plugin-extensions-embyflowe2_{version}_all.ipk'
    ipk = directory / filename
    subprocess.run(['ar', 'rcsD', filename, *parts], cwd=directory, check=True)
    # Verify the actual distributable, not only the staging files.
    assert read_part(ipk, 'data') == data
    assert read_part(ipk, 'control') == control
    assert subprocess.check_output(['ar', 't', str(ipk)]).decode().split() == list(parts)
    from PIL import Image
    for name, raw in data.items():
        if name.endswith(('.png', '.jpg', '.jpeg')):
            Image.open(io.BytesIO(raw)).verify()
    result = dict(timestamp=stamp, timestamp_timezone='Europe/Berlin', build=manifest['build'],
                  version=version, filename=filename, sha256=hashlib.sha256(ipk.read_bytes()).hexdigest(),
                  size=ipk.stat().st_size, python_magic=baseline['python_magic'], file_count=len(data))
    (directory / 'release.json').write_text(json.dumps(result, indent=2) + '\n')
    (directory / 'SHA256SUMS').write_text(result['sha256'] + '  ' + filename + '\n')
    (directory / 'README.md').write_text(
        '# EmbyFlowE2 clean IPK\n\nBuild %d. Timestamp Europe/Berlin: %s.\n\n' % (manifest['build'], stamp) +
        'Contains plugin, blank legacy account defaults and packaged runtime resources. '
        'No receiver accounts, login INI, settings, cache, logs, downloads or bot credentials. '
        'The existing package treats emby_config.py as a conffile; installed settings are not reset. '
        'No automatic GUI restart.\n\nFour helper modules are available only as bytecode from the verified VU basis. '
        'The pre-install guard requires Python ABI 2b0e0d0a and rejects a mismatch before installation. '
        'Architecture all does not imply compatibility with all Python versions. '
        'Receiver installation has not been tested.\n\nVerified: original package/resource hashes, public release hash, '
        'exactly two resource-path changes, syntax, archive round-trip, empty account defaults and image integrity.\n')
    for name in parts:
        (directory / name).unlink()
    print(json.dumps(result, indent=2))
    return ipk


if __name__ == '__main__':
    build()

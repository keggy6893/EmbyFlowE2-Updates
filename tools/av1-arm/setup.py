"""Rootless Debian ARM cross toolchain. No receiver/system packages modified."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(os.environ.get('EMBYFLOW_ARM_BUILD_ROOT', '/workspace/local-artifacts/av1-arm-build'))
SOURCES = {
    'ffmpeg': ('https://github.com/FFmpeg/FFmpeg.git', '38b88335f99e76ed89ff3c93f877fdefce736c13'),
    'dav1d': ('https://github.com/videolan/dav1d.git', '54706fc6bc0cdecab7e9593974a4039cc038fca7'),
    'x264': ('https://github.com/mirror/x264.git', '31e19f92f00c7003fa115047ce50978bc98c3a0d'),
}


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    for path in ('apt/lists/partial', 'apt/cache', 'debs', 'toolchain', 'src'):
        (ROOT / path).mkdir(parents=True, exist_ok=True)
    options = ['-o', 'Dir::State::lists=' + str(ROOT / 'apt/lists'),
               '-o', 'Dir::Cache=' + str(ROOT / 'apt/cache'), '-o', 'Debug::NoLocking=1']
    run(['/usr/bin/apt-get'] + options + ['update'])
    result = run(['/usr/bin/apt-get'] + options + ['--no-install-recommends', '-s', 'install',
              'gcc-arm-linux-gnueabihf', 'libc6-dev-armhf-cross', 'qemu-user'], capture_output=True, text=True)
    packages = [line.split()[1] for line in result.stdout.splitlines() if line.startswith('Inst ')]
    # APT validates repository signatures and package hashes on download.
    if packages:
        run(['/usr/bin/apt-get'] + options + ['download'] + packages, cwd=ROOT / 'debs')
    for package in (ROOT / 'debs').glob('*.deb'):
        run(['dpkg-deb', '-x', str(package), str(ROOT / 'toolchain')])
    run([sys.executable, '-m', 'venv', str(ROOT / 'tools')])
    run([str(ROOT / 'tools/bin/pip'), 'install', 'meson==1.9.1', 'ninja==1.13.0'])
    for name, (url, commit) in SOURCES.items():
        target = ROOT / 'src' / name
        if not (target / '.git').exists():
            run(['git', 'init', str(target)])
            run(['git', '-C', str(target), 'remote', 'add', 'origin', url])
            run(['git', '-C', str(target), 'fetch', '--depth', '1', 'origin', commit])
            run(['git', '-C', str(target), 'checkout', '--detach', commit])
        actual = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != commit:
            raise RuntimeError('Existing source checkout differs: ' + name)
    manifest = {'sources': SOURCES, 'debian_packages': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (ROOT / 'debs').glob('*.deb')}}
    (ROOT / 'setup-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('ARM cross toolchain ready at', ROOT)


if __name__ == '__main__':
    main()

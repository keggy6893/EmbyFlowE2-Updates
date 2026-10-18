"""Run the PowerShell workflow with real AV1 conversion and mocked SSH/SCP."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PWSH = os.environ.get('EMBYFLOW_TEST_PWSH') or shutil.which('pwsh')


@unittest.skipUnless(PWSH, 'PowerShell required for the Windows script harness')
class PcOfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.original = Path(cls.fixture.name) / 'original.mkv'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=96x64:r=10',
            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
            '-f', 'lavfi', '-i', 'sine=frequency=880:sample_rate=48000', '-t', '3',
            '-map', '0:v', '-map', '1:a', '-map', '2:a', '-c:v', 'libaom-av1', '-cpu-used', '8',
            '-c:a', 'aac', '-metadata:s:a:0', 'language=eng', '-metadata:s:a:1', 'language=deu',
            str(cls.original)], check=True, timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote box'
        self.remote.mkdir()
        self.movie = self.remote / 'Die W\u00fcstenratten_1731728_mediasource_1731728.mkv'
        shutil.copyfile(self.original, self.movie)
        self.work = self.root / 'PC working folder'
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.tools = self.root / 'ffmpeg'
        self.tools.mkdir()
        (self.tools / 'ffprobe.exe').symlink_to(shutil.which('ffprobe'))
        wrapper = self.tools / 'ffmpeg.exe'
        wrapper.write_text('''#!/usr/bin/env python3
import json, os, subprocess, sys
with open(os.environ['PC_TEST_ARGUMENTS'], 'w') as out:
    json.dump(sys.argv[1:], out)
if os.environ.get('PC_TEST_FAIL'):
    sys.exit(1)
sys.exit(subprocess.call([%r] + sys.argv[1:]))
''' % shutil.which('ffmpeg'))
        wrapper.chmod(0o755)
        ssh = self.bin / 'ssh'
        ssh.write_text('''#!/usr/bin/env python3
import base64, json, os, sys
from pathlib import Path
code = sys.stdin.read().lstrip('\\ufeff')
if code.startswith('record64 = '):
    exec(compile(code, '<remote-publish>', 'exec'))
else:
    path = Path(os.environ['PC_TEST_SOURCE'])
    destination = path.with_suffix('').as_posix() + '_H264_AAC.mp4'
    if os.path.lexists(destination):
        sys.exit(1)
    print(json.dumps({'path64':base64.b64encode(str(path).encode()).decode(),
                      'size':path.stat().st_size, 'free':20*1024**3}))
''')
        ssh.chmod(0o755)
        scp = self.bin / 'scp'
        scp.write_text('''#!/usr/bin/env python3
import shutil, sys
args = sys.argv[1:]
source, target = args[-2:]
def path(value):
    return value.split(':',1)[1].strip("'") if value.startswith('root@') else value
shutil.copyfile(path(source), path(target))
''')
        scp.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
            PC_TEST_SOURCE=str(self.movie), PC_TEST_ARGUMENTS=str(self.root / 'arguments.json'))

    def run_script(self):
        return subprocess.run([PWSH, '-NoProfile', '-File', str(ROOT / 'convert-wuestenratten-pc.ps1'),
            '-WorkDirectory', str(self.work), '-FfmpegDirectory', str(self.tools)],
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)

    def test_real_av1_pc_conversion_and_verified_return_copy(self):
        before = hashlib.sha256(self.movie.read_bytes()).hexdigest()
        result = self.run_script()
        self.assertEqual(0, result.returncode, (result.stdout + result.stderr).decode())
        target = self.movie.with_suffix('').as_posix() + '_H264_AAC.mp4'
        self.assertEqual((self.work / 'Wuestenratten-H264-AAC.mp4').read_bytes(), Path(target).read_bytes())
        self.assertEqual(before, hashlib.sha256(self.movie.read_bytes()).hexdigest())
        args = json.loads((self.root / 'arguments.json').read_text())
        self.assertIn('0:2', args)  # German second audio track, not English first.
        self.assertFalse(list(self.remote.glob('*.part')))
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', target]))
        self.assertEqual(['h264', 'aac'], [s['codec_name'] for s in probe['streams']])
        self.assertIn(b'FERTIG', result.stdout)

    def test_failed_encoder_does_not_upload_or_modify_original(self):
        self.env['PC_TEST_FAIL'] = '1'
        before = self.movie.read_bytes()
        result = self.run_script()
        self.assertEqual(1, result.returncode)
        self.assertEqual(before, self.movie.read_bytes())
        self.assertEqual([self.movie], list(self.remote.iterdir()))

    def test_existing_pc_movie_is_not_overwritten(self):
        self.work.mkdir()
        existing = self.work / 'Wuestenratten-original.mkv'
        existing.write_bytes(b'personal existing file')
        result = self.run_script()
        self.assertEqual(1, result.returncode)
        self.assertEqual(b'personal existing file', existing.read_bytes())
        self.assertFalse((self.root / 'arguments.json').exists())


if __name__ == '__main__':
    unittest.main()

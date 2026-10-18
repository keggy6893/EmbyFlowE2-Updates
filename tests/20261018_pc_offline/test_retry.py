"""Run copy-only recovery with real hashing and simulated receiver transport."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PWSH = os.environ.get('EMBYFLOW_TEST_PWSH') or shutil.which('pwsh')


@unittest.skipUnless(PWSH, 'PowerShell required')
class CopyRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote'
        self.remote.mkdir()
        self.original = self.remote / 'Die W\u00fcstenratten_1731728_mediasource_1731728.mkv'
        self.original.write_bytes(b'AV1 original unchanged')
        self.work = self.root / 'PC working directory'
        self.work.mkdir()
        self.movie = self.work / 'Wuestenratten-H264-AAC.mp4'
        self.movie.write_bytes(b'completed movie bytes' * 1000)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        ssh = self.bin / 'ssh'
        ssh.write_text('''#!/usr/bin/env python3
import ast, base64, contextlib, glob, io, json, os, sys
from pathlib import Path
from unittest.mock import patch
code = sys.stdin.read().lstrip('\\ufeff')
remote = Path(os.environ['RETRY_TEST_REMOTE'])
if code.startswith('record64 = '):
    first, body = code.split('\\n', 1)
    record = json.loads(base64.b64decode(ast.literal_eval(first.split('=',1)[1].strip())))
    stage = base64.b64decode(record['stage64']).decode()
    record['stage64'] = base64.b64encode(str(remote / Path(stage).name).encode()).decode()
    value = base64.b64encode(json.dumps(record).encode()).decode()
    exec(compile(body,'<publish>','exec'), {'record64':value})
else:
    captured = io.StringIO()
    with patch('glob.glob',return_value=[os.environ['RETRY_TEST_SOURCE']]), \\
         patch('os.path.ismount',return_value=True), contextlib.redirect_stdout(captured):
        exec(compile(code,'<discovery>','exec'))
    value = json.loads(captured.getvalue())
    stage = base64.b64decode(value['stage64']).decode()
    value['stage64'] = base64.b64encode(('/media/usb/movie/EmbyFlow/' + Path(stage).name).encode()).decode()
    print(json.dumps(value))
''')
        ssh.chmod(0o755)
        scp = self.bin / 'scp'
        scp.write_text('''#!/usr/bin/env python3
import os, shutil, sys
from pathlib import Path
if os.environ.get('RETRY_TEST_FAIL'):
    sys.exit(255)
source, target = sys.argv[-2:]
stage = Path(target.split(':',1)[1]).name
out = Path(os.environ['RETRY_TEST_REMOTE']) / stage
shutil.copyfile(source,out)
if os.environ.get('RETRY_TEST_CORRUPT'):
    with out.open('r+b') as stream: stream.write(b'bad')
with open(os.environ['RETRY_TEST_COUNT'],'a') as stream: stream.write('copy\\n')
''')
        scp.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ['PATH'],
            RETRY_TEST_REMOTE=str(self.remote), RETRY_TEST_SOURCE=str(self.original),
            RETRY_TEST_COUNT=str(self.root / 'copies'))
        self.target = self.original.with_suffix('').as_posix() + '_H264_AAC.mp4'

    def run_script(self):
        return subprocess.run([PWSH, '-NoProfile', '-File', str(ROOT / 'copy-wuestenratten-to-box.ps1'),
            '-WorkDirectory', str(self.work)], env=self.env, capture_output=True, timeout=20)

    def test_copy_only_and_rerun_reuses_verified_receiver_movie(self):
        result = self.run_script()
        self.assertEqual(0, result.returncode, (result.stdout+result.stderr).decode())
        self.assertEqual(self.movie.read_bytes(), Path(self.target).read_bytes())
        self.assertEqual(b'AV1 original unchanged', self.original.read_bytes())
        self.assertFalse(list(self.remote.glob('*.part')))
        second = self.run_script()
        self.assertEqual(0, second.returncode, (second.stdout+second.stderr).decode())
        self.assertEqual('copy\n', (self.root / 'copies').read_text())

    def test_dropped_connection_keeps_completed_pc_movie(self):
        self.env['RETRY_TEST_FAIL'] = '1'
        result = self.run_script()
        self.assertEqual(1, result.returncode)
        self.assertFalse(Path(self.target).exists())
        self.assertEqual(b'completed movie bytes'*1000, self.movie.read_bytes())
        self.assertEqual(b'AV1 original unchanged', self.original.read_bytes())

    def test_corrupt_copy_not_published(self):
        self.env['RETRY_TEST_CORRUPT'] = '1'
        result = self.run_script()
        self.assertEqual(1, result.returncode)
        self.assertFalse(Path(self.target).exists())
        self.assertTrue(self.movie.exists())


if __name__ == '__main__':
    unittest.main()

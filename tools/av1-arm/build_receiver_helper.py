"""Pin the receiver helper to a previously committed, hash-verified artifact."""
import argparse
import hashlib
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--artifact-commit', required=True)
args = parser.parse_args()
if not re.fullmatch('[a-f0-9]{40}', args.artifact_commit):
    raise SystemExit('An immutable full Git commit is required.')
metadata = json.loads((root / 'receiver-tests/av1-arm-20261018/build.json').read_text())
url = ('https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/' + args.artifact_commit
       + '/receiver-tests/av1-arm-20261018/ffmpeg-av1-armhf.gz')
source = (root / 'tools/av1-arm/receiver_test.py').read_text()
source = source.replace('__BINARY_URL__', url).replace('__ARCHIVE_SHA256__', metadata['archive_sha256'])
source = source.replace('__BINARY_SHA256__', metadata['binary_sha256'])
data = source.encode('ascii')
compile(data, 'test-av1-receiver.py', 'exec')
destination = root / 'test-av1-receiver.py'
destination.write_bytes(data)
print(destination.name, hashlib.sha256(data).hexdigest())

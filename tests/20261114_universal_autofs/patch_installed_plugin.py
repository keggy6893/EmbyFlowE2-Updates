#!/usr/bin/env python3
# EmbyFlowE2 experimental universal NAS direct-play resolver patch.
# Local opt-in test only; does not modify update manifests.
import os
import re
import sys
import tempfile

TARGET = '/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py'
MARKER = '# EMBYFLOW_UNIVERSAL_NAS_DIRECT_TEST_20261114'
BACKUP = TARGET + '.before_universal_nas'
if sys.version_info[0] < 3:
    sys.exit('ERROR: Python 3 required')

with open(TARGET, 'rb') as handle:
    original = handle.read()
if MARKER.encode('ascii') in original:
    sys.exit('Already patched; no changes.')
source = original.decode('utf-8')

def one(old, new, label):
    global source
    if source.count(old) != 1:
        sys.exit('STOP: unexpected source layout: ' + label)
    source = source.replace(old, new, 1)

# Enable the same strict NAS verification for every receiver, not model names.
head = 'def _embyflow_nfs_uses_ts_workaround():'
tail = '\n\ndef _embyflow_nfs_is_direct_ts('
a = source.find(head)
b = source.find(tail, a)
if a < 0 or b < 0 or source.count(head) != 1:
    sys.exit('STOP: model-gate block not found')
source = source[:a] + head + '\n    return True\n' + source[b:]

one("if not server_path.lower().endswith('.ts'):\n        return None, None, 'not-ts'",
    "if not server_path.lower().endswith(('.ts', '.mkv', '.mp4', '.m2ts')):\n        return None, None, 'unsupported-container'",
    'container-check')
one("python = _nfs_shutil.which('python3')",
    "python = _nfs_shutil.which('python3') or _nfs_shutil.which('python')",
    'python-cli')
one("local_extension='.ts', playback_mode='direct', service_type=1,",
    "local_extension=os.path.splitext(path)[1].lower(), playback_mode='direct', service_type=1,",
    'native-extension')

# A failed/missing NAS file must not prevent regular HTTP playback.
start = "    def failed_start(reason):\n"
end = "\n    timer = eTimer()"
a = source.find(start, source.find('def _embyflow_nfs_direct_open('))
b = source.find(end, a)
if a < 0 or b < 0:
    sys.exit('STOP: fallback block not found')
source = source[:a] + (
    "    def failed_start(reason):\n"
    "        _embyflow_nfs_log('HTTP-FALLBACK', 'reason=' + reason)\n"
    "        return _EMBYFLOW_NFS_ORIGINAL_OPEN(session, ref, title, stream_url, playback_info)\n"
) + source[b:]

source += '\n' + MARKER + '\n'
compile(source, TARGET, 'exec')
directory = os.path.dirname(TARGET)
mode = os.stat(TARGET).st_mode & 0o777
if not os.path.exists(BACKUP):
    with open(BACKUP, 'xb') as handle:
        handle.write(original)
fd, temporary = tempfile.mkstemp(prefix='.embyflow_universal_', suffix='.py', dir=directory)
try:
    with os.fdopen(fd, 'wb') as handle:
        handle.write(source.encode('utf-8'))
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, mode)
    os.replace(temporary, TARGET)
except Exception:
    if os.path.exists(temporary):
        os.unlink(temporary)
    raise
print('UNIVERSAL_NAS_TEST_INSTALLED; backup=' + BACKUP)

#!/usr/bin/env python3
"""Experimental detail-page resume UI port from VU+ V6 checkpoint.
Preserves installed NAS player code; does not touch update manifests.
Usage: python3 patch_resume_detail.py vu8-v6-local.patch
"""
import os
import re
import sys
import tempfile

TARGET = "/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py"
BACKUP = TARGET + ".before_resume_detail"
MARKER = "# RC26.3 detail-page resume test."
HUNKS = (2496, 2844, 6167, 39145, 39354, 39363,
         42658, 42704, 42721, 42749)

if sys.version_info[0] < 3 or len(sys.argv) != 2:
    sys.exit("STOP: Python 3 and VU+ checkpoint diff required")
with open(TARGET, "rb") as f:
    original = f.read()
source = original.decode("utf-8")
if MARKER in source:
    sys.exit("Already installed; no changes")
if "_embyflow_nfs_direct_open" not in source or "_efpolish_ready" not in source:
    sys.exit("STOP: unsupported installed EmbyFlowE2 base")
with open(sys.argv[1], encoding="utf-8") as f:
    patch = f.read()
chunks = re.split(r"(?=^@@ -\\d+)", patch, flags=re.MULTILINE)
selected = {}
for chunk in chunks:
    match = re.match(r"@@ -(\\d+)", chunk)
    if not match or int(match.group(1)) not in HUNKS:
        continue
    lines = chunk.splitlines(keepends=True)[1:]
    before = "".join(line[1:] for line in lines if line.startswith((" ", "-")))
    after = "".join(line[1:] for line in lines if line.startswith((" ", "+")))
    number = int(match.group(1))
    if source.count(before) != 1:
        sys.exit("STOP: source mismatch in VU+ hunk %d" % number)
    selected[number] = (before, after)
if set(selected) != set(HUNKS):
    sys.exit("STOP: incomplete VU+ resume patch")
for n in HUNKS:
    before, after = selected[n]
    if source.count(before) != 1:
        sys.exit("STOP: conflicting hunk %d" % n)
    source = source.replace(before, after, 1)

start = patch.find("+" + MARKER)
end = patch.find("+class EmbyFlowStartupUpdateNotice", start)
if start < 0 or end < 0:
    sys.exit("STOP: detail UI block not found")
block_lines = patch[start:end].splitlines(keepends=True)
if not all(line.startswith("+") for line in block_lines if line.strip()):
    sys.exit("STOP: malformed detail UI block")
block = "".join(line[1:] if line.startswith("+") else line for line in block_lines)
if "EmbyFlowDetailScreen.detail_ok = _detail_resume_ok" not in block:
    sys.exit("STOP: incomplete detail UI block")
source += "\n\n" + block
compile(source, TARGET, "exec")
if not os.path.exists(BACKUP):
    with open(BACKUP, "xb") as f:
        f.write(original)
fd, tmp = tempfile.mkstemp(prefix=".embyflow_resume_", suffix=".py",
                           dir=os.path.dirname(TARGET))
try:
    with os.fdopen(fd, "wb") as f:
        f.write(source.encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, os.stat(TARGET).st_mode & 0o777)
    os.replace(tmp, TARGET)
except Exception:
    if os.path.exists(tmp):
        os.unlink(tmp)
    raise
print("RESUME_DETAIL_TEST_INSTALLED; backup=" + BACKUP)

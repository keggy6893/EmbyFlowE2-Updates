"""Generate synthetic AV1 fixtures with the host FFmpeg, never receiver media."""
import os
from pathlib import Path
import subprocess

root = Path(os.environ.get('EMBYFLOW_ARM_BUILD_ROOT', '/workspace/local-artifacts/av1-arm-build'))
directory = root / 'fixtures'
directory.mkdir(parents=True, exist_ok=True)
for bits, audio in [(8, 'aac'), (10, 'eac3')]:
    target = directory / ('av1-%dbit-%s.mkv' % (bits, audio))
    if target.exists():
        continue
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=96x64:rate=12',
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', '2', '-c:v', 'libaom-av1',
        '-cpu-used', '8', '-crf', '35', '-pix_fmt', 'yuv420p' if bits == 8 else 'yuv420p10le',
        '-c:a', audio, '-n', str(target)], check=True, timeout=30)

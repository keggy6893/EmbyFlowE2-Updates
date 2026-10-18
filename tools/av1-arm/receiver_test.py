"""Bounded AV1 software decode/encode test. No movie files are modified."""
import gzip
import hashlib
import io
import os
from pathlib import Path
import platform
import signal
import subprocess
import tempfile
import time
from urllib.request import urlopen

# Filled with an immutable artifact commit by the release builder.
BINARY_URL = '__BINARY_URL__'
ARCHIVE_SHA256 = '__ARCHIVE_SHA256__'
BINARY_SHA256 = '__BINARY_SHA256__'
INSTALL_DIR = Path('/home/root/embyflow-av1-test-20261018')
SOURCE = Path('/media/usb/Serien/Greys/greys_s01e02.mkv')
MAX_DOWNLOAD = 16 * 1024 * 1024
MAX_BINARY = 32 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def install():
    if platform.machine().lower() not in ('armv7l', 'armv8l'):
        raise RuntimeError('Dieser Test ist nur fuer ARMv7-Hardfloat mit NEON vorgesehen.')
    if 'neon' not in Path('/proc/cpuinfo').read_text().lower():
        raise RuntimeError('NEON-Unterstuetzung nicht bestaetigt. Test nicht gestartet.')
    if INSTALL_DIR.is_symlink():
        raise RuntimeError('Unerwartetes Testverzeichnis.')
    INSTALL_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    binary = INSTALL_DIR / 'ffmpeg-av1-armhf'
    if os.path.lexists(binary):
        if binary.is_symlink() or not binary.is_file() or binary.stat().st_size > MAX_BINARY:
            raise RuntimeError('Unerwartete vorhandene Testdatei.')
        if digest(binary.read_bytes()) != BINARY_SHA256:
            raise RuntimeError('Vorhandene Testdatei hat eine andere Pruefsumme. Nichts ersetzt.')
        return binary
    print('Separaten AV1-Test laden; Pruefsummen werden geprueft ...', flush=True)
    with urlopen(BINARY_URL, timeout=25) as response:
        archive = response.read(MAX_DOWNLOAD + 1)
    if len(archive) > MAX_DOWNLOAD or digest(archive) != ARCHIVE_SHA256:
        raise RuntimeError('Download-Pruefsumme falsch. Keine Ausfuehrung.')
    with gzip.GzipFile(fileobj=io.BytesIO(archive)) as compressed:
        data = compressed.read(MAX_BINARY + 1)
    if len(data) > MAX_BINARY or digest(data) != BINARY_SHA256:
        raise RuntimeError('Programm-Pruefsumme falsch. Keine Ausfuehrung.')
    descriptor, temporary = tempfile.mkstemp(prefix='.ffmpeg-', dir=INSTALL_DIR)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o700)
        os.link(temporary, binary)
    finally:
        os.unlink(temporary)
    return binary


def execute(command, timeout=30):
    start = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise RuntimeError('Test gestoppt: Abbruch oder Zeitlimit von %s Sekunden.' % timeout) from None
    if process.returncode:
        detail = stderr.decode(errors='replace').splitlines()[-4:]
        print('\n'.join(detail), flush=True)
        raise RuntimeError('Der separate FFmpeg-Test ist fehlgeschlagen.')
    return stdout.decode(errors='replace'), time.monotonic() - start


def progress_summary(output, elapsed):
    values = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
    frames = int(values.get('frame') or 0)
    seconds = int(values.get('out_time_us') or 0) / 1000000
    if frames < 2 or seconds < 1 or values.get('progress') != 'end':
        raise RuntimeError('Keine vollstaendig dekodierte Testsequenz bestaetigt.')
    return frames, seconds / max(.001, elapsed)


def test(binary, source=SOURCE):
    if not source.is_file() or source.is_symlink():
        raise RuntimeError('Originaldatei Grey auf der USB-HDD nicht gefunden.')
    print('System-FFmpeg und Filme bleiben unveraendert. Kein Emby-Aufruf.', flush=True)
    common = [str(binary), '-hide_banner', '-nostdin', '-loglevel', 'error', '-xerror',
        '-filter_threads', '1', '-filter_complex_threads', '1', '-c:v', 'libdav1d', '-threads', '2',
        '-i', str(source), '-map', '0:v:0', '-an', '-sn', '-t', '2', '-progress', 'pipe:1', '-nostats']
    print('1/2 AV1-Softwaredekodierung: 2 Sekunden Film, hoechstens 30 Sekunden warten ...', flush=True)
    output, elapsed = execute(common + ['-f', 'null', '-'])
    frames, speed = progress_summary(output, elapsed)
    print('AV1-SOFTWAREDEKODER FUNKTIONIERT: %d Bilder, %.2fx inkl. Startzeit.' % (frames, speed), flush=True)
    print('2/2 AV1 nach H.264: 2 Sekunden Film, hoechstens 30 Sekunden warten ...', flush=True)
    output, elapsed = execute(common + ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-pix_fmt', 'yuv420p', '-threads', '2', '-x264-params', 'lookahead_threads=1',
        '-f', 'mpegts', '-y', '/dev/null'])
    frames, speed = progress_summary(output, elapsed)
    print('H264-UMWANDLUNG FUNKTIONIERT: %d Bilder, %.2fx inkl. Startzeit.' % (frames, speed), flush=True)
    print('Nur ein kurzer Orientierungstest. Keine Filmdatei erzeugt oder veraendert.', flush=True)


def main():
    try:
        test(install())
    except (Exception, KeyboardInterrupt) as error:
        print('STOPP:', str(error) if isinstance(error, RuntimeError) else 'Test oder Download nicht moeglich.', flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

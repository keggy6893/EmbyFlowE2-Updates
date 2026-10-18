"""Short offline-only receiver conversion test. Does not alter the plugin."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time


def convert(source, seconds=3):
    source = Path(source).resolve()
    if not source.is_file():
        raise RuntimeError('Quelldatei nicht gefunden.')
    if shutil.disk_usage(source.parent).free < 256 * 1024 * 1024:
        raise RuntimeError('Weniger als 256 MiB frei. Test abgebrochen.')
    ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise RuntimeError('ffmpeg oder ffprobe fehlt.')
    descriptor, temporary = tempfile.mkstemp(prefix='.embyflow-av1-offline-', suffix='.mkv', dir=source.parent)
    os.close(descriptor)
    start = time.monotonic()
    try:
        command = [ffmpeg, '-hide_banner', '-v', 'error', '-nostdin', '-y', '-threads', '2',
                   '-i', str(source), '-t', str(seconds), '-map', '0:v:0', '-map', '0:a:0?',
                   '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p',
                   '-threads', '2', '-c:a', 'aac', '-ac', '2', '-b:a', '160k', '-f', 'matroska', temporary]
        process = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
        if process.returncode:
            error = process.stderr.decode('utf-8', errors='replace').lower()
            if any(word in error for word in ('hardware', 'pixel format', 'function not implemented', 'not supported')):
                raise RuntimeError('AV1-Dekodierung auf dieser Box nicht verfuegbar. Der Eintrag av1 allein ist kein Nachweis fuer Software-Dekodierung; libdav1d oder libaom-av1 wird benoetigt.')
            if 'unknown encoder' in error:
                raise RuntimeError('H.264- oder AAC-Encoder konnte nicht verwendet werden.')
            raise RuntimeError('Konvertierung fehlgeschlagen. Keine fertige Testdatei erstellt.')
        probe = subprocess.run([ffprobe, '-v', 'error', '-show_entries',
                                'stream=codec_type,codec_name:format=duration', '-of', 'json', temporary],
                               capture_output=True, timeout=10, check=True)
        result = json.loads(probe.stdout)
        streams = result.get('streams') or []
        if not any(stream.get('codec_type') == 'video' and stream.get('codec_name') == 'h264' for stream in streams):
            raise RuntimeError('Testdatei enthaelt kein geprueftes H.264-Video.')
        if float((result.get('format') or {}).get('duration') or 0) < seconds * 0.7:
            raise RuntimeError('Testdatei ist unvollstaendig.')
        output = source.parent / ('EmbyFlow H264 Offline Test ' + Path(temporary).stem.rsplit('-', 1)[-1] + '.mkv')
        # Reserve the visible destination exclusively, never overwrite a movie.
        descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.close(descriptor)
        try:
            os.replace(temporary, output)
        except Exception:
            output.unlink(missing_ok=True)
            raise
        return output, round(time.monotonic() - start, 1), streams
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source')
    args = parser.parse_args()
    try:
        if args.source:
            source = Path(args.source)
        else:
            candidates = set()
            for mount in Path('/media').iterdir():
                if re.fullmatch(r'(hdd|usb)[0-9]*', mount.name) and os.path.ismount(mount.resolve()):
                    for file in (mount / 'movie/EmbyFlow').glob('*_1731728_*.mkv'):
                        if file.is_file():
                            candidates.add(file.resolve())
            if len(candidates) != 1:
                raise RuntimeError('Download nicht eindeutig gefunden. Bitte Dateipfad mit --source angeben.')
            source = candidates.pop()
        print('Offline-Test: 3 Sekunden AV1 nach H.264/AAC, Zeitlimit 60 Sekunden. Original bleibt unveraendert.', flush=True)
        output, elapsed, streams = convert(source)
        print('ERFOLG:', output, flush=True)
        print('Dauer:', elapsed, 'Sekunden. Testdatei im normalen Box-MediaPlayer oeffnen.', flush=True)
    except subprocess.TimeoutExpired:
        print('Zeitlimit erreicht. Keine fertige Testdatei. Original unveraendert.', flush=True)
        return 1
    except Exception as error:
        print(str(error) if isinstance(error, RuntimeError) else 'Offline-Test fehlgeschlagen. Original unveraendert.', flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

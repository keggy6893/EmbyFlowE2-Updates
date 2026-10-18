import gzip
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('av1_receiver', ROOT / 'tools/av1-arm/receiver_test.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
BUILD = Path(os.environ.get('EMBYFLOW_ARM_BUILD_ROOT', '/workspace/local-artifacts/av1-arm-build'))


class ReceiverHelperTests(unittest.TestCase):
    def test_short_progress_is_not_success(self):
        for output in ('frame=0\nout_time_us=0\nprogress=end',
                       'frame=24\nout_time_us=2000000\nprogress=continue'):
            with self.assertRaises(RuntimeError):
                helper.progress_summary(output, 2)

    def test_timeout_kills_own_process_group(self):
        start = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, 'Zeitlimit'):
            helper.execute(['/bin/sh', '-c', 'sleep 10'], timeout=.15)
        self.assertLess(time.monotonic() - start, 2)

    def test_download_checksums_and_existing_binary_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            data = b'test binary contents'
            archive = gzip.compress(data)
            original_read = Path.read_text
            def read_text(path, *args, **kwargs):
                return 'Features: neon' if str(path) == '/proc/cpuinfo' else original_read(path, *args, **kwargs)
            with patch.object(helper, 'INSTALL_DIR', Path(directory) / 'private'), \
                 patch.object(helper.platform, 'machine', return_value='armv7l'), \
                 patch.object(Path, 'read_text', read_text), \
                 patch.object(helper, 'ARCHIVE_SHA256', helper.digest(archive)), \
                 patch.object(helper, 'BINARY_SHA256', helper.digest(data)), \
                 patch.object(helper, 'urlopen', return_value=io.BytesIO(archive)):
                binary = helper.install()
                self.assertEqual(data, binary.read_bytes())
                self.assertEqual(binary, helper.install())
                binary.write_bytes(b'personal existing file')
                with self.assertRaisesRegex(RuntimeError, 'Nichts ersetzt'):
                    helper.install()
                self.assertEqual(b'personal existing file', binary.read_bytes())

    def test_corrupt_archive_not_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(helper, 'INSTALL_DIR', Path(directory) / 'private'), \
                 patch.object(helper.platform, 'machine', return_value='armv7l'), \
                 patch.object(Path, 'read_text', return_value='neon'), \
                 patch.object(helper, 'urlopen', return_value=io.BytesIO(b'corrupt')):
                with self.assertRaisesRegex(RuntimeError, 'Pruefsumme'):
                    helper.install()
                self.assertFalse((Path(directory) / 'private/ffmpeg-av1-armhf').exists())


@unittest.skipUnless((BUILD / 'output/bin/ffmpeg-av1-armhf').exists(), 'ARM build required')
class RealArmTests(unittest.TestCase):
    def test_actual_arm_helper_decodes_and_encodes_av1(self):
        with tempfile.TemporaryDirectory() as directory:
            wrapper = Path(directory) / 'arm-ffmpeg'
            wrapper.write_text('#!/bin/sh\nexec "%s" -L "%s" -cpu cortex-a15 "%s" "$@"\n' %
                (BUILD / 'toolchain/usr/bin/qemu-arm', BUILD / 'toolchain/usr/arm-linux-gnueabihf',
                 BUILD / 'output/bin/ffmpeg-av1-armhf'))
            wrapper.chmod(0o700)
            source = BUILD / 'fixtures/av1-8bit-aac.mkv'
            before = source.read_bytes()
            helper.test(wrapper, source)
            self.assertEqual(before, source.read_bytes())

    def test_actual_arm_10bit_av1_eac3_to_h264_aac(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'converted.mp4'
            command = [str(BUILD / 'toolchain/usr/bin/qemu-arm'), '-L',
                str(BUILD / 'toolchain/usr/arm-linux-gnueabihf'), '-cpu', 'cortex-a15',
                str(BUILD / 'output/bin/ffmpeg-av1-armhf'), '-v', 'error', '-nostdin', '-xerror',
                '-c:v', 'libdav1d', '-threads', '2', '-i', str(BUILD / 'fixtures/av1-10bit-eac3.mkv'),
                '-t', '2', '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                '-threads', '2', '-c:a', 'aac', '-ac', '2', '-b:a', '160k', '-movflags', '+faststart', str(target)]
            subprocess.run(command, check=True, capture_output=True, timeout=30)
            import json
            value = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                '-show_format', '-of', 'json', str(target)]))
            self.assertEqual(['h264', 'aac'], [s['codec_name'] for s in value['streams']])
            self.assertEqual('yuv420p', value['streams'][0]['pix_fmt'])
            self.assertEqual(2, value['streams'][1]['channels'])
            self.assertAlmostEqual(2, float(value['format']['duration']), delta=.1)


if __name__ == '__main__':
    unittest.main()

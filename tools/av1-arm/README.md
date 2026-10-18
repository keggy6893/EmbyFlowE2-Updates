# Isolated AV1 receiver test build

Target: ARMv7 hard-float Cortex-A15/NEON (Vu+ Duo4K SE), glibc >=2.38.
This is not a general binary for all Enigma2 receivers. It does not replace
`/usr/bin/ffmpeg`, modify system libraries, use Emby, or update the plugin.

On Debian 13 with gcc, make, git, pkg-config, Python and python3-venv:

```
python tools/av1-arm/setup.py
bash tools/av1-arm/build.sh
python tools/av1-arm/make_fixtures.py
python -m unittest discover -s tests/20261018_receiver_av1 -v
```

The setup downloads APT-verified cross compiler/emulator packages and extracts
them below `/workspace/local-artifacts/av1-arm-build`, without installation into
the host. Meson/Ninja live in a dedicated venv. Dependencies are pinned by Git
commit. Build parallelism is four jobs. Existing matching outputs are reused.
`EMBYFLOW_ARM_BUILD_ROOT` can select a different build directory.

dav1d 1.5.4, x264 and FFmpeg 8.1.2 are linked into one executable. Only the target
system's libc and libm remain dynamic dependencies. The libdav1d integration is
enabled explicitly; no disabled alias from the OE-Alliance recipe is used.
Network protocols are disabled. File/pipe, MKV/MP4 input, AV1/AAC/AC3/EAC3 and a
few ancillary audio decoders, H.264/AAC output and null test output are enabled.
This intentionally minimal tool is not a replacement for the system FFmpeg.

Validate with the QEMU Cortex-A15 emulator against both an 8-bit AV1/AAC fixture
and a 10-bit AV1/EAC3 fixture. Probe the generated MP4 with the host ffprobe and
confirm H.264 yuv420p, AAC stereo and full fixture duration. Emulated performance
is not a measurement of receiver performance. The published helper runs two
bounded, two-second tests on the receiver, discarding output into `/dev/null`.

Distribution includes licenses and an adjacent corresponding-source archive for
FFmpeg, dav1d and x264 at the exact commits used, plus these build instructions.
glibc/libm and the cross compiler are not shipped in the receiver binary package.

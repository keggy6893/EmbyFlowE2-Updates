# Vu+ Duo4K SE: isolated dav1d software-decoder test

The compressed executable has libdav1d and libx264 built in. It needs only the
receiver's glibc/libm (glibc >=2.38) and targets ARMv7 hard-float Cortex-A15 NEON.
It is not suitable for all E2 models. The installer stores it privately below
`/home/root/embyflow-av1-test-20261018`, verifies both compressed and extracted
SHA256 hashes, and leaves the system FFmpeg and plugin untouched.

The test reads `/media/usb/Serien/Greys/greys_s01e02.mkv`. It runs two tests,
each with a 30-second watchdog and two seconds of input: software AV1 decode,
then AV1-to-H.264 encoding with two threads and ultrafast settings. Output is
discarded. No movie is converted in full, no server is contacted, and no
background job or GUI restart is created. Performance is preliminary, not a
guarantee of live playback or full-film conversion speed.

Build sources, exact commits and SHA256 hashes are in `build.json`. Complete
corresponding FFmpeg/dav1d/x264 sources are in the adjacent
`corresponding-source.tar.xz`. Build scripts are under `tools/av1-arm` and also
included in that archive. FFmpeg/x264 are GPL-2.0-or-later; dav1d is BSD-2-Clause.
The target system libc/libm are not distributed. The cross compiler and emulator
are development prerequisites, not installed on the receiver.

Verified in QEMU Cortex-A15: real 8-bit AV1 decode; real 10-bit AV1/EAC3 input
to H.264 yuv420p/AAC stereo MP4 with matching duration. Six tests passed,
including process-group timeout, wrong-checksum rejection, no overwrite of
existing files, and refusal to report partial progress as successful decoding.
Actual receiver performance remains to be measured by the user.

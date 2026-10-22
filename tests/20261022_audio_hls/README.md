# Receiver audio compatibility trial 2026102201

Reported trigger: selecting another language through Green succeeds, but audio
and video hang after approximately 30 seconds. EMC plays the source successfully.
The latest screenshot confirms Direct / 4097 on a Gigablue Quad Pro. It does not
establish the post-switch stream mode or prove the root cause.

For Dreambox One (dreamone / dmone) and Gigablue Quad Pro (gbquad4kpro),
the existing server-selected audio restart now requests HLS / MPEG-TS with
AAC stereo, 48 kHz, 192 kbit/s. The requested source audio index, media-source
ID, position and fresh session ID are preserved. The video codec remains
H.264 or HEVC and video stream copy is requested; the server's actual response
and permissions still determine whether playback succeeds.

This changes the container, audio output and timing path together. It is a
compatibility trial, not an isolated proof of the fault. It requires server-side
audio conversion. Multichannel/passthrough audio becomes stereo after switching.
The standard 4097 backend is retained; no external player is installed.

Local files, other receivers, unknown video codecs and the existing burned-in
subtitle restart keep their previous behavior. The previous MKV path remains
in source. The 2026102105 genre/layout/LCD changes are preserved.

## Primary references

- https://dev.emby.media/reference/RestAPI/DynamicHlsService/getVideosByIdMasterM3u8.html
  documents the HLS endpoint, audio stream selection, channels, start offset and
  timestamp-copy setting.
- https://gstreamer.freedesktop.org/documentation/playback/playbin.html
  documents stream selection, network buffering and asynchronous playback state.
  It does not establish a receiver-specific 30-second fault.

## Local validation

From the repository root:

    python tests/20261022_audio_hls/test_audio_hls.py

11 tests execute the actual generated restart, selection and reporting functions
with mocked Enigma2 services and HTTP. Tests cover both directions, selected
source/index/position, HLS/AAC parameters, codec and receiver scope, local file
exclusion, subtitle profile preservation, single Playing announcement with
Progress through simulated 60 seconds, and Python 3.8 syntax.

No hardware, real Emby server or media playback was available for this validation.

## Receiver check

Install only through EmbyFlow -> Updates. Start the same affected film, switch
German -> English, watch at least two minutes, then switch back and watch another
two minutes. Check picture, sound and position. The temporary state label shows
AAC-Stereo / HLS when this path is selected. Confirm the actual codec/mode in
Quality & Stats. Do not interpret a local unit test as a hardware pass.

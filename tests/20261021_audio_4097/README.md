# Anskar: 4097 server-selected audio test

Receiver evidence: Gigablue UHD Quad Pro runs Auto -> Direct 4097; ExtEplayer3/5002 is missing. The older local-backend candidate is superseded and must not be deployed.

The 4097 candidate replaces native selectTrack with a server-side remux at the captured movie position. Video and audio use copy; no ExtEplayer3 dependency. Native timestamps are never treated as proof of audible sound or visible video. Both audio directions use the complete source list, including after the server exposes only one output audio track. The native startup monitor is bounded to 15 seconds and never retries the restart automatically.

The async replacement helper is adapted from the published baseline, fixed to 4097 and an explicit server AudioStreamIndex. It keeps the existing content-clock and old-session cleanup behavior. Burned-in server subtitles must first be switched off, to avoid implicit video re-encoding. Other playback paths retain their existing behavior.

Validation: 27 local tests passed, including the actual restart helper with mocked receiver and worker boundaries. Full generated plugin parsed as Python 3.8 and compiled. Build baseline SHA256: 01fa460d5d7f5146d0963d9df27f19f0c9266fefc9a6494a856913395b01ef88. No receiver or real Emby-server success is established by these tests.

Run python tests/20261021_audio_4097/test_4097.py and python tests/20261021_audio_4097/build_4097.py from the repository root. Build 2026102102 is a receiver test, not a confirmed fix. Anskar installs only through EmbyFlow -> Updates.

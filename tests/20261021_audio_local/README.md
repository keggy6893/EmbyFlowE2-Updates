# Anskar: DirectPlay audio-switch candidate

Reported on Gigablue UHD Quad Pro: German to English freezes video, removes
audio, and resets displayed remaining time; switching back does not recover.
LCD time during ordinary playback is confirmed fixed by build 2026102001.

The current artifact calls native `selectTrack` in the active backend. The
receiver backend and presence of ServiceApp/ExtEplayer3 have not been reported.
Decoder failure in 4097 is a hypothesis, not a confirmed diagnosis.

This candidate promotes static DirectPlay from 4097 to installed 5002 before
selecting audio, using the existing local backend-switch/resume path. It keeps
the URL/session, validates language/codec/channels after remapping native track
numbers, and resumes the saved movie position after acknowledgement. Explicit
Enigma2 mode is respected. Missing backend/identity produces a message rather
than attempting the known failing 4097 switch. Nonstatic streams retain their
existing path. Existing 5002 selection gains position restoration, but its
decoder behavior is not proven by these tests.

Run `python tests/20261021_audio_local/test_audio.py` and
`python tests/20261021_audio_local/build_audio.py` from the repository root.
21 local tests pass, including the existing backend helper with mocked service
boundaries. The complete generated plugin parses as Python 3.8 and compiles.
No local test establishes audible output, moving video, or successful receiver
seek. No claim is made that the defect is resolved on hardware.

Before releasing through the normal EmbyFlow updater, obtain Anskar's player
mode (4097/Enigma2 or 5002/ExtEplayer3) and backend availability. If 5002 is
already active, investigate that path rather than publishing this hypothesis
as a 4097 fix. No SSH or separate installer for Anskar. `update.json` is
intentionally unchanged. Keep the existing LCD fix.

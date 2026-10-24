# DreamOne native audio receiver trial — build 2026102401

Anskar reported that MKV starts in English, changing audio starts the film again
from the beginning, the menu and infobar disagree, and playback stutters. TS
starts in German but changing languages has the same restart/stale-badge issue.
Receiver was confirmed as DreamOne.

The 2301/2201 test intercepts every static 4097 audio selection and opens a fresh
server remux/HLS session. This candidate restores the existing confirmed native
track selection only on dreamone/dmone + service 4097. MKV and TS keep their
current stream URL, session, position and audio format. No automatic remux/HLS
fallback, server requests or package installation is added. The selector shows
tracks actually exposed by the current service. If the stream exposes only one
language, this candidate cannot manufacture another native track.

German is selected at startup using actual native descriptors, with bounded
readiness retries. Explicit manual choices have priority. The original native
confirmation waits for a stable current track before updating metadata and
badges. Infobar refresh reads the confirmed override. Metadata operations use
the active MediaSource rather than another version's first source. Other
receivers and engines keep their existing path. Burned-in subtitle handling,
updater, server authorization and LCD code are unchanged.

Tests use actual published player methods and mocked Enigma2 services. They
verify both switch directions, a five-minute position, no playService/stopService
or server-restart calls, active-source metadata, failed confirmations, native
German startup, manual priority, missing German, machine and engine boundaries.
There is no DreamOne hardware, audio capture or real playback in this environment.
Neither first-frame German nor absence of long-term stutter is a hardware result.

Install via EmbyUpdate on Anskar's DreamOne. Exit the current film first. Start
the original MKV, check audible language and infobar, wait five minutes, switch
to English, watch another five minutes, switch back. Repeat for TS. Record
whether playback position, sound, infobar and smoothness agree. An earlier
py_compile updater failure still needs the one-time updater repair before the
new build can be installed.

Build: python3 tests/20261024_dreamone_native/build.py
Tests: python3 -m unittest discover -s tests/20261024_dreamone_native -p 'test_*.py' -q

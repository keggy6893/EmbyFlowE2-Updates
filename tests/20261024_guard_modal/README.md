# Guard-notice modal crash — 2026102402

Anskar's DreamOne/openATV crash log from 2026-10-24 18:12:55 identifies
_efguard_gui_tick calling session.open(MessageBox, ...) when StartEnigma refuses
modal opens. This unhandled Python exception terminates Enigma2. The earlier
5002/exteplayer3 PLAYBACK_OPEN and FF_ERROR events do not establish an external
player crash. The log does not establish the eventual native audio selection.
No raw log, media URL, username or access token is included in this repository.

This patch changes only the guard-notification timer and release identity.
When session.in_exec is false, the notice stays queued. A transition race during
session.open is caught; the old notice is restored unless a newer one arrived.
The existing plugin-ownership and timer-lifetime rules stay intact. Stream
abort/backoff rules, player type, URLs, seeking and audio code are unchanged.

The tests reproduce the original exception and cover deferred/successful opens,
modal races, newer notices, nested dialogs, leaving the plugin and no session.
The release comparison excludes only four release identity constants and the
guard tick, proving the remainder has the same AST as immutable build 2401.
Local tests are not a hardware playback or anti-stutter certification.

python3 tests/20261024_guard_modal/build.py
python3 -m unittest discover -s tests/20261024_guard_modal -p 'test_*.py' -q

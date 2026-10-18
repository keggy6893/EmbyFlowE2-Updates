# Optional LCD4linux content clock – receiver test V1

Goal: while the current service belongs to EmbyFlow, give LCD4linux the same
duration and absolute content position used by EmbyFlow's TV overlay. The LCD
renderer receives 90 kHz PTS converted from Emby's 10 MHz ticks with integer
arithmetic. The external LCD's existing layout, poster and progress options
are retained. Missing duration/position leaves the original renderer unchanged.

## Scope and lifecycle

The helper only uses the already loaded LCD4linux module. It checks the
LCD4linuxPIC function signature and recursively checks compiled code for the
Llength/Lposition fields. Thus it also supports a pyc-only installation without
importing optional plugins or assuming a source file exists. An incompatible
renderer is left untouched; failure of this optional feature does not prevent
the player from opening.

A GUI timer publishes an immutable snapshot once per second. Only the currently
playing EmbyFlow service may publish. The renderer worker uses that snapshot,
the session identity and its cached service reference; it calls no Enigma2
navigation, seek or player methods. Snapshots expire after five seconds and
are cleared on player close or service mismatch. Close callbacks cannot clear
a newer player's snapshot. A per-render proxy overrides only Llength and
Lposition; raw LCD4linux state and Enigma2 service APIs are not overwritten.
There is no change to LCD configuration, native seek, audio or subtitle code.

## Evidence and limitations

Reported receiver: Dream One, LCD4linux V5.0-r40, both ProgressType and
MPProgressType 21. The public source available for investigation is r36, commit
4d4bde2651a25bf9570be58182af8f6ad64b29d9 in oe-alliance/oe-alliance-plugins.
Its original putProgress function displays +1391 min with test inputs of
24h duration / 49min position. The bridge changes that output to +109 min
with 158min content duration, preserving the original backend fields. These
inputs reproduce the symptom; they are not measurements from the receiver.

The exact installed r40 rendering API and actual display still require the
receiver test. The helper does not claim a verified r40 fix or feed readiness.
No live-TV/other-player metadata is replaced, and no receiver files outside
EmbyFlow are modified. No public update manifest change.

## Build, tests and installation

`python3 -m unittest discover -s tests/20261018_lcd_time -p 'test_*.py'`
checks clock conversion, seek/pause/end, foreign services/sessions, expiry,
close/reopen, unsupported API, missing optional plugin and atomic installation.
`python3 tests/20261018_lcd_time/check_upstream.py` downloads the pinned public
source and executes only the original progress function with drawing stubs.
It also validates the structural guard against the real public picture code.

`python3 tests/20261018_lcd_time/build.py` generates root `install-lcd-time.py`.
Download that immutable file to /home/root, verify its SHA256, then run Python 3.
The installer preserves the existing plugin and local additions, compiles
before writing, creates a dated plugin.py.vor-lcdzeit-* backup, replaces
atomically and restarts the GUI. The normal full-plugin updater will replace
this local test. Rollback is the printed backup; it must not overwrite newer
plugin changes without checking their version first.

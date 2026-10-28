# Direct audio selection, build 2026102801

Only the confirmed direct-play audio change is added to public build 2026102502.
The receiver backup is not used as the release base.

Direct static streams and local files use native audio-track selection on all
receiver models. German is selected using native language and codec metadata;
manual audio choices take priority. A server remux or audio-compatibility session
keeps its existing server-based path. GRUEN opens the native audio list for direct
playback. Pending server switches now display feedback.

The matcher retries at most eight times as tracks become available. It does not
map an advertised German track onto an explicitly English native track. Metadata
is written to the active source; changes to another source are restored.

Receiver confirmation: the user reported that 2012 in 1080p now starts in German
on Vu+ Duo 4K SE / OpenATV and supplied a working audio-menu screenshot with
German DTS 5.1 selected and English DTS 5.1 available. This is not confirmation
for other receivers, all movies, or the previously reported HTTP freeze.

No new TS, teletext, subtitle, or private UI experiments are included.
The subtitle inventory for the two 2012 entries was a read-only diagnosis.

## Local validation

    python3 tests/20261028_universal_audio/test_audio.py

Tests cover reordered native tracks, manual priority, missing German tracks,
local and direct playback, remux fallback, pending feedback, active-source
selection, forced Audio metadata and deferred selection confirmation.
An AST comparison checks that only release identity and appended audio code
change. Output is reproducible; syntax is parsed with Python 3.8 grammar.

Runtime events go to /tmp/embyflow-audio-universal.log without URLs or tokens.
The full-file update uses the existing updater backup and requires a GUI restart.

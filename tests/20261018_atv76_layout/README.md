# GigaBlue / openATV 7.6 detail layout test V2

Separate test helper; no change to the public RCDEV update manifest.
Receiver confirmation is pending. The first test aligned button labels, but
the overview rows still overlapped. The uploaded receiver output showed the
corrupted condition `detail_overviewline` rather than `detail_overview_line_`.

V2 replaces the two helper functions as complete, compiled source. It moves
the overview as one block, keeps row spacing, and hides the superseded original
multiline field when the six replacement rows exist. Buttons follow their
existing frame geometry. On other images the runtime helper stays inactive.
Other installed local additions are preserved. Audio and subtitle code is not
changed. The installer validates openATV 7.6, compiles first, backs up, and
replaces atomically in the plugin directory; then it restarts the GUI.

Build the standalone ASCII file with `python3 tests/20261018_atv76_layout/build_v2.py`.
Run `python3 -m unittest discover -s tests/20261018_atv76_layout -p 'test_*.py'`.
Download `install-gb76.py` directly to `/home/root` and verify its SHA256 before
running with Python 3. This avoids copying Python payloads through chat.
After opening the detail page, optional diagnostic rectangles (no titles,
credentials, or server addresses) are in `/home/root/embyflow-layout.json`.
The ordinary updater replaces this experimental helper on the next update.

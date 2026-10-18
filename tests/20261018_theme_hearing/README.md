# Limited theme hearing test

Receiver stream probe V2 confirmed Skyfall AAC/m4a HTTP 206 in 5.6 seconds.
Audible playback and native service compatibility remain receiver checks.

This optional test appends a fallback to the existing detail background music
resolver. Emby-provided theme songs keep priority. Existing settings, native
playback, download limits, subtitle handling and detail close hooks are retained.
Only Movie IDs 37724/157336 and Series IDs 1399/1396 are enabled: Skyfall,
Interstellar, Game of Thrones and Breaking Bad. Episode inheritance is not added.
External metadata requests contain no Emby token; generated stream URLs stay in
memory. No audio file is saved. Resolver cancellation kills its process group.

The installer compiles before modifying, backs up plugin.py and replaces it
atomically. It restarts the GUI after a successful first install. It does not
change the update manifest or main release. Re-running is a no-op.

Use existing advanced settings, BLUE Music, Detail background: Music + Fanart,
save. Reopen a supported title's details and wait for resolution. Check audible
sound and that leaving details or starting the film stops the background track.
A pre-existing ENABLE_LOCAL_THEME_TESTS marker can override Skyfall with the
older local test; Interstellar avoids that old Bond-only override.

Run `python3 -m unittest discover -s tests/20261018_theme_hearing -v`.
Build helper: `python3 tests/20261018_theme_hearing/build.py`.

Private technical prototype only. ThemerrDB's metadata license does not license
the music. YouTube/background audio usage and feed distribution remain unresolved;
passing these checks does not establish permission or readiness for a feed release.

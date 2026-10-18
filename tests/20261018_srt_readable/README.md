# SRT readability receiver test

The active external SRT renderer uses the MoviePlayer's
`external_subtitle_text` widget, previously Regular;25 on a 1920x1080 skin.
The separate legacy subtitle dialog is not the active SRT rendering path.

The optional installer changes only that widget: Regular;58, position 150,810,
size 1620,180, bottom aligned. It retains white text and the black 3 px border.
The existing scale_skin function scales this to Regular;39 at 1280x720.
The first test used 52; the user requested a modest increase to 58 after
comparing the receiver screenshot with e2Emby. Existing 52 installations upgrade
without adding duplicate markers or changing the position or border.
The larger field can accommodate three lines without leaving the screen.
SRT timing, native PGS, selection, audio and video code are preserved.

Syntax is checked before backup or mutation. A timestamped adjacent backup
retains existing local fixes. Replacement is atomic and repeat installation is
a no-op. First successful installation restarts the receiver GUI.

Run `python3 -m unittest discover -s tests/20261018_srt_readable -v`.
Receiver acceptance: the user confirmed the Mayday screenshot with German SRT
at size 58 and requested this appearance as the automatic default.
Build 2026101803 includes this widget directly in the normal update payload;
no installer command or separate setting is required after updating.
The build is reproducible via `.github/build_srt_2026101803.py`. Release checks
exercise the actual 2026101802 updater, including backup and hash rejection.

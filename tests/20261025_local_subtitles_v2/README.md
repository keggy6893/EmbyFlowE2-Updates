# Local native subtitle window correction V2 (receiver candidate)

User observed freezing after a local teletext selection. The activation log
records native type 1 / PID 34 / English as accepted at 14:31:28 and a subsequent
menu inventory at 14:32:40; it does not establish decoding, subtitle reception
or root cause of the reported freeze. The OSD screenshot displayed PAUSE.
No automatic unpause is added based on that screenshot.

Source comparison found V1 passes movie-player.instance as native subtitle
parent; standard Enigma2 InfoBarSubtitleSupport, also used by EMC, passes
SubtitleDisplay.instance. V2 makes that correction only in the local subtitle
module. It reuses the existing native subtitle off/close cleanup, with the
correct parent recorded in _efpg_active. A native tuple's optional title field
is retained in the menu and active state, but the five activation fields are
passed to the backend. This also preserves language with the reference SWIG
implementation that only reads it for five-element tuples.

V2 logs the activation fields (including teletext page/magazine), requested
window parent, pause flag and a best-effort position snapshot. It does not seek,
change audio, unpause, restart the service or call a server. Remote handlers
are delegated unchanged. It does not prove the observed freeze is solved.

Installer accepts only the exact previously distributed V1 module, preserves
all bytes outside it, creates a backup and atomically replaces the plugin while
the GUI is stopped. Checks cover V2 idempotence, unknown prior edits rejection,
original restoration on replacement failure, GUI restart in finally, and 16
native selection/menu/owner/window/cleanup/language and pause-state tests.
The installer was exercised with complete private candidates in temp files;
GUI control was mocked. A receiver retest is required before any success claim.

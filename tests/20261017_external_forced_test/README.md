# External German forced-SRT receiver solution test

Required outside prerequisite: the server admin must put the correct German forced-dialogue SRT next to the exact affected movie version, e.g. `Filmname.mkv` and `Filmname.de.forced.srt`, then refresh the Emby library. The installer cannot create, extract or upload that file, and no server/admin access has been provided here. File naming follows https://support.emby.media/support/articles/Subtitles.html . Whether the admin has supplied it is currently unknown.

For a 4K active MediaSource, this test automatically prefers a valid external German forced SRT over an embedded German forced default, or when no subtitle default exists. A non-forced or foreign server default remains authoritative. Manual off/selection remains authoritative. Only the active version's metadata is inspected. It never substitutes full subtitles or another language, synthesizes a subtitle file, transcodes video or claims all-film support.

If no suitable external SRT is in the metadata, the test explicitly reports it in the player status and `/tmp/embyflow_external_forced_test.json`. It does not re-run the unsuccessful embedded/native path for that 4K automatic test. Reload the movie after the library refresh; stale metadata cannot prove that the file is absent on disk.

The unsuccessful native experiment is unhooked if installed. The V4 15-second read timeout is restored to 120 seconds; the existing decoder, parser, guarded HTTP client, TLS checks, update manifest and local layout remain. A checkmark still requires actual SRT download/activation. HD delegates to the preceding automatic selection logic.

Thirteen local tests pass: selection priority, full/foreign/manual default preservation, missing-file reporting, language/format filtering, HD delegation, stacked-experiment installation and retirement, plus two real local HTTP tests using original download/parser/poll/stop functions through activation and manual off. A separate installer exercise verified full compilation, exact backup, retained local layout and repeat refusal. These are local fixtures, not receiver/server confirmation.

Install with Python 3 on the receiver, restart GUI, reload the affected 4K film after the admin's rescan, and do not manually select subtitles. Verify actual German dialogue text, not just a checkmark. Read the safe status JSON if the file is not found. To revert, restore the printed `plugin.py.vor-externem-ut-test-<timestamp>` backup and restart GUI. No automatic update change is made by this test.

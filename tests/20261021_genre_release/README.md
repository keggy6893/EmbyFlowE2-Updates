# Genre spacing release 2026102105

Isolated change based on the immutable published audio-session test 2026102104 (SHA-256 verified). In `_efbad_init`, only genre Y=442 changes to Y=400 and genre colour changes from #CFD5DD to #F2C94C. The earlier local Y=420 step and subsequent additional 20px correction are combined. No synopsis/title/poster/badge coordinates change. Existing HD scaling, LCD and 4097 audio-session code are preserved byte-for-byte except release identity/changelog.

Three release checks: AST comparison permits only the two genre constants and release identity changes; no rejected local layout wrapper; complete plugin parses as Python 3.8. Receiver confirmation of the genre-only local patch has not yet been supplied. Audio-session hardware confirmation and UT investigation remain open.

Publication uses a temporary Git index based on current origin/main. Local experimental features in EmbyFlowE2_2026101901.py are not bundled. The updater payload is pinned to an immutable commit and SHA-256.

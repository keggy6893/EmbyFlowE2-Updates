# Updater source validation repair — 2026102301

The single-file and bundle updater previously imported the optional py_compile module before downloading an update. Images without that module aborted with No module named py_compile.

This release validates staged files, installed files and rollback files using Python built-in compile() without executing the source. All five syntax checks remain in place. SHA-256 validation and backup/rollback behavior remain unchanged. No extra image package is required by the repaired updater.

Validation: 7 updater regression tests and 11 existing audio compatibility tests passed locally. The updater tests cover a missing py_compile module, valid installation, no execution during validation, invalid syntax, wrong SHA-256, rollback after replacement, and all five syntax checks. Python 3.8 grammar validation passed. Receiver installation of the 2105 repair was confirmed; successful update after that repair has not yet been confirmed.

Run updater tests from this directory with python -m unittest test_updater_compile_fix.py. The tests require Python 3.8 or newer and no receiver modules. Existing audio tests are under tests/20261022_audio_hls; their playback functions are unchanged in this release.

The audio compatibility change from 2026102201 remains experimental and requires receiver/server testing. It requests AAC stereo over HLS/TS for Dreambox One and Gigablue Quad Pro; there is no confirmed hardware fix.

Important upgrade limitation: a receiver already running the old updater without py_compile fails before it can install this release. Publishing a new manifest cannot repair that old installation by itself. Do not instruct affected users to repeatedly retry Updates as a workaround. A separate first repair is needed for those installations; no additional installer or package is published here.

# Forced text subtitle follow-up: active MediaSource

The user reported another film with a visible German forced SRT entry while subtitles remained off after the first fix. This screenshot demonstrates the intended workflow still fails; it does not identify the precise runtime cause.

Code inspection found a reproducible mismatch: the selector lists the active MediaSource, while the old text renderer and first automatic fix read the first MediaSource. V2 shares the active source inventory across automatic selection and rendering, preserves its default stream index including zero, and updates that source when enabling/disabling subtitles. German language variants such as de-DE are recognized. Missing stream metadata gets at most four timer retries. Manual selection remains authoritative. Bitmap subtitles are outside this change.

The manual installer requires the first fix (or build 2026101701), validates and compiles the full source before writing, backs up plugin.py, uses atomic replacement, and rejects repeated installation. It preserves the existing download retry and unrelated layout changes.

Validation: nine V2 tests include a regression that misses the active source with V1, multiple-source HTTP download/parse/activation/off tests using original player functions, language variants, default index zero, bounded delayed-metadata retries, manual off, and unsupported bitmap tracks. Full plugin compilation, backup integrity, and repeat refusal were also checked. Receiver confirmation of V2 is pending. The automatic update channel is unchanged.

Run from the repository root:

```sh
/workspace/.embyflow-venv/bin/python -m unittest discover -s tests/20261017_forced_subtitles_v2 -p 'test_*.py' -v
```

On the receiver, run install.py with Python 3, then restart the GUI and reopen the affected film. To revert, restore the exact `plugin.py.vor-ut-v2-<timestamp>` backup printed by the installer and restart the GUI.

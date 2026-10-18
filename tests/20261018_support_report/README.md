# Local support report prototype

Advanced settings: BLUE Extras opens the existing ChoiceBox with Music and
Create support report. The report is saved to `/etc/enigma2/embyflow_support.txt`
and its FTP path shown in the existing MessageBox. Red, green and yellow retain
their bindings; music remains available through the same blue key. No INFO key
is needed. The existing blue footer label becomes EXTRAS.

Includes plugin/build/Python, receiver model identifier, selected image fields,
saved debug/download/trailer flags, and presence of the local LCD clock bridge.
The receiver identifier can be an image compatibility name rather than the retail
model. The report creates no network request, reads no account/settings files,
does not enable debug logging, and never sends anything automatically.

From ten allowlisted private plugin logs, reads at most the last 64 KiB each.
Exports only counts of fixed exception classes, 4xx/5xx HTTP status codes and
plugin.py traceback line numbers. Raw text, URLs, credentials, titles, full paths,
machine hostname/IP/MAC and IDs are not copied. Missing logs and unrecognized
messages are explicitly distinguished from a successful run. This deliberately
loses exception-message detail; the report is a starting point for diagnosis.

Files must be regular and not symlinks; FIFO reads cannot block. Report output is
atomic mode 0600. Repeated use replaces the previous report. Installer compiles
first, creates an adjacent backup, preserves other changes and restarts the GUI.
This is an optional prototype; normal update manifest is unchanged.

Run `python3 -m unittest discover -s tests/20261018_support_report -v`.
Build `python3 tests/20261018_support_report/build.py`.
Receiver check: advanced settings BLUE Extras, verify the file via FTP, existing color
keys and report display on HD/FHD. Receiver confirmation is pending.

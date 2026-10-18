# Numbered download disks

Receiver evidence: openATV mounts the new 500 GB disk at `/media/hdd2` while a
small stick occupies `/media/hdd` and a second stick `/media/usb`. The previous
target and library lists only enumerated the two unnumbered paths.

Build 2026101804 discovers hdd/usb names and numeric suffixes directly under
`/media` on every target selection and library scan. Each candidate must resolve
to an actual mount on a filesystem other than receiver root. Duplicate device
IDs are listed once. Writable destinations also require W_OK and a non-readonly
filesystem. The offline library can still scan read-only mounted disks.
Existing rechecks before transfer and free-space checks remain active.

The target label now uses the mount name (`Speicher · hdd2`) instead of inferring
physical HDD/USB type from an arbitrary mount name. Capacity remains displayed
by the existing dialog. Download files and sidecars remain under movie/EmbyFlow.
No remount, formatting, filesystem configuration or new directory creation is
performed during discovery. Named network shares and arbitrary mount labels are
outside this change; supported names are hdd, hddN, usb, usbN.

Build: `python3 .github/build_mounts_2026101804.py`.
Check: `python3 -m unittest discover -s tests/20261018_download_mounts -v`.
Tests reproduce the three-device mount layout, reject unmounted/flash/duplicate
targets, preserve read-only library access and use the actual prior updater.
Receiver confirmation of the new disk appearing remains pending.

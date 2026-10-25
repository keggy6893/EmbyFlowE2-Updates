# Local subtitle display layer candidate V4

V3's correct key result removed the user's unintended pause on menu open, but
the user reports no visible captions after native teletext selection. Accepted
track activation does not establish that captions are received or drawn.

The standard SubtitleDisplay skin uses desktop zPosition=-1. The private
EmbyFlow player is full-screen. V4 places this dedicated transparent subtitle
window on layer 10, above the movie screen, retaining SubtitleDisplay.instance
as the native widget parent. This corrects a possible occlusion path; receiver
caption rendering and actual teletext reception still require verification.

Local player onHide hides the display before child dialogs; onShow restores it
only with an active local subtitle and the same service reference. No duplicate
hooks are added on language changes. Off, changed service and closed player
never restore the display. Existing native disable/hide cleanup is reused.
The V3 integer return consuming GELB remains. No automatic resume, audio switch,
seek, engine swap, remote subtitle download or provider request is added.

Installer replaces exactly one known V1/V2/V3 local subtitle module and preserves
all surrounding bytes. It retains backup, syntax validation, atomic replacement,
unchanged-source and free-space checks. Repeat V4 installs are no-ops. Unknown
prior edits are rejected. No full-release manifest is changed.

27 tests cover native selection, key consumption and display layer/lifecycle.
Installer tests use complete private candidates in temporary files with GUI
control mocked to validate preservation, backups, repeats, unknown edits and
failed-replacement cleanup. A box test is necessary before a success claim.

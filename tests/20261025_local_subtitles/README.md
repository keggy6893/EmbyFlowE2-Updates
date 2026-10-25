# Local native subtitle inventory correction

The screenshot's error originates from `_embyflow_subtitle_open_0629`: it raises
when the active Emby MediaSource has no subtitle rows, ignoring the current
local file service's `getSubtitleList()` entirely.

Local-file playback now uses the current native inventory for its subtitle
menu. Exact native tuples (DVB PIDs, teletext page identifiers, GStreamer
ordinals) are preserved; no ordinal mapping to Emby stream indexes occurs.
Selection validates both current service ownership and fresh tuple membership.
Native subtitles use the existing visible-screen attachment and `_efpg_active`
shutdown path; manual off also stops the automatic-selection timer. No remote
subtitle request, transcoding, audio change, seek or service restart is added.
No native tracks means an Off-only menu, not invented subtitle availability.
Remote Emby playback delegates to the original handlers without alteration.

Installer appends only this module to the installed plugin, with syntax/free
space/unchanged-source checks, exclusive backup, download lock and atomic
replace. Existing local seek correction and comparison module remain intact.
Tests cover original error reproduction, exact native activation, off, stale
service/track rejection, rejected activation cleanup, shared native shutdown,
GStreamer/teletext entries, duplicates/malformed entries and remote delegation.
Additional installer tests used the complete private local comparison candidate
in temporary files to check byte preservation, backup, idempotence and failed
replacement with GUI-start cleanup mocked. No receiver subtitle hardware pass
has been claimed.

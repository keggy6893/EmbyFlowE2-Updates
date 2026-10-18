# Local compatible offline-download test

Receiver test only. This branch does not change `update.json` or publish an IPK.
Run `python tests/20261018_compatible_download/build.py` to regenerate the
standalone installer, then run the tests with unittest discovery in this folder.

AV1 sources gain an optional **HDD-kompatibel** choice in the existing download
dialogs. The server must authorize an HTTP MP4 transcode through PlaybackInfo for
the exact item/source. No invented transcoding URL or download-policy bypass is
used. A server offering only HLS is rejected with a readable message. Actual Emby
server support still needs a receiver test; the HTTP contract is mocked in CI.

Output is a separate MP4, at most 1080p, H.264 8-bit 4:2:0 and AAC stereo (or
video only for a source without audio). The existing original file remains
untouched. The expected budget is 6.2 Mbit/s times duration plus 25%, with the
existing additional 512 MiB disk reserve. Progress indicates bytes against this
budget, not a claimed movie-completion percentage. Default server audio is used;
no subtitles are requested or downloaded.

The existing account download permission, per-item check, shared five-download
daily quota and single-download lock remain in force. Failed/cancelled attempts
refund the reservation and delete partial files. TLS stays verified, redirects
are disabled and tokens are confined to requests. Sidecars contain descriptive
metadata only, using the existing library whitelist.

Before publication, ffprobe scans media packets, checks codec/pixel format,
channels, packet counts and duration. Broken/truncated/incorrect-format files
are rejected. Verification supports cancellation and has a bounded timeout.
Only a verified complete file is linked into the library without replacing an
existing file. The current AV1 playback wrapper probes the resulting H.264 file
and retains native HDD playback.

The installer compiles the combined plugin before touching it, backs up the
installed plugin beside the original and appends the test atomically. Existing
local modifications remain present. Re-running the same test is idempotent.
After installation the GUI restarts. Test **Die Wüstenratten → Herunterladen →
HDD-kompatibel → target HDD → Herunterladen**. Wait for the verified completion
message, then open the new MP4 in the box's ordinary media player with the Emby
server disconnected to verify actual offline picture and sound.

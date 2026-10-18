# Download AV1 playback fallback

Receiver confirmation: Die Wuestenratten downloaded as AV1/E-AC3 failed native
local playback. The local test installed from commit 37462b6 restored both video
and audio through the current Emby direct-stream decision path. User confirmed
both and requested inclusion in Git. Build 2026101805 appends that exact runtime.

AV1/av01 downloads use their exact filename item ID, require the connected Emby
server's item ID/title/type to match, then reuse fetch_stream_info(audio_mode=
direct). This existing playback decision negotiates H.264 HLS for AV1. The older
audio_mode=aac branch forces progressive MP4 and is not reused. No fuzzy search
is used. Network failures show generic messages without credentials. Closing the
screen prevents a late worker result from starting playback.

The original file is untouched; this fallback needs an online server with
appropriate playback/transcoding rights. Other codecs retain local playback.
The original file ID can be recovered for existing downloaded filenames even
without a metadata sidecar. The fallback uses the local resume position. It
does not reserve a download quota slot or overwrite source/metadata files.

Run `python3 -m unittest discover -s tests/20261018_download_av1 -v`.
Build release: `python3 .github/build_av1_download_2026101805.py`.
Build optional test helper: `python3 tests/20261018_download_av1/build.py`.

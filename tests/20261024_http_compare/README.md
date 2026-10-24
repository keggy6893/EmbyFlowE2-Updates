# Local Skyfall transport comparison (Vu+ only, not a DreamOne fix)

Prerequisite: the user confirmed original USB/native service 1 audio selection
and key 9 work with LOCAL_SEEK_V1. Original file:
`/media/usb/Filme/James Bond 007 - Skyfall (2012).ts`.

The standalone installer only appends this comparison module to the currently
installed private plugin. It requires the existing Skyfall detail and local seek
fix, creates an exclusive backup, checks syntax/free space/current bytes, and
uses atomic replacement while the GUI is stopped. No release manifest changes.

From the existing Emby Local / Skyfall detail:
- Green: existing USB/native service 1 playback, unchanged.
- Yellow: same original bytes from disk through service 4097 / GStreamer.
- Blue: same original bytes through loopback HTTP and service 4097 / GStreamer.

For each comparison start, switch audio first. Only if audio/video continue,
try key 9. Stop on a hang, without further seek retries.

The server binds only 127.0.0.1 on a random port. It serves only a random route
mapped to the one original file, read-only, with HEAD/GET and single byte-range
support. The original video is not copied, modified or transcoded. Closing the
parent detail screen asynchronously shuts the listener down. HTTP requests do
not expose other paths or directory listings. Running original streams closes
on normal player exit; daemon request workers do not block GUI shutdown.

Test modes use the existing EmbyFlow native audio handler and pin engine e2;
seeks stay on that service and have no server restart or automatic 5002 fallback.
Provider Playing/Progress/Stopped and encoding cancellation are suppressed only
for explicitly marked comparison players. They start from zero using separate
comparison IDs. This intentionally isolates native transport behavior, not the
production Emby restart chain. Do not present this as a full Emby-server test:
there is no Emby authentication, remote latency, server remux or DreamOne here.

Diagnostic output: `/tmp/embyflow_http_compare.jsonl`, up to 600 one-second
samples per player and max 256 KiB. Contains native position/length, actual
service type, track number, seek requests and HTTP range requests, without
provider URLs or credentials. Position advancement alone does not establish
fluid video/audio; visual observation remains required.

Cloud validation: 23 unit/real HTTP tests; existing 10 local seek tests; installer
backup/idempotence/replace-failure tests in temporary directories; additionally
real FFmpeg/FFprobe used a generated TS with two labelled audio streams to
check file-vs-HTTP metadata, both audio streams, HTTP seeking and Range 206.
These are not receiver GStreamer or DreamOne hardware passes.

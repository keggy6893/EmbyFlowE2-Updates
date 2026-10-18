# PC-only offline conversion for Die Wuestenratten

`convert-wuestenratten-pc.ps1` targets Windows PowerShell 5.1 and an OpenSSH
client. It discovers the existing original MKV for item 1731728 on a mounted
receiver disk, copies it to the PC, converts using PC FFmpeg and returns a
separate H.264/AAC MP4. No Emby API, server transcode, plugin modification or
quota reservation is involved. The original on the receiver is never modified.
The receiver computes the original's SHA256 before copying. For Windows/receiver
legacy-SCP UTF-8 filename-check incompatibility, the fetch uses `scp -T`; SSH host
verification remains enabled and the exact received file must match the original
SHA256 before encoding. The received name never controls the local destination.
A unique partial path is cleaned on failure, and a verified original can be reused
on retry. Older files from the first helper are left untouched.

The script downloads the pinned Gyan FFmpeg 9.0.2 essentials Windows x64 ZIP
(about 115 MB) only when needed, and verifies its SHA256 before extraction.
Download source is the Windows-build provider linked by ffmpeg.org. An existing
FFmpeg directory can be passed explicitly with `-FfmpegDirectory`.

It requires space on the PC for the original, 6 GiB output budget and 512 MiB
reserve, and space for the output plus reserve on the receiver. This helper is
specifically bounded to the known film (maximum 90 minutes). Encoding uses x264
veryfast, CRF 21, a 6 Mbit/s video peak, 1080p maximum, 8-bit 4:2:0 and AAC stereo.
It prefers a German audio track, then the default track, then the first track.
Subtitles are omitted. Codec and duration are checked before returning the file;
a SHA256 of the receiver copy must match before its MP4 filename is published.
Receiver publication uses a hard link without overwriting existing files.

Local files remain under Documents/EmbyFlow-Offline; they are never replaced on
reruns. Interrupted transfers can leave a `.part` on the receiver; this is not
presented as a completed film. Failed copies/conversions leave both the original
and available PC files intact. The script reports the stop reason.

The tests run the actual PowerShell script and real AV1-to-H.264 conversion with
mocked SSH/SCP into a temporary filesystem. They check the German second audio
track is selected, original preservation, verified return-copy equality, failed
conversion without upload, rejection of a corrupted source copy before encoding,
and preservation of an existing PC movie. The SCP test peer reproduces the
reported filename-check error unless the transfer uses the fix. Set
`EMBYFLOW_TEST_PWSH` to a portable PowerShell executable when pwsh is not on PATH.
Linux PowerShell validation does not establish compatibility on the user's
Windows installation or decoding performance on their receiver.

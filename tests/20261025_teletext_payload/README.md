# Read-only teletext payload evidence

The tested recording is **Gesetz der Rache**, not Skyfall. The user's file list
shows this exact recording at 613343232 bytes. The native subtitle selection
log identified teletext type 1 / PID 34 and advertised German/English pages.
No actual visible captions have been confirmed for this recording in EMC.

Following accepted track activation and the confirmed GELB key fix, text remains
invisible even with the V4 display-layer change. Do not apply further speculative
renderer patches before checking whether recorded caption payload exists.

The standalone reader inspects only the known recording, never the player,
settings or original content. PID 34 is a diagnostic target taken from the
observed log for this specific file; production page numbers remain dynamic.
It detects 188/192/204-byte packet alignment, counts target PID packets,
scrambling/transport/continuity errors, reassembles PES, counts teletext data
units, and records dynamic page headers and nonblank row counts. It does not
print movie dialogue, correct Hamming errors, decode all national characters,
check PTS synchronization or claim captions have rendered on the receiver.
Page/row evidence is not proof of correct timing or complete decodability.

Scan is limited to 1 GiB or approximately 50 seconds, with progress per 128 MiB.
The result explicitly reports completeness and file size/mtime stability.
An incomplete scan cannot prove a PID/page is absent from the entire file.
A complete zero PID count would establish that this advertised PID has no
recorded packets in the scanned original file, subject to detected alignment.
Positive payload counts alone do not prove the production renderer is correct.

16 tests cover bit extraction, dynamic pages, nonblank versus empty rows,
alignment, absent/scrambled/damaged packets, bounded PES assembly, adaptation,
duplicates, continuity gaps, and read-only complete scan. Known Hamming wire
vectors validate address bit order; no error correction is claimed. A synthetic
47 MB packet file was also scanned with the expected zero target-PID result.
No receiver files are copied, remuxed, transcoded or modified.

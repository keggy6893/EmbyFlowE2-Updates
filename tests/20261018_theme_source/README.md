# ThemerrDB source probe

This standalone probe checks four public sample titles: Skyfall, Interstellar,
Game of Thrones and Breaking Bad. No Emby credentials or TMDB API key are used.
It does not modify EmbyFlow, change configuration, start receiver playback,
restart Enigma2, or save audio files. A successful result means that a direct
HTTPS audio stream resolved and its first byte was readable, not that native
4097 playback was verified. The HTTP request uses Range bytes=0-0 and closes
after one byte even when the remote server ignores Range.

Uses an existing system yt-dlp module or already-installed executable zipapp.
No receiver package installation/upgrade. Each resolver subprocess has a
40-second deadline; at most two run concurrently. Signed media URLs and raw
extractor errors are not printed. Standard TLS verification remains enabled.

Initial cloud result with yt-dlp 2026.08.19: ThemerrDB lookups succeeded for
all four titles; all YouTube resolver attempts failed with HTTP 403. This does
not establish whether receiver playback works in the user's network.

The ThemerrDB metadata license is not a music license. The probe does not
establish permission for audio-only/background playback from YouTube. No theme
feature is enabled and no release manifest is changed by this test branch.

Run: `python3 test-themes.py` in a Python environment with an existing yt-dlp.
On the receiver, the helper can live in /home/root and may be deleted after use.

#!/bin/sh
# Install EmbyFlow's trailer dependency from the receiver's configured feed.
set -eu

if [ "$(id -u)" != 0 ]; then
    echo 'Bitte als root ausfuehren.' >&2
    exit 1
fi
command -v opkg >/dev/null 2>&1 || { echo 'opkg fehlt.' >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo 'python3 fehlt.' >&2; exit 1; }

umask 077
backup="/etc/enigma2/embyflow-dependency-backups/yt-dlp-$(date +%Y%m%d_%H%M%S)-$$"
mkdir -p "$backup"
opkg list-installed > "$backup/packages-before.txt"
echo "Paketliste gesichert: $backup/packages-before.txt"

opkg update
opkg install python3-yt-dlp
python3 -m yt_dlp --version
python3 - <<'PY'
import re
from yt_dlp.version import __version__
numbers = tuple(int(v) for v in re.findall(r'\d+', __version__)[:3])
if numbers < (2026, 8, 19):
    raise SystemExit('Feed-Version zu alt fuer den Trailer-Resolver: ' + __version__)
print('OK: yt_dlp importierbar und Mindestversion erfuellt.')
PY
opkg list-installed > "$backup/packages-after.txt"
echo 'Trailer-Abhaengigkeit bereit. Bitte Receiver neu starten und Trailer testen.'

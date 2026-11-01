#!/bin/sh
set -eu
if [ -n "${D:-}" ]; then exit 0; fi
python3 - <<'PYCHECK'
import importlib.util, sys
if importlib.util.MAGIC_NUMBER != bytes.fromhex("2b0e0d0a"):
    sys.stderr.write("EmbyLocal TEST1: Python-ABI stimmt nicht mit den enthaltenen Hilfsmodulen ueberein. Installation abgebrochen.\n")
    sys.exit(1)
PYCHECK
plugin=/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2
if [ -d "$plugin" ]; then
    umask 077
    destination=/etc/enigma2/embyflow-backups
    mkdir -p "$destination"
    chmod 700 "$destination"
    backup="$destination/embylocal-test1-$(date +%Y%m%d-%H%M%S)-$$.tar.gz"
    tar -czf "$backup" -C "$plugin" .
    echo "EmbyLocal-Sicherung: $backup"
fi

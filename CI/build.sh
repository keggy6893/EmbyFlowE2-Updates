#!/bin/sh
set -eu

project=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
output=${1:-"$project/dist"}
mkdir -p "$output"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
target=/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2
mkdir -p "$stage$target" "$stage/DEBIAN"
cp -R "$project/src/EmbyFlowE2/." "$stage$target/"
find "$stage$target" -name '*.pyc' -type f -delete
cat > "$stage/DEBIAN/control" <<'CONTROL'
Package: enigma2-plugin-extensions-embyflowe2
Version: 2026.11.14.1-r1411
Architecture: all
Section: extra
Priority: optional
Maintainer: EmbyFlowE2
Depends: enigma2, python3-core, python3-requests, python3-pillow
Description: EmbyFlowE2 RC26.5 local packaging test
CONTROL
printf '%s\n' "$target/emby_config.py" > "$stage/DEBIAN/conffiles"
python3 - "$stage$target" <<'PY'
import sys
from pathlib import Path
from xml.etree import ElementTree

target = Path(sys.argv[1])
for source in target.rglob("*.py"):
    compile(source.read_bytes(), str(source), "exec")
ElementTree.parse(target / "keymap.xml")
PY
dpkg-deb --root-owner-group -Zgzip --build "$stage" "$output/enigma2-plugin-extensions-embyflowe2_2026.11.14.1-r1411_all.ipk"

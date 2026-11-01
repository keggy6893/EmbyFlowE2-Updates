#!/bin/sh
set -eu
if [ -n "${D:-}" ]; then exit 0; fi
plugin=/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2
python3 - "$plugin/plugin.py" <<'PYSYNTAX'
import sys
with open(sys.argv[1], "rb") as handle:
    compile(handle.read(), sys.argv[1], "exec", dont_inherit=True)
PYSYNTAX
rm -f "$plugin/plugin.pyc" "$plugin/plugin.py.pyc"
if [ -d "$plugin/__pycache__" ]; then
    find "$plugin/__pycache__" -maxdepth 1 -type f -name 'plugin.*.pyc' -exec rm -f {} \;
fi
echo 'EmbyLocal TEST1 installiert. Benutzeroberflaeche jetzt manuell neu starten.'

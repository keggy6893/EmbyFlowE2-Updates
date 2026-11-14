#!/bin/sh
# Isolated RC26.5 trial install; production update feed unchanged.
set -eu
DIR=/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2
TARGET="$DIR/plugin.py"
BACKUP="$DIR/plugin.py.before_rc265_universal"
TMP=/tmp/embyflow_rc265_universal.py
URL=https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/rcdev-universal-test-20261114/tests/20261114_universal_release/plugin.py
EXPECTED=c15ac3a028d4b30b2343667912b4bd24a9ac782c4729cfe9619671dbc1b18e79
[ -s "$TARGET" ] || { echo "STOP: plugin.py nicht gefunden"; exit 1; }
wget -qO "$TMP" "$URL" || { echo "STOP: Download fehlgeschlagen"; exit 1; }
ACTUAL=$(sha256sum "$TMP" | cut -d ' ' -f 1)
[ "$ACTUAL" = "$EXPECTED" ] || { echo "STOP: SHA256 falsch"; exit 1; }
python -c "compile(open('$TMP','rb').read(),'plugin.py','exec')" || { echo "STOP: Syntaxpruefung fehlgeschlagen"; exit 1; }
[ -e "$BACKUP" ] || cp -p "$TARGET" "$BACKUP"
cp "$TMP" "$TARGET.rc265_new"
chmod 644 "$TARGET.rc265_new"
mv -f "$TARGET.rc265_new" "$TARGET"
echo "RC265_TEST_INSTALLED; BACKUP=$BACKUP"
echo "GUI neu starten: init 4; sleep 3; init 3"

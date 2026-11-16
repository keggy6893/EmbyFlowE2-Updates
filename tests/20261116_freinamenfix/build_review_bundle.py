#!/usr/bin/env python3
"""Generate an isolated static-review bundle from the exact RC26.9 source."""
from pathlib import Path
import hashlib
import zipfile
import ast

base = Path("plugin_2026111523.py")
raw = base.read_bytes()
expected = "b7bcf3dc4bbefd4c938b7747258eb8bcbc061be0d303aa0b19c11ec31d7cdbb9"
assert hashlib.sha256(raw).hexdigest() == expected, "Source hash differs from reviewed RC26.9"
source = raw.decode("utf-8")
patches = [
    ("scale_skin_value(positions[self._controlIndex])", "sx(positions[self._controlIndex])"),
    ("scale_skin_value(871)", "sy(871)"),
    ('"username": user.get("Name") or username,', '"username": username,'),
    ("            shutil.rmtree(directory, ignore_errors=True)", "            import shutil\n            shutil.rmtree(directory, ignore_errors=True)"),
    ("if '_efn4_start_before' in globals():", "if all(name in globals() for name in ('_efn4_start_before', '_efn4_stop_before', '_efn4_close_before')):"),
]
for old, new in patches:
    assert source.count(old) == 1, "Unmatched or ambiguous patch: " + old
    source = source.replace(old, new, 1)
ast.parse(source)
corrected = source.encode("utf-8")
expected_fixed = "bc7c2a7c4a1ecdfea6e1fcdc77de642c582e4c3faea28cdf9a5f4bfbfc6aa271"
assert hashlib.sha256(corrected).hexdigest() == expected_fixed, "Unexpected corrected source hash"
report = """# EmbyFlowE2 RC26.9 – Freinamenfix (Prüfversion)

Stand 16.11.2026. **Keine Installationsfreigabe.**

Ausgang: plugin_2026111523.py / SHA256 b7bcf3dc4bbefd4c938b7747258eb8bcbc061be0d303aa0b19c11ec31d7cdbb9

Korrigiert:
1. Audio-Player: scale_skin_value durch sx/sy ersetzt.
2. Synchronisierung: undefinierten user-Zugriff durch username ersetzt.
3. Grid/Trailer: fehlenden lokalen shutil-Import ergänzt.
4. Untertitel: Existenz aller drei Rücksetzfunktionen geprüft.

Python-AST-Syntaxprüfung und fünf eindeutige Ersetzungen bestätigt.
**Enigma2-Laufzeittest, GUI, Tonspuren, Grid und Bilder noch nicht geprüft.**
Die offizielle update.json und der Updatekanal bleiben unverändert.
"""
probe = """#!/usr/bin/env python3
from pathlib import Path
import ast
import hashlib
p=Path(__file__).with_name("EmbyFlowE2_RC26.9_Freinamenfix_PRUEFVERSION.py")
data=p.read_bytes()
ast.parse(data.decode("utf-8"))
assert hashlib.sha256(data).hexdigest()=="bc7c2a7c4a1ecdfea6e1fcdc77de642c582e4c3faea28cdf9a5f4bfbfc6aa271"
print("Syntax und SHA256 OK – KEIN Enigma2-Laufzeittest")
"""
out = Path("EmbyFlowE2_RC26.9_Freinamenfix_PRUEFPAKET.zip")
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    z.writestr("EmbyFlowE2_RC26.9_Freinamenfix_PRUEFVERSION.py", corrected)
    z.writestr("EmbyFlowE2_Freinamenfix_Pruefbericht.md", report)
    z.writestr("EmbyFlowE2_Freinamenfix_pruefen.py", probe)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
print(out, out.stat().st_size, hashlib.sha256(out.read_bytes()).hexdigest())

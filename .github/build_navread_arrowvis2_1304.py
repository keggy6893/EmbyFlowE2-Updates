from pathlib import Path
import hashlib
import json
import re

OLD_PLUGIN = Path("plugin_RCDEV12_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py")
NEW_PLUGIN = Path("plugin_RCDEV13_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_NAVREAD1_ARROWVIS2_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py")
MANIFEST = Path("update.json")

OLD_VERSION = "2026-RCDEV12-SERVERSAFE1-DREAMSAFE2-LOGINV21-FAVRES28-NAVV30-DISCOVERFIX1-PUBLICCLEAN1"
NEW_VERSION = "2026-RCDEV13-SERVERSAFE1-DREAMSAFE2-LOGINV21-FAVRES28-NAVV30-DISCOVERFIX1-NAVREAD1-ARROWVIS2-PUBLICCLEAN1"
OLD_BUILD = "PLUGIN_UPDATE_BUILD = 2026091303"
NEW_BUILD = "PLUGIN_UPDATE_BUILD = 2026091304"

for required in (OLD_PLUGIN, MANIFEST):
    if not required.is_file():
        raise SystemExit("required release input missing: %s" % required)
if NEW_PLUGIN.exists():
    raise SystemExit("1304 release plugin already exists")

baseline = OLD_PLUGIN.read_text(encoding="utf-8")
if 'PLUGIN_VERSION = "%s"' % OLD_VERSION not in baseline:
    raise SystemExit("1303 baseline version marker missing")
if OLD_BUILD not in baseline:
    raise SystemExit("1303 baseline build marker missing")
if "# EMBYFLOW_HOME_DISCOVERFIX1_START" not in baseline:
    raise SystemExit("1303 DiscoverFix1 marker missing")
if '"discoverfix1": 1' not in baseline:
    raise SystemExit("1303 DiscoverFix1 cache marker missing")
if "# EMBYFLOW_NAV_GROUPS_V30_START" not in baseline:
    raise SystemExit("NAVV30 marker missing")

text = baseline.replace(
    'PLUGIN_VERSION = "%s"' % OLD_VERSION,
    'PLUGIN_VERSION = "%s"' % NEW_VERSION,
    1,
)
text = text.replace(OLD_BUILD, NEW_BUILD, 1)
text, date_count = re.subn(
    r'^PLUGIN_BUILD_DATE\s*=\s*"[^"]*"',
    'PLUGIN_BUILD_DATE = "13.09.2026"',
    text,
    count=1,
    flags=re.MULTILINE,
)
if date_count != 1:
    raise SystemExit("PLUGIN_BUILD_DATE marker mismatch")

changelog_open = "PLUGIN_UPDATE_CHANGELOG = (\n"
if changelog_open not in text:
    raise SystemExit("PLUGIN_UPDATE_CHANGELOG marker missing")
notes = (
    '    "Navigation Lesbarkeit: Hauptnavigation und Unterpunkte jeweils 1 px groesser, Textfarbe heller (#D6DBE2)|"\n'
    '    "Navigation Pfeile: Filme und Serien zeigen gelbe sichtbare Dreiecke; ▶ eingeklappt, ▼ aufgeklappt|"\n'
    '    "Release 1304 baut direkt auf 1303/DiscoverFix1 auf; Posterlogik, Playback und Untertitel bleiben unveraendert|"\n'
)
text = text.replace(changelog_open, changelog_open + notes, 1)

# ---------------------------------------------------------------------------
# NAV_READABILITY1: Home sidebar only.
# ---------------------------------------------------------------------------
skin_start_marker = "<!-- EMBYFLOW_HOME_SIDEBAR_V26_SOFTFOCUS -->"
skin_end_marker = '<eLabel text="EmbyFlowE2" position="290,36"'
skin_start = text.find(skin_start_marker)
skin_end = text.find(skin_end_marker, skin_start)
if skin_start < 0 or skin_end < 0:
    raise SystemExit("Sidebar skin boundaries not found")
skin = text[skin_start:skin_end]

before_b8 = skin.count('foregroundColor="#B8C0CC"')
if before_b8 < 10:
    raise SystemExit("unexpected sidebar foreground baseline count: %s" % before_b8)

# Largest first so replacements cannot cascade.
skin = skin.replace(
    'font="Regular;19" foregroundColor="#B8C0CC"',
    'font="Regular;20" foregroundColor="#B8C0CC"',
)
skin = skin.replace(
    'font="Regular;18" foregroundColor="#B8C0CC"',
    'font="Regular;19" foregroundColor="#B8C0CC"',
)
skin = skin.replace(
    'font="Regular;17" foregroundColor="#B8C0CC"',
    'font="Regular;18" foregroundColor="#B8C0CC"',
)
skin = skin.replace('foregroundColor="#B8C0CC"', 'foregroundColor="#D6DBE2"')
text = text[:skin_start] + skin + text[skin_end:]

# Keep V30 runtime-created text aligned with the tested +1 px / brighter style.
nav_start = text.find("# EMBYFLOW_NAV_GROUPS_V30_START")
nav_end = text.find("# EMBYFLOW_NAV_GROUPS_V30_END", nav_start)
if nav_start < 0 or nav_end < 0:
    raise SystemExit("NAVV30 block boundaries missing")
nav_end += len("# EMBYFLOW_NAV_GROUPS_V30_END")
nav = text[nav_start:nav_end]
nav = nav.replace('parseColor("#B8C0CC")', 'parseColor("#D6DBE2")')
nav = nav.replace("parseColor('#B8C0CC')", "parseColor('#D6DBE2')")
nav = nav.replace('foregroundColor="#B8C0CC"', 'foregroundColor="#D6DBE2"')
nav = nav.replace('gFont("Regular", 17)', 'gFont("Regular", 18)')
nav = nav.replace("gFont('Regular', 17)", "gFont('Regular', 18)")
text = text[:nav_start] + nav + text[nav_end:]

# ---------------------------------------------------------------------------
# NAV_ARROWVIS2: explicit high-z arrow widgets + UI refresher bound to the
# actually visible Filme/Serien rows. No navigation behavior is changed.
# ---------------------------------------------------------------------------
skin_anchor = '<widget name="side_sub_0" position="48,224"'
skin_pos = text.find(skin_anchor)
if skin_pos < 0:
    raise SystemExit("side_sub_0 skin anchor missing")

# 1303 should not already contain the local test widgets.
if '<widget name="side_sub_arrow_0"' in text:
    raise SystemExit("1303 baseline unexpectedly already has explicit ArrowVIS widgets")

rows = []
for i in range(18):
    y = 224 + 34 * i
    rows.append(
        '        <widget name="side_sub_arrow_%d" position="30,%d" size="20,30" '
        'zPosition="250" font="Regular;18" foregroundColor="#FFD400" '
        'backgroundColor="#050A12" halign="center" valign="center" transparent="1" />'
        % (i, y)
    )
arrow_block = (
    '        <!-- EMBYFLOW_NAV_ARROWVIS2: visible main-group arrows -->\n'
    + "\n".join(rows)
    + "\n"
)
text = text[:skin_pos] + arrow_block + text[skin_pos:]

component_anchor = '''        for _side_sub_i in range(18):
            self["side_sub_%d" % _side_sub_i] = Label("")
'''
if component_anchor not in text:
    raise SystemExit("side_sub component anchor missing")
if 'self["side_sub_arrow_%d" % _side_sub_i] = Label("")' not in text:
    text = text.replace(
        component_anchor,
        component_anchor + '''        for _side_sub_i in range(18):
            self["side_sub_arrow_%d" % _side_sub_i] = Label("")
''',
        1,
    )

timer_anchor = '''        self["side_sub_page"] = Label("")
'''
if text.count(timer_anchor) != 1:
    raise SystemExit("side_sub_page timer anchor mismatch")

timer_code = r'''
        # EMBYFLOW_NAV_ARROWVIS2
        # V30 rendert die sichtbare Navigation dynamisch in side_sub_0..17.
        # Die gelben Pfeile folgen deshalb den tatsaechlich sichtbaren
        # Filme-/Serien-Zeilen statt festen Zeilennummern.
        self._embyflow_nav_arrowvis2_timer = eTimer()

        def _embyflow_nav_arrowvis2_refresh():
            try:
                labels = []
                for _idx in range(18):
                    try:
                        _txt = (self["side_sub_%d" % _idx].getText() or "").strip()
                    except Exception:
                        _txt = ""
                    labels.append(_txt)

                for _idx in range(18):
                    _arrow_name = "side_sub_arrow_%d" % _idx
                    try:
                        self[_arrow_name].setText("")
                        self[_arrow_name].hide()
                    except Exception:
                        pass

                for _idx, _txt in enumerate(labels):
                    if _txt not in ("Filme", "Serien"):
                        continue

                    _next = labels[_idx + 1] if (_idx + 1) < len(labels) else ""
                    _expanded = bool(
                        _next.startswith(_txt + " ")
                        or _next.startswith("○ " + _txt + " ")
                        or _next.startswith("• " + _txt + " ")
                    )
                    _symbol = "▼" if _expanded else "▶"
                    _arrow_name = "side_sub_arrow_%d" % _idx

                    try:
                        self[_arrow_name].setText(_symbol)
                        if self[_arrow_name].instance:
                            try:
                                self[_arrow_name].instance.setForegroundColor(
                                    parseColor("#FFD400")
                                )
                            except Exception:
                                pass
                            self[_arrow_name].instance.show()
                        self[_arrow_name].show()
                    except Exception:
                        pass
            except Exception:
                pass

        self._embyflow_nav_arrowvis2_refresh = _embyflow_nav_arrowvis2_refresh
        try:
            self._embyflow_nav_arrowvis2_timer.callback.append(
                self._embyflow_nav_arrowvis2_refresh
            )
        except Exception:
            try:
                self._embyflow_nav_arrowvis2_timer.timeout.connect(
                    self._embyflow_nav_arrowvis2_refresh
                )
            except Exception:
                pass
        try:
            self._embyflow_nav_arrowvis2_timer.start(350, False)
        except Exception:
            pass

'''
text = text.replace(timer_anchor, timer_anchor + timer_code, 1)

class_marker = "class EmbyFlowE2Screen(Screen):"
if text.count(class_marker) != 1:
    raise SystemExit("EmbyFlowE2Screen class marker mismatch")
text = text.replace(
    class_marker,
    "# EMBYFLOW_NAV_READABILITY1\n# EMBYFLOW_NAV_ARROWVIS2\n" + class_marker,
    1,
)

# ---------------------------------------------------------------------------
# Release guards.
# ---------------------------------------------------------------------------
for required in (
    "# EMBYFLOW_HOME_DISCOVERFIX1_START",
    '"discoverfix1": 1',
    "# EMBYFLOW_NAV_GROUPS_V30_START",
    "# EMBYFLOW_NAV_GROUPS_V30_END",
    "# EMBYFLOW_NAV_READABILITY1",
    "# EMBYFLOW_NAV_ARROWVIS2",
    'foregroundColor="#D6DBE2"',
    'foregroundColor="#FFD400"',
    'side_sub_arrow_17',
    '_embyflow_nav_arrowvis2_refresh',
):
    if required not in text:
        raise SystemExit("required 1304 marker missing: %s" % required)

# Exactly 18 explicit high-z arrow widgets.
if text.count('zPosition="250" font="Regular;18" foregroundColor="#FFD400"') != 18:
    raise SystemExit("ArrowVIS2 widget count mismatch")

# Protect playback / subtitle experimental markers from changing.
protected_markers = (
    "EMBYFLOW_PGS_HLS_RETRY_PROXY_FIX",
    "PGS_HLS_RETRY_PROXY",
    "TRANSCODE_RECOVERY",
    "UTFIX16",
    "UTFIX17",
    "UTFIX18",
    "UTFIX19",
    "_embyflow_pgs_hls_restart_v1",
)
for needle in protected_markers:
    if text.count(needle) != baseline.count(needle):
        raise SystemExit("1304 changed protected playback marker count: %s" % needle)

# DiscoverFix1 must remain exactly present at least once and its unique markers
# must not disappear.
for needle in (
    "# EMBYFLOW_HOME_DISCOVERFIX1_START",
    "# EMBYFLOW_HOME_DISCOVERFIX1_END",
    '"discoverfix1": 1',
    'IndexNumber,ParentIndexNumber,ImageTags',
):
    if text.count(needle) != baseline.count(needle):
        raise SystemExit("1304 changed DiscoverFix1 marker count: %s" % needle)

compile(text, str(NEW_PLUGIN), "exec")
NEW_PLUGIN.write_text(text, encoding="utf-8")
sha256 = hashlib.sha256(NEW_PLUGIN.read_bytes()).hexdigest()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
if int(manifest.get("build", 0)) != 2026091303:
    raise SystemExit("update.json baseline build mismatch")
if manifest.get("version") != OLD_VERSION:
    raise SystemExit("update.json baseline version mismatch")

manifest["version"] = NEW_VERSION
manifest["build"] = 2026091304
manifest["channel"] = "rcdev"
manifest["download"] = (
    "https://raw.githubusercontent.com/keggy6893/"
    "EmbyFlowE2-Updates/build-2026091304/"
    "plugin_RCDEV13_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_NAVREAD1_ARROWVIS2_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py"
)
manifest["sha256"] = sha256
manifest["target"] = "plugin.py"
manifest["artifact_type"] = "plugin_py"
release_notes = [
    "Navigation Lesbarkeit: Hauptnavigation und Unterpunkte jeweils 1 px groesser und heller (#D6DBE2)",
    "Navigation Pfeile: Filme und Serien zeigen sichtbar gelbe Dreiecke; ▶ eingeklappt, ▼ aufgeklappt",
    "Release 1304 baut auf 1303/DiscoverFix1 auf; Posterlogik, Playback und Untertitel bleiben unveraendert",
]
manifest["changelog"] = release_notes + list(manifest.get("changelog") or [])
MANIFEST.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

print("CHECK NAV_READABILITY1 + ARROWVIS2 plugin OK")
print("release_file=%s" % NEW_PLUGIN)
print("sha256=%s" % sha256)
print("size=%s" % NEW_PLUGIN.stat().st_size)

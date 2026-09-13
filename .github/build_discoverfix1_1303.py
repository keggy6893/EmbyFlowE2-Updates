from pathlib import Path
import hashlib
import json
import re

OLD_PLUGIN = Path("plugin_RCDEV10_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py")
NEW_PLUGIN = Path("plugin_RCDEV12_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py")
MANIFEST = Path("update.json")

OLD_VERSION = "2026-RCDEV10-SERVERSAFE1-DREAMSAFE2-LOGINV21-FAVRES28-NAVV30-PUBLICCLEAN1"
NEW_VERSION = "2026-RCDEV12-SERVERSAFE1-DREAMSAFE2-LOGINV21-FAVRES28-NAVV30-DISCOVERFIX1-PUBLICCLEAN1"
OLD_BUILD = "PLUGIN_UPDATE_BUILD = 2026091301"
NEW_BUILD = "PLUGIN_UPDATE_BUILD = 2026091303"

for required in (OLD_PLUGIN, MANIFEST):
    if not required.is_file():
        raise SystemExit("required release input missing: %s" % required)
if NEW_PLUGIN.exists():
    raise SystemExit("1303 release plugin already exists")

baseline = OLD_PLUGIN.read_text(encoding="utf-8")
if 'PLUGIN_VERSION = "%s"' % OLD_VERSION not in baseline:
    raise SystemExit("1301 baseline version marker missing")
if OLD_BUILD not in baseline:
    raise SystemExit("1301 baseline build marker missing")

# Navigation V30 must remain byte-identical.
NAV_START = "# EMBYFLOW_NAV_GROUPS_V30_START"
NAV_END = "# EMBYFLOW_NAV_YELLOW_PARENT_ARROWS_V1_END"
nav_start = baseline.find(NAV_START)
nav_end = baseline.find(NAV_END, nav_start)
if nav_start < 0 or nav_end < 0:
    raise SystemExit("Navigation V30 block not found")
nav_end += len(NAV_END)
nav_baseline = baseline[nav_start:nav_end]
for marker in (
    "# EMBYFLOW_NAV_GROUPS_V30_START",
    "# EMBYFLOW_NAV_GROUPS_V30_END",
    "# EMBYFLOW_NAV_YELLOW_PARENT_ARROWS_V1_START",
    "# EMBYFLOW_NAV_YELLOW_PARENT_ARROWS_V1_END",
):
    if baseline.count(marker) != 1:
        raise SystemExit("Navigation V30 baseline marker mismatch: %s" % marker)

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
    '    "DiscoverFix1: Entdecken fuellt einen fehlenden zweiten Kartenslot auf, statt eine vorhandene Karte zu ersetzen|"\n'
    '    "DiscoverFix1: leere Home-Karten zeigen keinen Phantom-Typ Titel mehr|"\n'
    '    "DiscoverFix1: Movie-/Series-Eintraege ohne bekanntes Primary-Poster werden fuer Posterreihen uebersprungen; Navigation V30, Playback und Untertitel bleiben unveraendert|"\n'
)
text = text.replace(changelog_open, changelog_open + notes, 1)

# ---------------------------------------------------------------------------
# Fix A: an actually empty slot must have no title/meta placeholder.
# ---------------------------------------------------------------------------
old_labels = '''                item = (self.dynamic_poster_items or {}).get("poster%d" % i) or {}
                title = item.get("title") or item.get("Name") or ""
'''
new_labels = '''                item = (self.dynamic_poster_items or {}).get("poster%d" % i) or {}
                # EMBYFLOW_HOME_DISCOVERFIX1_START
                # Ein wirklich leerer Slot darf weder einen Phantom-Titel noch
                # den Typ-Fallback "Titel" anzeigen.
                if not item:
                    self["poster_title%d" % i].setText("")
                    self["poster_meta%d" % i].setText("")
                    continue
                # EMBYFLOW_HOME_DISCOVERFIX1_END
                title = item.get("title") or item.get("Name") or ""
'''
if text.count(old_labels) != 1:
    raise SystemExit("update_poster_labels marker mismatch")
text = text.replace(old_labels, new_labels, 1)

# Limit the remaining changes strictly to load_dynamic_posters().
func_start = text.find("    def load_dynamic_posters(self, force_refresh=False):")
func_end = text.find("\n    def load_static_posters_fallback(self):", func_start)
if func_start < 0 or func_end < 0:
    raise SystemExit("load_dynamic_posters boundaries not found")
home_func = text[func_start:func_end]

# Request image tags so Movie/Series items known to lack a Primary poster can
# be rejected before they consume a visible card slot.
old_fields = (
    '"Fields": "PrimaryImageAspectRatio,Overview,Genres,ProductionYear,'
    'RunTimeTicks,UserData,SeriesName,SeriesId,SeasonId,ParentId,'
    'IndexNumber,ParentIndexNumber",'
)
new_fields = (
    '"Fields": "PrimaryImageAspectRatio,Overview,Genres,ProductionYear,'
    'RunTimeTicks,UserData,SeriesName,SeriesId,SeasonId,ParentId,'
    'IndexNumber,ParentIndexNumber,ImageTags",'
)
if home_func.count(old_fields) < 1:
    raise SystemExit("Home Fields marker missing")
home_func = home_func.replace(old_fields, new_fields)

old_remove = '''            def remove_duplicates(source, used):
                out = []

                for item in source or []:
                    keys = item_duplicate_keys(item)
'''
new_remove = '''            def remove_duplicates(source, used):
                out = []

                for item in source or []:
                    if not isinstance(item, dict):
                        continue

                    item_id = str(
                        item.get("Id")
                        or item.get("id")
                        or ""
                    ).strip()
                    item_title = str(
                        item.get("Name")
                        or item.get("title")
                        or item.get("search_term")
                        or ""
                    ).strip()
                    item_type = str(
                        item.get("Type")
                        or item.get("type")
                        or ""
                    ).strip()

                    if not item_id or not item_title:
                        continue

                    if item_type in ("Movie", "Series"):
                        image_tags = item.get("ImageTags")
                        if isinstance(image_tags, dict) and not image_tags.get("Primary"):
                            continue

                        primary_tag = item.get("PrimaryImageTag")
                        if primary_tag is not None and not primary_tag:
                            continue

                    keys = item_duplicate_keys(item)
'''
if home_func.count(old_remove) != 1:
    raise SystemExit("remove_duplicates marker mismatch")
home_func = home_func.replace(old_remove, new_remove, 1)

old_row0 = '''                row2 = remove_duplicates(fetch_items("Movie,Series", 8, None, poster_offset), used)[:2]
                recommended_offset = ((poster_offset + 10) % 40)
                row3 = remove_duplicates(fetch_items("Movie,Series", 12, None, recommended_offset), used)[:2]
                if len(row2) < 2:
                    row2 = remove_duplicates(fetch_items("Movie,Series", 8, None, 0), used)[:2]
                if len(row3) < 2:
                    row3 = remove_duplicates(fetch_items("Movie,Series", 12, None, 4), used)[:2]
'''
new_row0 = '''                row2 = remove_duplicates(
                    fetch_items("Movie,Series", 8, None, poster_offset),
                    used
                )[:2]
                recommended_offset = ((poster_offset + 10) % 40)
                row3 = remove_duplicates(
                    fetch_items("Movie,Series", 12, None, recommended_offset),
                    used
                )[:2]

                # DISCOVERFIX1: fehlende Karten auffuellen, niemals die bereits
                # gefundene erste Karte durch einen neuen Fallback ersetzen.
                if len(row2) < 2:
                    row2 += remove_duplicates(
                        fetch_items("Movie,Series", 12, None, 0),
                        used
                    )[:max(0, 2 - len(row2))]
                if len(row2) < 2:
                    row2 += remove_duplicates(
                        fetch_items("Movie,Series", 12, None, 12),
                        used
                    )[:max(0, 2 - len(row2))]

                if len(row3) < 2:
                    row3 += remove_duplicates(
                        fetch_items("Movie,Series", 12, None, 4),
                        used
                    )[:max(0, 2 - len(row3))]
                if len(row3) < 2:
                    row3 += remove_duplicates(
                        fetch_items("Movie,Series", 12, None, 16),
                        used
                    )[:max(0, 2 - len(row3))]
'''
if home_func.count(old_row0) != 1:
    raise SystemExit("Discover/Recommended fallback block mismatch")
home_func = home_func.replace(old_row0, new_row0, 1)

text = text[:func_start] + home_func + text[func_end:]

# Force one fresh Home-poster generation after update. The user's local test
# did the equivalent by deleting home_posters.json before restart.
cache_func_start = text.find("    def load_cached_posters(self):")
cache_func_end = text.find("\n    def load_dynamic_posters(self, force_refresh=False):", cache_func_start)
if cache_func_start < 0 or cache_func_end < 0:
    raise SystemExit("load_cached_posters boundaries not found")
cache_func = text[cache_func_start:cache_func_end]
old_meta = '            meta = read_json_file(POSTER_CACHE_DIR + "/home_posters.json", {}) or {}\n'
new_meta = old_meta + '''            # DISCOVERFIX1: alte Home-Metadaten einmalig nicht wiederverwenden.
            if int(meta.get("discoverfix1", 0) or 0) != 1:
                return False
'''
if cache_func.count(old_meta) != 1:
    raise SystemExit("home poster cache read marker mismatch")
cache_func = cache_func.replace(old_meta, new_meta, 1)
text = text[:cache_func_start] + cache_func + text[cache_func_end:]

# Add the cache generation marker when the refreshed Home data is persisted.
write_marker = '''                write_json_file(POSTER_CACHE_DIR + "/home_posters.json", {
                    "last_sync": time.strftime("%Y-%m-%d %H:%M"),
                    "last_sync_ts": int(time.time()),
                    "items": self.dynamic_poster_items,
'''
write_replacement = '''                write_json_file(POSTER_CACHE_DIR + "/home_posters.json", {
                    "last_sync": time.strftime("%Y-%m-%d %H:%M"),
                    "last_sync_ts": int(time.time()),
                    "discoverfix1": 1,
                    "items": self.dynamic_poster_items,
'''
if text.count(write_marker) != 1:
    raise SystemExit("home poster cache write marker mismatch")
text = text.replace(write_marker, write_replacement, 1)

# Navigation must be exactly unchanged, not merely present.
new_nav_start = text.find(NAV_START)
new_nav_end = text.find(NAV_END, new_nav_start)
if new_nav_start < 0 or new_nav_end < 0:
    raise SystemExit("Navigation V30 block lost")
new_nav_end += len(NAV_END)
if text[new_nav_start:new_nav_end] != nav_baseline:
    raise SystemExit("DiscoverFix1 changed Navigation V30 block")

# Explicitly guard against accidentally importing any experimental PGS fixes.
protected_markers = (
    "EMBYFLOW_PGS_HLS_RETRY_PROXY_FIX",
    "PGS_HLS_RETRY_PROXY",
    "TRANSCODE_RECOVERY",
    "UTFIX16",
    "UTFIX17",
    "UTFIX18",
    "UTFIX19",
)
for needle in protected_markers:
    if text.count(needle) != baseline.count(needle):
        raise SystemExit("DiscoverFix1 changed protected playback marker count: %s" % needle)

for required in (
    "# EMBYFLOW_HOME_DISCOVERFIX1_START",
    "# EMBYFLOW_HOME_DISCOVERFIX1_END",
    '"discoverfix1": 1',
    'IndexNumber,ParentIndexNumber,ImageTags',
):
    if required not in text:
        raise SystemExit("DiscoverFix1 required marker missing: %s" % required)

compile(text, str(NEW_PLUGIN), "exec")
NEW_PLUGIN.write_text(text, encoding="utf-8")
sha256 = hashlib.sha256(NEW_PLUGIN.read_bytes()).hexdigest()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
if int(manifest.get("build", 0)) != 2026091301:
    raise SystemExit("update.json baseline build mismatch")
if manifest.get("version") != OLD_VERSION:
    raise SystemExit("update.json baseline version mismatch")

manifest["version"] = NEW_VERSION
manifest["build"] = 2026091303
manifest["channel"] = "rcdev"
manifest["download"] = (
    "https://raw.githubusercontent.com/keggy6893/"
    "EmbyFlowE2-Updates/build-2026091303/"
    "plugin_RCDEV12_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py"
)
manifest["sha256"] = sha256
manifest["target"] = "plugin.py"
manifest["artifact_type"] = "plugin_py"
release_notes = [
    "DiscoverFix1: Entdecken fuellt fehlende zweite Karten auf, statt eine vorhandene Karte zu ersetzen",
    "DiscoverFix1: leere Home-Slots zeigen keinen Phantom-Typ Titel mehr; Movie-/Series-Eintraege ohne bekanntes Primary-Poster werden uebersprungen",
    "DiscoverFix1: Home-Poster-Cache wird einmalig frisch aufgebaut; Navigation V30, Playback und Untertitel bleiben unveraendert",
]
manifest["changelog"] = release_notes + list(manifest.get("changelog") or [])
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("CHECK DiscoverFix1 plugin OK")
print("release_file=%s" % NEW_PLUGIN)
print("sha256=%s" % sha256)
print("size=%s" % NEW_PLUGIN.stat().st_size)

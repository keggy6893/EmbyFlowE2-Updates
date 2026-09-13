from pathlib import Path
import hashlib
import json

OLD_PLUGIN = Path("plugin_RCDEV13_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_NAVREAD1_ARROWVIS2_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py")
NEW_PLUGIN = Path("plugin_RCDEV14_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_NAVREAD1_ARROWVIS2_SERVERLOADFIX1_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py")
MANIFEST = Path("update.json")

OLD_VERSION = "2026-RCDEV13-SERVERSAFE1-DREAMSAFE2-LOGINV21-FAVRES28-NAVV30-DISCOVERFIX1-NAVREAD1-ARROWVIS2-PUBLICCLEAN1"
NEW_VERSION = "2026-RCDEV14-SERVERSAFE1-DREAMSAFE2-LOGINV21-FAVRES28-NAVV30-DISCOVERFIX1-NAVREAD1-ARROWVIS2-SERVERLOADFIX1-PUBLICCLEAN1"
OLD_BUILD = "PLUGIN_UPDATE_BUILD = 2026091304"
NEW_BUILD = "PLUGIN_UPDATE_BUILD = 2026091305"
EXPECTED_BASE_SHA256 = "af7d1f09d071f4bf3f48a2476ece04ec6dd7ca3a3f4553cd9dbb4c3fc8d0dbe5"

for required in (OLD_PLUGIN, MANIFEST):
    if not required.is_file():
        raise SystemExit("required release input missing: %s" % required)
if NEW_PLUGIN.exists():
    raise SystemExit("1305 release plugin already exists")

base_bytes = OLD_PLUGIN.read_bytes()
base_sha = hashlib.sha256(base_bytes).hexdigest()
if base_sha != EXPECTED_BASE_SHA256:
    raise SystemExit("1304 baseline SHA mismatch: %s" % base_sha)

baseline = base_bytes.decode("utf-8")
if 'PLUGIN_VERSION = "%s"' % OLD_VERSION not in baseline:
    raise SystemExit("1304 baseline version marker missing")
if OLD_BUILD not in baseline:
    raise SystemExit("1304 baseline build marker missing")
for marker in (
    "# EMBYFLOW_HOME_DISCOVERFIX1_START",
    "# EMBYFLOW_NAV_GROUPS_V30_START",
    "# EMBYFLOW_NAV_READABILITY1",
    "# EMBYFLOW_NAV_ARROWVIS2",
):
    if marker not in baseline:
        raise SystemExit("required 1304 marker missing: %s" % marker)

text = baseline.replace(
    'PLUGIN_VERSION = "%s"' % OLD_VERSION,
    'PLUGIN_VERSION = "%s"' % NEW_VERSION,
    1,
)
text = text.replace(OLD_BUILD, NEW_BUILD, 1)

changelog_open = "PLUGIN_UPDATE_CHANGELOG = (\n"
if changelog_open not in text:
    raise SystemExit("PLUGIN_UPDATE_CHANGELOG marker missing")
notes = (
    '    "SERVERLOADFIX1: nach Kaltstart werden nur leere Runtime-Verbindungswerte aus bereits vorhandenen /etc/enigma2/settings wieder eingelesen|"\n'
    '    "SERVERLOADFIX1 arbeitet read-only: keine Zugangsdaten werden geloescht, ueberschrieben oder automatisch gespeichert|"\n'
    '    "SERVERLOADFIX1 auf VU+ nach Enigma2-Neustart und echtem Deep-Standby/Kaltstart bestaetigt; Playback und Untertitel bleiben unveraendert|"\n'
)
text = text.replace(changelog_open, changelog_open + notes, 1)

anchor = 'config.embyflow.api_key = ConfigText(default="", fixed_size=False)\n\n'
if text.count(anchor) != 1:
    raise SystemExit("server config insertion anchor mismatch")

fix = r'''# EMBYFLOW_SERVERLOADFIX1_START
# Einige Enigma2-Images koennen nach einem Kaltstart leere Runtime-ConfigText-
# Werte liefern, obwohl config.embyflow.* bereits in /etc/enigma2/settings
# persistiert ist. Nur fehlende Runtime-Verbindungswerte werden read-only aus
# dieser Datei wiederhergestellt. Kein persistierender Schreibzugriff.
def _embyflow_serverloadfix1_hydrate_missing_runtime_values():
    settings_path = "/etc/enigma2/settings"
    key_to_attr = {
        "config.embyflow.server": "server",
        "config.embyflow.server_slot_1": "server_slot_1",
        "config.embyflow.server_slot_2": "server_slot_2",
        "config.embyflow.server_slot_3": "server_slot_3",
        "config.embyflow.server_slot_4": "server_slot_4",
        "config.embyflow.username": "username",
        "config.embyflow.password": "password",
        "config.embyflow.api_key": "api_key",
    }

    missing = {}
    for key, attr in key_to_attr.items():
        try:
            item = getattr(config.embyflow, attr)
            current = str(getattr(item, "value", "") or "")
        except Exception:
            current = ""
        if not current:
            missing[key] = attr

    if not missing:
        return 0

    persisted = {}
    try:
        with open(settings_path, "r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                line = raw_line.rstrip("\r\n")
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key in missing and value:
                    persisted[key] = value
    except Exception:
        return 0

    restored = 0
    for key, attr in missing.items():
        value = persisted.get(key, "")
        if not value:
            continue
        try:
            item = getattr(config.embyflow, attr)
            try:
                item.setValue(value)
            except Exception:
                item.value = value
            restored += 1
        except Exception:
            pass
    return restored


_EMBYFLOW_SERVERLOADFIX1_RESTORED = (
    _embyflow_serverloadfix1_hydrate_missing_runtime_values()
)
# EMBYFLOW_SERVERLOADFIX1_END

'''
text = text.replace(anchor, anchor + fix, 1)

for required in (
    "# EMBYFLOW_SERVERLOADFIX1_START",
    "# EMBYFLOW_SERVERLOADFIX1_END",
    '_embyflow_serverloadfix1_hydrate_missing_runtime_values',
    'settings_path = "/etc/enigma2/settings"',
    "# EMBYFLOW_HOME_DISCOVERFIX1_START",
    "# EMBYFLOW_NAV_GROUPS_V30_START",
    "# EMBYFLOW_NAV_READABILITY1",
    "# EMBYFLOW_NAV_ARROWVIS2",
):
    if required not in text:
        raise SystemExit("required 1305 marker missing: %s" % required)

# The tested fix is deliberately read-only. Keep write/save calls out of its block.
fix_start = text.index("# EMBYFLOW_SERVERLOADFIX1_START")
fix_end = text.index("# EMBYFLOW_SERVERLOADFIX1_END", fix_start)
fix_block = text[fix_start:fix_end]
for forbidden in ("configfile.save(", ".save()", 'open(settings_path, "w"', "open(settings_path, 'w'"):
    if forbidden in fix_block:
        raise SystemExit("SERVERLOADFIX1 unexpectedly writes configuration: %s" % forbidden)

# No experimental PGS/session-recovery code may enter this release.
for needle in (
    "UTFIX16",
    "UTFIX17",
    "UTFIX18",
    "UTFIX19",
    "UTFIX20",
    "PGS_HLS_RETRY_PROXY",
    "TRANSCODE_RECOVERY",
):
    if text.count(needle) != baseline.count(needle):
        raise SystemExit("1305 changed protected playback marker count: %s" % needle)

# Existing 1304 feature markers must remain byte-for-byte present/count-stable.
for needle in (
    "# EMBYFLOW_HOME_DISCOVERFIX1_START",
    "# EMBYFLOW_HOME_DISCOVERFIX1_END",
    '"discoverfix1": 1',
    "# EMBYFLOW_NAV_GROUPS_V30_START",
    "# EMBYFLOW_NAV_GROUPS_V30_END",
    "# EMBYFLOW_NAV_READABILITY1",
    "# EMBYFLOW_NAV_ARROWVIS2",
):
    if text.count(needle) != baseline.count(needle):
        raise SystemExit("1305 changed stable marker count: %s" % needle)

compile(text, str(NEW_PLUGIN), "exec")
NEW_PLUGIN.write_text(text, encoding="utf-8")
sha256 = hashlib.sha256(NEW_PLUGIN.read_bytes()).hexdigest()

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
if int(manifest.get("build", 0)) != 2026091304:
    raise SystemExit("update.json baseline build mismatch")
if manifest.get("version") != OLD_VERSION:
    raise SystemExit("update.json baseline version mismatch")

manifest["version"] = NEW_VERSION
manifest["build"] = 2026091305
manifest["channel"] = "rcdev"
manifest["download"] = (
    "https://raw.githubusercontent.com/keggy6893/"
    "EmbyFlowE2-Updates/build-2026091305/"
    "plugin_RCDEV14_SERVERSAFE1_LOGINV21_FAVRES28_NAVV30_DISCOVERFIX1_NAVREAD1_ARROWVIS2_SERVERLOADFIX1_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py"
)
manifest["sha256"] = sha256
manifest["target"] = "plugin.py"
manifest["artifact_type"] = "plugin_py"
release_notes = [
    "SERVERLOADFIX1: nach Kaltstart werden nur leere Runtime-Verbindungswerte aus vorhandenen /etc/enigma2/settings wieder eingelesen",
    "SERVERLOADFIX1 ist read-only und schreibt oder loescht keine gespeicherten Zugangsdaten",
    "Auf VU+ nach GUI-Neustart und Deep-Standby/Kaltstart bestaetigt; Playback und Untertitel bleiben unveraendert",
]
manifest["changelog"] = release_notes + list(manifest.get("changelog") or [])
MANIFEST.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

print("CHECK SERVERLOADFIX1 1305 plugin OK")
print("release_file=%s" % NEW_PLUGIN)
print("sha256=%s" % sha256)
print("size=%s" % NEW_PLUGIN.stat().st_size)

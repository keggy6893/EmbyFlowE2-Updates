from pathlib import Path
import hashlib
import json

PLUGIN = Path("plugin_RCDEV7_SERVERSAFE1_LOGINREF17_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py")
MANIFEST = Path("update.json")
EXPECTED_BEFORE = "eaabd2266087b4d1ed9cb858cd3e67985049d14de7d25f2b098c2b4c14c9a6fd"

raw = PLUGIN.read_bytes()
got_before = hashlib.sha256(raw).hexdigest()
if got_before != EXPECTED_BEFORE:
    raise SystemExit("Unexpected 0623 baseline sha256: %s" % got_before)

text = raw.decode("utf-8")


def one(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit("%s marker mismatch: %s" % (label, count))
    text = text.replace(old, new, 1)


one(
    "PLUGIN_UPDATE_BUILD = 2026090623",
    "PLUGIN_UPDATE_BUILD = 2026090624",
    "build",
)

one(
    'Kapitelansicht V18: sechs Bildkarten, sofortige lokale Artwork-Platzhalter und echte Kapitelbilder im Hintergrund"',
    'Kapitelansicht V18: sechs Bildkarten, sofortige lokale Artwork-Platzhalter und echte Kapitelbilder im Hintergrund|"\n'
    '    "Kapitelbilder V18: kein 6er-Vorladen mehr; nur das ausgewählte fehlende Kapitelbild wird erzeugt"',
    "embedded changelog",
)

marker = "\ndef _embyflow_chapter_cards_v18_open(self):\n"
if text.count(marker) != 1:
    raise SystemExit("V18 open marker mismatch")
if "EMBYFLOW_CHAPTER_CARDS_V18_SINGLE_SELECTED_0624" in text:
    raise SystemExit("0624 patch already present")

patch = r'''

# EMBYFLOW_CHAPTER_CARDS_V18_SINGLE_SELECTED_0624
# V18 keeps all six visible cards and immediate cached/fallback artwork, but
# frame extraction is demand-driven: only the selected chapter may be queued.
_EMBYFLOW_V18_0624_REFRESH_ORIGINAL = EmbyFlowChapterNavigatorV18._refresh_carousel_v17


def _embyflow_v18_0624_refresh_single_selected(self):
    starter = getattr(self, "_maybe_start_carousel_preview_v17", None)
    shadowed = False
    try:
        # The original V18 refresh builds the six-card UI and queue. Suppress
        # its immediate starter until that queue has been reduced to one item.
        setattr(self, "_maybe_start_carousel_preview_v17", lambda: None)
        shadowed = True
        _EMBYFLOW_V18_0624_REFRESH_ORIGINAL(self)
    finally:
        if shadowed:
            try:
                delattr(self, "_maybe_start_carousel_preview_v17")
            except Exception:
                try:
                    setattr(self, "_maybe_start_carousel_preview_v17", starter)
                except Exception:
                    pass

    try:
        selected = int(getattr(self, "selected", 0) or 0)
    except Exception:
        selected = 0

    selected_request = None
    for request in list(getattr(self, "_carousel_queue", []) or []):
        try:
            # generation, visible-slot, chapter-index, chapter, output-path
            if int(request[2]) == selected:
                selected_request = request
                break
        except Exception:
            continue

    self._carousel_queue = [selected_request] if selected_request is not None else []

    try:
        if self._carousel_queue or bool(getattr(self, "_carousel_busy", False)):
            self["status_text"].setText("Kapitelbild wird vorbereitet …")
        else:
            current = str(self["status_text"].getText() or "")
            if current in (
                "Echte Kapitelbilder werden im Hintergrund vorbereitet …",
                "Kapitelbild wird vorbereitet …",
            ):
                self["status_text"].setText("")
    except Exception:
        pass

    try:
        self._maybe_start_carousel_preview_v17()
    except Exception:
        pass


EmbyFlowChapterNavigatorV18._refresh_carousel_v17 = (
    _embyflow_v18_0624_refresh_single_selected
)
# EMBYFLOW_CHAPTER_CARDS_V18_SINGLE_SELECTED_0624_RELEASE
'''

text = text.replace(marker, patch + marker, 1)
PLUGIN.write_text(text, encoding="utf-8", newline="\n")
final_sha = hashlib.sha256(PLUGIN.read_bytes()).hexdigest()
print("Final plugin sha256:", final_sha)

data = json.loads(MANIFEST.read_text(encoding="utf-8"))
if int(data.get("build") or 0) != 2026090623:
    raise SystemExit("Unexpected manifest baseline build: %s" % data.get("build"))

data["build"] = 2026090624
data["download"] = (
    "https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/"
    "build-2026090624/"
    "plugin_RCDEV7_SERVERSAFE1_LOGINREF17_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py"
)
data["sha256"] = final_sha
changelog = list(data.get("changelog") or [])
msg = "Kapitelbilder V18: kein 6er-Vorladen mehr; nur das ausgewählte fehlende Kapitelbild wird erzeugt"
if msg not in changelog:
    changelog.append(msg)
data["changelog"] = changelog
MANIFEST.write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)

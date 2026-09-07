from pathlib import Path
import hashlib
import json

plugin = Path('plugin_RCDEV7_SERVERSAFE1_LOGINREF17_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py')
manifest = Path('update.json')
text = plugin.read_text(encoding='utf-8')

if text.count('PLUGIN_UPDATE_BUILD = 2026090633') != 1:
    raise SystemExit('0633 baseline build marker mismatch')
if '# EMBYFLOW_SERVER_MANAGER_UI_V2_0632_RELEASE' not in text:
    raise SystemExit('0632 server manager base marker missing')
if '# EMBYFLOW_SERVER_MANAGER_UI_V3_MENULIST_0634_RELEASE' in text:
    raise SystemExit('0634 MenuList manager already present')

if 'from Components.MenuList import MenuList' not in text:
    needle = 'from Components.Label import Label\n'
    if needle not in text:
        raise SystemExit('Label import anchor missing')
    text = text.replace(
        needle,
        needle + 'from Components.MenuList import MenuList\n',
        1,
    )

patch = r'''

# EMBYFLOW_SERVER_MANAGER_UI_V3_MENULIST_0634_RELEASE
# 0632/0633 zeigten auf einzelnen OpenATV-Images zwar den statischen Skin,
# aber keine dynamischen Label-Komponenten. V3 verwendet deshalb für ALLE
# variablen Inhalte einen echten Enigma2-MenuList-Unterbau. Keine ChoiceBox,
# keine Playback-/Serverlogikänderung.
class EmbyFlowServerManageScreenV3List(Screen):
    skin = scale_skin("""
    <screen name="EmbyFlowServerManageScreenV3List" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#030811">
        <eLabel position="0,0" size="1920,1080" backgroundColor="#030811" />

        <eLabel text="EMBY" position="92,58" size="210,58" font="Bold;46" foregroundColor="#23E6E8" backgroundColor="#030811" transparent="1" />
        <eLabel text="FLOW" position="302,58" size="210,58" font="Bold;46" foregroundColor="#FF42B5" backgroundColor="#030811" transparent="1" />
        <eLabel text="SERVERVERWALTUNG" position="96,122" size="470,34" font="Regular;20" foregroundColor="#8D96A1" backgroundColor="#030811" transparent="1" />
        <eLabel text="0634" position="1640,66" size="190,34" font="Regular;20" foregroundColor="#23E6E8" backgroundColor="#030811" transparent="1" halign="right" />
        <eLabel position="90,184" size="1740,2" backgroundColor="#1689FF" />

        <eLabel position="190,235" size="1540,690" backgroundColor="#07111E" />
        <eLabel position="194,239" size="1532,682" backgroundColor="#050C16" />

        <widget name="menu" position="260,286" size="1380,500" font="Regular;30" itemHeight="92" foregroundColor="#EAF1F8" foregroundColorSelected="#FFFFFF" backgroundColor="#050C16" backgroundColorSelected="#1689FF" transparent="0" scrollbarMode="showNever" />

        <eLabel text="ROT  Zurück" position="260,864" size="320,34" font="Regular;21" foregroundColor="#FF6B79" backgroundColor="#050C16" transparent="1" />
        <eLabel text="OK / GRÜN  Auswählen" position="600,864" size="430,34" font="Regular;21" foregroundColor="#42E66B" backgroundColor="#050C16" transparent="1" />
        <eLabel text="▲ / ▼  Navigieren" position="1170,864" size="470,34" font="Regular;21" foregroundColor="#8D96A1" backgroundColor="#050C16" transparent="1" halign="right" />
    </screen>
    """)

    def __init__(self, session, slot_index, server_url, active=False):
        Screen.__init__(self, session)
        self.slot_index = max(0, min(3, int(slot_index)))
        self.server_url = str(server_url or "").strip()
        self.active = bool(active)
        self.confirming = False
        self["menu"] = MenuList(
            self._main_entries(),
            enableWrapAround=True,
        )
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "cancel": self.go_back,
                "red": self.go_back,
                "ok": self.activate,
                "green": self.activate,
                "up": self.move_up,
                "down": self.move_down,
                "left": self.move_up,
                "right": self.move_down,
            },
            -1,
        )

    def _safe_url(self):
        value = str(self.server_url or "").strip()
        try:
            value = re.sub(
                r"(?i)(https?://)[^/@\s]+:[^/@\s]+@",
                r"\1•••:•••@",
                value,
            )
        except Exception:
            pass
        if len(value) > 58:
            value = value[:55] + "..."
        return value

    def _main_entries(self):
        number = self.slot_index + 1
        state = "AKTIV" if self.active else "BEREIT"
        url = self._safe_url() or "keine Adresse"
        return [
            "SERVER %d  •  %s  —  %s" % (number, state, url),
            "Server %d verwenden" % number,
            "Server %d bearbeiten" % number,
            "Server %d löschen" % number,
            "Zurück",
        ]

    def _confirm_entries(self):
        number = self.slot_index + 1
        return [
            "SERVER %d WIRKLICH LÖSCHEN?" % number,
            "Nein — Server behalten",
            "Ja — Server endgültig löschen",
        ]

    def _set_entries(self, entries, index=0):
        self["menu"].setList(list(entries or []))
        try:
            self["menu"].moveToIndex(max(0, int(index)))
        except Exception:
            pass

    def move_up(self):
        try:
            self["menu"].up()
        except Exception:
            pass

    def move_down(self):
        try:
            self["menu"].down()
        except Exception:
            pass

    def _selected_index(self):
        try:
            return int(self["menu"].getSelectedIndex())
        except Exception:
            return 0

    def go_back(self):
        if self.confirming:
            self.confirming = False
            self._set_entries(self._main_entries(), 3)
            return
        self.close(None)

    def activate(self):
        index = self._selected_index()
        if self.confirming:
            if index == 2:
                self.close(("delete", self.slot_index))
                return
            if index in (0, 1):
                self.confirming = False
                self._set_entries(self._main_entries(), 3)
                return
            return

        if index == 0:
            try:
                self["menu"].moveToIndex(1)
            except Exception:
                pass
            return
        if index == 1:
            self.close(("use", self.slot_index))
            return
        if index == 2:
            self.close(("edit", self.slot_index))
            return
        if index == 3:
            self.confirming = True
            self._set_entries(self._confirm_entries(), 1)
            return
        self.close(None)


def _embyflow_server_manager_v3_open(self):
    index = _embyflow_server_manager_v1_selected_index(self)
    current = str(self.server_slots[index] or "").strip()
    if not current:
        self.edit_server_slot(index)
        return

    active = ""
    try:
        active = self._cfg(config.embyflow.server).strip().rstrip("/")
    except Exception:
        pass
    is_active = bool(
        active and current.rstrip("/").casefold() == active.casefold()
    )

    self.session.openWithCallback(
        self._embyflow_server_manager_v3_result,
        EmbyFlowServerManageScreenV3List,
        index,
        current,
        is_active,
    )


def _embyflow_server_manager_v3_result(self, result=None):
    if not result:
        return
    try:
        action, index = result
        index = max(0, min(3, int(index)))
    except Exception:
        return

    if action == "use":
        self._select_server(index)
        return
    if action == "edit":
        self.edit_server_slot(index)
        return
    if action == "delete":
        self._embyflow_server_manager_v1_pending_delete = index
        self._embyflow_server_manager_v1_delete_done(True)
        return


EmbyFlowConnectionWizard.manage_server_slot = _embyflow_server_manager_v3_open
EmbyFlowConnectionWizard._embyflow_server_manager_v3_result = _embyflow_server_manager_v3_result
'''

text += patch
text = text.replace(
    'PLUGIN_UPDATE_BUILD = 2026090633',
    'PLUGIN_UPDATE_BUILD = 2026090634',
    1,
)
plugin.write_text(text, encoding='utf-8', newline='\n')

final_sha = hashlib.sha256(plugin.read_bytes()).hexdigest()
data = json.loads(manifest.read_text(encoding='utf-8'))
if int(data.get('build') or 0) != 2026090633:
    raise SystemExit('manifest baseline mismatch: %r' % data.get('build'))
data['build'] = 2026090634
data['download'] = 'https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/build-2026090634/plugin_RCDEV7_SERVERSAFE1_LOGINREF17_DREAMSAFE2_HTTPPOOL_PUBLICCLEAN1.py'
data['sha256'] = final_sha
changelog = list(data.get('changelog') or [])
messages = [
    'Serververwaltung 0634: dynamische Label-Menüs durch robusten Enigma2-MenuList-Unterbau ersetzt',
    'MenuList 0634: Serverstatus, URL und alle Aktionen werden in einer einzigen sicher gerenderten Liste dargestellt',
    'EmbyFlow-Design bleibt erhalten; keine native blaue ChoiceBox und keine Änderung an Playback-/Serverlogik',
]
for msg in messages:
    if msg not in changelog:
        changelog.append(msg)
data['changelog'] = changelog
manifest.write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8',
    newline='\n',
)
print('Final plugin sha256:', final_sha)

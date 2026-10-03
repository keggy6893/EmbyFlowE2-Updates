from pathlib import Path
import ast
import types
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
class Screen(dict):
    def __init__(self, session, parent=None):
        self.session = session
        self.onShow, self.onHide, self.onClose = [], [], []
    def createSummary(self):
        return 'original'
class Label:
    def __init__(self, text=''): self.text = text
    def setText(self, text): self.text = text
class Progress:
    def setRange(self, value): self.range = value
    def setValue(self, value): self.value = value
class Timer:
    def __init__(self): self.callback, self.running = [], False
    def start(self, interval): self.running = True
    def stop(self): self.running = False
dimensions = [400, 240]
size = types.SimpleNamespace(width=lambda:dimensions[0], height=lambda:dimensions[1])
display = lambda number: types.SimpleNamespace(size=lambda:size)
setting = types.SimpleNamespace(value=False)
config = types.SimpleNamespace(embyflow=types.SimpleNamespace(box_display=setting))
class Player(Screen): pass
ns = dict(Screen=Screen, EmbyFlowMoviePlayer=Player, config=config,
          _EFDisplayLabel=Label, _EFDisplayProgress=Progress,
          _EFDisplayDesktop=display, _EFDisplayTimer=Timer)
tree = ast.parse((root/'release_tools/boxdisplay_0303.inc.py').read_text())
tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
exec(compile(tree,'display','exec'), ns)
player = Player(None)
assert player.createSummary() == 'original'
setting.value = True
assert player.createSummary() is ns['_EFDisplaySummary']
dimensions[:] = [0, 0]
assert player.createSummary() == 'original'
dimensions[:] = [400, 240]
state = [81*90000, 8590*90000]
seek = types.SimpleNamespace(getPlayPosition=lambda:(0,state[0]),getLength=lambda:(0,state[1]))
service = types.SimpleNamespace(seek=lambda:seek)
session = types.SimpleNamespace(nav=types.SimpleNamespace(getCurrentService=lambda:service))
player.title_text, player.paused = 'James Bond 007 - Skyfall', False
summary = ns['_EFDisplaySummary'](session,player)
summary.begin()
assert summary['times'].text == '1:21 / 2:23:10'
assert summary['remaining'].text == 'Noch 2:21:49'
assert summary['status'].text == 'Wiedergabe'
player.paused = True
summary.refresh()
assert summary['status'].text == 'PAUSE'
state[0] = state[1]*2
summary.refresh()
assert summary['progress'].value == 100
assert summary['remaining'].text == 'Noch 0:00'
state[1] = 0
summary.refresh()
assert summary['remaining'].text == 'Noch --:--'
summary.onClose[0]()
assert not summary.timer.running
for dims in ([400,240], [132,64], [800,480]):
    dimensions[:] = dims
    summary = ns['_EFDisplaySummary'](session, player)
    skin = ET.fromstring(summary.skin)
    for widget in skin.findall('widget'):
        x,y = map(int,widget.attrib['position'].split(','))
        w,h = map(int,widget.attrib['size'].split(','))
        assert x+w <= dims[0] and y+h <= dims[1]
    assert skin.find("widget[@name='title']").attrib['foregroundColor'] == '#ffffff'
artifact = (root/'EmbyFlowE2_Boxdisplay_20261003_0303.py').read_text()
assert 'config.embyflow.box_display = ConfigYesNo(default=False)' in artifact
assert artifact.count('getConfigListEntry("Boxdisplay: Titel und Wiedergabezeiten", config.embyflow.box_display)') == 1
assert '# EMBYFLOW_TRAILER_FAILURE_CACHE_LOCAL1' in artifact
print('PASS: optional default, fallback, display times, pause, lifecycle, layout and trailer cache preserved')

class Settings(Screen):
    skin = '<screen><widget name="debug_value" position="722,528"/><widget name="api_value" position="722,665"/><widget name="middle_help" position="715,746"/></screen>'
    def __init__(self, session):
        super().__init__(session)
        self.focus = 0
        self['middle_help'] = Label()
    def refresh_all(self): self._focus_target()
    def _onoff(self, value): return 'AN' if value else 'AUS'
    def _focus_target(self): return (0,0)
    def _toggle_current(self): self.old_toggle = True
    def move_left(self): self.old_left = True
    def move_right(self): self.old_right = True
    def activate(self): self.old_activate = True
    def _set_value(self, item, value): item.value = value
    def save_settings(self, close_after=False): self.saved = True
setting.save = lambda:None
ns = dict(EmbyFlowAdvancedSettingsNeon=Settings, config=config, Label=Label)
exec((root/'release_tools/boxdisplay_settings_0303.inc.py').read_text(), ns)
setting.value = False
screen = Settings(None)
visited = []
for i in range(8):
    visited.append(screen.focus)
    screen.move_down()
assert visited == [0,6,1,2,3,4,7,5] and screen.focus == 0
screen.focus = 7
screen.activate()
assert screen.box_display and not setting.value
assert 'AN' in screen['box_display_value'].text
screen.move_left()
assert not screen.box_display
screen.move_right()
screen.save_settings()
assert setting.value and screen.saved
screen.focus = 3
assert screen._focus_target() == (688,503)
screen.focus = 4
assert screen._focus_target() == (688,615)
screen.focus = 6
screen.activate()
assert screen.old_activate
skin = ET.fromstring(Settings.skin)
assert skin.find("widget[@name='box_display_value']") is not None
assert '# EMBYFLOW_BOXDISPLAY_NEON_SETTINGS_0303' in artifact
print('PASS: advanced settings navigation, toggle without premature save, persistence and existing controls')

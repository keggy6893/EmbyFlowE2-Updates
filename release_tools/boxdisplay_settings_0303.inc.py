# EMBYFLOW_BOXDISPLAY_NEON_SETTINGS_0303
import xml.etree.ElementTree as _ef_display_et
_ef_display_settings_skin = _ef_display_et.fromstring(EmbyFlowAdvancedSettingsNeon.skin)
for _node in _ef_display_settings_skin:
    _name, _text, _pos = _node.get('name', ''), _node.get('text', ''), _node.get('position', '')
    if _name == 'debug_value':
        _node.set('position', '722,503')
    elif _text == 'Debug-Log':
        _node.set('position', '715,450')
    elif _pos == '705,517':
        _node.set('position', '705,492')
    elif _name == 'api_value':
        _node.set('position', '722,615')
    elif _text == 'API-Key (optional)':
        _node.set('position', '715,560')
    elif _pos == '705,652':
        _node.set('position', '705,602')
    elif _name == 'middle_help':
        _node.attrib.update(position='715,780', size='470,52')
_ef_display_et.SubElement(_ef_display_settings_skin, 'eLabel', {
    'text': 'Boxdisplay', 'position': '715,670', 'size': '470,34',
    'font': 'Regular;22', 'foregroundColor': '#F4F7FB', 'transparent': '1'})
_ef_display_et.SubElement(_ef_display_settings_skin, 'eLabel', {
    'position': '705,712', 'size': '500,60', 'backgroundColor': '#0A1627'})
_ef_display_et.SubElement(_ef_display_settings_skin, 'widget', {
    'name': 'box_display_value', 'position': '722,725', 'size': '466,38',
    'zPosition': '6', 'font': 'Bold;22', 'foregroundColor': '#b54ce8',
    'backgroundColor': '#0A1627', 'transparent': '1', 'valign': 'center'})
EmbyFlowAdvancedSettingsNeon.skin = _ef_display_et.tostring(_ef_display_settings_skin, encoding='unicode')

_ef_display_settings_init = EmbyFlowAdvancedSettingsNeon.__init__
_ef_display_settings_refresh = EmbyFlowAdvancedSettingsNeon.refresh_all
_ef_display_settings_target = EmbyFlowAdvancedSettingsNeon._focus_target
_ef_display_settings_toggle = EmbyFlowAdvancedSettingsNeon._toggle_current
_ef_display_settings_left = EmbyFlowAdvancedSettingsNeon.move_left
_ef_display_settings_right = EmbyFlowAdvancedSettingsNeon.move_right
_ef_display_settings_activate = EmbyFlowAdvancedSettingsNeon.activate
_ef_display_settings_save = EmbyFlowAdvancedSettingsNeon.save_settings

def _ef_display_settings_init_new(self, session):
    self.box_display = bool(config.embyflow.box_display.value)
    _ef_display_settings_init(self, session)
    self['box_display_value'] = Label('')

def _ef_display_settings_refresh_new(self):
    _ef_display_settings_refresh(self)
    self['box_display_value'].setText(('> ' if self.focus == 7 else '') + self._onoff(self.box_display) + (' <' if self.focus == 7 else ''))
    if self.focus == 7:
        self['middle_help'].setText('Titel und Wiedergabezeiten auf dem Boxdisplay. Mit Gruen speichern; ab naechster Wiedergabe.')

def _ef_display_settings_target_new(self):
    return {3: (688,503), 4: (688,615), 7: (688,725)}.get(self.focus, _ef_display_settings_target(self))

def _ef_display_settings_up(self):
    order = (0,6,1,2,3,4,7,5)
    self.focus = order[(order.index(self.focus)-1) % len(order)]
    self.refresh_all()

def _ef_display_settings_down(self):
    order = (0,6,1,2,3,4,7,5)
    self.focus = order[(order.index(self.focus)+1) % len(order)]
    self.refresh_all()

def _ef_display_settings_toggle_new(self):
    if self.focus == 7:
        self.box_display = not self.box_display
        self.refresh_all()
    else:
        _ef_display_settings_toggle(self)

def _ef_display_settings_left_new(self):
    if self.focus == 7:
        self._toggle_current()
    else:
        _ef_display_settings_left(self)

def _ef_display_settings_right_new(self):
    if self.focus == 7:
        self._toggle_current()
    else:
        _ef_display_settings_right(self)

def _ef_display_settings_activate_new(self):
    if self.focus == 7:
        self._toggle_current()
    else:
        _ef_display_settings_activate(self)

def _ef_display_settings_save_new(self, close_after=False):
    self._set_value(config.embyflow.box_display, bool(self.box_display))
    config.embyflow.box_display.save()
    return _ef_display_settings_save(self, close_after=close_after)

EmbyFlowAdvancedSettingsNeon.__init__ = _ef_display_settings_init_new
EmbyFlowAdvancedSettingsNeon.refresh_all = _ef_display_settings_refresh_new
EmbyFlowAdvancedSettingsNeon._focus_target = _ef_display_settings_target_new
EmbyFlowAdvancedSettingsNeon.move_up = _ef_display_settings_up
EmbyFlowAdvancedSettingsNeon.move_down = _ef_display_settings_down
EmbyFlowAdvancedSettingsNeon._toggle_current = _ef_display_settings_toggle_new
EmbyFlowAdvancedSettingsNeon.move_left = _ef_display_settings_left_new
EmbyFlowAdvancedSettingsNeon.move_right = _ef_display_settings_right_new
EmbyFlowAdvancedSettingsNeon.activate = _ef_display_settings_activate_new
EmbyFlowAdvancedSettingsNeon.save_settings = _ef_display_settings_save_new

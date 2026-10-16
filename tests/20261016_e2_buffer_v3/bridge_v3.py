
# EMBYFLOW_OPTIONAL_RAM_BUFFER_TEST_V1
# Opt-in only; native Player, original URLs for Emby reports and server guard retained.
import json as _efb_json
_EFB_SETTINGS = '/etc/enigma2/embyflow_buffer_v1.json'
_efb_proxy = None
_efb_test_next = False


def _efb_enabled():
    try:
        with open(_EFB_SETTINGS, 'r') as handle:
            return _efb_json.load(handle).get('enabled') is True
    except Exception:
        return False


def _efb_save(enabled):
    temporary = _EFB_SETTINGS + '.tmp'
    with open(temporary, 'w') as handle:
        _efb_json.dump({'enabled': bool(enabled)}, handle)
    os.replace(temporary, _EFB_SETTINGS)


def _efb_reference(reference, url):
    global _efb_proxy
    if not _efb_enabled():
        if _efb_proxy:
            _efb_proxy.release()
        return reference
    from .embyflow_buffer_v1 import BufferProxy, eligible
    if not eligible(url):
        if _efb_proxy:
            _efb_proxy.release()
        return reference
    if _efb_proxy is None:
        if requests is None:
            raise RuntimeError('Puffermodus benötigt requests.')
        _efb_proxy = BufferProxy(requests.request)
    local = _efb_proxy.register(url)
    copied = eServiceReference(reference.toString())
    copied.setPath(local)
    try:
        copied.setName(reference.getName())
    except AttributeError:
        pass
    return copied


class EmbyFlowBufferTestStatusV1(Screen):
    skin = scale_skin('''<screen name="EmbyFlowBufferTestStatusV1" position="100,55" size="1720,105" flags="wfNoBorder" backgroundColor="#0C1827">
    <widget name="status" position="25,15" size="1670,78" font="Regular;28" foregroundColor="#26DFF5" backgroundColor="#0C1827" valign="center" />
    </screen>''')
    def __init__(self, session):
        Screen.__init__(self, session)
        self['status'] = Label('Puffertest wartet auf mindestens 8 MiB Reserve …')
        self['actions'] = ActionMap(['OkCancelActions'], {'cancel': self.close}, -2)
        self.started = 0.0
        self.created = time.monotonic()
        self.done = 0.0
        self.timer = eTimer()
        self.timer.callback.append(self.poll)
        self.onClose.append(self.cleanup)
        self.timer.start(250, False)

    def cleanup(self):
        self.timer.stop()
        if _efb_proxy:
            _efb_proxy.test(0)

    def poll(self):
        proxy = _efb_proxy
        now = time.monotonic()
        if proxy is None:
            self['status'].setText('Test nicht verfügbar: kein direkter gepufferter Filmstream. Zurück zum Schließen.')
            if now - self.created > 10:
                self.close()
            return
        reserve = proxy.buffered()
        if not self.started:
            if reserve >= 8 * 1024 * 1024:
                self.started = now
                proxy.test(15)
            elif now - self.created > 90:
                self['status'].setText('Test nicht gestartet: zu wenig Reserve. Nachladen bleibt frei.')
                self.done = self.done or now
            else:
                self['status'].setText('Puffertest wartet auf 8 MiB Reserve · Aktuell %.1f MiB' % (reserve / 1048576.0))
        if self.started:
            remaining = 15 - (now - self.started)
            if remaining > 0:
                self['status'].setText('Puffertest: Nachladen aus · noch %ds · Reserve %.1f MiB' % (int(remaining) + 1, reserve / 1048576.0))
            else:
                self['status'].setText('Puffertest beendet: Nachladen wieder frei. Liefen Bild und Ton durchgehend?')
                self.done = self.done or now
        if self.done and now - self.done > 10:
            self.close()


_efb_original_player_init = EmbyFlowMoviePlayer.__init__


def _efb_player_init(self, *args, **kwargs):
    global _efb_test_next
    _efb_original_player_init(self, *args, **kwargs)
    def release_owned_buffer():
        proxy = _efb_proxy
        if proxy:
            with proxy.lock:
                owned = str(getattr(self, 'stream_url', '')) in proxy.routes.values()
            if owned:
                proxy.release()
    self.onClose.append(release_owned_buffer)
    if _efb_test_next:
        _efb_test_next = False
        self._efb_test_timer = eTimer()
        self._efb_test_timer.callback.append(lambda: self.session.open(EmbyFlowBufferTestStatusV1))
        self._efb_test_timer.start(10000, True)
        self.onClose.append(self._efb_test_timer.stop)


EmbyFlowMoviePlayer.__init__ = _efb_player_init

# EMBYFLOW_BUFFER_SCROLL_SETTINGS_V3
# Six visible rows; existing settings remain at their original entry point.
import xml.etree.ElementTree as _efbs_et
_efbs_fields = ('adaptive_value', 'debug_value', 'api_value', 'box_display_value', 'trailers_value', 'youtube_search_value')
_efbs_focuses = (2, 3, 4, 7, 8, 9, 10, 11)
_efbs_labels = ('Adaptive OSD-Helligkeit (Beta)', 'Debug-Log', 'API-Key (optional)',
                'Boxdisplay', 'Trailer aktivieren (Erprobung)', 'Trailer bei YouTube suchen',
                'Stabilitätsmodus', '15-Sekunden-Puffertest')
_efbs_root = _efbs_et.fromstring(EmbyFlowAdvancedSettingsNeon.skin)
for _efbs_parent in _efbs_root.iter():
    for _efbs_node in list(_efbs_parent):
        _efbs_pos = _efbs_node.get('position', '0,0').split(',')
        if (_efbs_node.tag == 'eLabel' and _efbs_pos[0] == '715'
                and 340 <= int(_efbs_pos[1]) <= 850):
            _efbs_parent.remove(_efbs_node)
        elif _efbs_node.get('name') in _efbs_fields + ('middle_help',):
            # Existing refresh methods still update their own model labels.
            _efbs_node.set('position', '1,1')
            _efbs_node.set('size', '1,1')
for _efbs_slot in range(6):
    _efbs_et.SubElement(_efbs_root, 'widget', {
        'name': 'efbs_label%d' % _efbs_slot, 'position': '715,%d' % (344 + 82 * _efbs_slot),
        'size': '480,28', 'font': 'Regular;22', 'foregroundColor': '#F4F7FB',
        'transparent': '1', 'zPosition': '7'})
    _efbs_et.SubElement(_efbs_root, 'widget', {
        'name': 'efbs_value%d' % _efbs_slot, 'position': '722,%d' % (377 + 82 * _efbs_slot),
        'size': '466,44', 'font': 'Bold;22', 'foregroundColor': '#b54ce8',
        'backgroundColor': '#0A1627', 'transparent': '0', 'zPosition': '7', 'valign': 'center'})
_efbs_et.SubElement(_efbs_root, 'widget', {
    'name': 'efbs_range', 'position': '715,316', 'size': '470,25',
    'font': 'Regular;16', 'foregroundColor': '#AAB7C8', 'transparent': '1', 'zPosition': '7'})
EmbyFlowAdvancedSettingsNeon.skin = _efbs_et.tostring(_efbs_root, encoding='unicode')
_efbs_old_init = EmbyFlowAdvancedSettingsNeon.__init__
_efbs_old_refresh = EmbyFlowAdvancedSettingsNeon.refresh_all
_efbs_old_target = EmbyFlowAdvancedSettingsNeon._focus_target
_efbs_old_activate = EmbyFlowAdvancedSettingsNeon.activate
_efbs_old_left = EmbyFlowAdvancedSettingsNeon.move_left
_efbs_old_right = EmbyFlowAdvancedSettingsNeon.move_right
_efbs_old_toggle = EmbyFlowAdvancedSettingsNeon._toggle_current
_efbs_old_save = EmbyFlowAdvancedSettingsNeon.save_settings


def _efbs_init(self, session):
    self._efbs_offset = 0
    self._efbs_enabled = _efb_enabled()
    self._efbs_test = _efb_test_next
    _efbs_old_init(self, session)
    self['efbs_range'] = Label('▼ Weitere Optionen · 1–6 / 8')
    for slot in range(6):
        self['efbs_label%d' % slot] = Label('')
        self['efbs_value%d' % slot] = Label('')


def _efbs_refresh(self):
    if self.focus in _efbs_focuses:
        index = _efbs_focuses.index(self.focus)
        self._efbs_offset = max(0, min(2, max(index - 5, min(self._efbs_offset, index))))
    _efbs_old_refresh(self)
    if 'efbs_range' not in self:
        return
    values = [self[name].getText() for name in _efbs_fields]
    values.extend([
        ('> ' if self.focus == 10 else '') + ('AN' if self._efbs_enabled else 'AUS') + (' <' if self.focus == 10 else ''),
        ('> ' if self.focus == 11 else '') + ('Nächster Film vorgemerkt' if self._efbs_test else 'Aus · OK zum Vormerken') + (' <' if self.focus == 11 else '')])
    for name in _efbs_fields + ('middle_help',):
        self[name].hide()
    for slot in range(6):
        index = self._efbs_offset + slot
        self['efbs_label%d' % slot].setText(_efbs_labels[index])
        self['efbs_value%d' % slot].setText(values[index])
    self['efbs_range'].setText('%s  %d–%d / 8  %s' % (
        '▲' if self._efbs_offset else '', self._efbs_offset + 1,
        self._efbs_offset + 6, '▼ Weitere Optionen' if self._efbs_offset < 2 else ''))
    if self.focus == 10:
        self['left_help'].setText('Mehr Videopuffer für direkte Filme und Serien. Start kann länger dauern. Mit Grün speichern.')
    elif self.focus == 11:
        self['left_help'].setText('OK merkt den Test vor und aktiviert den Puffer. Mit Grün speichern, dann einen direkten Film von Beginn starten.')


def _efbs_target(self):
    if self.focus in _efbs_focuses:
        index = _efbs_focuses.index(self.focus)
        return (688, 374 + 82 * (index - self._efbs_offset))
    return _efbs_old_target(self)


def _efbs_move(self, step):
    order = (0, 6, 1, 2, 3, 4, 7, 8, 9, 10, 11, 5)
    self.focus = order[(order.index(self.focus) + step) % len(order)]
    self.refresh_all()


def _efbs_toggle(self):
    if self.focus == 10:
        self._efbs_enabled = not self._efbs_enabled
        if not self._efbs_enabled:
            self._efbs_test = False
        self.refresh_all()
    elif self.focus == 11:
        self._efbs_test = not self._efbs_test
        if self._efbs_test:
            self._efbs_enabled = True
        self.refresh_all()
    else:
        return _efbs_old_toggle(self)


def _efbs_save(self, close_after=False):
    global _efb_test_next
    try:
        _efbs_old_save(self, close_after=False)
        if 'Speichern fehlgeschlagen' in self['account_status'].getText():
            return False
        _efb_save(self._efbs_enabled)
        _efb_test_next = self._efbs_test
        self['account_status'].setText('[OK] Einstellungen gespeichert.')
        if close_after:
            self.close('saved')
        return True
    except Exception:
        self['account_status'].setText('Speichern fehlgeschlagen: Wiedergabeeinstellungen.')
        return False


EmbyFlowAdvancedSettingsNeon.__init__ = _efbs_init
EmbyFlowAdvancedSettingsNeon.refresh_all = _efbs_refresh
EmbyFlowAdvancedSettingsNeon._focus_target = _efbs_target
EmbyFlowAdvancedSettingsNeon.move_up = lambda self: _efbs_move(self, -1)
EmbyFlowAdvancedSettingsNeon.move_down = lambda self: _efbs_move(self, 1)
EmbyFlowAdvancedSettingsNeon._toggle_current = _efbs_toggle
EmbyFlowAdvancedSettingsNeon.activate = lambda self: self._toggle_current() if self.focus in (10, 11) else _efbs_old_activate(self)
EmbyFlowAdvancedSettingsNeon.move_left = lambda self: self._toggle_current() if self.focus in (10, 11) else _efbs_old_left(self)
EmbyFlowAdvancedSettingsNeon.move_right = lambda self: self._toggle_current() if self.focus in (10, 11) else _efbs_old_right(self)
EmbyFlowAdvancedSettingsNeon.save_settings = _efbs_save

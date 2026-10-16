
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


def _efb_open_settings(screen):
    def selected(result):
        global _efb_test_next
        if not result:
            return
        action = result[1]
        if action == 'connection':
            _efb_original_setup(screen)
        elif action in ('on', 'off', 'test'):
            try:
                _efb_save(action != 'off')
                _efb_test_next = action == 'test'
                message = ('Puffertest vorgemerkt. Einen direkten Film von Beginn starten.\n'
                           'Nach etwa 10 Sekunden erscheint die Testanzeige.') if action == 'test' else (
                           'Stabilitätsmodus %s. Gilt ab dem nächsten Filmstart.' % ('ein' if action == 'on' else 'aus'))
                screen.session.open(MessageBox, message, MessageBox.TYPE_INFO, timeout=8)
            except Exception:
                screen.session.open(MessageBox, 'Puffereinstellung konnte nicht gespeichert werden.', MessageBox.TYPE_ERROR, timeout=8)
    screen.session.openWithCallback(selected, EmbyFlowChoiceScreen,
        title='Einstellungen · Wiedergabe · Stabilitätsmodus: ' + ('Ein' if _efb_enabled() else 'Aus'),
        entries=[('Serververbindung / bisherige Einstellungen', 'connection'),
                 ('Stabilitätsmodus einschalten (direkte Filme / Serien)', 'on'),
                 ('Stabilitätsmodus ausschalten', 'off'),
                 ('15-Sekunden-Puffertest beim nächsten Film', 'test')])


_efb_original_setup = EmbyFlowE2Screen.open_setup
EmbyFlowE2Screen.open_setup = _efb_open_settings
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
# EMBYFLOW_OPTIONAL_RAM_BUFFER_TEST_V1_END

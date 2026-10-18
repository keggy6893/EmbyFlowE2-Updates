# EMBYFLOW_LOCAL_MOVIE_DOWNLOAD_20261017
import threading as _efdl_threading
import queue as _efdl_queue
import os as _efdl_os
from urllib.parse import quote as _efdl_quote
from Components.ProgressBar import ProgressBar as _EFDLProgress
_EFDLChoice = EmbyFlowDownloadChoice

config.embyflow.movie_download_enabled = ConfigYesNo(default=False)

# EMBYFLOW_DOWNLOAD_QUOTA_VISIBLE_V10
def _efdl_update_quota(screen):
    status = _efdl_engine.quota_status()
    if status is None:
        text = 'Tageslimit nicht prüfbar · kein Download möglich'
    elif status['remaining'] == 0:
        text = 'Heute 5 von 5 · Tageslimit erreicht'
    else:
        text = 'Heute %d von %d · noch %d verfügbar' % (status['used'], status['limit'], status['remaining'])
    screen['quota'].setText(text)
    widget = screen['quota'].instance
    if widget is not None:
        try:
            from skin import parseColor
            widget.setForegroundColor(parseColor('#D49A9F' if status is None or not status['remaining'] else '#26DFF5'))
        except Exception:
            pass

def _efdl_targets():
    result = []
    for mount in ('/media/hdd', '/media/usb'):
        real = _efdl_os.path.realpath(mount)
        if _efdl_os.path.ismount(real) and real != '/' and _efdl_os.access(real, _efdl_os.W_OK):
            result.append((mount, real))
    return result

class EmbyFlowLocalDownloadScreen(Screen):
    skin = scale_skin('''<screen name="EmbyFlowLocalDownloadScreen" position="center,center" size="1120,640" flags="wfNoBorder" backgroundColor="#FF000000">
      <widget name="panel" position="0,0" size="1120,640" zPosition="0" alphatest="blend" />
      <eLabel text="EMBY" position="40,24" size="60,26" font="Regular;18" foregroundColor="#26DFF5" backgroundColor="#0B1522" transparent="1" zPosition="2" />
      <eLabel text="FLOW" position="100,24" size="65,26" font="Regular;18" foregroundColor="#EC3EA9" backgroundColor="#0B1522" transparent="1" zPosition="2" />
      <eLabel text="E2" position="170,24" size="45,26" font="Regular;18" foregroundColor="#99ACBD" backgroundColor="#0B1522" transparent="1" zPosition="2" />
      <eLabel position="40,66" size="1040,1" backgroundColor="#294052" zPosition="1" />
      <eLabel text="Film herunterladen" position="40,86" size="1040,46" font="Regular;32" foregroundColor="#E1E7ED" backgroundColor="#0B1522" transparent="1" zPosition="2" />
      <widget name="film_title" position="40,142" size="1040,34" font="Regular;22" foregroundColor="#98A9B9" backgroundColor="#0B1522" transparent="1" zPosition="2" />
      <widget name="quota" position="40,188" size="1040,30" font="Regular;22" foregroundColor="#26DFF5" backgroundColor="#0B1522" transparent="1" zPosition="2" />
      <widget name="permission" position="40,232" size="1040,30" font="Regular;18" foregroundColor="#79C5CE" backgroundColor="#0B1522" transparent="1" zPosition="2" />
      <widget name="status" position="40,284" size="1040,212" font="Regular;22" foregroundColor="#E1E7ED" backgroundColor="#0B1522" transparent="1" zPosition="2" />
      <widget name="progress_bar" position="40,530" size="1040,4" foregroundColor="#26DFF5" backgroundColor="#172B40" borderWidth="0" zPosition="2" />
      <eLabel position="40,578" size="1040,1" backgroundColor="#294052" zPosition="1" />
      <widget name="footer" position="40,596" size="1040,28" font="Regular;18" foregroundColor="#93AABD" backgroundColor="#0B1522" transparent="1" zPosition="2" />
    </screen>''')
    def __init__(self, session, data):
        Screen.__init__(self, session)
        self.data = dict(data)
        self.cancel = _efdl_threading.Event()
        self.events = _efdl_queue.Queue()
        self.progress = (0, 0)
        self.closed = False
        self.permission_state = 'checking'
        self['panel'] = Pixmap()
        self['permission'] = Label('Downloadfreigabe: Wird beim Anbieter geprüft …')
        self['quota'] = Label('')
        _efdl_update_quota(self)
        self.onLayoutFinish.append(self._efdl_layout)
        self['film_title'] = Label(str(self.data.get('title') or self.data.get('Name') or 'Film'))
        self['progress_bar'] = _EFDLProgress()
        self['progress_bar'].setValue(0)
        self['footer'] = Label('ROT / EXIT  Abbrechen und schließen')
        self['status'] = Label('Filmversionen und Downloadberechtigung werden geprueft ...')
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], {'cancel': self.abort, 'red': self.abort}, -2)
        self.timer = eTimer()
        self.timer.callback.append(self.poll)
        self.onClose.append(self.cleanup)
        self.onFirstExecBegin.append(self.prepare)

    def _efdl_layout(self):
        _efdl_style_apply(self['panel'], 'panel')

    def cleanup(self):
        self.closed = True
        self.cancel.set()
        self.timer.stop()

    def abort(self):
        self.cancel.set()
        self.close()

    def prepare(self):
        self.timer.start(300, False)
        _efdl_threading.Thread(target=self.metadata, daemon=True).start()

    def metadata(self):
        granted = False
        try:
            server, token, user = get_emby_auth()
            if not token or not user:
                raise ValueError('Keine gueltige Emby-Anmeldung.')
            self.auth = (server.rstrip('/'), token)
            self.user = user
            _efdl_engine.check_permission(requests, server, token, user, self.cancel)
            granted = True
            self.events.put(('permission', ('granted', 'Downloadfreigabe: Freigegeben für dein Benutzerkonto')))
            def get(path):
                with requests.get(server.rstrip('/') + path, params={'api_key': token}, timeout=(8, 20), verify=True, allow_redirects=False) as response:
                    if response.status_code != 200:
                        raise ValueError('Metadaten nicht verfuegbar: HTTP %s' % response.status_code)
                    return response.json()
            item = get('/Users/%s/Items/%s' % (_efdl_quote(str(user), safe=''), _efdl_quote(str(self.data.get('id') or self.data.get('Id') or ''), safe='')))
            if item.get('CanDownload') is False:
                raise _efdl_engine.DownloadPermissionDenied('Der Anbieter erlaubt den Download dieses Films nicht.')
            if self.cancel.is_set():
                return
            if item.get('Type') not in ('Movie', 'Episode'):
                raise ValueError('Bitte einen Film oder eine einzelne Serienfolge waehlen.')
            sources = []
            for raw_source in item.get('MediaSources') or []:
                if not isinstance(raw_source, dict):
                    continue
                try:
                    size = int(raw_source.get('Size') or 0)
                except (ValueError, TypeError):
                    continue
                if raw_source.get('Id') and size > 0 and not raw_source.get('IsRemote') and str(raw_source.get('Protocol') or 'File').lower() == 'file':
                    source = dict(raw_source, Size=size)
                    sources.append(source)
            if not sources:
                raise ValueError('Keine herunterladbare Originaldatei mit bekannter Groesse gefunden.')
            self.events.put(('sources', (item, sources)))
        except _efdl_engine.DownloadCancelled:
            return
        except _efdl_engine.DownloadPermissionDenied as error:
            self.events.put(('permission', ('denied', 'Downloadfreigabe: Nicht erlaubt')))
            self.events.put(('error', str(error)))
        except Exception as error:
            if not granted:
                self.events.put(('permission', ('unknown', 'Downloadfreigabe: Nicht prüfbar · kein Downloadstart')))
            self.events.put(('error', str(error) if isinstance(error, ValueError) else 'Verbindungsfehler bei der Vorbereitung.'))

    def poll(self):
        if self.closed:
            return
        _efdl_update_quota(self)
        if self.progress[1]:
            done, size = self.progress
            self['progress_bar'].setValue(int(done * 100 / size))
            self['status'].setText('Film wird heruntergeladen: %.1f %%\n%.2f / %.2f GiB\n\n%s' % (done * 100.0 / size, done / 2**30, size / 2**30, self.target))
        try:
            kind, value = self.events.get_nowait()
        except _efdl_queue.Empty:
            return
        if kind == 'permission':
            self.permission_state, text = value
            self['permission'].setText(text)
            if self['permission'].instance is not None:
                from skin import parseColor
                self['permission'].instance.setForegroundColor(parseColor('#D49A9F' if self.permission_state in ('denied','unknown') else '#79C5CE'))
        elif kind == 'sources':
            if self.permission_state != 'granted':
                return
            self.item, sources = value
            self.session.openWithCallback(self.source_chosen, _EFDLChoice, title='Filmversion auswählen', description='Wähle die passende Version für deinen Download', access_status='✓ Benutzerfreigabe vom Anbieter bestätigt', list=[(s.get('Name') or s['Id'], s) for s in sources])
        elif kind == 'done':
            self.progress = (0, 0)
            self['progress_bar'].setValue(100)
            self['footer'].setText('ROT / EXIT  Schließen')
            self['status'].setText('Download abgeschlossen:\n%s\n\nOriginaldatei mit enthaltenen Spuren. Externe Untertitel wurden nicht heruntergeladen.\nEXIT: Schliessen' % value)
        else:
            self.progress = (0, 0)
            self['footer'].setText('ROT / EXIT  Schließen')
            self['status'].setText('Download nicht abgeschlossen:\n%s\n\nEXIT: Schliessen' % value)

    def source_chosen(self, choice):
        if not choice or self.closed:
            return self.close()
        if self.permission_state != 'granted':
            self.events.put(('error', 'Downloadfreigabe fehlt. Bitte den Dialog erneut öffnen.'))
            return
        self.source = choice[1]
        targets = _efdl_targets()
        if not targets:
            self.events.put(('error', 'Keine beschreibbare, eingehaengte HDD/USB unter /media/hdd oder /media/usb.'))
            return
        storage = {root: _efdl_engine.storage_info(root, self.source['Size']) for label, root in targets}
        self.session.openWithCallback(self.target_chosen, _EFDLChoice, title='Downloadziel auswählen', description='Speichern auf HDD oder USB · Ordner movie/EmbyFlow', access_status='✓ Benutzerfreigabe vom Anbieter bestätigt', list=targets, storage=storage)

    def target_chosen(self, choice):
        if not choice or self.closed:
            return self.close()
        try:
            root = choice[1]
            if root not in [real for label, real in _efdl_targets()]:
                raise ValueError('Datentraeger nicht mehr verfuegbar.')
            directory = _efdl_os.path.join(root, 'movie', 'EmbyFlow')
            _efdl_os.makedirs(directory, exist_ok=True)
            if _efdl_os.path.commonpath([root, _efdl_os.path.realpath(directory)]) != root or _efdl_os.stat(directory).st_dev != _efdl_os.stat(root).st_dev:
                raise ValueError('Ziel liegt nicht auf dem gewaehlten Datentraeger.')
            _efdl_engine.check_space(directory, self.source['Size'])
            self.target = _efdl_os.path.join(directory, _efdl_engine.filename(self.item.get('Name', 'Film'), self.item['Id'], self.source))
            free = _efdl_engine.shutil.disk_usage(directory).free
            summary = 'Film: %s\nGröße: %.2f GiB · Frei: %.2f GiB\nZiel: %s\n\nOriginaldatei mit enthaltenen Ton- und Untertitelspuren.\nExterne Untertitel werden nicht mitgeladen.\nAbbruch löscht die Teildatei; Fortsetzen ist noch nicht verfügbar.' % (str(self.item.get('Name', ''))[:100], int(self.source['Size']) / 2**30, free / 2**30, directory)
            self.session.openWithCallback(lambda choice: self.confirmed(bool(choice and choice[1])), _EFDLChoice, title='Download starten?', description=summary, access_status='Benutzerfreigabe bestätigt · vor dem Start erneute Prüfung', confirmation=True, list=[('Abbrechen', False), ('Herunterladen', True)])
        except Exception:
            self.events.put(('error', 'Downloadziel ungueltig oder Speicherplatz nicht ausreichend.'))

    def confirmed(self, yes):
        if not yes or self.closed:
            return self.close()
        if self.permission_state != 'granted':
            self.events.put(('error', 'Downloadfreigabe fehlt. Kein Download gestartet.'))
            return
        self.permission_state = 'checking'
        self['permission'].setText('Downloadfreigabe: Wird vor dem Start erneut geprüft …')
        self['status'].setText('Download wird vorbereitet …')
        _efdl_threading.Thread(target=self.transfer, daemon=True).start()

    def transfer(self):
        try:
            server, token = self.auth
            _efdl_engine.check_permission(requests, server, token, self.user, self.cancel)
            self.events.put(('permission', ('granted', 'Downloadfreigabe: Vor dem Start erneut bestätigt')))
            # Re-check the mounted disk immediately before starting the worker.
            if not any(_efdl_os.path.commonpath([root, _efdl_os.path.realpath(self.target)]) == root for label, root in _efdl_targets()):
                raise ValueError('Datentraeger nicht mehr verfuegbar.')
            server, token = self.auth
            url = server + '/Items/' + _efdl_quote(str(self.item['Id']), safe='') + '/Download'
            path = _efdl_engine.download(requests, url, token, self.source, self.target, self.cancel, lambda done, size: setattr(self, 'progress', (done, size)))
            self.events.put(('done', path))
        except _efdl_engine.DownloadCancelled:
            pass
        except _efdl_engine.DownloadPermissionDenied as error:
            self.events.put(('permission', ('denied', 'Downloadfreigabe: Nicht erlaubt')))
            self.events.put(('error', str(error)))
        except _efdl_engine.DownloadPermissionUnknown as error:
            self.events.put(('permission', ('unknown', 'Downloadfreigabe: Nicht prüfbar · kein Downloadstart')))
            self.events.put(('error', str(error)))
        except Exception as error:
            self.events.put(('error', str(error) if isinstance(error, ValueError) else 'Uebertragung fehlgeschlagen. Teildatei wird entfernt.'))

_EFDL_DETAIL_INIT = EmbyFlowDetailScreen.__init__
_EFDL_DETAIL_FOCUS = EmbyFlowDetailScreen.update_detail_focus
_EFDL_DETAIL_OK = EmbyFlowDetailScreen.detail_ok
_EFDL_DETAIL_UP = EmbyFlowDetailScreen.detail_up
_EFDL_DETAIL_DOWN = EmbyFlowDetailScreen.detail_down

def _efdl_detail_init(self, session, data):
    self._efdl_button_ready = False
    self._efdl_button_enabled = bool(config.embyflow.movie_download_enabled.value)
    _EFDL_DETAIL_INIT(self, session, data)
    if not self._efdl_button_enabled or str(data.get('type') or data.get('Type') or 'Movie').lower() not in ('movie', 'episode'):
        self._efdl_button_enabled = False
        return
    import xml.etree.ElementTree as ET
    root = ET.fromstring(self.skin)
    trailer = bool(getattr(self, '_trailer_enabled', False))
    download_y, back_y = (805, 900) if trailer else (710, 805)
    for node in root.iter('widget'):
        name = node.get('name', '')
        if name == 'detail_back_btn':
            node.set('position', '%d,%d' % (sx(1510), sy(back_y)))
        elif name == 'cinema_button_bg_1':
            node.set('position', '%d,%d' % (sx(1506), sy(back_y - 4)))
    self['movie_download_button'] = Label('↓  Herunterladen')
    self['movie_download_background'] = Pixmap()
    ET.SubElement(root, 'widget', {
        'name': 'movie_download_background', 'position': '%d,%d' % (sx(1506), sy(download_y - 4)),
        'size': '%d,%d' % (sx(338), sy(80)), 'zPosition': '39', 'alphatest': 'blend'})
    ET.SubElement(root, 'widget', {
        'name': 'movie_download_button', 'position': '%d,%d' % (sx(1510), sy(download_y)),
        'size': '%d,%d' % (sx(330), sy(72)), 'font': 'Regular;%d' % sy(30),
        'foregroundColor': '#F1F4F8', 'backgroundColor': '#0C1827', 'transparent': '1',
        'halign': 'center', 'valign': 'center', 'zPosition': '40'})
    self.skin = ET.tostring(root, encoding='unicode')
    self._efdl_button_ready = True
    self.onLayoutFinish.append(self.update_detail_focus)

def _efdl_detail_focus(self):
    focus = self.detail_focus
    # Existing player/trailer styling understands only indexes 0, 1 and 2.
    if focus == 3:
        self.detail_focus = 0
    try:
        _EFDL_DETAIL_FOCUS(self)
    finally:
        self.detail_focus = focus
    if not getattr(self, '_efdl_button_ready', False):
        return
    images = getattr(self, '_efpolish_images', {})
    if focus == 3:
        for index in (0, 1, 2):
            name = 'cinema_button_bg_%d' % index
            if name in self and self[name].instance and images.get(False):
                self[name].instance.setPixmap(images[False])
                self[name].instance.setScale(1)
            name = 'cinema_focus_%d' % index
            if name in self:
                self[name].hide()
    widget = self['movie_download_background']
    pix = images.get(focus == 3)
    if pix and widget.instance:
        widget.instance.setPixmap(pix)
        widget.instance.setScale(1)
    self['movie_download_button'].setText('↓  Herunterladen')

def _efdl_detail_move(self, step):
    if not getattr(self, '_efdl_button_ready', False):
        return (_EFDL_DETAIL_UP if step < 0 else _EFDL_DETAIL_DOWN)(self)
    order = [0] + ([2] if getattr(self, '_trailer_enabled', False) else []) + [3, 1]
    index = order.index(self.detail_focus) if self.detail_focus in order else 0
    self.detail_focus = order[max(0, min(len(order) - 1, index + step))]
    self.update_detail_focus()

def _efdl_detail_ok(self):
    if self.detail_focus == 3 and getattr(self, '_efdl_button_ready', False):
        if config.embyflow.movie_download_enabled.value:
            self.session.open(EmbyFlowLocalDownloadScreen, self.data)
        return
    return _EFDL_DETAIL_OK(self)

EmbyFlowDetailScreen.__init__ = _efdl_detail_init
EmbyFlowDetailScreen.update_detail_focus = _efdl_detail_focus
EmbyFlowDetailScreen.detail_up = lambda self: _efdl_detail_move(self, -1)
EmbyFlowDetailScreen.detail_down = lambda self: _efdl_detail_move(self, 1)
EmbyFlowDetailScreen.detail_ok = _efdl_detail_ok

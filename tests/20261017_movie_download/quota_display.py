# EMBYFLOW_DOWNLOAD_QUOTA_DISPLAY_ADDON_V10
import xml.etree.ElementTree as _efdlq_xml

def _efdlq_update(screen):
    value = _efdl_engine.quota_status()
    if value is None:
        text = 'Tageslimit nicht prüfbar · kein Download möglich'
    elif value['remaining'] == 0:
        text = 'Heute 5 von 5 · Tageslimit erreicht'
    else:
        text = 'Heute %d von %d · noch %d verfügbar' % (value['used'], value['limit'], value['remaining'])
    screen['quota'].setText(text)
    instance = screen['quota'].instance
    if instance is not None:
        try:
            from skin import parseColor
            instance.setForegroundColor(parseColor('#D49A9F' if value is None or not value['remaining'] else '#26DFF5'))
        except Exception:
            pass

_efdlq_progress_init_before = EmbyFlowLocalDownloadScreen.__init__
_efdlq_poll_before = EmbyFlowLocalDownloadScreen.poll
_efdlq_root = _efdlq_xml.fromstring(EmbyFlowLocalDownloadScreen.skin)
for _efdlq_node in _efdlq_root:
    if _efdlq_node.get('name') == 'permission':
        _efdlq_permission = dict(_efdlq_node.attrib)
        _efdlq_node.set('position', '%d,%d' % (sx(40), sy(232)))
    elif _efdlq_node.get('name') == 'status':
        _efdlq_node.set('position', '%d,%d' % (sx(40), sy(284)))
        _efdlq_node.set('size', '%d,%d' % (sx(1040), sy(212)))
_efdlq_permission.update(name='quota', position='%d,%d' % (sx(40), sy(188)),
    size='%d,%d' % (sx(1040), sy(30)), font='Regular;%d' % sy(22), foregroundColor='#26DFF5')
_efdlq_xml.SubElement(_efdlq_root, 'widget', _efdlq_permission)
EmbyFlowLocalDownloadScreen.skin = _efdlq_xml.tostring(_efdlq_root, encoding='unicode')

def _efdlq_progress_init(self, session, data):
    _efdlq_progress_init_before(self, session, data)
    self['quota'] = Label('')
    _efdlq_update(self)

def _efdlq_poll(self):
    if not self.closed:
        _efdlq_update(self)
    return _efdlq_poll_before(self)

_efdlq_choice_init_before = EmbyFlowDownloadChoice.__init__
def _efdlq_choice_init(self, *args, **kwargs):
    _efdlq_choice_init_before(self, *args, **kwargs)
    root = _efdlq_xml.fromstring(self.skin)
    permission = next(node for node in root if node.get('name') == 'permission')
    attributes = dict(permission.attrib)
    quota_y = int(attributes['position'].split(',')[1])
    shift = sy(44)
    width, height = map(int, root.get('size').split(','))
    root.set('size', '%d,%d' % (width, height + shift))
    for node in root:
        x, y = map(int, node.get('position').split(','))
        if node.get('name') == 'panel':
            node.set('size', '%d,%d' % (width, height + shift))
        elif y >= quota_y:
            node.set('position', '%d,%d' % (x, y + shift))
    attributes.update(name='quota', size='%d,%d' % (sx(1040), sy(30)),
                      font='Regular;%d' % sy(22), foregroundColor='#26DFF5')
    _efdlq_xml.SubElement(root, 'widget', attributes)
    self.skin = _efdlq_xml.tostring(root, encoding='unicode')
    self['quota'] = Label('')
    _efdlq_update(self)
    self._quota_timer = eTimer()
    self._quota_timer.callback.append(self._efdlq_refresh)
    self.onClose.append(self._quota_timer.stop)
    self._quota_timer.start(1000, False)

def _efdlq_refresh(self):
    _efdlq_update(self)

EmbyFlowLocalDownloadScreen.__init__ = _efdlq_progress_init
EmbyFlowLocalDownloadScreen.poll = _efdlq_poll
EmbyFlowDownloadChoice.__init__ = _efdlq_choice_init
EmbyFlowDownloadChoice._efdlq_refresh = _efdlq_refresh

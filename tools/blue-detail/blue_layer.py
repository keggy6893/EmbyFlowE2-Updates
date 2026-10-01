# EMBYFLOW_DETAIL_ORIGINAL_SOLID_BLUE_20261001
# Restore the verified original solid #0C1827 color. Preserve actual theme videos.
def _embyflow_blue_detail_skin(skin, width, height, panel_pos, panel_size):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(skin)
    full = '%d,%d' % (width, height)
    for node in list(root):
        if node.tag == 'eLabel' and (
            (node.get('position') == '0,0' and node.get('size') == full) or
            (node.get('position') == panel_pos and node.get('size') == panel_size)):
            root.remove(node)
        elif node.get('name') in ('fallback_detail_plain_panel',):
            node.set('transparent', '1')
        elif node.get('name', '').startswith('detail_') and node.get('transparent') == '0':
            node.set('transparent', '1')
    ET.SubElement(root, 'widget', {'name':'detail_blue_background', 'position':'0,0',
        'size':full, 'zPosition':'-1', 'backgroundColor':'#0C1827', 'transparent':'0'})
    return ET.tostring(root, encoding='unicode')

_BLUE_DETAIL_INIT = EmbyFlowDetailScreen.__init__
_BLUE_DETAIL_POLL = EmbyFlowDetailScreen._fallback_detail_poll

def _embyflow_blue_detail_apply(self):
    try:
        self['detail_blue_background'].show()
        for name in ('fallback_screen_base', 'fallback_detail_backdrop',
                     'fallback_detail_plain_panel', 'fallback_detail_video_tint'):
            try: self[name].hide()
            except Exception: pass
    except Exception as error:
        print('[EmbyFlow][BlueDetail] %s' % error)

def _embyflow_blue_detail_init(self, session, data):
    _BLUE_DETAIL_INIT(self, session, data)
    self.skin = _embyflow_blue_detail_skin(self.skin, sx(1920), sy(1080),
        '%d,%d' % (sx(96), sy(80)), '%d,%d' % (sx(1728), sy(920)))
    self['detail_blue_background'] = Label('')
    self.onLayoutFinish.insert(0, self._blue_detail_apply)
    self.onShow.append(self._blue_detail_return)
    if getattr(self, '_skyfall_local_theme_enabled', False):
        self.onLayoutFinish.append(self._blue_detail_hide)

def _embyflow_blue_detail_poll(self):
    result = getattr(self, '_fallback_result', None)
    _BLUE_DETAIL_POLL(self)
    if result is not None:
        if result.get('video') and getattr(self, '_fallback_theme_active', False):
            self['detail_blue_background'].hide()
        else:
            _embyflow_blue_detail_apply(self)

def _embyflow_blue_detail_hide(self):
    self['detail_blue_background'].hide()

def _embyflow_blue_detail_return(self):
    # onLayoutFinish runs only once; onShow also runs after the movie closes.
    if not (getattr(self, '_skyfall_local_theme_active', False) or
            getattr(self, '_fallback_theme_active', False)):
        self._blue_detail_apply()

EmbyFlowDetailScreen._blue_detail_return = _embyflow_blue_detail_return
EmbyFlowDetailScreen._blue_detail_apply = _embyflow_blue_detail_apply
EmbyFlowDetailScreen._blue_detail_hide = _embyflow_blue_detail_hide
EmbyFlowDetailScreen.__init__ = _embyflow_blue_detail_init
EmbyFlowDetailScreen._fallback_detail_poll = _embyflow_blue_detail_poll

# Capture before themes/detail screens can stop or replace the TV service.
_TV_RETURN_MAIN = main
_TV_RETURN_ROOT_INIT = EmbyFlowE2Screen.__init__
_TV_RETURN_TIMERS = []

def _embyflow_tv_return_log(message):
    try:
        with open('/tmp/embyflow_tv_return.log', 'a') as handle:
            handle.write('%s | %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), message))
    except Exception:
        pass

def _embyflow_tv_return_main(session, **kwargs):
    try:
        session._embyflow_entry_service = session.nav.getCurrentlyPlayingServiceReference()
    except Exception:
        session._embyflow_entry_service = None
    _embyflow_tv_return_log('ENTRY saved=%d' % int(session._embyflow_entry_service is not None))
    return _TV_RETURN_MAIN(session, **kwargs)

def _embyflow_tv_return_close(self):
    session = self.session
    previous = self._embyflow_entry_service
    if previous is None:
        _embyflow_tv_return_log('SKIP no_entry_service')
        return
    timer = eTimer()
    def restore():
        try:
            current = session.nav.getCurrentlyPlayingServiceReference()
            # Never replace a service that another screen or user has started.
            if current is None:
                session.nav.playService(previous)
                _embyflow_tv_return_log('RESTORED')
            else:
                _embyflow_tv_return_log('SKIP active_service')
        except Exception as error:
            _embyflow_tv_return_log('ERROR %s' % error)
        finally:
            try: _TV_RETURN_TIMERS.remove(timer)
            except ValueError: pass
    timer.callback.append(restore)
    _TV_RETURN_TIMERS.append(timer)
    # Run after the player's 120 ms stop timer.
    timer.start(350, True)

def _embyflow_tv_return_root_init(self, session, *args, **kwargs):
    _TV_RETURN_ROOT_INIT(self, session, *args, **kwargs)
    self._embyflow_entry_service = getattr(session, '_embyflow_entry_service', None)
    self.onClose.append(self._tv_return_close)

EmbyFlowE2Screen._tv_return_close = _embyflow_tv_return_close
EmbyFlowE2Screen.__init__ = _embyflow_tv_return_root_init
main = _embyflow_tv_return_main

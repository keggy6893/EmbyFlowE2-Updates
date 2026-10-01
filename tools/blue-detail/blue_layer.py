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

EmbyFlowDetailScreen._blue_detail_apply = _embyflow_blue_detail_apply
EmbyFlowDetailScreen._blue_detail_hide = _embyflow_blue_detail_hide
EmbyFlowDetailScreen.__init__ = _embyflow_blue_detail_init
EmbyFlowDetailScreen._fallback_detail_poll = _embyflow_blue_detail_poll

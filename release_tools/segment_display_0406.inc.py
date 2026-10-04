# EMBYFLOW_SEGMENT_DISPLAY_0406
# Use Enigma2's text renderer; never write to display devices directly.
def _efsegment_detect():
    try:
        from Components.SystemInfo import BoxInfo
        return bool(BoxInfo.getItem('7segment')) or str(BoxInfo.getItem('displaytype') or '').lower() == '7segment'
    except (ImportError, AttributeError):
        try:
            from Components.SystemInfo import SystemInfo
            return bool(SystemInfo.get('7segment', False))
        except (ImportError, AttributeError):
            return False

def _efsegment_remaining(position, length):
    if not position or not length or position[0] or length[0] or length[1] <= 0:
        return '----'
    ticks = max(0, length[1] - max(0, position[1]))
    minutes = (ticks + 90000 * 60 - 1) // (90000 * 60)
    minutes = min(minutes, 99 * 60 + 59)
    return '%02d%02d' % (minutes // 60, minutes % 60)

class _EFSegmentSummary(Screen):
    skin = """
    <screen position="0,0" size="132,64" flags="wfNoBorder">
        <widget name="segment_time" position="0,0" size="132,64" font="Regular;18" noWrap="1" />
    </screen>"""
    def __init__(self, session, parent):
        Screen.__init__(self, session, parent=parent)
        self['segment_time'] = _EFDisplayLabel('----')
        self.timer = _EFDisplayTimer()
        try:
            self.timer.callback.append(self.refresh)
        except AttributeError:
            self.timer_connection = self.timer.timeout.connect(self.refresh)
        self.onShow.append(self.begin)
        self.onHide.append(self.timer.stop)
        self.onClose.append(self.timer.stop)

    def begin(self):
        self.refresh()
        self.timer.start(1000)

    def refresh(self):
        text = '----'
        try:
            service = self.session.nav.getCurrentService()
            seek = service.seek() if service else None
            if seek:
                text = _efsegment_remaining(seek.getPlayPosition(), seek.getLength())
        except Exception:
            pass
        self['segment_time'].setText(text)

_efsegment_previous_summary = EmbyFlowMoviePlayer.createSummary
def _efsegment_create_summary(self):
    if config.embyflow.box_display.value and _efsegment_detect():
        return _EFSegmentSummary
    return _efsegment_previous_summary(self)

EmbyFlowMoviePlayer.createSummary = _efsegment_create_summary

# EMBYFLOW_BOXDISPLAY_OPTIONAL_0303
from Components.Label import Label as _EFDisplayLabel
from Components.ProgressBar import ProgressBar as _EFDisplayProgress
from enigma import getDesktop as _EFDisplayDesktop, eTimer as _EFDisplayTimer

class _EFDisplaySummary(Screen):
    def __init__(self, session, parent):
        size = _EFDisplayDesktop(1).size()
        w, h = max(64, size.width()), max(32, size.height())
        margin = max(2, w // 40)
        inner = w - margin * 2
        title_font = max(10, min(36, h // 7)) + 2
        time_font = max(9, min(26, h // 10))
        self.skin = (
            '<screen position="0,0" size="%d,%d" flags="wfNoBorder" backgroundColor="#000000">'
            '<widget name="title" position="%d,0" size="%d,%d" font="Regular;%d" foregroundColor="#ffffff" borderWidth="1" borderColor="#ffffff" backgroundColor="#000000" halign="center" valign="center" />'
            '<widget name="status" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#ffffff" backgroundColor="#000000" halign="center" valign="center" />'
            '<widget name="progress" position="%d,%d" size="%d,%d" foregroundColor="#ffffff" backgroundColor="#333333" />'
            '<widget name="times" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#ffffff" borderWidth="1" borderColor="#ffffff" backgroundColor="#000000" halign="center" valign="center" />'
            '<widget name="remaining" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#ffffff" borderWidth="1" borderColor="#ffffff" backgroundColor="#000000" halign="center" valign="center" />'
            '</screen>'
        ) % (
            w, h,
            margin, inner, h * 42 // 100, title_font,
            margin, h * 42 // 100, inner, h * 13 // 100, time_font,
            margin, h * 57 // 100, inner, max(3, h // 30),
            margin, h * 64 // 100, inner, h * 17 // 100, time_font,
            margin, h * 82 // 100, inner, h * 18 // 100, time_font
        )
        Screen.__init__(self, session, parent=parent)
        self.player = parent
        for name in ('title', 'status', 'times', 'remaining'):
            self[name] = _EFDisplayLabel('')
        self['progress'] = _EFDisplayProgress()
        self['progress'].setRange((0, 100))
        self.timer = _EFDisplayTimer()
        self.timer.callback.append(self.refresh)
        self.onShow.append(self.begin)
        self.onHide.append(self.timer.stop)
        self.onClose.append(self.timer.stop)

    @staticmethod
    def clock(seconds):
        seconds = max(0, int(seconds))
        if seconds >= 3600:
            return '%d:%02d:%02d' % (seconds // 3600, seconds // 60 % 60, seconds % 60)
        return '%d:%02d' % (seconds // 60, seconds % 60)

    def begin(self):
        self.refresh()
        self.timer.start(1000)

    def refresh(self):
        self['title'].setText(str(getattr(self.player, 'title_text', 'EmbyFlow')))
        self['status'].setText('PAUSE' if bool(getattr(self.player, 'paused', False)) else 'Wiedergabe')
        try:
            service = self.session.nav.getCurrentService()
            seek = service.seek() if service else None
            pos = seek.getPlayPosition() if seek else (1, 0)
            total = seek.getLength() if seek else (1, 0)
            if pos[0] or total[0] or total[1] <= 0:
                raise ValueError('Zeit noch nicht verfuegbar')
            elapsed = max(0, pos[1] // 90000)
            duration = total[1] // 90000
            left = max(0, duration - elapsed)
            percent = max(0, min(100, int(pos[1] * 100 / total[1])))
            self['progress'].setValue(percent)
            self['times'].setText('%s / %s' % (self.clock(elapsed), self.clock(duration)))
            self['remaining'].setText('Noch ' + self.clock(left))
        except Exception:
            self['progress'].setValue(0)
            self['times'].setText('--:-- / --:--')
            self['remaining'].setText('Noch --:--')

_ef_display_previous_summary = EmbyFlowMoviePlayer.createSummary

def _ef_display_create_summary(self):
    if config.embyflow.box_display.value:
        try:
            desktop = _EFDisplayDesktop(1)
            if desktop and desktop.size().width() > 0 and desktop.size().height() > 0:
                return _EFDisplaySummary
        except Exception:
            pass
    return _ef_display_previous_summary(self)

EmbyFlowMoviePlayer.createSummary = _ef_display_create_summary

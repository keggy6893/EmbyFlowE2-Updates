# EMBYFLOW_LCD_CONTENT_CLOCK_V1
import sys as _eflcd_sys
import time as _eflcd_time
import types as _eflcd_types


class _EFLCDTimeView:
    """Override only renderer-local clock fields, forwarding the existing UI."""
    def __init__(self, original, length, position):
        object.__setattr__(self, '_original', original)
        object.__setattr__(self, 'Llength', [0, length])
        object.__setattr__(self, 'Lposition', [0, position])

    def __getattr__(self, name):
        return getattr(self._original, name)

    def __setattr__(self, name, value):
        if name in ('Llength', 'Lposition'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._original, name, value)


def _eflcd_code_names(code):
    names = set(code.co_names)
    for value in code.co_consts:
        if isinstance(value, _eflcd_types.CodeType):
            names.update(_eflcd_code_names(value))
    return names


def _eflcd_bridge(module):
    original = getattr(module, 'LCD4linuxPIC', None)
    state = getattr(original, '_embyflow_clock_state', None)
    if state is not None:
        return state
    code = getattr(original, '__code__', None)
    if (code is None or code.co_argcount != 2
            or code.co_varnames[:2] != ('self', 'session')
            or not {'Llength', 'Lposition'}.issubset(_eflcd_code_names(code))):
        return None
    state = {'snapshot': None}

    def render(status, session):
        snapshot = state['snapshot']
        view = status
        if snapshot is not None:
            owner, session_id, reference, length, position, timestamp = snapshot
            age = _eflcd_time.monotonic() - timestamp
            if (id(session) == session_id and 0 <= age <= 5
                    and getattr(status, 'LsreftoString', None) == reference):
                view = _EFLCDTimeView(status, length, position)
        return original(view, session)

    render._embyflow_clock_state = state
    module.LCD4linuxPIC = render
    return state


def _eflcd_publish(self):
    state = getattr(self, '_eflcd_state', None)
    if state is None:
        return
    try:
        if bool(getattr(self, 'closed', False)):
            raise ValueError('Player closed')
        active = self.session.nav.getCurrentlyPlayingServiceReference()
        own = getattr(self, 'ref', None)
        if active is None or own is None or active.toString() != own.toString():
            raise ValueError('Different service')
        duration = int(self.duration_ticks or 0)
        position = int(self.current_position_ticks())
        if duration <= 0 or position < 0:
            raise ValueError('Unknown clock')
        position = min(position, duration)
        # Emby uses 10 MHz ticks; LCD4linux consumes 90 kHz PTS.
        length_pts = duration * 9 // 1000
        position_pts = position * 9 // 1000
        if length_pts <= 0:
            raise ValueError('Unknown length')
        state['snapshot'] = (self._eflcd_owner, id(self.session), own.toString(),
                             length_pts, position_pts, _eflcd_time.monotonic())
    except Exception:
        snapshot = state['snapshot']
        if snapshot is not None and snapshot[0] is self._eflcd_owner:
            state['snapshot'] = None


def _eflcd_close(self):
    timer = getattr(self, '_eflcd_timer', None)
    if timer is not None:
        timer.stop()
    state = getattr(self, '_eflcd_state', None)
    if state is not None:
        snapshot = state['snapshot']
        if snapshot is not None and snapshot[0] is self._eflcd_owner:
            state['snapshot'] = None


_EFLCD_PLAYER_INIT = EmbyFlowMoviePlayer.__init__


def _eflcd_init(self, *args, **kwargs):
    _EFLCD_PLAYER_INIT(self, *args, **kwargs)
    module = _eflcd_sys.modules.get('Plugins.Extensions.LCD4linux.plugin')
    if module is None:
        return
    try:
        state = _eflcd_bridge(module)
        if state is None:
            print('[EmbyFlow LCD] Renderer API unsupported; left unchanged.')
            return
        from enigma import eTimer
        self._eflcd_state = state
        self._eflcd_owner = object()
        self._eflcd_timer = eTimer()
        if hasattr(self._eflcd_timer, 'callback'):
            self._eflcd_timer.callback.append(self._eflcd_publish)
        else:
            self._eflcd_connection = self._eflcd_timer.timeout.connect(self._eflcd_publish)
        self.onClose.append(self._eflcd_close)
        self._eflcd_publish()
        self._eflcd_timer.start(1000)
    except Exception as error:
        self._eflcd_close()
        print('[EmbyFlow LCD] Optional clock bridge inactive: %s' % type(error).__name__)


EmbyFlowMoviePlayer._eflcd_publish = _eflcd_publish
EmbyFlowMoviePlayer._eflcd_close = _eflcd_close
EmbyFlowMoviePlayer.__init__ = _eflcd_init

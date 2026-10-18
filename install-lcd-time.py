"""Receiver-local addon; compile, back up and replace without changing LCD4linux."""
from pathlib import Path
import os
import shutil
import tempfile
import time


def patched(source, runtime):
    if '# EMBYFLOW_LCD_CONTENT_CLOCK_V1' in source:
        return source
    for required in ('class EmbyFlowMoviePlayer', 'def current_position_ticks(', 'def item_duration_ticks('):
        if required not in source:
            raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
    result = source + '\n\n' + runtime
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, runtime):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad.')
    source = path.read_text()
    result = patched(source, runtime)
    if source == result:
        print('LCD-Zeittest bereits installiert.', flush=True)
        return False
    backup = str(path)+'.vor-lcdzeit-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits.')
    shutil.copy2(path, backup)
    fd, name = tempfile.mkstemp(prefix='plugin.py.lcd-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(result);handle.flush();os.fsync(handle.fileno())
        shutil.copystat(path, name)
        os.replace(name, path)
    finally:
        if os.path.exists(name):os.unlink(name)
    print('LCD-Zeittest installiert. Sicherung:', backup, flush=True)
    return True

RUNTIME = '# EMBYFLOW_LCD_CONTENT_CLOCK_V1\nimport sys as _eflcd_sys\nimport time as _eflcd_time\nimport types as _eflcd_types\n\n\nclass _EFLCDTimeView:\n    """Override only renderer-local clock fields, forwarding the existing UI."""\n    def __init__(self, original, length, position):\n        object.__setattr__(self, \'_original\', original)\n        object.__setattr__(self, \'Llength\', [0, length])\n        object.__setattr__(self, \'Lposition\', [0, position])\n\n    def __getattr__(self, name):\n        return getattr(self._original, name)\n\n    def __setattr__(self, name, value):\n        if name in (\'Llength\', \'Lposition\'):\n            object.__setattr__(self, name, value)\n        else:\n            setattr(self._original, name, value)\n\n\ndef _eflcd_code_names(code):\n    names = set(code.co_names)\n    for value in code.co_consts:\n        if isinstance(value, _eflcd_types.CodeType):\n            names.update(_eflcd_code_names(value))\n    return names\n\n\ndef _eflcd_bridge(module):\n    original = getattr(module, \'LCD4linuxPIC\', None)\n    state = getattr(original, \'_embyflow_clock_state\', None)\n    if state is not None:\n        return state\n    code = getattr(original, \'__code__\', None)\n    if (code is None or code.co_argcount != 2\n            or code.co_varnames[:2] != (\'self\', \'session\')\n            or not {\'Llength\', \'Lposition\'}.issubset(_eflcd_code_names(code))):\n        return None\n    state = {\'snapshot\': None}\n\n    def render(status, session):\n        snapshot = state[\'snapshot\']\n        view = status\n        if snapshot is not None:\n            owner, session_id, reference, length, position, timestamp = snapshot\n            age = _eflcd_time.monotonic() - timestamp\n            if (id(session) == session_id and 0 <= age <= 5\n                    and getattr(status, \'LsreftoString\', None) == reference):\n                view = _EFLCDTimeView(status, length, position)\n        return original(view, session)\n\n    render._embyflow_clock_state = state\n    module.LCD4linuxPIC = render\n    return state\n\n\ndef _eflcd_publish(self):\n    state = getattr(self, \'_eflcd_state\', None)\n    if state is None:\n        return\n    try:\n        if bool(getattr(self, \'closed\', False)):\n            raise ValueError(\'Player closed\')\n        active = self.session.nav.getCurrentlyPlayingServiceReference()\n        own = getattr(self, \'ref\', None)\n        if active is None or own is None or active.toString() != own.toString():\n            raise ValueError(\'Different service\')\n        duration = int(self.duration_ticks or 0)\n        position = int(self.current_position_ticks())\n        if duration <= 0 or position < 0:\n            raise ValueError(\'Unknown clock\')\n        position = min(position, duration)\n        # Emby uses 10 MHz ticks; LCD4linux consumes 90 kHz PTS.\n        length_pts = duration * 9 // 1000\n        position_pts = position * 9 // 1000\n        if length_pts <= 0:\n            raise ValueError(\'Unknown length\')\n        state[\'snapshot\'] = (self._eflcd_owner, id(self.session), own.toString(),\n                             length_pts, position_pts, _eflcd_time.monotonic())\n    except Exception:\n        snapshot = state[\'snapshot\']\n        if snapshot is not None and snapshot[0] is self._eflcd_owner:\n            state[\'snapshot\'] = None\n\n\ndef _eflcd_close(self):\n    timer = getattr(self, \'_eflcd_timer\', None)\n    if timer is not None:\n        timer.stop()\n    state = getattr(self, \'_eflcd_state\', None)\n    if state is not None:\n        snapshot = state[\'snapshot\']\n        if snapshot is not None and snapshot[0] is self._eflcd_owner:\n            state[\'snapshot\'] = None\n\n\n_EFLCD_PLAYER_INIT = EmbyFlowMoviePlayer.__init__\n\n\ndef _eflcd_init(self, *args, **kwargs):\n    _EFLCD_PLAYER_INIT(self, *args, **kwargs)\n    module = _eflcd_sys.modules.get(\'Plugins.Extensions.LCD4linux.plugin\')\n    if module is None:\n        return\n    try:\n        state = _eflcd_bridge(module)\n        if state is None:\n            print(\'[EmbyFlow LCD] Renderer API unsupported; left unchanged.\')\n            return\n        from enigma import eTimer\n        self._eflcd_state = state\n        self._eflcd_owner = object()\n        self._eflcd_timer = eTimer()\n        if hasattr(self._eflcd_timer, \'callback\'):\n            self._eflcd_timer.callback.append(self._eflcd_publish)\n        else:\n            self._eflcd_connection = self._eflcd_timer.timeout.connect(self._eflcd_publish)\n        self.onClose.append(self._eflcd_close)\n        self._eflcd_publish()\n        self._eflcd_timer.start(1000)\n    except Exception as error:\n        self._eflcd_close()\n        print(\'[EmbyFlow LCD] Optional clock bridge inactive: %s\' % type(error).__name__)\n\n\nEmbyFlowMoviePlayer._eflcd_publish = _eflcd_publish\nEmbyFlowMoviePlayer._eflcd_close = _eflcd_close\nEmbyFlowMoviePlayer.__init__ = _eflcd_init\n'

if __name__ == '__main__':
    changed = install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py', RUNTIME)
    if changed:
        print('GUI startet neu. Danach Film in EmbyFlow starten.', flush=True)
        os.system('init 4')
        time.sleep(3)
        os.system('init 3')

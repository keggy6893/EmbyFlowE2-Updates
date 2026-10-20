# EMBYFLOW_DISPLAY_CONTENT_CLOCK_V1_BEGIN
# One corrected content clock for EmbyFlow's own displays and compatible L4L renderers.
# Never replace seek/getCurrentService or write LCD4linux files/settings.
import time as _eflc_time
import sys as _eflc_sys
import weakref as _eflc_weak
import types as _eflc_types
import os as _eflc_os

_EFLC_ACTIVE = None
_EFLC_ATTACH_AT = 0.0
_EFLC_LOG_AT = {}


def _eflc_log(kind, **values):
    now = _eflc_time.monotonic()
    if now - _EFLC_LOG_AT.get(kind, -1000.0) < 30:
        return
    _EFLC_LOG_AT[kind] = now
    try:
        path='/tmp/embyflow-display-time.log'
        mode='w' if _eflc_os.path.exists(path) and _eflc_os.path.getsize(path)>65536 else 'a'
        with open(path,mode) as f:
            f.write(_eflc_time.strftime('%H:%M:%S')+' '+kind+' '+
                    ' '.join('%s=%s'%(key,str(value)[:80]) for key,value in sorted(values.items()))+'\n')
    except OSError:
        pass


def _eflc_clock(player):
    """Same metadata duration and absolute content position as the TV overlay, in PTS."""
    if player is None or getattr(player,'closed',False):
        return None
    try:
        duration=int(getattr(player,'duration_ticks',0) or 0)
        if duration<=0:
            duration=int(player.item_duration_ticks() or 0)
        position=int(player.current_position_ticks())
        if duration<10000000 or position<0:
            return None
        position=min(position,duration)
        return (position*9//1000,duration*9//1000)
    except Exception:
        return None


def _eflc_owned_reference(player):
    try:
        current=player.session.nav.getCurrentlyPlayingServiceReference()
        own=player.ref
        if current is None or own is None:
            return None
        current_text=current.toString()
        if current_text==own.toString():
            return current_text
        # The existing optional buffer proxy legitimately changes the service URL.
        state=globals().get('_efstream_active')
        if isinstance(state,dict) and state.get('owner') is player and state.get('nav') is player.session.nav and state.get('reference')==current_text:
            return current_text
    except Exception:
        pass
    return None


def _eflc_publish(player):
    global _EFLC_ACTIVE
    try:
        reference=_eflc_owned_reference(player)
        clock=_eflc_clock(player) if reference else None
        if clock is None:
            if _EFLC_ACTIVE and _EFLC_ACTIVE['owner']() is player:
                _EFLC_ACTIVE=None
            return
        position,duration=clock
        _EFLC_ACTIVE={'owner':_eflc_weak.ref(player),'session':player.session,
                      'reference':reference,'position':position,'duration':duration,
                      'at':_eflc_time.monotonic()}
        _eflc_log('CONTENT_CLOCK',position_pts=position,duration_pts=duration,
                  remaining_seconds=max(0,duration-position)//90000)
        _eflc_attach()
    except Exception:
        # A diagnostic/front-panel failure must not break playback or its overlay.
        _eflc_log('CLOCK_UNAVAILABLE')


def _eflc_snapshot(display,session):
    state=_EFLC_ACTIVE
    if not state or state['session'] is not session or _eflc_time.monotonic()-state['at']>3:
        return None
    owner=state['owner']()
    if owner is None or getattr(owner,'closed',False):
        return None
    if getattr(display,'LsreftoString',None)!=state['reference']:
        return None
    # Music casting and external inputs retain their native clocks.
    if any(bool(getattr(display,key,False)) for key in ('SonosRunning','YMCastRunning','BlueRunning')):
        return None
    return state


class _EFLCView:
    """Render-only view; never overwrite L4L's shared service cache."""
    def __init__(self,display,state):
        object.__setattr__(self,'_display',display)
        object.__setattr__(self,'_clock',state)
    def __getattr__(self,name):
        if name=='Llength':return [0,self._clock['duration']]
        if name=='Lposition':return [0,self._clock['position']]
        return getattr(self._display,name)
    def __setattr__(self,name,value):
        if name in ('Llength','Lposition'):
            # Writes inside a future renderer must not leak corrected values globally.
            return
        setattr(self._display,name,value)


def _eflc_renderer_supported(fn):
    code=getattr(fn,'__code__',None)
    if not isinstance(code,_eflc_types.CodeType) or code.co_argcount!=2 or code.co_varnames[:2]!=('self','session'):
        return False
    # Inspect compiled code as well: installed LCD4linux often ships only plugin.pyc.
    for child in code.co_consts:
        if isinstance(child,_eflc_types.CodeType) and child.co_name=='putProgress':
            return {'Llength','Lposition'}.issubset(child.co_names) and 90000 in child.co_consts
    return False


def _eflc_attach_module(module):
    original=getattr(module,'LCD4linuxPIC',None)
    if getattr(original,'_embyflow_content_clock',False):
        return True
    if not _eflc_renderer_supported(original):
        _eflc_log('LCD4LINUX_UNSUPPORTED',version=str(getattr(module,'Version','unknown')))
        return False
    def picture(display,session):
        state=_eflc_snapshot(display,session)
        if state is None:
            return original(display,session)
        native_length=getattr(display,'Llength',None)
        native_position=getattr(display,'Lposition',None)
        def number(value):
            return int(value[1]) if isinstance(value,(tuple,list)) and len(value)>1 and isinstance(value[1],int) else 'unknown'
        _eflc_log('LCD4LINUX_CONTENT_CLOCK',native_length_pts=number(native_length),
                  native_position_pts=number(native_position),content_length_pts=state['duration'],
                  content_position_pts=state['position'])
        return original(_EFLCView(display,state),session)
    picture._embyflow_content_clock=True
    picture._embyflow_original=original
    module.LCD4linuxPIC=picture
    _eflc_log('LCD4LINUX_ATTACHED',version=str(getattr(module,'Version','unknown')))
    return True


def _eflc_attach():
    global _EFLC_ATTACH_AT
    now=_eflc_time.monotonic()
    if now<_EFLC_ATTACH_AT:return
    _EFLC_ATTACH_AT=now+10
    # Do not import/start another plugin. Adapt only an already active renderer.
    for name,module in list(_eflc_sys.modules.items()):
        if name=='Plugins.Extensions.LCD4linux.plugin':
            _eflc_attach_module(module)
            break


def _eflc_summary_refresh(self):
    self['title'].setText(str(getattr(self.player,'title_text','EmbyFlow')))
    self['status'].setText('PAUSE' if bool(getattr(self.player,'paused',False)) else 'Wiedergabe')
    clock=_eflc_clock(self.player)
    if clock is None:
        self['progress'].setValue(0)
        self['times'].setText('--:-- / --:--')
        self['remaining'].setText('Noch --:--')
        return
    position,duration=clock
    self['progress'].setValue(min(100,position*100//duration))
    self['times'].setText('%s / %s'%(self.clock(position//90000),self.clock(duration//90000)))
    self['remaining'].setText('Noch '+self.clock(max(0,duration-position)//90000))


_EFLC_SEGMENT_INIT=_EFSegmentSummary.__init__
def _eflc_segment_init(self,session,parent):
    self.player=parent
    _EFLC_SEGMENT_INIT(self,session,parent)


def _eflc_segment_refresh(self):
    clock=_eflc_clock(self.player)
    text='----' if clock is None else _efsegment_remaining((0,clock[0]),(0,clock[1]))
    self['segment_time'].setText(text)


_EFLC_PLAYER_INIT=EmbyFlowMoviePlayer.__init__
_EFLC_PLAYER_OVERLAY=EmbyFlowMoviePlayer.update_playback_overlay

def _eflc_player_init(self,*args,**kwargs):
    _EFLC_PLAYER_INIT(self,*args,**kwargs)
    self.onClose.append(self._display_content_clock_close)


def _eflc_player_overlay(self,*args,**kwargs):
    result=_EFLC_PLAYER_OVERLAY(self,*args,**kwargs)
    _eflc_publish(self)
    return result


def _eflc_player_close(self):
    global _EFLC_ACTIVE
    if _EFLC_ACTIVE and _EFLC_ACTIVE['owner']() is self:
        _EFLC_ACTIVE=None


_EFDisplaySummary.refresh=_eflc_summary_refresh
_EFSegmentSummary.__init__=_eflc_segment_init
_EFSegmentSummary.refresh=_eflc_segment_refresh
EmbyFlowMoviePlayer._display_content_clock_close=_eflc_player_close
EmbyFlowMoviePlayer.__init__=_eflc_player_init
EmbyFlowMoviePlayer.update_playback_overlay=_eflc_player_overlay
# EMBYFLOW_DISPLAY_CONTENT_CLOCK_V1_END

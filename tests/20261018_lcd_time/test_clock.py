from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
import sys
import tempfile
import unittest

from install import patched, install

HERE = Path(__file__).resolve().parent
RUNTIME = (HERE/'runtime.py').read_text()
LCD_MODULE = 'Plugins.Extensions.LCD4linux.plugin'


class Ref:
    def __init__(self, value):self.value=value
    def toString(self):return self.value


class Timer:
    def __init__(self):self.callback=[];self.active=False
    def start(self, milliseconds):self.active=True
    def stop(self):self.active=False


def load():
    class Player:
        def __init__(self, session, duration=158*60*10000000, position=49*60*10000000):
            self.session=session;self.ref=Ref('own');self.duration_ticks=duration
            self.position=position;self.onClose=[];self.closed=False
        def current_position_ticks(self):return self.position
    ns={'EmbyFlowMoviePlayer':Player}
    exec(RUNTIME,ns)
    return ns


def renderer(self, session):
    self.frames += 1
    return self.Llength[:], self.Lposition[:], self.poster


class ClockTests(unittest.TestCase):
    def setUp(self):
        self.ns=load()
        self.module=ModuleType(LCD_MODULE);self.module.LCD4linuxPIC=renderer
        enigma=ModuleType('enigma');enigma.eTimer=Timer
        self.patch=patch.dict(sys.modules,{LCD_MODULE:self.module,'enigma':enigma})
        self.patch.start();self.addCleanup(self.patch.stop)
        self.active=Ref('own')
        self.session=SimpleNamespace(nav=SimpleNamespace(getCurrentlyPlayingServiceReference=lambda:self.active))
        self.status=SimpleNamespace(Llength=[0,86400*90000],Lposition=[0,49*60*90000],
                                    LsreftoString='own',poster=object(),frames=0)
        self.player=self.ns['EmbyFlowMoviePlayer'](self.session)

    def render(self, session=None):return self.module.LCD4linuxPIC(self.status,session or self.session)

    def test_true_content_clock_and_original_fields_untouched(self):
        length,position,poster=self.render()
        self.assertEqual(length,[0,158*60*90000])
        self.assertEqual(position,[0,49*60*90000])
        self.assertIs(poster,self.status.poster)
        self.assertEqual(self.status.Llength,[0,86400*90000])
        self.assertEqual(self.status.frames,1)

    def test_seek_pause_and_end_follow_player_clock(self):
        for minutes in (0,20,49,100,158,160):
            self.player.position=minutes*60*10000000
            self.player._eflcd_publish()
            self.assertEqual(self.render()[1],[0,min(minutes,158)*60*90000])
        self.player.paused=True
        self.player._eflcd_publish()
        self.assertEqual(self.render()[1],[0,158*60*90000])

    def test_foreign_service_and_session_unmodified(self):
        self.status.LsreftoString='live-tv'
        self.assertEqual(self.render()[0],self.status.Llength)
        self.status.LsreftoString='own'
        self.assertEqual(self.render(SimpleNamespace())[0],self.status.Llength)

    def test_switch_away_clears_snapshot(self):
        self.active=Ref('live-tv');self.player._eflcd_publish()
        self.assertIsNone(self.player._eflcd_state['snapshot'])
        self.assertEqual(self.render()[0],self.status.Llength)

    def test_unknown_invalid_and_closed_clock_preserve_backend(self):
        for duration,position,closed in ((0,1,False),(100,-1,False),(100,1,True)):
            self.player.duration_ticks=duration;self.player.position=position;self.player.closed=closed
            self.player._eflcd_publish()
            self.assertEqual(self.render()[0],self.status.Llength)

    def test_snapshot_expires(self):
        state=self.player._eflcd_state
        state['snapshot']=state['snapshot'][:-1]+(self.ns['_eflcd_time'].monotonic()-6,)
        self.assertEqual(self.render()[0],self.status.Llength)

    def test_close_stops_timer_and_clears_only_own_snapshot(self):
        second=self.ns['EmbyFlowMoviePlayer'](self.session,position=10*10000000)
        self.player.onClose[-1]()
        self.assertFalse(self.player._eflcd_timer.active)
        self.assertEqual(self.render()[1],[0,900000])
        second.onClose[-1]()
        self.assertEqual(self.render()[0],self.status.Llength)

    def test_renderer_hook_is_idempotent(self):
        function=self.module.LCD4linuxPIC
        state=self.ns['_eflcd_bridge'](self.module)
        self.assertIs(self.module.LCD4linuxPIC,function)
        self.assertIs(state,self.player._eflcd_state)

    def test_absent_plugin_or_unsupported_api_does_not_break_player(self):
        with patch.dict(sys.modules,{LCD_MODULE:None}):
            player=self.ns['EmbyFlowMoviePlayer'](self.session)
            self.assertFalse(hasattr(player,'_eflcd_timer'))
        self.module.LCD4linuxPIC=lambda one:one
        player=self.ns['EmbyFlowMoviePlayer'](self.session)
        self.assertFalse(hasattr(player,'_eflcd_timer'))

    def test_renderer_exception_not_retried_or_hidden(self):
        def broken(self,session):
            self.frames+=1
            unused=(self.Llength,self.Lposition)
            raise RuntimeError('Renderer failure')
        self.module.LCD4linuxPIC=broken
        state=self.ns['_eflcd_bridge'](self.module)
        state['snapshot']=self.player._eflcd_state['snapshot']
        with self.assertRaisesRegex(RuntimeError,'Renderer failure'):
            self.render()
        self.assertEqual(self.status.frames,1)
        self.assertEqual(self.status.Llength,[0,86400*90000])

    def test_native_seek_not_called_from_renderer_worker(self):
        def unavailable():raise AssertionError('Receiver API in worker')
        self.session.nav.getCurrentlyPlayingServiceReference=unavailable
        self.assertEqual(self.render()[0],[0,158*60*90000])


class InstallerTests(unittest.TestCase):
    def test_full_release_and_custom_additions_preserved_with_backup(self):
        source=(HERE.parents[1]/'EmbyFlowE2_2026101802.py').read_text()+'\nCUSTOM_LOCAL = True\n'
        result=patched(source,RUNTIME)
        self.assertTrue(result.startswith(source))
        self.assertEqual(patched(result,RUNTIME),result)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'plugin.py';target.write_text(source);target.chmod(0o640)
            self.assertTrue(install(target,RUNTIME))
            self.assertEqual(target.read_text(),result)
            self.assertEqual(next(Path(directory).glob('*.vor-lcdzeit-*')).read_text(),source)
            self.assertEqual(target.stat().st_mode & 0o777,0o640)

    def test_wrong_plugin_rejected_before_write(self):
        with self.assertRaises(RuntimeError):patched('PLUGIN_VERSION = "other"',RUNTIME)

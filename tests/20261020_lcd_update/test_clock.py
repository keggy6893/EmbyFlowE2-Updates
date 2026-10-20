import ast,hashlib,sys,types,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
HERE=Path(__file__).parent
ROOT=HERE.parents[1]
BASE=ROOT/'EmbyFlowE2_2026101805.py'
RUNTIME=(HERE/'runtime.py').read_text()

def upstream():
    import urllib.request
    path=Path('/tmp/embyflow-lcd4linux-r36.py')
    expected='9d4774c9c9285b343d8e897096a79449b8ab7a9538093fda7f8747a4e874c288'
    if not path.exists():
        url='https://raw.githubusercontent.com/oe-alliance/oe-alliance-plugins/4d4bde2651a25bf9570be58182af8f6ad64b29d9/LCD4linux/src/plugin.py'
        path.write_bytes(urllib.request.urlopen(url,timeout=15).read())
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise AssertionError('LCD4linux reference checksum mismatch')
    return data.decode()
class Ref:
    def __init__(self,value='movie'):self.value=value
    def toString(self):return self.value
class Player:
    def __init__(self):
        self.closed=False;self.duration_ticks=180*60*10000000;self.position=20*60*10000000;self.ref=Ref();self.onClose=[];self.paused=False
        self.session=NS(nav=NS(getCurrentlyPlayingServiceReference=lambda:self.ref))
    def current_position_ticks(self):return self.position
    def item_duration_ticks(self):return 0
    def update_playback_overlay(self):return 'unchanged'
class Segment:
    def __init__(self,*args):pass
class Summary:pass
class Widget:
    def setText(self,value):self.text=value
    def setValue(self,value):self.value=value

def load():
    ns={'EmbyFlowMoviePlayer':type('Player',(Player,),{}),'_EFSegmentSummary':type('Segment',(Segment,),{}),'_EFDisplaySummary':type('Summary',(Summary,),{})}
    tree=ast.parse(BASE.read_text())
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_efsegment_remaining')
    exec(compile(ast.Module(body=[f],type_ignores=[]),'segment-original','exec'),ns)
    exec(RUNTIME,ns);ns['_eflc_log']=lambda *a,**kw:None;ns['_eflc_attach']=lambda:None
    return ns

class ClockTests(unittest.TestCase):
    def setUp(self):self.ns=load();self.p=self.ns['EmbyFlowMoviePlayer']()
    def test_metadata_wins_over_incorrect_native_duration(self):
        self.assertEqual(self.ns['_eflc_clock'](self.p),(20*60*90000,180*60*90000))
    def test_content_position_after_restart(self):
        self.p.position=(60*60+5)*10000000
        self.assertEqual(self.ns['_eflc_clock'](self.p)[0],(60*60+5)*90000)
    def test_exact_integer_unit_conversion(self):
        self.p.position=10000001
        self.assertEqual(self.ns['_eflc_clock'](self.p)[0],90000)
    def test_pause_does_not_advance_clock(self):
        self.p.paused=True
        self.assertEqual(self.ns['_eflc_clock'](self.p),self.ns['_eflc_clock'](self.p))
    def test_end_clamps_negative_remaining(self):
        self.p.position=self.p.duration_ticks+10000000
        a,b=self.ns['_eflc_clock'](self.p);self.assertEqual(a,b)
    def test_invalid_and_closed_are_unknown(self):
        for duration,pos in [(0,0),(1,0),(-1,0),(10000000,-1)]:
            self.p.duration_ticks=duration;self.p.position=pos;self.assertIsNone(self.ns['_eflc_clock'](self.p))
        self.p.closed=True;self.assertIsNone(self.ns['_eflc_clock'](self.p))
    def test_position_failure_is_safe(self):
        def failed():raise RuntimeError('seek not ready')
        self.p.current_position_ticks=failed;self.assertIsNone(self.ns['_eflc_clock'](self.p))
    def test_duration_metadata_fallback(self):
        self.p.duration_ticks=0;self.p.item_duration_ticks=lambda:120*60*10000000
        self.assertEqual(self.ns['_eflc_clock'](self.p)[1],120*60*90000)
    def test_overlay_return_and_close_preserved(self):
        self.assertEqual(self.p.update_playback_overlay(),'unchanged');self.assertIsNotNone(self.ns['_EFLC_ACTIVE'])
        for cb in self.p.onClose:cb()
        self.assertIsNone(self.ns['_EFLC_ACTIVE'])
    def test_other_service_never_receives_clock(self):
        self.p.session.nav.getCurrentlyPlayingServiceReference=lambda:Ref('live-tv')
        self.ns['_eflc_publish'](self.p);self.assertIsNone(self.ns['_EFLC_ACTIVE'])
    def test_buffer_proxy_requires_exact_owner(self):
        current=Ref('buffered');self.p.session.nav.getCurrentlyPlayingServiceReference=lambda:current
        self.ns['_efstream_active']={'owner':self.p,'nav':self.p.session.nav,'reference':'buffered'}
        self.ns['_eflc_publish'](self.p);self.assertIsNotNone(self.ns['_EFLC_ACTIVE'])
        self.ns['_efstream_active']['owner']=object();self.ns['_eflc_publish'](self.p);self.assertIsNone(self.ns['_EFLC_ACTIVE'])
    def test_own_front_display_uses_content_clock(self):
        p=self.p;d={name:Widget() for name in ('title','status','times','remaining','progress')}
        class S(dict):
            player=p
            clock=staticmethod(lambda sec:str(sec))
        screen=S(d);self.ns['_eflc_summary_refresh'](screen)
        self.assertEqual(screen['remaining'].text,'Noch 9600');self.assertEqual(screen['progress'].value,11)
    def test_segment_retains_correct_rounding(self):
        p=self.p
        class S(dict):player=p
        s=S(segment_time=Widget());self.ns['_eflc_segment_refresh'](s);self.assertEqual(s['segment_time'].text,'0240')

class LCDTests(unittest.TestCase):
    def setUp(self):self.ns=load();self.p=self.ns['EmbyFlowMoviePlayer']();self.ns['_eflc_publish'](self.p)
    def renderer(self):
        # Shape of real compiled L4L putProgress; no dependency on source installation.
        def LCD4linuxPIC(self,session):
            def putProgress():return (self.Llength[1]-self.Lposition[1])//90000
            self.Refresh=0
            return putProgress()
        return NS(LCD4linuxPIC=LCD4linuxPIC,Version='test')
    def display(self):return NS(Llength=[0,24*60*60*90000],Lposition=[0,60*90000],LsreftoString='movie',Refresh=5)
    def test_proxy_corrects_only_render_view(self):
        module=self.renderer();display=self.display();original_l=display.Llength;original_p=display.Lposition
        self.assertTrue(self.ns['_eflc_attach_module'](module))
        self.assertEqual(module.LCD4linuxPIC(display,self.p.session),160*60)
        self.assertIs(display.Llength,original_l);self.assertIs(display.Lposition,original_p);self.assertEqual(display.Refresh,0)
    def test_live_tv_and_other_sessions_unchanged(self):
        module=self.renderer();display=self.display();self.ns['_eflc_attach_module'](module)
        display.LsreftoString='live';self.assertEqual(module.LCD4linuxPIC(display,self.p.session),24*60*60-60)
        display.LsreftoString='movie';self.assertEqual(module.LCD4linuxPIC(display,object()),24*60*60-60)
    def test_casting_unchanged(self):
        module=self.renderer();display=self.display();display.YMCastRunning=True;self.ns['_eflc_attach_module'](module)
        self.assertEqual(module.LCD4linuxPIC(display,self.p.session),24*60*60-60)
    def test_stale_and_closed_clock_not_used(self):
        module=self.renderer();display=self.display();self.ns['_eflc_attach_module'](module)
        self.ns['_EFLC_ACTIVE']['at']-=10;self.assertEqual(module.LCD4linuxPIC(display,self.p.session),24*60*60-60)
        self.ns['_eflc_publish'](self.p);self.p.closed=True;self.assertEqual(module.LCD4linuxPIC(display,self.p.session),24*60*60-60)
    def test_unsupported_renderer_not_modified(self):
        fn=lambda self,session:42;module=NS(LCD4linuxPIC=fn)
        self.assertFalse(self.ns['_eflc_attach_module'](module));self.assertIs(module.LCD4linuxPIC,fn)
    def test_idempotent_attachment(self):
        module=self.renderer();self.ns['_eflc_attach_module'](module);fn=module.LCD4linuxPIC
        self.ns['_eflc_attach_module'](module);self.assertIs(module.LCD4linuxPIC,fn)
    def test_actual_compiled_r36_renderer_is_recognized(self):
        code=compile(upstream(),'lcd4linux-reference','exec')
        renderer=next(c for c in code.co_consts if isinstance(c,types.CodeType) and c.co_name=='LCD4linuxPIC')
        self.assertTrue(self.ns['_eflc_renderer_supported'](types.FunctionType(renderer,{})))
    def test_actual_upstream_putprogress_with_render_view(self):
        tree=ast.parse(upstream());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='putProgress')
        source=ast.unparse(node);captured=[]
        display=self.display();display.im={0:NS(size=(800,480))}
        view=self.ns['_EFLCView'](display,self.ns['_EFLC_ACTIVE'])
        ns={'self':view,'ImageFont':NS(truetype=lambda *a,**k:None),'getProgess':lambda width,percent:width,'getSplit':lambda *a:0,'getFsize':lambda text,font:(len(text)*8,16),'ShadowText':lambda *a:captured.append(a[3]),'L4log':lambda *a:None}
        exec(source,ns)
        ns['putProgress']((400,16,100,'21','white','white','0','0',True,'off','false','false','font'),0,0)
        self.assertEqual(captured,['+160 min'])
        self.assertEqual(display.Llength,[0,24*60*60*90000])

if __name__=='__main__':unittest.main()

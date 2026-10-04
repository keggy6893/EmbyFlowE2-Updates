from pathlib import Path
import ast,sys,types,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
s=(root/'EmbyFlowE2_Segmentdisplay_20261004_0406.py').read_text()
compile(s,'plugin.py','exec');tree=ast.parse(s)
names={'_efsegment_detect','_efsegment_remaining','_EFSegmentSummary','_efsegment_create_summary'}
code='\n\n'.join(ast.get_source_segment(s,n) for n in tree.body if getattr(n,'name',None) in names)
class Screen(dict):
 def __init__(self,session,parent=None):
  dict.__init__(self);self.session=session;self.parent=parent
  self.onShow=[];self.onHide=[];self.onClose=[]
class Label:
 def __init__(self,text):self.text=text
 def setText(self,text):self.text=text
class Timer:
 def __init__(self):self.callback=[];self.active=False
 def start(self,value):self.active=True
 def stop(self):self.active=False
setting=types.SimpleNamespace(value=True)
env=dict(Screen=Screen,_EFDisplayLabel=Label,_EFDisplayTimer=Timer,
 config=types.SimpleNamespace(embyflow=types.SimpleNamespace(box_display=setting)),
 _efsegment_previous_summary=lambda self:'previous')
exec(code,env)
f=env['_efsegment_remaining'];ticks=90000
assert f((0,0),(0,82*60*ticks))=='0122'
assert f((0,60*ticks),(0,82*60*ticks))=='0121'
assert f((0,82*60*ticks),(0,82*60*ticks))=='0000'
assert f((1,0),(0,100))=='----'
assert f((0,0),(0,0))=='----'
assert f((0,0),(0,61*ticks))=='0002'
assert f((0,0),(0,200*3600*ticks))=='9959'
module=types.ModuleType('Components.SystemInfo')
values={'7segment':True,'displaytype':'7segment','model':'dm8000'}
module.BoxInfo=types.SimpleNamespace(getItem=values.get)
previous=sys.modules.get('Components.SystemInfo')
sys.modules['Components.SystemInfo']=module
try:
 assert env['_efsegment_create_summary'](None) is env['_EFSegmentSummary']
 values.update({'7segment':False,'displaytype':'lcd'})
 assert env['_efsegment_create_summary'](None)=='previous'
 values['7segment']=True;setting.value=False
 assert env['_efsegment_create_summary'](None)=='previous'
 setting.value=True
 class Seek:
  def getPlayPosition(self):return (0,60*ticks)
  def getLength(self):return (0,82*60*ticks)
 session=types.SimpleNamespace(nav=types.SimpleNamespace(getCurrentService=lambda:types.SimpleNamespace(seek=lambda:Seek())))
 screen=env['_EFSegmentSummary'](session,None)
 for callback in screen.onShow:callback()
 assert screen.timer.active and screen['segment_time'].text=='0121'
 for callback in screen.onHide:callback()
 assert not screen.timer.active
 for callback in screen.onClose:callback()
 assert not screen.timer.active
 xml=ET.fromstring(screen.skin);widgets=xml.findall('widget')
 assert len(widgets)==1 and widgets[0].get('position')=='0,0'
 assert not any('open(' in line for line in (root/'release_tools/segment_display_0406.inc.py').read_text().splitlines())
finally:
 if previous is None:sys.modules.pop('Components.SystemInfo',None)
 else:sys.modules['Components.SystemInfo']=previous
print('PASS: segment detection independent of model, graphic fallback, option off, HHMM rounding, invalid time, overflow, one top-line widget and timer cleanup')

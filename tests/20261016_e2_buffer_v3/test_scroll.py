import ast
from pathlib import Path
source=Path('e2-buffer/plugin.py').read_text()
ns={}
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_embyflow_neon_advanced_skin')
helper=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_embyflow_neon_panel_edges')
exec(compile(ast.Module(body=[helper,node],type_ignores=[]),'skin','exec'),ns)
class Label:
    def __init__(self,text=''):self.text=text;self.hidden=False
    def setText(self,text):self.text=text
    def getText(self):return self.text
    def hide(self):self.hidden=True
class Advanced(dict):
    skin=ns['_embyflow_neon_advanced_skin']()
    def __init__(self,session):
        dict.__init__(self);self.focus=0;self.session=session
        for name in ('adaptive_value','debug_value','api_value','box_display_value','trailers_value','youtube_search_value','middle_help','left_help','account_status'):self[name]=Label(name)
    def refresh_all(self):self._focus_target()
    def _focus_target(self):return 48,415
    def activate(self):self['account_status'].setText('old activate')
    def move_left(self):self['account_status'].setText('old left')
    def move_right(self):self['account_status'].setText('old right')
    def _toggle_current(self):self['account_status'].setText('old toggle')
    def save_settings(self,close_after=False):self['account_status'].setText('old saved')
    def close(self,*args):pass
ns.update(EmbyFlowAdvancedSettingsNeon=Advanced,Label=Label)
# Reconstruct the exact installed 1080p settings XML modifications, without importing Enigma2.
for start,end in [
 ('import xml.etree.ElementTree as _tv_choice_et','\ndef _tv_left_up'),
 ('import xml.etree.ElementTree as _ef_display_et\n_ef_display_settings_skin','\n_ef_display_settings_init ='),
 ('_eftoggle_root = _ef_display_et.fromstring','\n_eftoggle_init_old ='),
 ('_trs5_settings_root = _ef_display_et.fromstring','\n_trs5_settings_init_old =')]:
 a=source.index(start);b=source.index(end,a);exec(source[a:b],ns)
persist=[]
ns.update(_efb_enabled=lambda:persist[-1] if persist else False,_efb_test_next=False,_efb_save=persist.append)
exec(Path('e2-buffer-test/settings_scroll.py').read_text(),ns)
import xml.etree.ElementTree as ET
root=ET.fromstring(Advanced.skin)
# Both visible text rows and value rows remain fully inside the center card.
for node in root:
 if node.get('name','').startswith('efbs_'):
  x,y=map(int,node.get('position').split(','));w,h=map(int,node.get('size').split(','))
  assert 675<=x and x+w<=1245 and 240<=y and y+h<=850
s=Advanced(None);s.refresh_all()
seen=set()
for i in range(24):
 seen.add(s.focus)
 if s.focus in ns['_efbs_focuses']:
  index=ns['_efbs_focuses'].index(s.focus);slot=index-s._efbs_offset
  assert 0<=slot<6
  assert s['efbs_label%d'%slot].getText()==ns['_efbs_labels'][index]
 s.move_down()
assert seen=={0,1,2,3,4,5,6,7,8,9,10,11}
assert s.focus==0
s.focus=11;s.refresh_all();s.activate()
assert s._efbs_test and s._efbs_enabled and not persist and ns['_efb_test_next'] is False
assert s.save_settings() is True and persist==[True] and ns['_efb_test_next'] is True
s.focus=10;s.activate();assert not s._efbs_test and not s._efbs_enabled
s.save_settings();assert persist==[True,False] and not ns['_efb_test_next']
s.focus=4;s.activate();assert s['account_status'].getText()=='old activate'
s.move_left();assert s['account_status'].getText()=='old left'
assert 'efb_more' not in Advanced.skin and 'Page2' not in Advanced.skin
print('PASS: actual settings XML, row bounds, every option reachable, automatic scrolling, original handlers retained, edits remain unsaved until Green, disabling clears test.')

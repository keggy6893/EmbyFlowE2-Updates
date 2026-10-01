import ast
from pathlib import Path
from types import SimpleNamespace
p=Path(__import__('sys').argv[1]).read_text()
tree=ast.parse(p)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_embyflow_local_tv_mute_main')
calls=[]
class State:
    finished=False
    def __init__(self,s): calls.append('mute');self.timer=SimpleNamespace(start=lambda *a: calls.append('timer'))
    def finish(self): pass
for enabled in (True,False):
    calls.clear()
    env={'config':SimpleNamespace(embyflow=SimpleNamespace(tv_sound=SimpleNamespace(value=enabled))), '_LOCAL_TV_MUTE_MAIN':lambda *a,**k:calls.append('open'), '_EmbyFlowLocalTvMute':State}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'test','exec'),env)
    env[node.name](SimpleNamespace())
    assert calls==(['open'] if enabled else ['mute','open','timer']), calls
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EmbyFlowAdvancedSettingsNeon')
for name in ('move_up','move_down','_toggle_current'):
    f=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
    env={};exec(compile(ast.Module(body=[f],type_ignores=[]),'test','exec'),env)
    obj=SimpleNamespace(focus=6,tv_sound=False,refresh_all=lambda:None)
    env[name](obj)
    assert (obj.tv_sound if name=='_toggle_current' else obj.focus)==({'move_up':5,'move_down':0,'_toggle_current':True}[name])
assert 'config.embyflow.tv_sound.save()' in p
print('5 checks passed; syntax passed; box test pending')

wizard=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EmbyFlowConnectionWizard')
assert 'tv_sound_value' not in ast.unparse(wizard)
refresh=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='refresh_all')
assert 'tv_sound_value' in ast.unparse(refresh)
assert "'name': 'tv_sound_value', 'zPosition': '6'" in p
assert "position='82,550'" in p
print('TV choice regression checks passed')

import ast, types, threading, tempfile
from pathlib import Path
from unittest.mock import Mock
root=Path(__file__).resolve().parents[1]
s=(root/'EmbyFlowE2_Detail_Hintergrund_20261004_0402.py').read_text()
tree=ast.parse(s)
# Use final definitions, as the plugin deliberately installs layers after base classes.
functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
def fn(name, env):
 node=functions[name]
 exec(compile(ast.Module(body=[node],type_ignores=[]),'test','exec'),env)
 return env[name]
for name in ('_embyflow_theme_schedule_v1','_embyflow_theme_begin_lookup_v1','_embyflow_theme_poll_lookup_v1'):
 assert fn(name,{})(object()) is None
# Cancelled background cannot access widgets, results or nav.
event=threading.Event();event.set()
screen=types.SimpleNamespace(_efbg_state={'cancel':event})
fn('_efbg_poll',{})(screen)
# Mode Off preserves the TV service and starts no worker.
fn('_efbg_start',{'_efbg_mode':lambda:'off'})(object())
# Trailer handoff cancels only UI application; ongoing resolution remains reusable.
process=Mock();timer=Mock()
screen=types.SimpleNamespace(_efbg_state={'cancel':threading.Event(),'lock':threading.RLock(),'process':process},_fallback_poll_timer=timer)
cancel=fn('_efbg_cancel',{})
cancel(screen,kill=False);assert screen._efbg_state['cancel'].is_set();process.kill.assert_not_called();timer.stop.assert_called_once()
cancel(screen);process.kill.assert_called_once()
# Cleanup removes only directories owned by this background job.
with tempfile.TemporaryDirectory() as d:
 own=Path(d)/'own';own.mkdir();keep=Path(d)/'keep';keep.mkdir()
 screen._efbg_state['directory']=str(own)
 import shutil
 fn('_efbg_cleanup',{'_efbg_cancel':cancel,'_eftr_shutil':shutil})(screen)
 assert not own.exists() and keep.exists()
# No metadata ID means no external resolver or title-based guessing for music.
response=types.SimpleNamespace(status_code=404)
network=Mock(return_value=response)
env={'embyflow_http_get':network,'AUTH_HEADER':'public', '_eftr_ensure_resolver':Mock()}
assert fn('_efbg_music',env)({'id':'42'},('https://example.invalid','token','user'),threading.Event())==''
env['_eftr_ensure_resolver'].assert_not_called()
assert "state['preview'] = dict(result)" in s
assert '_efbg_cancel(self, kill=False)' in s
print('OK: grid disabled, Off, cancellation, trailer handoff, scoped cleanup and missing music metadata tested.')

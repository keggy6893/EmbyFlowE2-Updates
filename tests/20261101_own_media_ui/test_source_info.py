import ast
import importlib.util
import os
from pathlib import Path
import queue
import tempfile
import threading
import time
import types
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('installer', ROOT / 'EmbyFlowE2_Quelleninfo_V1_20261031.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
original = (ROOT.parents[1] / 'EmbyFlowE2_2026102801.py').read_text(encoding='utf-8')
updated = installer.transform(original)


def skin(source):
    tree = ast.parse(source)
    scope = {'scale_skin': lambda text: text}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in (
                '_EMBYFLOW_V16_CARD_SKIN', '_EMBYFLOW_V16_MANAGER_ROWS_SKIN') for t in node.targets):
            exec(compile(ast.Module(body=[node], type_ignores=[]), '<constant>', 'exec'), scope)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'EmbyFlowLocalSourcesScreenV17')
    expr = next(n.value for n in cls.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'skin' for t in n.targets))
    return ET.fromstring(eval(compile(ast.Expression(expr), '<skin>', 'eval'), scope))


before, after = skin(original), skin(updated)
assert not any(e.attrib.get('name', '').startswith('mgr_') for e in after)
assert sum(e.attrib.get('name', '').startswith('source_info_') for e in after) == 8
# Everything outside the existing right-hand information panel is unchanged.
def outside(tree):
    return [ET.tostring(e) for e in tree if int(e.attrib.get('position', '0,0').split(',')[0]) < 1295]
assert outside(before) == outside(after)
for e in after:
    if e.attrib.get('name', '').startswith('source_info_'):
        x, y = map(int, e.attrib['position'].split(',')); w, h = map(int, e.attrib['size'].split(','))
        assert 1295 <= x and x + w <= 1865 and 260 <= y and y + h <= 735
        assert int(e.attrib['zPosition']) > 0
# No existing function or method changes, including the player and action handlers.
def bodies(source):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef)}
old_bodies, new_bodies = bodies(original), bodies(updated)
assert all(new_bodies[k] == v for k, v in old_bodies.items())
for source in (updated, original.replace('class EmbyFlowLocalSourcesScreenV17(', 'class ChangedSources(', 1)):
    try:
        installer.transform(source)
        raise AssertionError('Repeated/drifted source accepted')
    except ValueError:
        pass
print('PASS: complete syntax, XML, panel bounds, existing fonts/layout and functions, repeat/drift guards')


class Widget:
    def __init__(self, text=''):
        self.text = text
        self.hidden = False
    def setText(self, text):
        self.text = text
    def hide(self):
        self.hidden = True


class Timer:
    def __init__(self):
        self.callback = []
        self.stopped = False
    def start(self, *args):
        self.stopped = False
    def stop(self):
        self.stopped = True


class Screen(dict):
    def __init__(self):
        super().__init__()
        self.sources = []
        self.selected_index = 0
        self.closed_sources_v16 = False
    def refresh(self):
        self.original_refresh_called = True
    def cleanup(self):
        self.closed_sources_v16 = True
    def refresh_sources(self):
        self.original_status_called = True
    def _show_icon(self, *args):
        pass
    def _set_text_color(self, *args):
        pass


ns = dict(EmbyFlowLocalSourcesScreenV17=Screen, Label=Widget, Pixmap=Widget,
          eTimer=Timer, os=os, time=time, EMBYFLOW_LOCAL_VIDEO_EXTENSIONS={'.ts', '.mkv', '.mp4'},
          _embyflow_v16_source_type_label=lambda mode: mode,
          embyflow_local_human_size=lambda size: str(size))
exec(installer.RUNTIME, ns)

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    (root / 'film.ts').write_bytes(b'1')
    (root / 'poster.jpg').write_bytes(b'2')
    (root / '.hidden.ts').write_bytes(b'3')
    (root / 'Unterordner').mkdir()
    (root / 'Unterordner' / 'not-direct.ts').write_bytes(b'4')
    result = ns['_efsi_probe']({'path': str(root)}, threading.Event())
    assert result['online'] and result['videos'] == 1 and result['folders'] == 1
    assert result['free'] is not None
    result = ns['_efsi_probe']({'path': str(root / 'absent')}, threading.Event())
    assert not result['online']
print('PASS: direct-folder counts, hidden/nonvideo filtering, no recursive overcount, offline source')

# Controlled worker scheduler: result A may arrive after selecting B.
work = []
class DeferredThread:
    def __init__(self, target, **kwargs):
        self.target = target
    def start(self):
        work.append(self.target)
ns['_efsi_threading'] = types.SimpleNamespace(Thread=DeferredThread, Event=threading.Event)
ns['_efsi_probe'] = lambda source, cancelled: dict(online=True, checked=time.time(), connection='Test', free=None, videos=1 if source['id'] == 'A' else 2, folders=0, partial=False)
screen = Screen()
a = {'id': 'A', 'name': 'A', 'path': '/media/a', 'mode': 'movies'}
b = {'id': 'B', 'name': 'B', 'path': '/media/b', 'mode': 'series'}
screen.sources = [a, b]
screen.refresh()
assert len(work) == 1 and screen['source_info_name'].text == 'A'
screen.selected_index = 1
screen.refresh()
assert len(work) == 1 and screen['source_info_name'].text == 'B'
work.pop(0)()
ns['_efsi_poll'](screen)
assert screen['source_info_name'].text == 'B' and '1 Videodateien' not in screen['source_info_content'].text
assert len(work) == 1
work.pop(0)()
ns['_efsi_poll'](screen)
assert screen['source_info_name'].text == 'B' and '2 Videodateien' in screen['source_info_content'].text
screen.selected_index = 0
screen.refresh()
assert not work and '1 Videodateien' in screen['source_info_content'].text
screen.refresh_sources()
assert len(work) == 1 and screen.original_status_called
work.pop(0)()
ns['_efsi_poll'](screen)
screen.selected_index = 2
screen.refresh()
assert screen['source_info_name'].text == 'Alle Medien' and not work
screen.sources = []
screen.refresh()
assert screen['source_info_name'].text == 'Keine Quelle ausgewählt'
screen.cleanup()
assert screen._efsi_cancel.is_set() and screen._efsi_timer.stopped and screen.closed_sources_v16
print('PASS: selection follows cards, one worker, stale-result protection, cache, All Media, empty, cleanup')

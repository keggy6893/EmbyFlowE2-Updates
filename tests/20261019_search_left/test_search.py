import ast
from collections import deque
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

class Widget:
    def __init__(self, value=''):
        self.value = value; self.visible = True; self.instance = self
        self.position = None; self.size = None
    def setText(self, value): self.value = value
    def show(self): self.visible = True
    def hide(self): self.visible = False
    def move(self, value): self.position = value
    def resize(self, value): self.size = value
    def setPixmap(self, value): pass

class Screen(dict):
    def __init__(self, session):
        self.session = session; self.onClose = []; self.onLayoutFinish = []
    def close(self):
        for fn in self.onClose: fn()

class Timer:
    def __init__(self): self.callback = []; self.active = False
    def start(self, *args): self.active = True
    def stop(self): self.active = False

class SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.history = Path(self.tmp.name) / 'history.json'
        self.history.write_text(json.dumps([{'term': 'Term %d' % i} for i in range(8)]))
        self.opened = []; self.decoded = []; self.requests = []
        self.ns = dict(Screen=Screen, scale_skin=lambda x:x, Label=Widget, Pixmap=Widget,
            eTimer=Timer, ActionMap=lambda *x:x, os=os, json=json, time=time,
            sx=lambda v: round(v), sy=lambda v:round(v), ePoint=lambda *v:v, eSize=lambda *v:v,
            SEARCH_HISTORY_FILE=str(self.history), EmbyFlowDetailScreen='details',
            EMBYFLOW_POSTER_CACHE_MANAGER=SimpleNamespace(prioritize=lambda *a:None,enqueue=lambda *a,**k:None),
            _grid_cache_path=lambda item,*a:item['title'], _grid_cache_valid=lambda p:True,
            _grid_cache_item_id=lambda item:item['title'],
            embyflow_decode_image_to_widget=lambda *a,**kw:self.decoded.append((a,kw)))
        exec((HERE / 'runtime.py').read_text(), self.ns)
        self.cls = self.ns['EmbyFlowDisneySearchScreen']
        self.screen = self.cls(SimpleNamespace(open=lambda *a:self.opened.append(a)))
        self.screen._start()
        self.real_request = self.screen._request_search
        self.screen._request_search = lambda: self.requests.append(self.screen.query_text)

    def result_items(self, count=18):
        return [{'title': 'Title %02d' % i, 'meta': '2026', 'id': i} for i in range(count)]

    def test_all_alphabet_and_action_keys_reachable_and_grid_movement(self):
        s = self.screen
        seen = {0}; q = deque([0])
        while q:
            i = q.popleft()
            for direction in ('up','down','left','right'):
                s.key_index=i; s.focus_mode='keys'; getattr(s,direction)()
                if s.focus_mode=='keys' and s.key_index not in seen:
                    seen.add(s.key_index);q.append(s.key_index)
        self.assertEqual(seen,set(range(len(s.KEYS))))
        s.focus_mode='keys';s.key_index=0;s.down();self.assertEqual(s.key_index,6)
        s.right();self.assertEqual(s.key_index,7)
        s.up();self.assertEqual(s.key_index,1)

    def test_numeric_keyboard_positions_navigation_input_delete_and_return(self):
        s=self.screen;s.key_index=30;s.ok()
        self.assertTrue(s.number_keyboard)
        self.assertEqual(s._key_geo[10],(62,606,152,58))
        self.assertEqual(sum(s['k%d'%i].visible for i in range(33)),13)
        s.key_index=2;s.ok();s.key_index=11;s.ok();s.key_index=5;s.ok()
        self.assertEqual(s.query_text,'2 5')
        s.key_index=12;s.ok();self.assertEqual(s.query_text,'2 ')
        s.key_index=10;s.ok();self.assertFalse(s.number_keyboard)
        self.assertEqual(len(s._key_geo),33)
        self.assertEqual(s['k32'].value,'Löschen')
        self.assertTrue(s['k32'].visible)

    def test_all_eighteen_results_are_reachable_paged_and_open_exact_item(self):
        s=self.screen;s.results=self.result_items();s.query_text='Test';s.key_index=5;s.right()
        self.assertEqual(s.focus_mode,'results')
        for _ in range(17): s.right()
        self.assertEqual(s.result_index,17)
        self.assertEqual(s['t0'].value,'Title 16')
        self.assertEqual(s['t1'].value,'Title 17')
        self.assertEqual(s['t2'].value,'')
        self.assertIn('17–18',s['status'].value)
        s.ok();self.assertEqual(self.opened[-1][1]['id'],17)
        self.assertEqual(json.loads(self.history.read_text())[0]['term'],'Test')
        for _ in range(18):s.left()
        self.assertEqual(s.focus_mode,'keys')

    def test_history_scroll_load_and_delete_without_losing_other_entries(self):
        s=self.screen;s.key_index=32;s.down()
        self.assertEqual(s.focus_mode,'history')
        for _ in range(7):s.down()
        self.assertIn('› Term 7',s['history'].value)
        self.assertNotIn('Term 0',s['history'].value)
        s.backspace()
        self.assertEqual(len(json.loads(self.history.read_text())),7)
        self.assertNotIn('Term 7',self.history.read_text())
        s.ok();self.assertEqual(s.query_text,'Term 0')
        self.assertEqual(s.focus_mode,'keys')
        self.assertEqual(self.requests[-1],'Term 0')

    def test_new_query_invalidates_visible_old_result_and_stale_response(self):
        s=self.screen;s.results=self.result_items();s.focus_mode='results';s.query_text='A'
        self.real_request()
        self.assertEqual(s.results,[]);self.assertEqual(s.focus_mode,'keys')
        self.assertEqual(s['t0'].value,'')
        s.search_ready=(s.search_generation-1,'A',self.result_items());s._poll()
        self.assertEqual(s.results,[])
        s.closed_search=True;s.search_ready=(s.search_generation,'A',self.result_items());s._poll()
        self.assertEqual(s.results,[])

    def test_filter_reuses_server_types_and_timer_stops_on_close(self):
        s=self.screen
        s.cycle_filter();self.assertEqual(s.FILTERS[s.filter_index],('Filme','Movie'))
        s.cycle_filter();self.assertEqual(s.FILTERS[s.filter_index],('Serien','Series'))
        s.cycle_filter();self.assertEqual(s.filter_index,0)
        s.close();self.assertTrue(s.closed_search);self.assertFalse(s.poll_timer.active)

    def test_hd_runtime_focus_matches_skin_scale(self):
        self.ns['sx']=lambda v:round(v*2/3);self.ns['sy']=lambda v:round(v*2/3)
        self.screen.key_index=7;self.screen._update_focus()
        x,y,w,h=self.screen._key_geo[7]
        self.assertEqual(self.screen['focus_top'].position,(round((x-3)*2/3),round((y-3)*2/3)))
        self.assertEqual(self.screen['focus_top'].size,(round((w+6)*2/3),2))

    def test_skin_is_navy_with_large_left_grid_and_nonoverlapping_posters(self):
        root=ET.fromstring(self.cls.skin)
        self.assertEqual(root.attrib['backgroundColor'],'#0C1827')
        widgets={w.attrib['name']:w for w in root.findall('widget')}
        for i in range(33):
            w=widgets['k%d'%i];x,y=map(int,w.attrib['position'].split(','));ww,hh=map(int,w.attrib['size'].split(','))
            self.assertLess(x+ww,558);self.assertLess(y+hh,682)
            self.assertGreaterEqual(int(w.attrib['font'].split(';')[1]),28)
        for i in range(4):
            x,y,w,h=self.cls._poster_geo[i];self.assertGreater(x,588);self.assertLess(x+w,1878)
            self.assertEqual((w,h),(264,376))

class InstallerTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('search_builder',HERE/'build.py')
        self.builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.builder)
        self.ns={'__name__':'not_main'};exec(self.builder.INSTALLER,self.ns)

    def test_only_search_class_changes_and_repeated_install_is_identical(self):
        source=(ROOT/'EmbyFlowE2_2026101805.py').read_text()
        original_tree=ast.parse(source);updated=self.ns['patched'](source);updated_tree=ast.parse(updated)
        def outside(tree):return [ast.dump(n) for n in tree.body if not isinstance(n,ast.ClassDef) or n.name!='EmbyFlowDisneySearchScreen']
        self.assertEqual(outside(original_tree),outside(updated_tree))
        self.assertEqual(self.ns['patched'](updated),updated)
        self.assertEqual((ROOT/self.builder.ARTIFACT).read_text(),updated)

    def test_actual_install_backup_preserves_local_addons_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'plugin.py';source=(ROOT/'EmbyFlowE2_2026101805.py').read_text()+'\nLOCAL_TEST_SENTINEL = 42\n'
            p.write_text(source);p.chmod(0o640)
            self.assertTrue(self.ns['install'](p))
            self.assertEqual(next(Path(directory).glob('*.vor-suche-links-*')).read_text(),source)
            self.assertIn('LOCAL_TEST_SENTINEL = 42',p.read_text())
            self.assertEqual(p.stat().st_mode & 0o777,0o640)
            self.assertFalse(self.ns['install'](p))

    def test_missing_or_ambiguous_class_rejected(self):
        for source in ('x=1','class EmbyFlowDisneySearchScreen: pass','class EmbyFlowDisneySearchScreen: pass\nclass EmbyFlowDisneySearchScreen: pass'):
            with self.assertRaises(RuntimeError):self.ns['patched'](source)

if __name__=='__main__':unittest.main()

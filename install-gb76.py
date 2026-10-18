"""Repair existing layout helper functions without changing other local features."""
import ast
from pathlib import Path
import os
import shutil
import tempfile
import time


def patch(source, runtime):
    compile(source, 'existing_plugin.py', 'exec')
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if '_efl_plan' not in functions:
        if '_efl_detail_layout' in functions:
            raise RuntimeError('Unvollstaendiger Layout-Test. Nichts geaendert.')
        for required in ('class EmbyFlowDetailScreen', 'EMBYFLOW_CINEMA_POLISH_V2_20261013', 'EMBYFLOW_DETAIL_TEXT_SPACE_V4_20261013'):
            if required not in source:
                raise RuntimeError('Pluginversion abweichend. Nichts geaendert.')
        result = source + '\n\n' + runtime
    else:
        wanted = ('_efl_plan', '_efl_detail_layout')
        snippets = {}
        for node in ast.parse(runtime).body:
            if isinstance(node, ast.FunctionDef) and node.name in wanted:
                snippets[node.name] = ast.get_source_segment(runtime, node) + '\n'
        if not all(name in functions for name in wanted):
            raise RuntimeError('Layoutfunktion fehlt. Nichts geaendert.')
        lines = source.splitlines(keepends=True)
        for name in sorted(wanted, key=lambda name: functions[name].lineno, reverse=True):
            node = functions[name]
            lines[node.lineno-1:node.end_lineno] = [snippets[name]]
        result = ''.join(lines)
    compile(result, 'plugin.py', 'exec')
    return result


def install(path, runtime):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Unerwarteter Pluginpfad. Nichts geaendert.')
    source = path.read_text()
    result = patch(source, runtime)
    if source == result:
        print('Layout-Test V2 bereits vorhanden.', flush=True)
        return False
    backup = str(path) + '.vor-layout-v2-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    if os.path.exists(backup):
        raise RuntimeError('Sicherung existiert bereits. Nichts geaendert.')
    shutil.copy2(path, backup)
    fd, name = tempfile.mkstemp(prefix='plugin.py.layout-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(result)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copystat(path, name)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print('Layout-Test V2 installiert. Sicherung:', backup, flush=True)
    return True

RUNTIME = '# EMBYFLOW_ATV76_DETAIL_LAYOUT_LOCAL_V1\n# Reapply final embedded geometry after Enigma2 has created its widgets.\nimport json as _efl_json\nimport os as _efl_os\nimport xml.etree.ElementTree as _efl_xml\n\n\ndef _efl_image_76():\n    try:\n        with open(\'/etc/image-version\') as handle:\n            data = dict(line.strip().split(\'=\',1) for line in handle if \'=\' in line)\n        version = data.get(\'version\',\'\').strip(\'"\\x27\')\n        return data.get(\'distro\',\'\').strip(\'"\\x27\').lower() == \'openatv\' and (version == \'7.6\' or version.startswith(\'7.6.\'))\n    except (OSError,ValueError):\n        return False\n\n\ndef _efl_pair(value):\n    pair = tuple(int(part) for part in value.split(\',\'))\n    if len(pair) != 2:\n        raise ValueError(\'Invalid geometry\')\n    return pair\n\n\ndef _efl_geometry(node):\n    return _efl_pair(node.get(\'position\',\'0,0\')) + _efl_pair(node.get(\'size\',\'0,0\'))\n\n\ndef _efl_plan(skin, width, height):\n    root = _efl_xml.fromstring(skin)\n    widgets = {node.get(\'name\'):node for node in root.iter(\'widget\') if node.get(\'name\')}\n    plan = {}\n    for name,node in widgets.items():\n        if not (name.startswith(\'detail_overview_line_\') or name == \'detail_overview\'):\n            continue\n        x,y,w,h = _efl_geometry(node)\n        if w <= 1 or h <= 1:\n            continue\n        # Respect the final heading and retain the existing text/page content.\n        heading_bottom = max((p[1]+p[3] for p in (\n            _efl_geometry(label) for label in root.iter(\'eLabel\')\n            if label.get(\'text\') and label.get(\'position\') and label.get(\'size\'))\n            if abs(p[0]-x) <= max(2,int(width/1920*8))\n            and height*.39 <= p[1] <= height*.50), default=0)\n        baseline = _efl_geometry(widgets.get(\'detail_overview_line_0\',node))[1] if name.startswith(\'detail_overview_line_\') else y\n        y += max(0,heading_bottom+max(3,round(height/1080*6))-baseline)\n        if x >= 0 and y >= 0 and w > 1 and h > 1 and x+w <= width+2 and y+h <= height+2:\n            plan[name] = (x,y,w,h,\'left\',\'top\',node.get(\'font\'))\n    for label,bg in ((\'detail_play_btn\',\'cinema_button_bg_0\'),(\'detail_back_btn\',\'cinema_button_bg_1\'),(\'trailer_button\',\'cinema_button_bg_2\'),(\'movie_download_button\',\'movie_download_bg\')):\n        if label not in widgets or bg not in widgets:\n            continue\n        x,y,w,h = _efl_geometry(widgets[bg])\n        if x < 0 or y < 0 or w <= 2 or h <= 2 or x+w > width+2 or y+h > height+2:\n            continue\n        margin = max(1,round(width/1920*4))\n        plan[label] = (x+margin,y+margin,w-2*margin,h-2*margin,\'center\',\'center\',widgets[label].get(\'font\'))\n    return plan\n\n\ndef _efl_detail_layout(self):\n    if not getattr(self,\'_efl_active\',False) or getattr(self,\'instance\',None) is None:\n        return\n    from enigma import ePoint,eSize,eRect\n    from skin import parseFont\n    try:\n        size = self.instance.size()\n        plan = _efl_plan(self.skin,size.width(),size.height())\n        report = {\'screen\':[size.width(),size.height()],\'widgets\':{}}\n        if \'detail_overview_line_0\' in plan and \'detail_overview\' in self:\n            # The legacy multiline field is superseded by the six row widgets.\n            self[\'detail_overview\'].hide()\n        for name,(x,y,w,h,horizontal,vertical,font) in plan.items():\n            if name not in self:\n                continue\n            instance = getattr(self[name],\'instance\',None)\n            if instance is None:\n                continue\n            position,bounds = instance.position(),instance.size()\n            before = [position.x(),position.y(),bounds.width(),bounds.height()]\n            instance.move(ePoint(x,y));instance.resize(eSize(w,h))\n            if hasattr(instance,\'setPadding\'):\n                instance.setPadding(eRect(0,0,0,0))\n            if font:\n                instance.setFont(parseFont(font))\n            # Same numeric values used by openATV 7.6 skin alignment parsers.\n            instance.setHAlign(1 if horizontal==\'center\' else 0)\n            instance.setVAlign(1 if vertical==\'center\' else 0)\n            position,bounds = instance.position(),instance.size()\n            report[\'widgets\'][name] = {\'before\':before,\'wanted\':[x,y,w,h],\n                \'after\':[position.x(),position.y(),bounds.width(),bounds.height()]}\n        # One small, atomic diagnostic file. Never includes title or server data.\n        if report[\'widgets\'] and not getattr(self,\'_efl_reported\',False):\n            import tempfile\n            fd,path = tempfile.mkstemp(prefix=\'embyflow-layout-\',dir=\'/home/root\')\n            try:\n                with _efl_os.fdopen(fd,\'w\') as handle:\n                    _efl_json.dump(report,handle)\n                _efl_os.replace(path,\'/home/root/embyflow-layout.json\')\n                self._efl_reported = True\n            finally:\n                if _efl_os.path.exists(path):_efl_os.unlink(path)\n    except Exception:\n        # A diagnostic or optional API failure must not break the detail page.\n        pass\n\n\n_EFL_DETAIL_INIT = EmbyFlowDetailScreen.__init__\n_EFL_DETAIL_FOCUS = EmbyFlowDetailScreen.update_detail_focus\n\n\ndef _efl_detail_init(self,*args,**kwargs):\n    _EFL_DETAIL_INIT(self,*args,**kwargs)\n    self._efl_active = _efl_image_76()\n    if self._efl_active:\n        self.onLayoutFinish.append(self._efl_detail_layout)\n\n\ndef _efl_detail_focus(self,*args,**kwargs):\n    result = _EFL_DETAIL_FOCUS(self,*args,**kwargs)\n    if getattr(self,\'_efl_active\',False):\n        self._efl_detail_layout()\n    return result\n\n\nEmbyFlowDetailScreen._efl_detail_layout = _efl_detail_layout\nEmbyFlowDetailScreen.__init__ = _efl_detail_init\nEmbyFlowDetailScreen.update_detail_focus = _efl_detail_focus\n'

if __name__ == '__main__':
    image = dict(line.strip().split('=', 1) for line in Path('/etc/image-version').read_text().splitlines() if '=' in line)
    if image.get('distro') != 'openatv' or not image.get('version', '').startswith('7.6'):
        raise SystemExit('Dieser Layout-Test ist fuer openATV 7.6. Nichts geaendert.')
    changed = install('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py', RUNTIME)
    if changed:
        print('GUI startet neu.', flush=True)
        os.system('init 4')
        time.sleep(3)
        os.system('init 3')

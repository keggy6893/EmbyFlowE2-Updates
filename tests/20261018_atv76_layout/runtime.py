# EMBYFLOW_ATV76_DETAIL_LAYOUT_LOCAL_V1
# Reapply final embedded geometry after Enigma2 has created its widgets.
import json as _efl_json
import os as _efl_os
import xml.etree.ElementTree as _efl_xml


def _efl_image_76():
    try:
        with open('/etc/image-version') as handle:
            data = dict(line.strip().split('=',1) for line in handle if '=' in line)
        version = data.get('version','').strip('"\x27')
        return data.get('distro','').strip('"\x27').lower() == 'openatv' and (version == '7.6' or version.startswith('7.6.'))
    except (OSError,ValueError):
        return False


def _efl_pair(value):
    pair = tuple(int(part) for part in value.split(','))
    if len(pair) != 2:
        raise ValueError('Invalid geometry')
    return pair


def _efl_geometry(node):
    return _efl_pair(node.get('position','0,0')) + _efl_pair(node.get('size','0,0'))


def _efl_plan(skin, width, height):
    root = _efl_xml.fromstring(skin)
    widgets = {node.get('name'):node for node in root.iter('widget') if node.get('name')}
    plan = {}
    for name,node in widgets.items():
        if not (name.startswith('detail_overview_line_') or name == 'detail_overview'):
            continue
        x,y,w,h = _efl_geometry(node)
        if w <= 1 or h <= 1:
            continue
        # Respect the final heading and retain the existing text/page content.
        heading_bottom = max((p[1]+p[3] for p in (
            _efl_geometry(label) for label in root.iter('eLabel')
            if label.get('text') and label.get('position') and label.get('size'))
            if abs(p[0]-x) <= max(2,int(width/1920*8))
            and height*.39 <= p[1] <= height*.50), default=0)
        baseline = _efl_geometry(widgets.get('detail_overview_line_0',node))[1] if name.startswith('detail_overview_line_') else y
        y += max(0,heading_bottom+max(3,round(height/1080*6))-baseline)
        if x >= 0 and y >= 0 and w > 1 and h > 1 and x+w <= width+2 and y+h <= height+2:
            plan[name] = (x,y,w,h,'left','top',node.get('font'))
    for label,bg in (('detail_play_btn','cinema_button_bg_0'),('detail_back_btn','cinema_button_bg_1'),('trailer_button','cinema_button_bg_2'),('movie_download_button','movie_download_bg')):
        if label not in widgets or bg not in widgets:
            continue
        x,y,w,h = _efl_geometry(widgets[bg])
        if x < 0 or y < 0 or w <= 2 or h <= 2 or x+w > width+2 or y+h > height+2:
            continue
        margin = max(1,round(width/1920*4))
        plan[label] = (x+margin,y+margin,w-2*margin,h-2*margin,'center','center',widgets[label].get('font'))
    return plan


def _efl_detail_layout(self):
    if not getattr(self,'_efl_active',False) or getattr(self,'instance',None) is None:
        return
    from enigma import ePoint,eSize,eRect
    from skin import parseFont
    try:
        size = self.instance.size()
        plan = _efl_plan(self.skin,size.width(),size.height())
        report = {'screen':[size.width(),size.height()],'widgets':{}}
        if 'detail_overview_line_0' in plan and 'detail_overview' in self:
            # The legacy multiline field is superseded by the six row widgets.
            self['detail_overview'].hide()
        for name,(x,y,w,h,horizontal,vertical,font) in plan.items():
            if name not in self:
                continue
            instance = getattr(self[name],'instance',None)
            if instance is None:
                continue
            position,bounds = instance.position(),instance.size()
            before = [position.x(),position.y(),bounds.width(),bounds.height()]
            instance.move(ePoint(x,y));instance.resize(eSize(w,h))
            if hasattr(instance,'setPadding'):
                instance.setPadding(eRect(0,0,0,0))
            if font:
                instance.setFont(parseFont(font))
            # Same numeric values used by openATV 7.6 skin alignment parsers.
            instance.setHAlign(1 if horizontal=='center' else 0)
            instance.setVAlign(1 if vertical=='center' else 0)
            position,bounds = instance.position(),instance.size()
            report['widgets'][name] = {'before':before,'wanted':[x,y,w,h],
                'after':[position.x(),position.y(),bounds.width(),bounds.height()]}
        # One small, atomic diagnostic file. Never includes title or server data.
        if report['widgets'] and not getattr(self,'_efl_reported',False):
            import tempfile
            fd,path = tempfile.mkstemp(prefix='embyflow-layout-',dir='/home/root')
            try:
                with _efl_os.fdopen(fd,'w') as handle:
                    _efl_json.dump(report,handle)
                _efl_os.replace(path,'/home/root/embyflow-layout.json')
                self._efl_reported = True
            finally:
                if _efl_os.path.exists(path):_efl_os.unlink(path)
    except Exception:
        # A diagnostic or optional API failure must not break the detail page.
        pass


_EFL_DETAIL_INIT = EmbyFlowDetailScreen.__init__
_EFL_DETAIL_FOCUS = EmbyFlowDetailScreen.update_detail_focus


def _efl_detail_init(self,*args,**kwargs):
    _EFL_DETAIL_INIT(self,*args,**kwargs)
    self._efl_active = _efl_image_76()
    if self._efl_active:
        self.onLayoutFinish.append(self._efl_detail_layout)


def _efl_detail_focus(self,*args,**kwargs):
    result = _EFL_DETAIL_FOCUS(self,*args,**kwargs)
    if getattr(self,'_efl_active',False):
        self._efl_detail_layout()
    return result


EmbyFlowDetailScreen._efl_detail_layout = _efl_detail_layout
EmbyFlowDetailScreen.__init__ = _efl_detail_init
EmbyFlowDetailScreen.update_detail_focus = _efl_detail_focus

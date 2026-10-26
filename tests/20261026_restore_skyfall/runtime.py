# EMBYFLOW_LOCAL_SKYFALL_DETAIL_V1_BEGIN
import json as _els_json
import os as _els_os
import threading as _els_thread
_ELS_PATH='/media/usb/Filme/James Bond 007 - Skyfall (2012).ts'
_ELS_CACHE='/etc/enigma2/embyflow_local_skyfall.json'
_ELS_ART='/media/usb/Filme/.embyflow-skyfall'
_ELS_OPEN_BEFORE=EmbyFlowLocalLibraryScreenV3.open_selected
_ELS_NAV_BEFORE=EmbyFlowE2Screen._direct_nav_build_entries_ref12
_ELS_ACTIVATE_BEFORE=EmbyFlowE2Screen._direct_nav_activate_ref12

def _els_metadata(candidates):
    matches=[x for x in candidates if isinstance(x,dict) and x.get('Type')=='Movie'
             and str(x.get('ProductionYear') or '')=='2012' and 'skyfall' in str(x.get('Name') or '').casefold()]
    return matches[0] if matches else None

def _els_read_cache():
    try:
        with open(_ELS_CACHE,encoding='utf-8') as handle:data=_els_json.load(handle)
        return data if isinstance(data,dict) and data.get('path')==_ELS_PATH else {}
    except Exception:return {}

def _els_save_json(path,data):
    import tempfile
    h,tmp=tempfile.mkstemp(prefix='.skyfall-',dir=_els_os.path.dirname(path))
    try:
        with _els_os.fdopen(h,'w',encoding='utf-8') as out:_els_json.dump(data,out,ensure_ascii=True);out.flush();_els_os.fsync(out.fileno())
        _els_os.replace(tmp,path)
    finally:
        if _els_os.path.exists(tmp):_els_os.unlink(tmp)

class EmbyFlowLocalSkyfallDetail(Screen):
    skin=scale_skin('''<screen name="EmbyFlowLocalSkyfallDetail" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#0C1827">
    <eLabel text="EMBYFLOW E2 · EMBY LOCAL" position="90,42" size="1200,42" font="Regular;26" foregroundColor="#38C7F4" transparent="1" />
    <widget name="title" position="90,110" size="1310,120" font="Bold;56" foregroundColor="#FFFFFF" transparent="1" />
    <widget name="meta" position="90,255" size="1280,52" font="Regular;29" foregroundColor="#DCE5EE" transparent="1" />
    <widget name="genres" position="90,343" size="1270,45" font="Regular;27" foregroundColor="#D7BE62" transparent="1" />
    <eLabel text="Inhaltsangabe" position="90,425" size="1260,50" font="Bold;32" foregroundColor="#FFFFFF" transparent="1" />
    <widget name="overview" position="90,490" size="1260,245" font="Regular;30" foregroundColor="#DCE5EE" transparent="1" />
    <widget name="people" position="90,772" size="1260,110" font="Regular;25" foregroundColor="#A5B5C3" transparent="1" />
    <widget name="poster" position="1495,95" size="335,502" alphatest="on" />
    <widget name="poster_hint" position="1495,245" size="335,130" font="Regular;32" foregroundColor="#A5B5C3" halign="center" transparent="1" />
    <widget name="play" position="1490,655" size="345,80" font="Bold;32" foregroundColor="#FFFFFF" backgroundColor="#173A5E" halign="center" valign="center" />
    <widget name="back" position="1490,780" size="345,80" font="Regular;30" foregroundColor="#DCE5EE" backgroundColor="#102432" halign="center" valign="center" />
    <widget name="focus" position="1485,650" size="355,90" transparent="1" widgetBorderWidth="3" widgetBorderColor="#38C7F4" zPosition="5" />
    <widget name="status" position="90,935" size="1720,40" font="Regular;23" foregroundColor="#A5B5C3" transparent="1" />
    <eLabel text="ROT Zurück     GRÜN Abspielen     ↑↓ Auswahl     ←→ Inhaltsangabe blättern" position="90,1010" size="1720,40" font="Regular;24" foregroundColor="#DCE5EE" transparent="1" />
    </screen>''')
    def __init__(self,session,entry=None):
        Screen.__init__(self,session)
        self.root_path=_els_os.path.dirname(_ELS_PATH);self.title_text='James Bond 007 - Skyfall (2012)'
        self.entry=dict(entry or {});self.data={'overview':'Als eine geheime Liste mit den Identitaeten verdeckter Agenten gestohlen wird, geraet M unter Druck. James Bond verfolgt die Spur eines Gegners, der mit ihrer Vergangenheit verbunden ist. Seine Loyalitaet wird auf die Probe gestellt, waehrend der MI6 selbst zum Angriffsziel wird.','genres':['Action','Abenteuer','Thriller'],'directors':['Sam Mendes'],'actors':['Daniel Craig','Judi Dench','Javier Bardem','Ralph Fiennes','Naomie Harris']};self.data.update(_els_read_cache());self.closed_local=False;self.ready_local=None;self.focus_local=0;self.page_local=0
        self.local_status='Originaldatei auf USB · Wiedergabe lokal'
        for name in ('title','meta','genres','overview','people','poster_hint','play','back','status'):self[name]=Label('')
        self['poster']=Pixmap();self['focus']=Label('');self['play'].setText('▶ Abspielen');self['back'].setText('← Zurück')
        self['actions']=ActionMap(['OkCancelActions','ColorActions','DirectionActions'],{'ok':self.accept_local,'green':self.play_local,'red':self.close,'cancel':self.close,'up':self.toggle_local,'down':self.toggle_local,'left':lambda:self.page_description(-1),'right':lambda:self.page_description(1)},-1)
        self.timer_local=eTimer();self.timer_local.callback.append(self.poll_local)
        self.onLayoutFinish.append(self.start_local);self.onClose.append(self.close_local)
    def safe_within_root(self,path):return _els_os.path.realpath(path)==_els_os.path.realpath(_ELS_PATH)
    def start_local(self):
        self.render_local();self.timer_local.start(200,False)
        try:_els_thread.Thread(target=self.load_local,name='EmbyFlowLocalSkyfall',daemon=True).start()
        except Exception:self.local_status='Lokale Datei bereit; Filminformationen konnten nicht geladen werden.';self.render_local()
    def close_local(self):self.closed_local=True;self.timer_local.stop()
    def load_local(self):
        data=dict(self.data);data['path']=_ELS_PATH
        try:
            probe=_embyflow_v21b_probe_local_file(_ELS_PATH) or {}
            ticks=int(probe.get('runtime_ticks') or 0)
            if ticks>0:data['runtime_minutes']=max(1,ticks//600000000)
        except Exception:pass
        # Offline detail: use existing cached/local artwork and metadata only.
        try:_els_save_json(_ELS_CACHE,data)
        except Exception:pass
        if not self.closed_local:self.ready_local=data
    def poll_local(self):
        if self.closed_local:return
        if self.ready_local is not None:
            self.data=self.ready_local;self.ready_local=None;self.render_local()
    def render_local(self):
        self['title'].setText('James Bond 007 – Skyfall')
        meta=['2012','TS','USB lokal']
        if self.data.get('runtime_minutes'):meta.insert(1,str(self.data['runtime_minutes'])+' Min.')
        self['meta'].setText(' · '.join(meta));self['genres'].setText(', '.join(self.data.get('genres') or []))
        import textwrap
        overview=self.data.get('overview') or 'Skyfall liegt als lokale Originaldatei auf der USB-Festplatte. Die Wiedergabe benoetigt keinen Emby-Stream. Weitere Filminformationen erscheinen, wenn sie lokal gespeichert oder vom verbundenen Emby-Server abrufbar sind.'
        lines=[]
        for paragraph in str(overview).splitlines():lines.extend(textwrap.wrap(paragraph,85) or [''])
        pages=['\n'.join(lines[i:i+6]) for i in range(0,len(lines),6)] or ['']
        self.page_local=max(0,min(self.page_local,len(pages)-1));self['overview'].setText(pages[self.page_local])
        people=[]
        if self.data.get('directors'):people.append('Regie: '+', '.join(self.data['directors']))
        if self.data.get('actors'):people.append('Darsteller: '+', '.join(self.data['actors']))
        self['people'].setText('\n'.join(people));self['status'].setText(self.local_status+(' · Inhaltsangabe %d/%d'%(self.page_local+1,len(pages)) if len(pages)>1 else ''))
        poster=self.data.get('poster') or self.entry.get('poster') or ''
        if not poster:
            stem=_els_os.path.splitext(_ELS_PATH)[0]
            poster=next((p for p in (stem+'.jpg',stem+'.png',self.root_path+'/Skyfall.jpg') if _els_os.path.isfile(p)),'')
        if poster and _els_os.path.isfile(poster):
            self['poster_hint'].hide()
            try:embyflow_decode_image_to_widget(self,'poster',poster,335,502,token='local-skyfall',is_current=lambda:not self.closed_local)
            except Exception:self['poster_hint'].setText('Skyfall\n2012');self['poster_hint'].show()
        else:self['poster_hint'].setText('Skyfall\n2012');self['poster_hint'].show()
        self.update_local_focus()
    def page_description(self,delta):self.page_local=max(0,self.page_local+delta);self.render_local()
    def update_local_focus(self):
        try:self['focus'].instance.move(ePoint(sx(1485),sy(650 if self.focus_local==0 else 775)))
        except Exception:pass
    def toggle_local(self):self.focus_local=1-self.focus_local;self.update_local_focus()
    def accept_local(self):
        if self.focus_local:self.close()
        else:self.play_local()
    def play_local(self):
        if not _els_os.path.isfile(_ELS_PATH):self.local_status='Originaldatei fehlt. USB-Festplatte pruefen.';self.render_local();return
        return EmbyFlowLocalMediaScreen.play_file(self,_ELS_PATH)

def _els_open(self):
    if not getattr(self,'scan_loading',False):
        entry=self.selected_entry() or {};path=entry.get('path') or ''
        if path and _els_os.path.realpath(path)==_els_os.path.realpath(_ELS_PATH):
            return self.session.open(EmbyFlowLocalSkyfallDetail,entry)
    return _ELS_OPEN_BEFORE(self)

def _els_nav(self):
    entries=list(_ELS_NAV_BEFORE(self))
    if not any(str(e[0]).strip().casefold()=='emby local' or e[1].get('_direct_action_ref12')=='local_usb' for e in entries):
        index=next((i for i,e in enumerate(entries) if e[1].get('_direct_action_ref12')=='settings'),len(entries))
        entries.insert(index,('Emby Local',{'_direct_action_ref12':'local_usb'}))
    return entries

def _els_activate(self):
    rows=self.direct_nav_entries_ref12;index=self.direct_nav_cursor_ref12
    if 0<=index<len(rows) and rows[index][1].get('_direct_action_ref12')=='local_usb':return self.session.open(EmbyFlowLocalSkyfallDetail, {'path': _ELS_PATH})
    return _ELS_ACTIVATE_BEFORE(self)

EmbyFlowLocalLibraryScreenV3.open_selected=_els_open
EmbyFlowE2Screen._direct_nav_build_entries_ref12=_els_nav
EmbyFlowE2Screen._direct_nav_activate_ref12=_els_activate
# EMBYFLOW_LOCAL_SKYFALL_ASYNC_NAV_V1_BEGIN
_ELS_ASYNC_NAV_BEFORE=_embyflow_nav_groups_v30_transform
def _els_async_nav(entries):
    rows=list(_ELS_ASYNC_NAV_BEFORE(entries) or [])
    if not any(str(row[0]).strip().casefold()=='emby local' or row[1].get('_direct_action_ref12')=='local_usb' for row in rows):
        index=next((i for i,row in enumerate(rows) if row[1].get('_direct_action_ref12')=='settings'),len(rows))
        rows.insert(index,('Emby Local',{'_direct_action_ref12':'local_usb'}))
    return rows
_embyflow_nav_groups_v30_transform=_els_async_nav
# EMBYFLOW_LOCAL_SKYFALL_ASYNC_NAV_V1_END

# EMBYFLOW_LOCAL_SKYFALL_DETAIL_V1_END

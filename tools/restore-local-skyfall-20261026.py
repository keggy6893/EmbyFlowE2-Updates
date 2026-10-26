"""Restore only the user's local original Skyfall entry after a full plugin update."""
import ast,os,stat,fcntl,time,subprocess,sys
from pathlib import Path
BEGIN='# EMBYFLOW_LOCAL_SKYFALL_DETAIL_V1_BEGIN'
END='# EMBYFLOW_LOCAL_SKYFALL_DETAIL_V1_END'
RUNTIME='# EMBYFLOW_LOCAL_SKYFALL_DETAIL_V1_BEGIN\nimport json as _els_json\nimport os as _els_os\nimport threading as _els_thread\n_ELS_PATH=\'/media/usb/Filme/James Bond 007 - Skyfall (2012).ts\'\n_ELS_CACHE=\'/etc/enigma2/embyflow_local_skyfall.json\'\n_ELS_ART=\'/media/usb/Filme/.embyflow-skyfall\'\n_ELS_OPEN_BEFORE=EmbyFlowLocalLibraryScreenV3.open_selected\n_ELS_NAV_BEFORE=EmbyFlowE2Screen._direct_nav_build_entries_ref12\n_ELS_ACTIVATE_BEFORE=EmbyFlowE2Screen._direct_nav_activate_ref12\n\ndef _els_metadata(candidates):\n    matches=[x for x in candidates if isinstance(x,dict) and x.get(\'Type\')==\'Movie\'\n             and str(x.get(\'ProductionYear\') or \'\')==\'2012\' and \'skyfall\' in str(x.get(\'Name\') or \'\').casefold()]\n    return matches[0] if matches else None\n\ndef _els_read_cache():\n    try:\n        with open(_ELS_CACHE,encoding=\'utf-8\') as handle:data=_els_json.load(handle)\n        return data if isinstance(data,dict) and data.get(\'path\')==_ELS_PATH else {}\n    except Exception:return {}\n\ndef _els_save_json(path,data):\n    import tempfile\n    h,tmp=tempfile.mkstemp(prefix=\'.skyfall-\',dir=_els_os.path.dirname(path))\n    try:\n        with _els_os.fdopen(h,\'w\',encoding=\'utf-8\') as out:_els_json.dump(data,out,ensure_ascii=True);out.flush();_els_os.fsync(out.fileno())\n        _els_os.replace(tmp,path)\n    finally:\n        if _els_os.path.exists(tmp):_els_os.unlink(tmp)\n\nclass EmbyFlowLocalSkyfallDetail(Screen):\n    skin=scale_skin(\'\'\'<screen name="EmbyFlowLocalSkyfallDetail" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#0C1827">\n    <eLabel text="EMBYFLOW E2 · EMBY LOCAL" position="90,42" size="1200,42" font="Regular;26" foregroundColor="#38C7F4" transparent="1" />\n    <widget name="title" position="90,110" size="1310,120" font="Bold;56" foregroundColor="#FFFFFF" transparent="1" />\n    <widget name="meta" position="90,255" size="1280,52" font="Regular;29" foregroundColor="#DCE5EE" transparent="1" />\n    <widget name="genres" position="90,343" size="1270,45" font="Regular;27" foregroundColor="#D7BE62" transparent="1" />\n    <eLabel text="Inhaltsangabe" position="90,425" size="1260,50" font="Bold;32" foregroundColor="#FFFFFF" transparent="1" />\n    <widget name="overview" position="90,490" size="1260,245" font="Regular;30" foregroundColor="#DCE5EE" transparent="1" />\n    <widget name="people" position="90,772" size="1260,110" font="Regular;25" foregroundColor="#A5B5C3" transparent="1" />\n    <widget name="poster" position="1495,95" size="335,502" alphatest="on" />\n    <widget name="poster_hint" position="1495,245" size="335,130" font="Regular;32" foregroundColor="#A5B5C3" halign="center" transparent="1" />\n    <widget name="play" position="1490,655" size="345,80" font="Bold;32" foregroundColor="#FFFFFF" backgroundColor="#173A5E" halign="center" valign="center" />\n    <widget name="back" position="1490,780" size="345,80" font="Regular;30" foregroundColor="#DCE5EE" backgroundColor="#102432" halign="center" valign="center" />\n    <widget name="focus" position="1485,650" size="355,90" transparent="1" widgetBorderWidth="3" widgetBorderColor="#38C7F4" zPosition="5" />\n    <widget name="status" position="90,935" size="1720,40" font="Regular;23" foregroundColor="#A5B5C3" transparent="1" />\n    <eLabel text="ROT Zurück     GRÜN Abspielen     ↑↓ Auswahl     ←→ Inhaltsangabe blättern" position="90,1010" size="1720,40" font="Regular;24" foregroundColor="#DCE5EE" transparent="1" />\n    </screen>\'\'\')\n    def __init__(self,session,entry=None):\n        Screen.__init__(self,session)\n        self.root_path=_els_os.path.dirname(_ELS_PATH);self.title_text=\'James Bond 007 - Skyfall (2012)\'\n        self.entry=dict(entry or {});self.data={\'overview\':\'Als eine geheime Liste mit den Identitaeten verdeckter Agenten gestohlen wird, geraet M unter Druck. James Bond verfolgt die Spur eines Gegners, der mit ihrer Vergangenheit verbunden ist. Seine Loyalitaet wird auf die Probe gestellt, waehrend der MI6 selbst zum Angriffsziel wird.\',\'genres\':[\'Action\',\'Abenteuer\',\'Thriller\'],\'directors\':[\'Sam Mendes\'],\'actors\':[\'Daniel Craig\',\'Judi Dench\',\'Javier Bardem\',\'Ralph Fiennes\',\'Naomie Harris\']};self.data.update(_els_read_cache());self.closed_local=False;self.ready_local=None;self.focus_local=0;self.page_local=0\n        self.local_status=\'Originaldatei auf USB · Wiedergabe lokal\'\n        for name in (\'title\',\'meta\',\'genres\',\'overview\',\'people\',\'poster_hint\',\'play\',\'back\',\'status\'):self[name]=Label(\'\')\n        self[\'poster\']=Pixmap();self[\'focus\']=Label(\'\');self[\'play\'].setText(\'▶ Abspielen\');self[\'back\'].setText(\'← Zurück\')\n        self[\'actions\']=ActionMap([\'OkCancelActions\',\'ColorActions\',\'DirectionActions\'],{\'ok\':self.accept_local,\'green\':self.play_local,\'red\':self.close,\'cancel\':self.close,\'up\':self.toggle_local,\'down\':self.toggle_local,\'left\':lambda:self.page_description(-1),\'right\':lambda:self.page_description(1)},-1)\n        self.timer_local=eTimer();self.timer_local.callback.append(self.poll_local)\n        self.onLayoutFinish.append(self.start_local);self.onClose.append(self.close_local)\n    def safe_within_root(self,path):return _els_os.path.realpath(path)==_els_os.path.realpath(_ELS_PATH)\n    def start_local(self):\n        self.render_local();self.timer_local.start(200,False)\n        try:_els_thread.Thread(target=self.load_local,name=\'EmbyFlowLocalSkyfall\',daemon=True).start()\n        except Exception:self.local_status=\'Lokale Datei bereit; Filminformationen konnten nicht geladen werden.\';self.render_local()\n    def close_local(self):self.closed_local=True;self.timer_local.stop()\n    def load_local(self):\n        data=dict(self.data);data[\'path\']=_ELS_PATH\n        try:\n            probe=_embyflow_v21b_probe_local_file(_ELS_PATH) or {}\n            ticks=int(probe.get(\'runtime_ticks\') or 0)\n            if ticks>0:data[\'runtime_minutes\']=max(1,ticks//600000000)\n        except Exception:pass\n        # Offline detail: use existing cached/local artwork and metadata only.\n        try:_els_save_json(_ELS_CACHE,data)\n        except Exception:pass\n        if not self.closed_local:self.ready_local=data\n    def poll_local(self):\n        if self.closed_local:return\n        if self.ready_local is not None:\n            self.data=self.ready_local;self.ready_local=None;self.render_local()\n    def render_local(self):\n        self[\'title\'].setText(\'James Bond 007 – Skyfall\')\n        meta=[\'2012\',\'TS\',\'USB lokal\']\n        if self.data.get(\'runtime_minutes\'):meta.insert(1,str(self.data[\'runtime_minutes\'])+\' Min.\')\n        self[\'meta\'].setText(\' · \'.join(meta));self[\'genres\'].setText(\', \'.join(self.data.get(\'genres\') or []))\n        import textwrap\n        overview=self.data.get(\'overview\') or \'Skyfall liegt als lokale Originaldatei auf der USB-Festplatte. Die Wiedergabe benoetigt keinen Emby-Stream. Weitere Filminformationen erscheinen, wenn sie lokal gespeichert oder vom verbundenen Emby-Server abrufbar sind.\'\n        lines=[]\n        for paragraph in str(overview).splitlines():lines.extend(textwrap.wrap(paragraph,85) or [\'\'])\n        pages=[\'\\n\'.join(lines[i:i+6]) for i in range(0,len(lines),6)] or [\'\']\n        self.page_local=max(0,min(self.page_local,len(pages)-1));self[\'overview\'].setText(pages[self.page_local])\n        people=[]\n        if self.data.get(\'directors\'):people.append(\'Regie: \'+\', \'.join(self.data[\'directors\']))\n        if self.data.get(\'actors\'):people.append(\'Darsteller: \'+\', \'.join(self.data[\'actors\']))\n        self[\'people\'].setText(\'\\n\'.join(people));self[\'status\'].setText(self.local_status+(\' · Inhaltsangabe %d/%d\'%(self.page_local+1,len(pages)) if len(pages)>1 else \'\'))\n        poster=self.data.get(\'poster\') or self.entry.get(\'poster\') or \'\'\n        if not poster:\n            stem=_els_os.path.splitext(_ELS_PATH)[0]\n            poster=next((p for p in (stem+\'.jpg\',stem+\'.png\',self.root_path+\'/Skyfall.jpg\') if _els_os.path.isfile(p)),\'\')\n        if poster and _els_os.path.isfile(poster):\n            self[\'poster_hint\'].hide()\n            try:embyflow_decode_image_to_widget(self,\'poster\',poster,335,502,token=\'local-skyfall\',is_current=lambda:not self.closed_local)\n            except Exception:self[\'poster_hint\'].setText(\'Skyfall\\n2012\');self[\'poster_hint\'].show()\n        else:self[\'poster_hint\'].setText(\'Skyfall\\n2012\');self[\'poster_hint\'].show()\n        self.update_local_focus()\n    def page_description(self,delta):self.page_local=max(0,self.page_local+delta);self.render_local()\n    def update_local_focus(self):\n        try:self[\'focus\'].instance.move(ePoint(sx(1485),sy(650 if self.focus_local==0 else 775)))\n        except Exception:pass\n    def toggle_local(self):self.focus_local=1-self.focus_local;self.update_local_focus()\n    def accept_local(self):\n        if self.focus_local:self.close()\n        else:self.play_local()\n    def play_local(self):\n        if not _els_os.path.isfile(_ELS_PATH):self.local_status=\'Originaldatei fehlt. USB-Festplatte pruefen.\';self.render_local();return\n        return EmbyFlowLocalMediaScreen.play_file(self,_ELS_PATH)\n\ndef _els_open(self):\n    if not getattr(self,\'scan_loading\',False):\n        entry=self.selected_entry() or {};path=entry.get(\'path\') or \'\'\n        if path and _els_os.path.realpath(path)==_els_os.path.realpath(_ELS_PATH):\n            return self.session.open(EmbyFlowLocalSkyfallDetail,entry)\n    return _ELS_OPEN_BEFORE(self)\n\ndef _els_nav(self):\n    entries=list(_ELS_NAV_BEFORE(self))\n    if not any(str(e[0]).strip().casefold()==\'emby local\' or e[1].get(\'_direct_action_ref12\')==\'local_usb\' for e in entries):\n        index=next((i for i,e in enumerate(entries) if e[1].get(\'_direct_action_ref12\')==\'settings\'),len(entries))\n        entries.insert(index,(\'Emby Local\',{\'_direct_action_ref12\':\'local_usb\'}))\n    return entries\n\ndef _els_activate(self):\n    rows=self.direct_nav_entries_ref12;index=self.direct_nav_cursor_ref12\n    if 0<=index<len(rows) and rows[index][1].get(\'_direct_action_ref12\')==\'local_usb\':return self.open_local_media_menu()\n    return _ELS_ACTIVATE_BEFORE(self)\n\nEmbyFlowLocalLibraryScreenV3.open_selected=_els_open\nEmbyFlowE2Screen._direct_nav_build_entries_ref12=_els_nav\nEmbyFlowE2Screen._direct_nav_activate_ref12=_els_activate\n# EMBYFLOW_LOCAL_SKYFALL_ASYNC_NAV_V1_BEGIN\n_ELS_ASYNC_NAV_BEFORE=_embyflow_nav_groups_v30_transform\ndef _els_async_nav(entries):\n    rows=list(_ELS_ASYNC_NAV_BEFORE(entries) or [])\n    if not any(str(row[0]).strip().casefold()==\'emby local\' or row[1].get(\'_direct_action_ref12\')==\'local_usb\' for row in rows):\n        index=next((i for i,row in enumerate(rows) if row[1].get(\'_direct_action_ref12\')==\'settings\'),len(rows))\n        rows.insert(index,(\'Emby Local\',{\'_direct_action_ref12\':\'local_usb\'}))\n    return rows\n_embyflow_nav_groups_v30_transform=_els_async_nav\n# EMBYFLOW_LOCAL_SKYFALL_ASYNC_NAV_V1_END\n\n# EMBYFLOW_LOCAL_SKYFALL_DETAIL_V1_END\n'

def patched(source):
    tree=ast.parse(source)
    classes={n.name for n in tree.body if isinstance(n,ast.ClassDef)}
    if not {'EmbyFlowE2Screen','EmbyFlowLocalLibraryScreenV3','EmbyFlowLocalMediaScreen'}.issubset(classes):
        raise RuntimeError('Lokale Mediathek fehlt in diesem Pluginstand. Nichts geaendert.')
    if BEGIN in source or END in source:
        if source.count(BEGIN)!=1 or source.count(END)!=1:
            raise RuntimeError('Skyfall-Einstieg nicht eindeutig. Nichts geaendert.')
        start=source.index(BEGIN);end=source.index(END,start)+len(END)
        block=source[start:end].rstrip()
        if block==RUNTIME.rstrip():return source
        # Upgrade only the exact previous offline restoration, preserving all
        # playback code and local source settings outside this known block.
        direct="if 0<=index<len(rows) and rows[index][1].get('_direct_action_ref12')=='local_usb':return self.session.open(EmbyFlowLocalSkyfallDetail, {'path': _ELS_PATH})"
        dashboard="if 0<=index<len(rows) and rows[index][1].get('_direct_action_ref12')=='local_usb':return self.open_local_media_menu()"
        previous=RUNTIME.replace(dashboard,direct,1).rstrip()
        if block!=previous:
            raise RuntimeError('Abweichender Skyfall-Einstieg bereits vorhanden. Nichts geaendert.')
        result=source[:start]+RUNTIME.rstrip()+source[end:]
        ast.parse(result,feature_version=(3,8));compile(result,'plugin.py','exec')
        return result
    # Dependencies of the established detail page must exist before activation.
    for name in ('_embyflow_v21b_probe_local_file','_embyflow_nav_groups_v30_transform'):
        if not any(isinstance(n,ast.FunctionDef) and n.name==name for n in tree.body):
            raise RuntimeError('Lokale Wiedergabe/Navigationsschnittstelle fehlt: '+name)
    result=source.rstrip()+'\n\n'+RUNTIME.rstrip()+'\n'
    ast.parse(result,feature_version=(3,8));compile(result,'plugin.py','exec')
    return result

def main(plugin_path="/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py",
         lock_path="/etc/enigma2/embyflow-download-quota.json.lock", restart_gui=True,
         movie_path="/media/usb/Filme/James Bond 007 - Skyfall (2012).ts"):
    movie=Path(movie_path)
    if not movie.is_file() or movie.stat().st_size <= 0:
        raise RuntimeError("Skyfall-Originaldatei auf USB fehlt oder ist leer. Nichts geaendert.")
    fd=os.open(lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise RuntimeError("Sperrdatei ungueltig")
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        p=Path(plugin_path)
        if p.is_symlink() or not p.is_file():raise RuntimeError("Plugin fehlt")
        raw=p.read_bytes();s=raw.decode("utf-8")
        result=patched(s).encode("utf-8")
        if result==raw:
            print("Lokale USB-/HDD-Oberflaeche und Skyfall-Detailseite bereits vorhanden. Kein Neustart.",flush=True);return
        space=os.statvfs(p.parent)
        if space.f_bavail*space.f_frsize<len(raw)*2+2097152:raise RuntimeError("Zu wenig Speicher")
        backup=str(p)+".vor-skyfall-lokal-"+time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid())
        mode=stat.S_IMODE(p.stat().st_mode)
        with open(backup,"xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.chmod(backup,mode)
        tmp=str(p.parent / (".skyfall-lokal-"+str(os.getpid())+"-"+str(time.time_ns())))
        h=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);stopped=False
        try:
            with os.fdopen(h,"wb") as f:f.write(result);f.flush();os.fsync(f.fileno())
            os.chmod(tmp,mode)
            if p.read_bytes()!=raw:raise RuntimeError("Plugin inzwischen geaendert")
            print("Sicherung: "+backup,flush=True)
            # A failed stop request may already have stopped part of the GUI.
            # Always request its restart once stopping has been attempted.
            if restart_gui:
                stopped=True
                subprocess.run(["init","4"],check=True);time.sleep(3)
            if p.read_bytes()!=raw:raise RuntimeError("Plugin inzwischen geaendert")
            os.replace(tmp,p)
        finally:
            try:
                if os.path.exists(tmp):os.unlink(tmp)
            except OSError as error:
                print("HINWEIS: Temporaere Datei konnte nicht entfernt werden: "+str(error),flush=True)
            finally:
                if stopped:subprocess.run(["init","3"],check=True)
        print("FERTIG. Emby Local oeffnet wieder die eigene USB-/HDD-Oberflaeche; Skyfall behaelt seine Detailseite. Originaldatei und Player-Fixes bleiben erhalten. "+
              ("GUI-Start angefordert." if restart_gui else "Bitte GUI nach der Paketinstallation manuell neu starten."),flush=True)
    finally:os.close(fd)
if __name__ == "__main__":
    try:
        if sys.argv[1:] not in ([], ["--no-restart"]):
            raise RuntimeError("Erlaubter Parameter: --no-restart")
        main(restart_gui=not bool(sys.argv[1:]))
    except Exception as error:
        print("STOPP: "+str(error),flush=True)
        raise SystemExit(1)

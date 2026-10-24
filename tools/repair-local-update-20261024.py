import os,stat,fcntl,tempfile,time,shutil,subprocess,re
from pathlib import Path
IMPORT="    import py_compile\n"
REPLACEMENT="    class py_compile:\n        @staticmethod\n        def compile(path, **kwargs):\n            with open(path, \"rb\") as handle:\n                compile(handle.read(), path, \"exec\", dont_inherit=True)\n"
FIXED="def _efguard_gui_tick():\n    global _efguard_notice, _efguard_gui_session\n    session = _efguard_gui_session\n    if session is None:\n        return\n    dialogs = [getattr(session, 'current_dialog', None)]\n    for entry in getattr(session, 'dialog_stack', ()):\n        dialogs.append(entry[0] if isinstance(entry, (tuple, list)) else entry)\n    if not any(getattr(type(dialog), '__module__', '') == __name__ for dialog in dialogs if dialog):\n        _efguard_gui_timer.stop()\n        _efguard_gui_session = None\n        return\n    # StartEnigma rejects session.open while a modal screen is not executing.\n    # Keep the pending notice through dialog/service transitions.\n    if not bool(getattr(session, 'in_exec', False)):\n        return\n    with _efguard_lock:\n        notice = _efguard_notice\n        _efguard_notice = None\n    if notice:\n        try:\n            session.open(MessageBox, notice, MessageBox.TYPE_INFO, timeout=12)\n        except Exception:\n            # Another transition may have begun between the check and open.\n            # A background notification must never crash Enigma2. Retry later;\n            # do not overwrite a newer notice generated while open was tried.\n            with _efguard_lock:\n                if _efguard_notice is None:\n                    _efguard_notice = notice\n"
def main():
    fd=os.open("/etc/enigma2/embyflow-download-quota.json.lock",os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise RuntimeError("Sperrdatei ungueltig")
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        p=Path("/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py")
        if p.is_symlink() or not p.is_file():raise RuntimeError("Plugin fehlt")
        raw=p.read_bytes();s=raw.decode("utf-8")
        updated=s
        if IMPORT in updated:
            if updated.count(IMPORT)!=1 or updated.count("py_compile.compile(")!=5:raise RuntimeError("Updater weicht ab. Nichts geaendert.")
            updated=updated.replace(IMPORT,REPLACEMENT,1)
        elif "class py_compile:" not in updated and "def _embyflow_update_check_python_source(" not in updated:
            raise RuntimeError("Updater nicht erkannt. Nichts geaendert.")
        matches=list(re.finditer(r"(?m)^def _efguard_gui_tick\(\):\n",updated))
        if len(matches)!=1:raise RuntimeError("Hinweis-Timer nicht eindeutig. Nichts geaendert.")
        begin=matches[0].start()
        following=re.search(r"(?m)^(?:def |class |#|[A-Za-z_])",updated[matches[0].end():])
        if following is None:raise RuntimeError("Funktionsende fehlt. Nichts geaendert.")
        end=matches[0].end()+following.start()
        updated=updated[:begin]+FIXED+"\n\n"+updated[end:]
        result=updated.encode("utf-8");compile(result,str(p),"exec")
        if result==raw:
            print("Bereits aktuell. Nichts geaendert.",flush=True);return
        if shutil.disk_usage(p.parent).free<len(raw)*2+2097152:raise RuntimeError("Zu wenig Speicher")
        backup=str(p)+".vor-update-lokal-"+time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid())
        mode=stat.S_IMODE(p.stat().st_mode)
        with open(backup,"xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.chmod(backup,mode)
        h,tmp=tempfile.mkstemp(dir=p.parent,prefix=".update-lokal-");stopped=False
        try:
            with os.fdopen(h,"wb") as f:f.write(result);f.flush();os.fsync(f.fileno())
            os.chmod(tmp,mode)
            if p.read_bytes()!=raw:raise RuntimeError("Plugin inzwischen geaendert")
            print("Sicherung: "+backup,flush=True)
            subprocess.run(["init","4"],check=True);stopped=True;time.sleep(3)
            if p.read_bytes()!=raw:raise RuntimeError("Plugin inzwischen geaendert")
            os.replace(tmp,p)
            print("FERTIG. Lokale Updatekorrektur installiert. GUI startet. Erweiterungen erhalten.",flush=True)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
            if stopped:subprocess.run(["init","3"],check=True)
    finally:os.close(fd)
try:main()
except Exception as error:
    print("STOPP: "+str(error),flush=True)
    raise SystemExit(1)

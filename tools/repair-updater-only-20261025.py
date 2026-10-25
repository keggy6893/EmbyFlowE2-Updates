import os,stat,fcntl,time,subprocess,sys
from pathlib import Path
import re

IMPORT='    import py_compile\n'
HELPER='''    def _embyflow_update_builtin_syntax(path):
        with open(path, "rb") as handle:
            compile(handle.read(), path, "exec", dont_inherit=True)
'''


def patched(source):
    headers=list(re.finditer(r'(?m)^def _embyflow_update_install_plugin\(manifest\):\n',source))
    if len(headers)!=1:raise RuntimeError('Updater nicht eindeutig erkannt. Nichts geaendert.')
    first=headers[0].start()
    following=re.search(r'(?m)^(?:def |class )',source[headers[0].end():])
    last=headers[0].end()+following.start() if following else len(source)
    body=source[first:last]
    if IMPORT not in body:
        if ('def _embyflow_update_builtin_syntax(path):' in body and body.count('_embyflow_update_builtin_syntax(')==6):
            compile(source,'plugin.py','exec');return source
        if ('class py_compile:' in body and 'compile(handle.read(), path, "exec", dont_inherit=True)' in body):
            compile(source,'plugin.py','exec');return source
        if ('def _embyflow_update_check_python_source(path):' in source and body.count('_embyflow_update_check_python_source(')==5):
            compile(source,'plugin.py','exec');return source
        raise RuntimeError('Abweichender Updater. Nichts geaendert.')
    if body.count(IMPORT)!=1 or body.count('py_compile.compile(')!=5:
        raise RuntimeError('Erwartete fuenf Syntaxpruefungen nicht gefunden. Nichts geaendert.')
    calls=re.compile(r'py_compile\.compile\(\s*([A-Za-z_]\w*)\s*,\s*doraise\s*=\s*True\s*\)')
    if len(list(calls.finditer(body)))!=5:
        raise RuntimeError('Syntaxpruefung weicht ab. Nichts geaendert.')
    body=body.replace(IMPORT,HELPER,1)
    body=calls.sub(lambda match:'_embyflow_update_builtin_syntax('+match.group(1)+')',body)
    if 'py_compile' in body:raise RuntimeError('Weitere Modulverwendung gefunden. Nichts geaendert.')
    result=source[:first]+body+source[last:]
    compile(result,'plugin.py','exec')
    return result

def main(plugin_path="/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py",
         lock_path="/etc/enigma2/embyflow-download-quota.json.lock", restart_gui=True):
    fd=os.open(lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise RuntimeError("Sperrdatei ungueltig")
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        p=Path(plugin_path)
        if p.is_symlink() or not p.is_file():raise RuntimeError("Plugin fehlt")
        raw=p.read_bytes();s=raw.decode("utf-8")
        result=patched(s).encode("utf-8")
        if result==raw:
            print("Updater ist bereits ohne py_compile-Modul nutzbar. Kein Neustart.",flush=True);return
        space=os.statvfs(p.parent)
        if space.f_bavail*space.f_frsize<len(raw)*2+2097152:raise RuntimeError("Zu wenig Speicher")
        backup=str(p)+".vor-updater-only-"+time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid())
        mode=stat.S_IMODE(p.stat().st_mode)
        with open(backup,"xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.chmod(backup,mode)
        tmp=str(p.parent / (".updater-only-"+str(os.getpid())+"-"+str(time.time_ns())))
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
        print("FERTIG. Nur Updater repariert. Alle 5 Syntaxpruefungen bleiben aktiv. "+
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

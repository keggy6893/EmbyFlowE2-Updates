import os,stat,fcntl,tempfile,time,shutil,subprocess
from pathlib import Path
RUNTIME="# EMBYFLOW_LOCAL_SEEK_V1_BEGIN\n_EFLS_CHAPTER_BEFORE = EmbyFlowMoviePlayer.embyflow_seek_to_chapter\n_EFLS_RESTART_BEFORE = EmbyFlowMoviePlayer.embyflow_v10_restart_stream\n_EFLS_FALLBACK_BEFORE = EmbyFlowMoviePlayer.restart_stream_at_ticks\n\n\ndef _efls_is_local(player):\n    return bool((getattr(player, 'playback_info', None) or {}).get('local_file'))\n\n\ndef _efls_native(player, target_ticks):\n    # Local files must never enter an Emby HTTP restart or backend promotion.\n    # Use the active file service, as standard Enigma2/EMC seeking does.\n    try:\n        import os\n        if getattr(player, 'closed', False):\n            return False\n        current = player.session.nav.getCurrentlyPlayingServiceReference()\n        own = getattr(player, 'ref', None)\n        path = str(getattr(player, 'stream_url', '') or '')\n        if (current is None or own is None or\n                current.toString() != own.toString() or not os.path.isabs(path) or\n                os.path.realpath(current.getPath()) != os.path.realpath(path)):\n            return False\n        service = player.session.nav.getCurrentService()\n        seek = service and service.seek()\n        if not seek:\n            return False\n        capability = getattr(seek, 'isCurrentlySeekable', None)\n        if callable(capability) and not capability():\n            return False\n        target = max(0, int(target_ticks))\n        # Prefer the active service length, not remote metadata for another cut.\n        length = seek.getLength()\n        if length and len(length) >= 2 and length[0] == 0 and int(length[1]) > 0:\n            target = min(target, max(0, (int(length[1]) * 10000000 // 90000) - 10000000))\n        target_pts = target * 90000 // 10000000\n        accepted = seek.seekTo(target_pts) in (None, 0)\n        # Do not replace real position with the requested position, reset audio,\n        # unpause deliberately paused playback, or report a server session.\n        if accepted:\n            player.seek_has_been_used = True\n        try:\n            with embyflow_open_log('/tmp/embyflow_local_seek.log', 'a') as log:\n                log.write('%s LOCAL_SEEK target_pts=%s accepted=%d service=%s\\n' %\n                          (time.strftime('%H:%M:%S'), target_pts, accepted, current.type))\n        except Exception:\n            pass\n        try:\n            player['state_label'].setText('Lokaler Sprung angefordert' if accepted else 'Lokaler Sprung nicht angenommen')\n            player.show_overlay()\n        except Exception:\n            pass\n        return accepted\n    except Exception:\n        return False\n\n\ndef _efls_chapter(player, target_ticks):\n    if _efls_is_local(player):\n        return _efls_native(player, target_ticks)\n    return _EFLS_CHAPTER_BEFORE(player, target_ticks)\n\n\ndef _efls_restart(player, target_ticks, subtitle_stream_index=None, subtitle_label=None):\n    if _efls_is_local(player):\n        return _efls_native(player, target_ticks)\n    return _EFLS_RESTART_BEFORE(player, target_ticks, subtitle_stream_index, subtitle_label)\n\n\ndef _efls_fallback(player, target_ticks):\n    if _efls_is_local(player):\n        return _efls_native(player, target_ticks)\n    return _EFLS_FALLBACK_BEFORE(player, target_ticks)\n\n\nEmbyFlowMoviePlayer.embyflow_seek_to_chapter = _efls_chapter\nEmbyFlowMoviePlayer.embyflow_v10_restart_stream = _efls_restart\nEmbyFlowMoviePlayer.restart_stream_at_ticks = _efls_fallback\n# EMBYFLOW_LOCAL_SEEK_V1_END\n"
def main():
    fd=os.open("/etc/enigma2/embyflow-download-quota.json.lock",os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise RuntimeError("Sperrdatei ungueltig")
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        p=Path("/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py")
        if p.is_symlink() or not p.is_file():raise RuntimeError("Plugin fehlt")
        raw=p.read_bytes();s=raw.decode("utf-8")
        if "# EMBYFLOW_SEEK_VERIFY_V1_START" in s:raise RuntimeError("Andere Seek-Testkorrektur vorhanden. Nichts geaendert.")
        if "# EMBYFLOW_LOCAL_SEEK_V1_BEGIN" in s:
            print("Lokale Sprungkorrektur bereits vorhanden. Nichts geaendert.",flush=True);return
        for name in ("    def embyflow_seek_to_chapter(","    def embyflow_v10_restart_stream(","    def restart_stream_at_ticks("):
            if s.count(name)!=1:raise RuntimeError("Player nicht eindeutig erkannt. Nichts geaendert.")
        result=(s.rstrip()+"\n\n"+RUNTIME).encode("utf-8");compile(result,str(p),"exec")
        if shutil.disk_usage(p.parent).free<len(raw)*2+2097152:raise RuntimeError("Zu wenig Speicher")
        backup=str(p)+".vor-local-seek-"+time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid())
        mode=stat.S_IMODE(p.stat().st_mode)
        with open(backup,"xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.chmod(backup,mode)
        h,tmp=tempfile.mkstemp(dir=p.parent,prefix=".local-seek-");stopped=False
        try:
            with os.fdopen(h,"wb") as f:f.write(result);f.flush();os.fsync(f.fileno())
            os.chmod(tmp,mode)
            if p.read_bytes()!=raw:raise RuntimeError("Plugin inzwischen geaendert")
            print("Sicherung: "+backup,flush=True)
            subprocess.run(["init","4"],check=True);stopped=True;time.sleep(3)
            if p.read_bytes()!=raw:raise RuntimeError("Plugin inzwischen geaendert")
            os.replace(tmp,p)
            print("FERTIG. Lokaler Sprungtest installiert. GUI startet. Nur lokale Dateispruenge geaendert.",flush=True)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
            if stopped:subprocess.run(["init","3"],check=True)
    finally:os.close(fd)
try:main()
except Exception as error:
    print("STOPP: "+str(error),flush=True)
    raise SystemExit(1)

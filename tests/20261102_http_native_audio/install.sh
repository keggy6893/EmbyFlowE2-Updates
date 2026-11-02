#!/bin/sh
set -eu
python3 - <<'EMBYFLOW_HTTP_AUDIO_PY'
from pathlib import Path
import ast, os, shutil, tempfile, time

GUARD = '''        # EMBYFLOW_HTTP_NATIVE_FIRST_LOCAL1_20261102
        try:
            if _efua_native(player):
                service = player.session.nav.getCurrentService()
                tracks = service and service.audioTracks()
                count = int(tracks.getNumberOfTracks() or 0) if tracks else 0
                if count >= 2:
                    _efua_log('http-native-first', native_tracks=count)
                    return False
        except Exception:
            pass
'''


def transform(source):
    if 'EMBYFLOW_HTTP_NATIVE_FIRST_LOCAL1_20261102' in source:
        raise ValueError('HTTP-Nativ-Test bereits vorhanden. Nichts geaendert.')
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)
           and n.name=='_efua_vu_remote_audio_trial']
    if len(nodes)!=1:
        raise ValueError('Erwarteter HTTP-Tonwechsel nicht eindeutig vorhanden.')
    node=nodes[0]; lines=source.splitlines(keepends=True)
    body=''.join(lines[node.lineno-1:node.end_lineno])
    target="        return bool(_efa2_enabled(player) and not _efa3_audio_compat_codec(player))"
    if body.count(target)!=1:
        raise ValueError('Tonwechsel-Code weicht vom geprueften Stand ab.')
    lines[node.lineno-1:node.end_lineno]=[body.replace(target,GUARD+target,1)]
    result=''.join(lines)
    compile(result,'plugin.py','exec')
    return result


def main():
    p=Path('/usr/lib/enigma2/python/Plugins/Extensions/EmbyFlowE2/plugin.py')
    original=p.read_bytes()
    after=transform(original.decode('utf-8')).encode('utf-8')
    backup=Path(str(p)+'.before_http_native_'+str(time.time_ns())+'.bak')
    shutil.copy2(p,backup)
    assert backup.read_bytes()==original and p.read_bytes()==original,'Sicherungspruefung fehlgeschlagen'
    fd,temp=tempfile.mkstemp(prefix='.http_native_',dir=str(p.parent))
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(after);handle.flush();os.fsync(handle.fileno())
        shutil.copystat(p,temp)
        os.chown(temp,p.stat().st_uid,p.stat().st_gid)
        assert p.read_bytes()==original,'Plugin wurde zwischenzeitlich geaendert'
        os.replace(temp,p)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    print('OK: HTTP-Nativ-Test; Syntax korrekt. Sicherung:',backup)


if __name__=='__main__':main()

EMBYFLOW_HTTP_AUDIO_PY

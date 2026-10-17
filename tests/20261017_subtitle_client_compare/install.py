"""Trace request identity in both installed clients without altering requests."""
from pathlib import Path
import ast, os, shutil, sys, time

HELPER='''
# EMBYFLOW_CLIENT_COMPARE_20261017
def _efcompare_record(client, url, event, status=None, size=None, elapsed=None, error=None):
    try:
        import hashlib, json, re, time
        from urllib.parse import urlsplit, unquote
        parts=urlsplit(url)
        match=re.search(r'/(Items|Videos)/([^/]+)/([^/]+)/Subtitles/(\\d+)/',parts.path,re.I)
        def digest(value):
            return hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]
        # Do not hash or record credentials, query strings or URL userinfo.
        origin='%s://%s:%s'%(parts.scheme.lower(),str(parts.hostname or '').lower(),parts.port or (443 if parts.scheme=='https' else 80))
        row=dict(time=time.strftime('%H:%M:%S'),client=client,event=event,
            server=digest(origin),route=match.group(1).lower() if match else 'unknown',
            item=digest(unquote(match.group(2))) if match else None,
            source=digest(unquote(match.group(3))) if match else None,
            stream=int(match.group(4)) if match else None,
            status=status,bytes=size,seconds=elapsed,error=error)
        with open('/tmp/emby_subtitle_compare.jsonl','a') as handle:
            handle.write(json.dumps(row)+'\\n')
    except Exception:
        pass
'''

FLOW='''
_efcompare_flow_before=_efut_get
def _efut_get(url, **kwargs):
    import time
    started=time.monotonic()
    _efcompare_record('EmbyFlow',url,'start')
    try:
        response=_efcompare_flow_before(url,**kwargs)
        _efcompare_record('EmbyFlow',url,'result',int(response.status_code),len(response.content or b''),round(time.monotonic()-started,2))
        return response
    except Exception as error:
        _efcompare_record('EmbyFlow',url,'error',elapsed=round(time.monotonic()-started,2),error=type(error).__name__)
        raise
'''

CLIENT='''
_efcompare_client_before=EmbyPlayer.loadAndParseSubs
def _efcompare_client_load(self, stream_url):
    import time
    started=time.monotonic()
    _efcompare_record('e2embyclient',stream_url,'start')
    result=_efcompare_client_before(self,stream_url)
    _efcompare_record('e2embyclient',stream_url,'loaded' if result else 'failed',elapsed=round(time.monotonic()-started,2))
    return result
EmbyPlayer.loadAndParseSubs=_efcompare_client_load
'''

def patch_flow(source):
    if '# EMBYFLOW_CLIENT_COMPARE_20261017' in source:raise RuntimeError('EmbyFlow-Vergleich bereits installiert.')
    if not any(isinstance(n,ast.FunctionDef) and n.name=='_efut_get' for n in ast.parse(source).body):raise RuntimeError('EmbyFlow-Untertitlelfix fehlt.')
    result=source+'\n'+HELPER+FLOW
    compile(result,'plugin.py','exec');return result

def patch_client(source):
    if '# EMBYFLOW_CLIENT_COMPARE_20261017' in source:raise RuntimeError('Client-Vergleich bereits installiert.')
    classes=[n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='EmbyPlayer']
    if len(classes)!=1 or not any(isinstance(n,ast.FunctionDef) and n.name=='loadAndParseSubs' for n in classes[0].body):raise RuntimeError('Client-Quellstand nicht unterstuetzt.')
    result=source+'\n'+HELPER+CLIENT
    compile(result,'EmbyPlayer.py','exec');return result

def main():
    root=Path('/usr/lib/enigma2/python/Plugins/Extensions')
    flow=root/'EmbyFlowE2/plugin.py'
    candidates=[p for p in root.rglob('EmbyPlayer.py') if p!=flow]
    if len(candidates)!=1:raise RuntimeError('e2embyclient-Quellpfad nicht eindeutig gefunden. Nichts geaendert.')
    client=candidates[0]
    updates=[(flow,patch_flow(flow.read_text())),(client,patch_client(client.read_text()))]
    stamp=time.strftime('%Y%m%d-%H%M%S')
    backups=[];temps=[];replaced=[]
    try:
        for path,result in updates:
            backup=path.with_name(path.name+'.vor-ut-vergleich-'+stamp)
            if backup.exists():raise RuntimeError('Sicherung existiert bereits.')
            shutil.copy2(str(path),str(backup));backups.append((path,backup))
            temp=path.with_name(path.name+'.ut-compare.tmp')
            with temp.open('x') as handle:
                handle.write(result);handle.flush();os.fsync(handle.fileno())
            shutil.copystat(str(path),str(temp));temps.append((path,temp))
        for path,temp in temps:
            os.replace(str(temp),str(path));replaced.append(path)
    except Exception:
        for path,backup in backups:
            if path in replaced:shutil.copy2(str(backup),str(path))
        for path,temp in temps:
            if temp.exists():temp.unlink()
        raise
    print('Vergleichsdiagnose in beiden Plugins installiert; Download und Auswahl unveraendert.')
    for path,backup in backups:print('Sicherung:',backup)
    print('GUI neu starten. Betroffenen 4K-Film erst in EmbyFlow, danach im e2embyclient testen.')

if __name__=='__main__':main()

from pathlib import Path
import ast,hashlib,json
root=Path(__file__).resolve().parents[1]
base=root/'EmbyFlowE2_Detail_Hintergrund_20261004_0402.py'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='d495d9dcb0736bf98af078ce21c2b7904c7e45e518f109295c5add0b74240e2b'
s=base.read_text();tree=ast.parse(s)
names={'_trall_words','_trall_queries','_trall_score','_trall_extract','_eftr_youtube_url','_eftr_select_stream'}
functions={n.name:ast.get_source_segment(s,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names}
assert set(functions)==names
child='''import sys,json,threading,time as _eftr_time,re as _trall_re,unicodedata as _trall_unicode
from urllib.parse import urlparse as _eftr_urlparse
sys.path.insert(0,sys.argv[1])
import yt_dlp
if not str(getattr(yt_dlp,'__file__','')).startswith(sys.argv[1]+'/'):
    raise ImportError('Resolver stammt nicht aus dem geprueften Paket')
payload=json.loads(sys.argv[2])
_trall_lock=threading.Lock()
_trall_context={payload['url']:payload['context']} if payload.get('context') else {}
def _trcache_log(message):
    print(message,file=sys.stderr,flush=True)
class Logger:
    def debug(self,message):
        if str(message).startswith('[youtube]'):
            _trcache_log(message)
    def warning(self,message):
        _trcache_log('WARNING: '+str(message))
    def error(self,message):
        _trcache_log('ERROR: '+str(message))
'''
child+='\n'+'\n\n'.join(functions[name] for name in sorted(names))+'\n'
child+='''try:
    options={'quiet':True,'logger':Logger(),'noplaylist':True,'skip_download':True,
             'socket_timeout':8,'retries':1,'format':payload['format'],
             'allowed_extractors':['youtube','youtube:search']}
    with yt_dlp.YoutubeDL(options) as ydl:
        info=_trall_extract(ydl,payload['url'],threading.Event())
        fields=('format_id','protocol','height','vcodec','acodec','url','tbr','language')
        output={'url':info.get('url'),'formats':[{k:f.get(k) for k in fields} for f in info.get('formats',[])]}
        print(json.dumps(output))
except Exception as error:
    print('ERROR: '+str(error),file=sys.stderr)
    sys.exit(1)
'''
compile(child,'isolated resolver','exec')
for old,new in [
('PLUGIN_VERSION = "2026-RCDEV-DETAIL-HINTERGRUND-20261004"','PLUGIN_VERSION = "2026-RCDEV-RESOLVER-20261004"'),
('PLUGIN_UPDATE_BUILD = 2026100402','PLUGIN_UPDATE_BUILD = 2026100403'),
("result['song'] = _efbg_music(data, auth, cancel)","result['song'] = _efbg_music(data, auth, cancel, state)"),
("        if process.returncode or cancel.is_set():\n            return ''\n        path, playlist", "        _efbg_diagnose(data, process.returncode, stderr, 'VIDEO')\n        if process.returncode or cancel.is_set():\n            return ''\n        path, playlist")]:
 assert s.count(old)==1,old
 s=s.replace(old,new,1)
s+='\n_TRISO_CODE = '+repr(child)+'\n'+(root/'release_tools/isolated_resolver_0403.inc.py').read_text()
compile(s,'plugin.py','exec')
target=root/'EmbyFlowE2_Resolver_Dreambox_20261004_0403.py';target.write_text(s)
m=json.loads((root/'update.json').read_text())
m.update(version='2026-RCDEV-RESOLVER-20261004',build=2026100403,download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
m['changelog']=[
'Bei bereits geladenem fremden yt-dlp: eigene gepruefte Version im separaten Prozess mit vollstaendigem Suchkontext',
'Auch im Prozess-Fallback: weitere Links und passende Trailer-Suche statt nur des ersten Links',
'Hintergrundmusik im isolierten Prozess; kein Importkonflikt mit anderen Plugins',
'Fehlerprotokoll fuer Hintergrundvideo und Musik: /tmp/embyflow_background_debug.log',
'Keine Deinstallation oder Aenderung des yt-dlp anderer Plugins; wiederholte erfolglose Import-Vorladung entfällt',
'Funktionen aus 0402 enthalten; automatisiert getestet, Dreambox-Test steht aus']
(root/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print('Built 2026100403',m['sha256'])

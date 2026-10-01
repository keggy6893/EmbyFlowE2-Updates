import ast,hashlib,json,pathlib,sys
BASE='9d0e194291abd8c29e4a58ed2d65fa39993467971df8ba1a857c1abe5eec0f5d'
OUTPUT='EmbyFlowE2_BlueDetail_20261001_0105.py'
def build(data,layer):
 if hashlib.sha256(data).hexdigest()!=BASE:raise ValueError('Unexpected base')
 s=data.decode()
 for old,new in [('PLUGIN_UPDATE_BUILD = 2026100101','PLUGIN_UPDATE_BUILD = 2026100105'),('PLUGIN_VERSION = "2026-RCDEV-THEMESTREAM-20261001"','PLUGIN_VERSION = "2026-RCDEV-DIRECTEXIT-20261001"')]:
  if s.count(old)!=1:raise ValueError('Anchor mismatch')
  s=s.replace(old,new,1)
 # Restore the two direct player exit bindings from the working September PY.
 for key in ('cancel','red'):
  old='"%s": self.cast_exit_or_leave,' % key
  if s.count(old)!=1:raise ValueError('Player exit anchor mismatch: '+key)
  s=s.replace(old,'"%s": self.leave_player,' % key,1)
 s+='\n\n'+layer+'\n';ast.parse(s);return s.encode()
if __name__=='__main__':
 source,layer,out=map(pathlib.Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
 data=build(source.read_bytes(),layer.read_text());(out/OUTPUT).write_bytes(data)
 m=dict(version='2026-RCDEV-DIRECTEXIT-20261001',build=2026100105,channel='rcdev',target='plugin.py',artifact_type='plugin_py',download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+OUTPUT,sha256=hashlib.sha256(data).hexdigest(),changelog=['EXIT und ROT beenden den Player wieder direkt wie in der älteren funktionierenden PY','Detailseite exakt wie bestätigte Vorschau: einfarbig #0C1827, ohne Verlauf','Poster unten rechts bleibt erhalten','ThemeVideos, Musik-Test und Lautstärkegrenze weiterhin enthalten'])
 (out/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(m['sha256'])

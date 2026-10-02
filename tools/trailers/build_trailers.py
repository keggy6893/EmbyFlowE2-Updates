import ast
import hashlib
import json
from pathlib import Path
BASE='EmbyFlowE2_BlueDetail_20261001_0110.py'
OUTPUT='EmbyFlowE2_Trailers_20261002_0201.py'
def build():
    original=Path(BASE).read_bytes()
    assert hashlib.sha256(original).hexdigest()=='91006fe0410811f29d330a3e9a8de23c0323a72561e2f2ffd2750e858648e447'
    source=original.decode()
    for old,new in [
        ('PLUGIN_UPDATE_BUILD = 2026100110','PLUGIN_UPDATE_BUILD = 2026100201'),
        ('PLUGIN_VERSION = "2026-RCDEV-TVCHOICE-20261001"','PLUGIN_VERSION = "2026-RCDEV-TRAILERS-20261002"')]:
        assert source.count(old)==1,old
        source=source.replace(old,new,1)
    layer=Path(__file__).with_name('trailer_layer.py').read_text()
    source+='\n\n'+layer+'\n'
    tree=ast.parse(source)
    names={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
    assert {'get_emby_auth','embyflow_http_get','_fallback_detail_stop','_embyflow_theme_stop_v1','_skyfall_local_theme_stop','_embyflow_theme_volume_release'}<=names
    assert 'SKYFALL_TRAILER_LOCAL1' not in source
    assert 'Trailer-Test' not in layer
    data=source.encode()
    Path(OUTPUT).write_bytes(data)
    manifest=json.loads(Path('update.json').read_text())
    assert manifest['build']==2026100110, 'Manifest moved'
    manifest.update(version='2026-RCDEV-TRAILERS-20261002',build=2026100201,
                    download='https://raw.githubusercontent.com/keggy6893/EmbyFlowE2-Updates/main/'+OUTPUT,
                    sha256=hashlib.sha256(data).hexdigest())
    manifest['changelog']=[
        'Trailer-Button fuer Filme und Serien; OK oder Taste 9 startet den bei Emby hinterlegten YouTube-Trailer',
        'Bei Staffeln und Episoden den Trailer der zugehoerigen Serie verwenden',
        'Trailer-Komponente beim ersten Bedarf direkt von GitHub laden und SHA256 pruefen; kein Image-Feed',
        'H.264 bis 720p mit Ton; STOP/EXIT kehrt zur Detailseite zurueck',
        'Bestaetigtes Layout: drei gleich grosse Buttons, gleiche Abstaende, Poster unten rechts',
        'TV-Ton-Auswahl und bestehende Player-Exit-Korrekturen bleiben enthalten']
    Path('update.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('BUILD',manifest['build'],'SHA256',manifest['sha256'])
if __name__=='__main__':build()

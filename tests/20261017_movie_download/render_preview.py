"""Render actual dialog XML, text and embedded PNG assets for a local preview.
This is a source-based rendering, not an Enigma2 receiver screenshot.
"""
from pathlib import Path
import base64
import io
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from test_ui import load_ui, Session
import sys

ns=load_ui()
ns['_efdl_engine'].quota_status=lambda:dict(used=2,remaining=3,limit=5)
source={'Id':'preview','Size':int(8.87*2**30),'Container':'mkv','MediaStreams':[{'Type':'Video','Width':1920,'Codec':'h264'}]}
name='Mayday.2026.German.DL.Atmos.1080p.ATVP.WEB.H264-ZeroTwo'
dialog=ns['EmbyFlowDownloadChoice'](Session(),title='Filmversion auswählen',list=[(name,source)],description='Wähle die passende Version für deinen Download',access_status='✓ Benutzerfreigabe vom Anbieter bestätigt')
if '--library' in sys.argv:
    from test_library import load_library
    ns = load_library()
    dialog = ns['EmbyFlowDownloadsScreen'](Session())
    dialog.entries = [dict(title=title, path='/media/%s/movie/EmbyFlow/%s.mkv' % (storage.lower(), title),
                           size=int(size*2**30), storage=storage, metadata=metadata)
                      for title, size, storage, metadata in (
                          ('Mayday',8.87,'USB',{'Type':'Movie'}),
                          ('Tenzing',9.74,'USB',{'Type':'Movie'}),
                          ('Berge · S01E02 · Der Aufstieg',1.42,'HDD',{'Type':'Episode'}))]
    dialog['status'].setText('Filme und Folgen · lokal auf HDD und USB')
images={}
ns['_efdl_style_apply']=lambda widget,name:images.__setitem__(id(widget),name)
ns['_efdl_style_apply'](dialog['panel'], 'panel')
dialog.draw()
root=ET.fromstring(dialog.skin)
w,h=map(int,root.get('size').split(','))
canvas=Image.new('RGBA',(1920,1080),'#040B12')
panel=Image.new('RGBA',(w,h))
font_file='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
for node in sorted(root,key=lambda n:int(n.get('zPosition','0'))):
    x,y=map(int,node.get('position').split(','));rw,rh=map(int,node.get('size').split(','))
    name=node.get('name');widget=dialog.get(name)
    if widget is not None and getattr(widget,'hidden',False):continue
    if widget is not None and id(widget) in images:
        raw=base64.b64decode(ns['_EFDL_STYLE_ASSETS'][images[id(widget)]])
        asset=Image.open(io.BytesIO(raw)).convert('RGBA').resize((rw,rh),Image.Resampling.LANCZOS)
        panel.alpha_composite(asset,(x,y));continue
    if node.tag=='eLabel' and not node.get('text'):
        ImageDraw.Draw(panel).rectangle((x,y,x+rw-1,y+rh-1),fill=node.get('backgroundColor','#294052'));continue
    text=node.get('text','') if widget is None else getattr(widget,'text','')
    if not text:continue
    font=ImageFont.truetype(font_file,int(node.get('font','Regular;20').split(';')[1]))
    tile=Image.new('RGBA',(rw,rh));draw=ImageDraw.Draw(tile)
    lines=text.split('\n');line_height=int(font.size*1.22)
    top=max(0,(rh-len(lines)*line_height)//2)
    for index,line in enumerate(lines):
        length=draw.textlength(line,font=font)
        align=node.get('halign','left')
        left=max(0,rw-length) if align=='right' else max(0,(rw-length)/2) if align=='center' else 0
        draw.text((left,top+index*line_height),line,font=font,fill=node.get('foregroundColor','#E1E7ED'))
    panel.alpha_composite(tile,(x,y))
canvas.alpha_composite(panel,((1920-w)//2,(1080-h)//2))
out=Path('/workspace/local-artifacts/EmbyFlowE2_download_library_preview.png' if '--library' in sys.argv else '/workspace/local-artifacts/EmbyFlowE2_download_counter_preview.png')
canvas.convert('RGB').save(out)
print(out)

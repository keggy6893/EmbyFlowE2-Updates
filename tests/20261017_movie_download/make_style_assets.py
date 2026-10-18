"""Build small embedded UI PNGs. Pillow is needed on the build machine only."""
from pathlib import Path
import base64
import io
from PIL import Image, ImageDraw

assets={}
def save(name,img):
    buf=io.BytesIO();img.save(buf,format='PNG',optimize=True)
    assets[name]=base64.b64encode(buf.getvalue()).decode('ascii')
# The rounded panel is vertically stretched, so use a tall low-contrast gradient.
img=Image.new('RGBA',(1120,800));d=ImageDraw.Draw(img)
d.rounded_rectangle((1,1,1118,798),radius=18,fill='#0B1522',outline='#29465C',width=1)
save('panel',img)
for selected in (False,True):
    img=Image.new('RGBA',(1040,96));d=ImageDraw.Draw(img)
    d.rounded_rectangle((1,1,1038,94),radius=10,fill='#0D202D' if selected else '#0C1A28',outline='#25C6DB' if selected else '#23364A',width=1)
    if selected:
        d.rounded_rectangle((1,7,6,88),radius=2,fill='#26DFF5')
    d.rounded_rectangle((22,21,76,75),radius=9,fill='#102C3C' if selected else '#102333')
    d.line((49,33,49,57),fill='#26DFF5' if selected else '#7B95A8',width=3)
    d.line((40,49,49,58,58,49),fill='#26DFF5' if selected else '#7B95A8',width=3)
    d.line((37,65,61,65),fill='#26DFF5' if selected else '#7B95A8',width=3)
    if selected:
        d.ellipse((985,33,1017,65),outline='#26DFF5',width=2)
        d.line((993,49,999,55,1010,43),fill='#26DFF5',width=3)
    save('selected' if selected else 'normal',img)
    # Generic destination/confirmation cards omit the download icon.
    d.rounded_rectangle((20,18,79,78),radius=5,fill='#0D202D' if selected else '#0C1A28')
    save('selected_plain' if selected else 'normal_plain',img)
img=Image.new('RGBA',(94,26));d=ImageDraw.Draw(img)
d.rounded_rectangle((0,0,93,25),radius=5,fill='#0E2030',outline='#4A667B',width=1)
save('badge',img)
code='''# Embedded UI assets: no Pillow or extra package required on the receiver.
import base64 as _efdl_asset_b64
import os as _efdl_asset_os
import tempfile as _efdl_asset_temp
_EFDL_STYLE_ASSETS = %r
_efdl_style_directory = None
_efdl_style_loaded = {}

def _efdl_style_path(name):
    global _efdl_style_directory
    if _efdl_style_directory is None:
        _efdl_style_directory = _efdl_asset_temp.mkdtemp(prefix='embyflow-download-style-v6-')
    path = _efdl_asset_os.path.join(_efdl_style_directory, name + '.png')
    if not _efdl_asset_os.path.exists(path):
        with open(path, 'xb') as handle:
            handle.write(_efdl_asset_b64.b64decode(_EFDL_STYLE_ASSETS[name], validate=True))
    return path

def _efdl_style_apply(widget, name):
    if widget.instance is None:
        return
    if name not in _efdl_style_loaded:
        _efdl_style_loaded[name] = LoadPixmap(_efdl_style_path(name))
    pix = _efdl_style_loaded[name]
    if pix:
        widget.instance.setPixmap(pix)
        widget.instance.setScale(1)
''' % assets
Path(__file__).with_name('style_assets.py').write_text(code)
print('Created embedded rounded panel/card/badge assets.')

"""Build the marine-blue local folder browser skin and bundled pictures."""
from pathlib import Path
import ast
import base64
import shutil
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def skin():
    parts = ['''<screen name="EmbyFlowLocalMediaScreen" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#0C1827">
    <eLabel position="0,0" size="1920,1080" backgroundColor="#0C1827" />
    <eLabel text="EmbyFlow · Eigene Medien" position="90,42" size="1650,45" font="Regular;30" foregroundColor="#38C7F4" transparent="1" />
    <widget name="title" position="90,104" size="1650,60" font="Bold;44" foregroundColor="#F4F7FB" transparent="1" />
    <widget name="path" position="90,175" size="1650,35" font="Regular;23" foregroundColor="#AEB8C5" transparent="1" />
    <widget name="summary" position="90,216" size="1150,30" font="Regular;20" foregroundColor="#AEB8C5" transparent="1" />''']
    for slot in range(9):
        x, y = 90 + slot % 3 * 395, 250 + slot // 3 * 190
        parts.append('''<widget name="tile_bg%d" position="%d,%d" size="375,170" backgroundColor="#10263F" cornerRadius="12" zPosition="1" />
        <widget name="tile_icon%d" position="%d,%d" size="64,64" alphatest="blend" zPosition="3" />
        <widget name="row%d" position="%d,%d" size="255,78" font="Regular;25" foregroundColor="#F4F7FB" transparent="1" zPosition="3" />
        <widget name="meta%d" position="%d,%d" size="255,32" font="Regular;20" foregroundColor="#69B9FA" transparent="1" zPosition="3" />''' % (
            slot, x, y, slot, x+20, y+25, slot, x+101, y+21, slot, x+101, y+113))
    parts.append('''<widget name="focus_bg" position="90,250" size="375,170" backgroundColor="#173A5E" transparent="0" widgetBorderWidth="3" widgetBorderColor="#2B8CFF" cornerRadius="12" zPosition="2" />
    <eLabel position="1320,250" size="510,550" backgroundColor="#10263F" cornerRadius="12" zPosition="1" />
    <eLabel text="Auswahl" position="1350,276" size="440,38" font="Bold;27" foregroundColor="#F4F7FB" transparent="1" zPosition="3" />
    <widget name="selection_icon" position="1350,335" size="96,96" alphatest="blend" zPosition="3" />
    <widget name="selection_meta" position="1470,365" size="320,70" font="Regular;23" foregroundColor="#69B9FA" transparent="1" zPosition="3" />
    <widget name="selection_name" position="1350,460" size="440,106" font="Bold;28" foregroundColor="#F4F7FB" transparent="1" zPosition="3" />
    <widget name="selection_path" position="1350,585" size="440,170" font="Regular;22" foregroundColor="#AEB8C5" transparent="1" zPosition="3" />
    <widget name="page" position="90,839" size="1140,32" font="Regular;21" foregroundColor="#AEB8C5" transparent="1" />
    <widget name="filter_hint" position="90,885" size="1140,32" font="Regular;21" foregroundColor="#D7BE62" transparent="1" />
    <widget name="status" position="90,931" size="1740,35" font="Regular;21" foregroundColor="#AEB8C5" transparent="1" />
    <eLabel position="0,980" size="1920,100" backgroundColor="#0C1827" />
    <eLabel position="0,979" size="1920,1" backgroundColor="#1689FF" />
    <eLabel text="ROT Zurück" position="90,1008" size="230,35" font="Regular;23" foregroundColor="#F2736D" transparent="1" />
    <eLabel text="GRÜN Öffnen / Abspielen" position="360,1008" size="400,35" font="Regular;23" foregroundColor="#6CCB7A" transparent="1" />
    <eLabel text="GELB Medien / Alle Ordner" position="800,1008" size="420,35" font="Regular;23" foregroundColor="#D7BE62" transparent="1" />
    <eLabel text="BLAU Neu laden" position="1280,1008" size="330,35" font="Regular;23" foregroundColor="#55B8E2" transparent="1" />
    <eLabel text="OK Auswählen" position="1620,1008" size="220,35" font="Regular;23" foregroundColor="#DCE5EE" transparent="1" />
    </screen>''')
    return ''.join(parts)


def build():
    assets = HERE / 'assets'
    assets.mkdir(exist_ok=True)
    image = Image.new('RGBA', (768, 768))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((15, 15, 753, 753), radius=147, fill=(15, 36, 59, 245), outline=(86,181,255,54), width=6)
    d.rounded_rectangle((135, 192, 363, 339), radius=33, fill=(22, 65, 105, 255), outline=(86,181,255,255), width=15)
    d.rounded_rectangle((135, 267, 639, 582), radius=45, fill=(22, 65, 105, 255), outline=(86,181,255,255), width=15)
    image.resize((256, 256), Image.Resampling.LANCZOS).save(assets / 'folder.png', optimize=True)
    shutil.copyfile(HERE.parent / '20261026_source_picons/assets/movies.png', assets / 'video.png')
    runtime = '_ELFG_SKIN=' + repr(skin()) + '\n' + (HERE / 'runtime.py').read_text()
    # Put the skin constant inside the patch markers to preserve idempotence.
    begin = '# EMBYFLOW_LOCAL_FOLDER_GRID_V1_BEGIN\n'
    runtime = begin + runtime.replace(begin, '', 1)
    source = (ROOT / 'tools/install-local-source-picons-20261026.py').read_text()
    tree = ast.parse(source)
    lines = source.splitlines(True)
    values = {'RUNTIME': runtime,
              'ASSETS': {p.name: base64.b64encode(p.read_bytes()).decode() for p in sorted(assets.glob('*.png'))}}
    changes = []
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in values:
            key = n.targets[0].id
            changes.append((n.lineno-1, n.end_lineno, key + '=' + repr(values[key]) + '\n'))
    for start, end, text in sorted(changes, reverse=True):
        lines[start:end] = [text]
    result = ''.join(lines).replace('EMBYFLOW_LOCAL_SOURCE_PICONS_V1', 'EMBYFLOW_LOCAL_FOLDER_GRID_V1')
    result = result.replace("{'EmbyFlowLocalSourcesScreenV16','EmbyFlowLocalSourcesScreenV17'}", "{'EmbyFlowLocalMediaScreen'}")
    result = result.replace('local_source_picons_20261026', 'local_folder_grid_20261026')
    result = result.replace('.vor-local-picons-', '.vor-local-browser-').replace('.local-picons-', '.local-browser-')
    result = result.replace('Picons sind vorhanden. Eigene Medien bitte neu oeffnen. Kein GUI-Neustart.', 'Marineblauer Ordnerbrowser bereits vorhanden. Kein GUI-Neustart.')
    result = result.replace('FERTIG. Quellenkarten und Quellenverwaltung haben lokale Picons.', 'FERTIG. Lokaler Ordnerbrowser in Marineblau mit Kartenansicht.')
    result = result.replace('Install offline source picons for the existing local USB/HDD dashboard only.', 'Restyle only the local folder browser; preserve scanning, root boundaries and playback.')
    compile(result, 'local-browser-installer.py', 'exec')
    (ROOT / 'tools/install-local-folder-grid-20261026.py').write_text(result)


if __name__ == '__main__':
    build()

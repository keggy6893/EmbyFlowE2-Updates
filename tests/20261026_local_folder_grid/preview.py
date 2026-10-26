"""Illustrate the new native skin with explicitly labelled example folders."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
image = Image.new('RGB', (1920, 1080), '#0C1827')
d = ImageDraw.Draw(image)


def text(x, y, value, size=23, color='#F4F7FB'):
    d.multiline_text((x, y), value, font=ImageFont.truetype(FONT, size), fill=color, spacing=8)


text(90, 12, 'Vorschau mit Beispielordnern · kein Receiver-Screenshot', 16, '#8BA7BD')
text(90, 42, 'EmbyFlow · Eigene Medien', 30, '#38C7F4')
text(90, 104, 'USB-Festplatte', 44)
text(90, 175, '/media/usb', 23, '#AEB8C5')
text(90, 216, '6 Ordner · 0 Videos', 20, '#AEB8C5')
folder = Image.open(HERE / 'assets/folder.png')
for slot, name in enumerate(('Filme', 'Serien', 'Aufnahmen', 'Dokumentationen', 'Konzerte', 'Kinder')):
    x, y = 90 + slot % 3 * 395, 250 + slot // 3 * 190
    d.rounded_rectangle((x, y, x+375, y+170), radius=12, fill='#173A5E' if slot == 0 else '#10263F',
                        outline='#2B8CFF' if slot == 0 else '#10263F', width=3)
    picture = folder.resize((64, 64), Image.Resampling.LANCZOS)
    image.paste(picture, (x+20, y+25), picture)
    text(x+101, y+21, name, 25)
    text(x+101, y+113, 'Ordner', 20, '#69B9FA')
d.rounded_rectangle((1320, 250, 1830, 800), radius=12, fill='#10263F')
text(1350, 276, 'Auswahl', 27)
picture = folder.resize((96, 96), Image.Resampling.LANCZOS)
image.paste(picture, (1350, 335), picture)
text(1470, 365, 'Ordner', 23, '#69B9FA')
text(1350, 460, 'Filme', 28)
text(1350, 585, '/media/usb/Filme', 22, '#AEB8C5')
text(90, 839, '1 / 1', 21, '#AEB8C5')
text(90, 885, 'Gelb: Alle Ordner (weitere Ordner einblenden)', 21, '#D7BE62')
text(90, 931, 'OK öffnet den gewählten Ordner. Rot führt zurück.', 21, '#AEB8C5')
d.line((0, 979, 1920, 979), fill='#1689FF', width=1)
for x, label, color in ((90, 'ROT Zurück', '#F2736D'), (360, 'GRÜN Öffnen / Abspielen', '#6CCB7A'),
                         (800, 'GELB Medien / Alle Ordner', '#D7BE62'), (1280, 'BLAU Neu laden', '#55B8E2'),
                         (1620, 'OK Auswählen', '#DCE5EE')):
    text(x, 1008, label, 23, color)
image.save(HERE / 'preview.png')

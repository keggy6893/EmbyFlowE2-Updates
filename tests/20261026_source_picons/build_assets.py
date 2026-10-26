"""Draw original source-category picons; no receiver-side Pillow dependency."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
COLORS = {'movies': '#56B5FF', 'series': '#39D6D2', 'drive': '#B28AFF',
          'recordings': '#FFB66A', 'all': '#B89CFF', 'documentary': '#EFCD71',
          'network': '#69BAF2'}


def icon(kind):
    scale = 3
    image = Image.new('RGBA', (256 * scale, 256 * scale))
    d = ImageDraw.Draw(image)
    rgb = tuple(bytes.fromhex(COLORS[kind][1:]))

    def rect(box, radius=12, fill=None, outline=None, width=5):
        d.rounded_rectangle(tuple(int(v * scale) for v in box), radius * scale,
                            fill=fill, outline=outline, width=width * scale)

    def line(points, color=None, width=5):
        d.line([(int(x * scale), int(y * scale)) for x, y in points],
               fill=color or rgb + (255,), width=width * scale, joint='curve')

    def circle(box, fill=None, outline=None, width=5):
        d.ellipse(tuple(int(v * scale) for v in box), fill=fill,
                  outline=outline, width=width * scale)

    rect((5, 5, 251, 251), 49, fill=(15, 36, 59, 245), outline=rgb + (54,), width=2)
    for r in range(97, 12, -2):
        a = int(2 + 7 * (1 - r / 100))
        circle((128-r, 116-r, 128+r, 116+r), fill=rgb + (a,))
    # Keep a transparent surround and a consistent central symbol footprint.
    if kind == 'movies':
        rect((56, 54, 200, 202), 14, fill=(19, 48, 76, 245), outline=rgb + (255,))
        line([(83, 57), (83, 199)], width=3)
        line([(173, 57), (173, 199)], width=3)
        for y in (72, 104, 136, 168):
            rect((65, y, 74, y + 15), 2, fill=rgb + (210,))
            rect((182, y, 191, y + 15), 2, fill=rgb + (210,))
        d.polygon([(109*scale, 101*scale), (151*scale, 128*scale),
                   (109*scale, 155*scale)], fill=rgb + (255,))
    elif kind == 'series':
        rect((44, 53, 192, 156), 14, fill=(16, 48, 61, 245), outline=rgb + (115,), width=4)
        rect((60, 73, 211, 177), 14, fill=(15, 45, 57, 255), outline=rgb + (255,))
        d.polygon([(122*scale, 101*scale), (156*scale, 124*scale),
                   (122*scale, 147*scale)], fill=rgb + (255,))
        line([(115, 178), (115, 196), (157, 196), (157, 178)], width=5)
        line([(99, 199), (173, 199)], width=5)
    elif kind in ('drive', 'network'):
        rect((57, 49, 199, 205), 18, fill=(30, 36, 66, 250), outline=rgb + (255,))
        line([(60, 157), (196, 157)], color=rgb + (180,), width=4)
        circle((164, 173, 178, 187), fill=(94, 224, 161, 255), width=1)
        for y in (174, 183):
            line([(78, y), (128, y)], color=rgb + (155,), width=3)
        if kind == 'drive':
            circle((91, 70, 165, 144), fill=rgb + (20,), outline=rgb + (180,), width=4)
            circle((120, 99, 136, 115), fill=rgb + (255,))
            line([(129, 107), (164, 136)], width=5)
        else:
            for y in (77, 107, 137):
                line([(78, y), (163, y)], width=4)
                circle((174, y-3, 180, y+3), fill=rgb + (255,), width=1)
    elif kind == 'recordings':
        circle((65, 46, 191, 172), fill=(48, 36, 35, 250), outline=rgb + (255,), width=6)
        circle((100, 81, 156, 137), fill=(255, 113, 103, 255), width=1)
        line([(88, 189), (168, 189)], width=5)
        line([(106, 204), (150, 204)], color=rgb + (150,), width=4)
    elif kind == 'all':
        for x in (63, 140):
            for y in (58, 135):
                rect((x, y, x+54, y+54), 12, fill=rgb + (42,), outline=rgb + (255,), width=4)
    else:
        rect((75, 43, 184, 210), 12, fill=(39, 41, 41, 250), outline=rgb + (255,))
        for y, end in ((86, 159), (112, 159), (138, 146), (164, 159)):
            line([(98, y), (end, y)], color=rgb + (210,), width=4)
    return image.resize((256, 256), Image.Resampling.LANCZOS)


def build():
    assets = HERE / 'assets'
    assets.mkdir(exist_ok=True)
    for kind in COLORS:
        icon(kind).save(assets / (kind + '.png'), optimize=True)
    # Original component preview, not a capture from a receiver.
    image = Image.new('RGB', (1180, 410), '#0C1827')
    d = ImageDraw.Draw(image)
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    title = ImageFont.truetype(font, 21)
    small = ImageFont.truetype(font, 14)
    d.text((35, 15), 'Eigene Medien · Quellenkarten mit Picons (Vorschau)', fill='#DDE7EF', font=title)
    cards = [('movies', 'Meine Filme', 'Filme', '/media/usb/Filme'),
             ('series', 'Meine Serien', 'Serien', '/media/usb/Serien'),
             ('drive', 'USB-Festplatte', 'Gemischt', '/media/usb'),
             ('recordings', 'Aufnahmen', 'Aufnahmen', '/media/hdd/movie'),
             ('all', 'Alle Medien', 'Übersicht', '4 Quellen')]
    for i, (kind, name, label, path) in enumerate(cards):
        x, y = 35 + i * 224, 72
        d.rounded_rectangle((x, y, x + 200, y + 302), 12,
                            fill='#12355C' if i == 0 else '#0D2138')
        picon = Image.open(assets / (kind + '.png')).resize((112, 112), Image.Resampling.LANCZOS)
        image.paste(picon, (x+44, y+24), picon)
        d.text((x+14, y+159), name, font=title, fill='#F4F7FB')
        d.text((x+14, y+201), label, font=small, fill='#AEB8C5' if kind == 'recordings' else COLORS[kind])
        d.text((x+14, y+241), path, font=small, fill='#AEB8C5')
        d.text((x+14, y+273), 'Bereit' if kind == 'all' else 'Online', font=small, fill='#53D769')
        if i == 0:
            d.rectangle((x, y, x+199, y+301), outline='#2B8CFF', width=3)
    image.save(HERE / 'preview.png')


if __name__ == '__main__':
    build()

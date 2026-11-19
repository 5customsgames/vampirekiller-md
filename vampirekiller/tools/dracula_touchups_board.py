#!/usr/bin/env python3
"""Boards "current / proposal A / proposal B" of the Dracula 16-bit touch-ups (research/dracula-touchups.md).

usage: dracula_touchups_board.py <castlevania-md> <background.png> <out-dir> [board ...]
  background.png: a 256 x 224 capture of the Dracula room without Dracula (the figures are laid over it at the in-game place)
  boards: head cape sickle bat all fade face (default: all of them)
Each picture is drawn from the tiles the generator would write (quantised to the variant palette), at x5.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dracula16 as D  # noqa: E402
import build_enemies16 as E  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

S = 5
FONT = ImageFont.load_default(size=15)
SMALL = ImageFont.load_default(size=12)


def colours(pal):
    return [(0, 0, 0)] + [tuple(v * 36 for v in E.lvl(pal[i])) for i in range(1, 16)]


class Art:
    """One variant: the cells, the busts, the palette, as the generator would write them."""

    def __init__(self, root, variants):
        self.variants = variants
        (self.pics, self.boxes, self.pal, self.err, self.tiles, self.unique, self.index) = D.make(root, variants)
        self.col = colours(self.pal)

    def cell(self, c):
        return D.cell_rows(self.tiles, c)

    def bust(self, code_set):
        img = [[0] * 32 for _ in range(32)]
        for t in range(16):
            for y in range(8):
                w = self.unique[self.index[code_set * 16 + t]][y]
                for x in range(8):
                    img[(t % 4) * 8 + y][(t // 4) * 8 + x] = (w >> (28 - 4 * x)) & 15
        return img

    def figure(self, state):
        """40 x 64 rows of indices of the standing Dracula. state: L closed left, LO opened left, R closed right, RO opened right."""
        rows = [[0] * 40 for _ in range(64)]

        def blit(img, x0, y0):
            for y, r in enumerate(img):
                for x, v in enumerate(r):
                    if v and 0 <= y0 + y < 64 and 0 <= x0 + x < 40:
                        rows[y0 + y][x0 + x] = v
        head, hood, cape, bust, dx = {'L': (0, 2, (3, 4), 1, 0), 'LO': (5, 2, (3, 4), 5, 0),
                                      'R': (1, 6, (7, 8), 3, 1), 'RO': (9, 6, (7, 8), 13, 1)}[state]
        blit(self.bust(bust), 4 + dx, 16)
        blit(self.cell(cape[0]), 4 + dx, 48)
        blit(self.cell(cape[1]), 20 + dx, 48)
        blit(self.cell(head), 12 + dx, 0)
        blit(self.cell(hood), 12 + dx, 0)                 # listed first in the sprite chain: drawn over the head
        return rows

    def cell_image(self, rows):
        return rows


def paint(base, rows, colour, x0, y0, zoom):
    """rows of indices over `base` (a PIL image at x zoom) at pixel (x0, y0)."""
    for y, r in enumerate(rows):
        for x, v in enumerate(r):
            if v and 0 <= (x0 + x) * zoom < base.size[0] - zoom + 1 and 0 <= (y0 + y) * zoom < base.size[1] - zoom + 1:
                for a in range(zoom):
                    for b in range(zoom):
                        base.putpixel(((x0 + x) * zoom + a, (y0 + y) * zoom + b), colour[v])


def backdrop(bg, box, zoom):
    return bg.crop(box).resize(((box[2] - box[0]) * zoom, (box[3] - box[1]) * zoom), Image.NEAREST)


def labelled(sheet, text, x, y, font=FONT, fill=(255, 235, 90)):
    d = ImageDraw.Draw(sheet)
    d.text((x + 1, y + 1), text, fill=(0, 0, 0), font=font)
    d.text((x, y), text, fill=fill, font=font)


def board(path, title, rows, cols, make_panel, panel_size, notes=None):
    """rows: [(label, Art)], cols: [label]; make_panel(art, col) -> PIL image."""
    pw, ph = panel_size
    head, side = 44, 128
    sheet = Image.new('RGB', (side + pw * len(cols) + 8, head + (ph + 8) * len(rows) + (24 if notes else 0)), (28, 30, 38))
    labelled(sheet, title, 8, 6, FONT, (255, 255, 255))
    for j, c in enumerate(cols):
        labelled(sheet, c, side + j * pw + 6, 26, SMALL, (190, 220, 255))
    for i, (label, art) in enumerate(rows):
        y = head + i * (ph + 8)
        for j, c in enumerate(cols):
            sheet.paste(make_panel(art, c), (side + j * pw, y))
        for k, line in enumerate(label.split('\n')):
            labelled(sheet, line, 6, y + 6 + k * 18, FONT if k == 0 else SMALL, (255, 235, 90) if k == 0 else (210, 210, 210))
        if getattr(art, 'err', None) is not None:
            labelled(sheet, 'err %.1f' % art.err, 6, y + ph - 20, SMALL, (150, 150, 150))
    if notes:
        labelled(sheet, notes, 8, sheet.size[1] - 20, SMALL, (200, 200, 200))
    sheet.save(path)


LEVELS = (0, 32, 65, 98, 139, 172, 205, 238)          # capture value of a 3-bit level


def lv_of(rgb):
    return tuple(min(range(8), key=lambda i: abs(LEVELS[i] - v)) for v in rgb)


FACE = {   # new levels of the skin ramp of the background palette (the same 3-bit levels as the MSX bytes of vk_dracula_initial_palette)
    'a': {(2, 1, 1): (1, 1, 2), (4, 2, 2): (3, 2, 3), (5, 3, 3): (4, 3, 4), (6, 4, 4): (5, 4, 5), (6, 5, 5): (6, 5, 6),
          (7, 5, 4): (7, 6, 6), (7, 5, 5): (7, 7, 6)},
    'b': {(2, 1, 1): (1, 0, 0), (4, 2, 2): (3, 1, 1), (5, 3, 3): (4, 2, 1), (6, 4, 4): (5, 3, 2), (6, 5, 5): (6, 4, 3),
          (7, 5, 4): (7, 5, 3), (7, 5, 5): (7, 6, 4), (6, 2, 3): (5, 1, 1)},
}


def recolour(im, table):
    out = im.copy()
    px = out.load()
    for y in range(out.size[1]):
        for x in range(out.size[0]):
            lv = lv_of(px[x, y])
            if lv in table:
                px[x, y] = tuple(LEVELS[i] for i in table[lv])
    return out


def pulse_panel(base, phase, zoom=6):
    """The head of the standing figure with its violet entries (6) in the phase of the MSX pulse (0..9 .. 0)."""
    a = Art.__new__(Art)
    a.__dict__.update(base.__dict__)
    a.col = list(base.col)
    t = phase / 9.0
    a.col[6] = tuple(int(LEVELS[v] ) for v in (round(3 + 4 * t), round(1 + 4 * t), round(4 + 3 * t)))
    return a


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    root, bgpath, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    which = sys.argv[4:] or ['head', 'cape', 'sickle', 'bat', 'all', 'fade', 'face']
    out.mkdir(parents=True, exist_ok=True)
    bg = Image.open(bgpath).convert('RGB')
    cache = {}

    def art(*v):
        key = ','.join(v)
        if key not in cache:
            cache[key] = Art(root, tuple(x for x in v if x))
        return cache[key]
    base = art()
    box = (160, 122, 222, 198)                        # screen crop around the figure (62 x 76)

    def fig_panel(a, state):
        im = backdrop(bg, box, S)
        paint(im, a.figure(state), a.col, 170 - box[0], 129 - box[1], S)
        return im
    states = ['L', 'LO', 'R', 'RO']
    names = ['closed, facing left (poses 91 / 92)', 'open, facing left', 'closed, facing right (93 / 94)', 'open, facing right']
    size = ((box[2] - box[0]) * S, (box[3] - box[1]) * S)
    if 'head' in which:
        board(out / 'planche_1_5_tete_capuche.png', '1 (the head floats) and 5 (empty hood): 1A / 1B',
              [('current\n(base)', base), ('1A / 5A\nhigh collar\n+ neck', art('head-a')), ('1B / 5B\nred hood with\ngold edge', art('head-b'))],
              names, lambda a, c: fig_panel(a, states[names.index(c)]), size)
    if 'cape' in which:
        board(out / 'planche_2_cape.png', '2 (cape in blocks)',
              [('current\n(base)', base), ('2A\npleats, same\nsilhouette', art('cape-a')), ('2B\nflared cape,\nwavy hem', art('cape-b'))],
              names, lambda a, c: fig_panel(a, states[names.index(c)]), size)
    if 'all' in which:
        board(out / 'planche_ensemble.png', 'Whole figure: current / all A / all B / recommended set (1B + 2B + 3A + 6B)',
              [('current', base), ('all A\n(1A 2A 3A 6A)', art('head-a', 'cape-a', 'bat-a', 'sickle-a')),
               ('all B\n(1B 2B 3B 6B)', art('head-b', 'cape-b', 'bat-b', 'sickle-b')),
               ('recommended\n1B 2B 3A/7A 6B', art('head-b', 'cape-b', 'bat-b', 'sickle-a'))],
              names, lambda a, c: fig_panel(a, states[names.index(c)]), size)
    zoom = 8
    if 'sickle' in which:
        cols = ['pose %d (cell %d)' % (27 + i, 18 + i) for i in range(6)]

        def sp(a, c):
            i = cols.index(c)
            im = backdrop(bg, (112, 100, 128, 116), zoom)
            paint(im, a.cell(18 + i), a.col, 0, 0, zoom)
            return im
        board(out / 'planche_3_7_faucilles.png', '3 (red, angular sickles) and 7 (4 images for 6 poses)',
              [('current\n(4 images\nrepeated)', base), ('3A / 7A\nsteel, six\nturns', art('sickle-a')), ('3B / 7B\ncrimson, six\nturns', art('sickle-b'))],
              cols, sp, (16 * zoom, 16 * zoom))
    if 'bat' in which:
        cols = ['pose 2 (cell 14)', 'pose 165 (15)', 'pose 166 (16)', 'pose 167 (17)']

        def bp(a, c):
            i = cols.index(c)
            im = backdrop(bg, (112, 100, 128, 116), zoom)
            paint(im, a.cell(14 + i), a.col, 0, 0, zoom)
            return im
        board(out / 'planche_6_chauves_souris.png', '6 (3 bat images for 4 poses)',
              [('current\n(15 = 17)', base), ('6A\n17 = 14 with\nwings raised', art('bat-a')), ('6B\nfour redrawn\nphases', art('bat-b'))],
              cols, bp, (16 * zoom, 16 * zoom))

    if 'fade' in which:
        a = art('head-a')
        phases = [0, 2, 4, 6, 8, 9]
        cols = ['phase %d / 9' % k for k in phases]
        hbox = (164, 126, 204, 156)

        def pp(mode, c):
            pa = pulse_panel(a, phases[cols.index(c)]) if mode == 'pulse' else a
            im = backdrop(bg, hbox, 8)
            paint(im, pa.figure('L')[:30], pa.col, 170 - hbox[0], 129 - hbox[1], 8)
            return im
        board(out / 'planche_4_palette.png', '4 (fixed palette): 4A = pulse of the violet of the head (PAL2 entry 6), one CRAM word per frame',
              [('current\n(fixed colour)', 'fixed'), ('4A\nviolet pulse', 'pulse')], cols, pp, (40 * 8, 30 * 8))
    if 'face' in which:
        fbox = (56, 36, 200, 184)

        def fp(a, c):
            im = bg.crop(fbox)
            if a is not None:
                im = recolour(im, FACE[a])
            return im.resize((im.size[0] * 3, im.size[1] * 3), Image.NEAREST)
        board(out / 'planche_8_visage.png', '8 (background face): palette re-grade only (zero tiles, zero runtime cost)',
              [('current', None), ('8A\nashen, cold\nskin ramp', 'a'), ('8B\ntorch-lit,\nwarm ramp', 'b')],
              ['room view 0 (Dracula entering)'], lambda a, c: fp(a, c), ((fbox[2] - fbox[0]) * 3, (fbox[3] - fbox[1]) * 3))


if __name__ == '__main__':
    main()

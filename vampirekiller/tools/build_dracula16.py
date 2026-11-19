#!/usr/bin/env python3
"""Dracula (stage 18, room 9) in the 16-bit art (research/gfx16.md, section "Dracula 16 bits").

usage: build_dracula16.py <castlevania-md checkout> [--preview FILE.png] [--variant none|NAME[,NAME]] [--out-dir DIR]\n(default: the retained touch-ups of dracula_touchups.RETAINED)

Writes sgdk/src/generated/dracula16_md.c/.h: vk_dracula16_tiles, the SAME layout as vk_dracula_tiles (dracula_md.h: 24 cells of
4 tiles, 96 tiles, in the order of the poses of dracula_poses.h), and vk_dracula16_palette, the fixed PAL2 the sprites use in
16-bit mode. The code (poses, cells, boxes, SAT) is the MSX one: only the picture of each cell changes. The VRAM tiles are loaded
by vk_dracula_view_begin in the same place with the same single transfer.

Pictures (Castlevania-MD, src/block7.c and level.c), each one laid on the MSX box of its cell (build_enemies16.place):
  head cells (poses 86 to 89, the head of 91 to 94)   b7_drac_head (profile of the head, 8 x 16), mirrored for the right-facing poses
  hood cells (first cell of 91 / 92 and 93 / 94)      left empty (the head picture covers the hood)
  cape cells (second row of 91 to 94, 32 x 16)        the lower 16 rows of b7_drac (the cloak), centred
  debris (pose 90)                                    b7_drac_bit (the flesh the body bursts into)
  ball (type 5)                                       red sphere (build_items16.sphere, the style of obj_47)
  flames (types 12 and 30, patterns F4 and F8)        the 16-bit death flames (vk_item16_death_flame_tiles), recoloured
  bats (type 44, poses 2, 165 to 167)                 obj_42, obj_43, obj_41 (the bat of block 1, as build_enemies16)
  sickles (type 44, poses 27 to 32)                   b7_sickle0 .. 3

Palette: one palette for all the cells (entries 1 to 15 chosen from the colours of the pictures, greedy choice + swaps, weighted
error). PAL2 is not the MSX palette of the room in 16-bit mode (the cells no longer fade with it).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_enemies16 as E  # noqa: E402
import build_items16 as I  # noqa: E402

GEN = E.GEN
CELLS = 24
FIXED = (8, 14)


def words_of(path, name):
    text = path.read_text()
    m = re.search(r'%s\[\d+\]\s*=\s*\{(.*?)\};' % name, text, re.S)
    return [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{1,8})', m.group(1))]


def cell_rows(words, c):
    """MSX cell c (4 tiles UL, LL, UR, LR) -> 16 x 16 indices."""
    out = [[0] * 16 for _ in range(16)]
    for t in range(4):
        cx, cy = (t // 2) * 8, (t % 2) * 8
        for y in range(8):
            row = words[(c * 4 + t) * 8 + y]
            for x in range(8):
                out[cy + y][cx + x] = (row >> (28 - 4 * x)) & 15
    return out


class B7:
    """Sprites of Castlevania-MD block7.c as rows of (r, g, b) levels or None."""

    def __init__(self, root):
        self.text = (Path(root) / 'src/block7.c').read_text()
        self.tiles = E.nums(self.text, 'block7_tiles')
        self.pal = [E.lvl(w) for w in E.nums(self.text, 'block7_palette')]

    def pose(self, name):
        m = re.search(r'static const SimonSprite %s\[\d+\] = \{(.*?)\};' % name, self.text, re.S)
        ents = [tuple(int(v, 0) for v in e.split(',')) for e in re.findall(r'\{([^{}]+)\}', m.group(1))]
        x0 = min(e[0] for e in ents)
        y0 = min(e[1] for e in ents)
        w = max(e[0] for e in ents) + 8 - x0
        h = max(e[1] for e in ents) + 16 - y0
        img = [[None] * w for _ in range(h)]
        for dx, dy, attr, tile in ents:
            line, hf, vf = (attr >> 13) & 3, attr & 0x800, attr & 0x1000
            for part in (0, 1):
                for y in range(8):
                    row = self.tiles[(tile + (1 - part if vf else part)) * 8 + (7 - y if vf else y)]
                    for x in range(8):
                        v = (row >> (28 - 4 * x)) & 15
                        if v:
                            img[dy - y0 + part * 8 + y][dx - x0 + (7 - x if hf else x)] = self.pal[line * 16 + v]
        return img


def indices_to_levels(rows, pal):
    return [[None if v == 0 else pal[v] for v in r] for r in rows]


def build(root):
    b7 = B7(root)
    cv = E.CV(root)
    msx = words_of(GEN / 'dracula_md.c', 'vk_dracula_tiles')
    assert len(msx) == CELLS * 32
    boxes = [E.ref_box(cell_rows(msx, c)) for c in range(CELLS)]
    flame_pal = [None] + [E.lvl(w) for w in words_of(GEN / 'items16_md.c', 'vk_item16_palette')][1:]
    flame_words = words_of(GEN / 'items16_md.c', 'vk_item16_death_flame_tiles')
    pics = {}                                   # cell -> 16 x 16 rows of levels / None

    def put(c, img, mode='centre', crop=True):
        if crop:
            img = E.crop(img)
        pics[c] = E.place(img, 16, 16, boxes[c], mode)

    head = E.crop(b7.pose('b7_drac_head'))
    # head pictures: A (pose 86, 91), its mirror (88, 93), the variant V (87, 92) and its mirror (89, 94)
    # (standing on the collar: its lowest row on the last row of the cell, where the bust starts, instead of two rows above as the MSX hood fills it)
    for c, m in ((0, False), (1, True), (5, False), (9, True)):
        x0, y0, x1, _ = boxes[c]
        pics[c] = E.place(E.mirror(head) if m else head, 16, 16, (x0, y0, x1, 16), 'feet')
    # hood cells: empty
    pics[2] = pics[6] = [[None] * 16 for _ in range(16)]
    # cape: lower 16 rows of the closed cloak (24 wide), centred on the 32 x 16 cape of the MSX pose (two cells side by side);
    # the cells of the mirrored poses (7, 8) are the mirror image (the cloak is symmetrical: the same picture shifted by one pixel)
    cloak = b7.pose('b7_drac')
    cape = [r + [None] * 8 for r in cloak[32:48]]
    for left, right, mir in ((3, 4, False), (7, 8, True)):
        canvas = [[None] * 4 + row[:24] + [None] * 4 for row in cape]
        if mir:
            canvas = E.mirror(canvas)
        for c, off in ((left, 0), (right, 16)):
            pics[c] = [row[off:off + 16] for row in canvas]
    # bust (the 32 x 32 sprite between the head and the cape, four layers: 1 = closed cloak facing left, 2 = the opened cloak over
    # it, 3 and 4 = the mirror images): the first 24 columns of rows 0 to 31 of b7_drac and b7_drac_open; layer 2 keeps only
    # the pixels where the open cloak differs from the closed one
    opened = b7.pose('b7_drac_open')
    closed = [row[:24] for row in cloak[:32]]
    over = [[(o if o is not None and o != c else None) for o, c in zip(orow[:24], crow)] for orow, crow in zip(opened[:32], closed)]
    canvas = lambda rows: [[None] * 4 + r + [None] * 4 for r in rows]
    bust = {1: canvas(closed), 2: canvas(over)}
    bust[3], bust[4] = E.mirror(bust[1]), E.mirror(bust[2])
    pics['bust'] = bust
    # debris
    put(10, b7.pose('b7_drac_bit'))
    # ball
    ball = I.sphere([(2, 0, 0), (4, 0, 0), (5, 1, 1), (5, 1, 1), (7, 5, 4)])
    pics[11] = E.place(ball, 16, 16, boxes[11], 'centre')
    # flames
    for c, k in ((12, 0), (13, 1)):
        rows = cell_rows(flame_words, k)
        pics[c] = indices_to_levels(rows, flame_pal)
    # bats: poses 2, 165, 166, 167 (cells 14 to 17): folded then the three wing positions
    for c, obj in ((14, 42), (15, 43), (16, 41), (17, 43)):
        put(c, cv.pose(obj))
    # sickles: poses 27 to 32 (cells 18 to 23)
    for i, c in enumerate(range(18, 24)):
        put(c, b7.pose('b7_sickle%d' % (i % 4)), crop=False)
    return pics, boxes


def palette_of(pics, boost=None):
    """boost: {cell: weight} makes the colours of a small picture count more in the choice (the touch-up variants keep the red ball's pink highlight)."""
    colours = {}
    imgs = [(v, (boost or {}).get(k, 1)) for k, v in pics.items() if k != 'bust'] + [(v, 1) for v in pics['bust'].values()]
    for img, weight in imgs:
        for row in img:
            for p in row:
                if p is not None:
                    colours[p] = colours.get(p, 0) + weight
    # entries 8 and 14 keep the MSX colours of the room (red 020E, white 0EEE at the start): Simon's one-colour silhouette
    # (items, death) reads them from PAL2 (actors.c load_simon_color) whatever the room
    initial = [int(x) for x in re.findall(r'\d+', re.search(r'vk_dracula_initial_palette\[32\]=\{(.*?)\};',
               (GEN / 'dracula_background.c').read_text(), re.S).group(1))]
    pal = [0] * 16
    for i in FIXED:
        rb, g = initial[2 * i], initial[2 * i + 1]
        pal[i] = ((rb & 7) * 2 << 8) | ((g & 7) * 2 << 4) | ((rb >> 4 & 7) * 2)
    saved, E.FREE = E.FREE, tuple(i for i in range(1, 16) if i not in FIXED)    # choose_free reads the module's FREE: put it back
    try:
        free, err = E.choose_free(colours, [E.lvl(pal[i]) for i in FIXED])
        for i, c in zip(E.FREE, free):
            pal[i] = E.word(c)
    finally:
        E.FREE = saved
    return pal, err


def tiles_of(pics, pal):
    out = []
    for c in range(CELLS):
        img = pics[c]
        rows = [[0 if p is None else E.to_index(pal, p) for p in r] for r in img]
        out += E.cell_tiles(rows)
    return out


def bust_of(pics, pal):
    """The 65 composites of dracula_view.c (the order of build_dracula_background.py: every ordered subset of the layers 1 to 4, the
    layers applied in that order, the opaque pixels of a layer replacing those below) as 16 tiles each, column by column, stored
    as the unique tiles and the 16 indexes of every composite."""
    import itertools
    layers = {k: [[0 if p is None else E.to_index(pal, p) for p in r] for r in img] for k, img in pics['bust'].items()}
    unique, unique_of, index = [], {}, []
    for k in range(5):
        for perm in itertools.permutations((1, 2, 3, 4), k):
            rows = [[0] * 32 for _ in range(32)]
            for layer in perm:
                for y in range(32):
                    for x in range(32):
                        if layers[layer][y][x]:
                            rows[y][x] = layers[layer][y][x]
            for c in range(4):
                for r in range(4):
                    tile = tuple(sum(rows[r * 8 + y][c * 8 + x] << (28 - 4 * x) for x in range(8)) for y in range(8))
                    if tile not in unique_of:
                        unique_of[tile] = len(unique)
                        unique.append(tile)
                    index.append(unique_of[tile])
    return unique, index


def fmt(vals, width):
    f = '0x%%0%dX' % width
    return '\n'.join('    ' + ','.join(f % v for v in vals[i:i + 8]) + ',' for i in range(0, len(vals), 8))


def face_of(variants):
    import dracula_touchups as T
    init = [int(x) for x in re.findall(r'\d+', re.search(r'vk_dracula_initial_palette\[32\]=\{(.*?)\};',
            (GEN / 'dracula_background.c').read_text(), re.S).group(1))]
    return T.face_palette(T.FACE_STYLE, init)


def write(tiles, pal, unique, index, out=GEN, face=None):
    (out / 'dracula16_md.h').write_text('\n'.join([
        '/* Generated by tools/build_dracula16.py (Castlevania-MD art, research/gfx16.md). Same layout as vk_dracula_tiles',
        ' * (dracula_md.h): loaded in its place by dracula_view.c in 16-bit mode. */',
        '#ifndef VK_DRACULA16_MD_H', '#define VK_DRACULA16_MD_H', '#include <genesis.h>',
        'extern const u16 vk_dracula16_palette[16];   /* PAL2 of the Dracula sprites in 16-bit mode */',
        'extern const u32 vk_dracula16_tiles[%d];   /* as vk_dracula_tiles */' % len(tiles),
        '#define VK_DRACULA16_BUST_UNIQUE %d' % len(unique),
        'extern const u32 vk_dracula16_bust_unique[VK_DRACULA16_BUST_UNIQUE][8];   /* as vk_dracula_bust_unique */',
        'extern const u8 vk_dracula16_bust_index[65][16];   /* as vk_dracula_bust_index */',
        'extern const u16 vk_dracula16_face_palette[16];   /* PAL0 of the room at the start of the fight, warm skin ramp (touch-up 8B) */',
        'extern const u8 vk_dracula16_face_initial[32];   /* the same in the MSX bytes of vk_dracula_initial_palette (the fade and the pulse work on them) */',
        '#endif', '']))
    (out / 'dracula16_md.c').write_text('\n'.join([
        '/* Generated by tools/build_dracula16.py. */', '#include "dracula16_md.h"',
        'const u16 vk_dracula16_palette[16] = {\n%s\n};' % fmt(pal, 4),
        'const u32 vk_dracula16_tiles[%d] = {\n%s\n};' % (len(tiles), fmt(tiles, 8)),
        'const u32 vk_dracula16_bust_unique[VK_DRACULA16_BUST_UNIQUE][8] = {\n%s\n};' % '\n'.join(
            '    {' + ','.join('0x%08X' % w for w in t) + '},' for t in unique),
        'const u8 vk_dracula16_bust_index[65][16] = {\n%s\n};' % '\n'.join(
            '    {' + ','.join(str(v) for v in index[i * 16:(i + 1) * 16]) + '},' for i in range(65)),
        'const u16 vk_dracula16_face_palette[16] = {\n%s\n};' % fmt(face[1], 4),
        'const u8 vk_dracula16_face_initial[32] = {\n%s\n};' % fmt(face[0], 2), '']))


def figure(tiles, unique, index, bust_set, pose_cells):
    """The figure of a pose (head and cape cells at their MSX offsets, bust in the middle) as rows of indices, 40 x 64."""
    rows = [[0] * 40 for _ in range(64)]

    def blit(img, x0, y0):
        for y, r in enumerate(img):
            for x, v in enumerate(r):
                if v:
                    rows[y0 + y][x0 + x] = v
    for c, x0, y0 in pose_cells:
        blit(cell_rows(tiles, c), x0, y0)
    if bust_set is not None:
        img = [[0] * 32 for _ in range(32)]
        for t in range(16):
            for y in range(8):
                w = unique[index[bust_set * 16 + t]][y]
                for x in range(8):
                    img[(t % 4) * 8 + y][(t // 4) * 8 + x] = (w >> (28 - 4 * x)) & 15
        blit(img, 4, 16)
    return rows


def preview(pics, tiles, pal, path, unique, index):
    from PIL import Image
    S = 5
    mp = [(0, 0, 0)] + [tuple(v * 36 for v in E.lvl(pal[i])) for i in range(1, 16)]
    msx = words_of(GEN / 'dracula_md.c', 'vk_dracula_tiles')
    pm = [(0, 0, 0), (200, 40, 40), (40, 200, 40), (60, 60, 230), (230, 230, 40), (230, 40, 230), (40, 230, 230), (150, 150, 150),
          (240, 140, 0), (140, 0, 240), (0, 140, 240), (250, 250, 250), (200, 120, 120), (120, 200, 120), (120, 120, 200), (70, 70, 70)]
    im = Image.new('RGB', (12 * 17 * S, (2 * 2 * 17 + 70) * S), (60, 70, 90))
    figs = [(1, [(0, 12, 0), (3, 4, 48), (4, 20, 48)]), (5, [(5, 12, 0), (3, 4, 48), (4, 20, 48)]),
            (3, [(1, 12, 0), (7, 4, 48), (8, 20, 48)]), (13, [(9, 12, 0), (7, 4, 48), (8, 20, 48)])]
    for i, (bs, cells) in enumerate(figs):
        fr = figure(tiles, unique, index, bs, cells)
        for y in range(64):
            for x in range(40):
                v = fr[y][x]
                if v:
                    for a in range(S):
                        for b in range(S):
                            im.putpixel(((i * 44 + x) * S + a, (68 + y) * S + b), mp[v])
    for c in range(CELLS):
        for row, (words, colors) in enumerate(((msx, pm), (tiles, mp))):
            rows = cell_rows(words, c)
            ox, oy = (c % 12) * 17 * S, ((c // 12) * 2 + row) * 17 * S
            for y in range(16):
                for x in range(16):
                    v = rows[y][x]
                    if v:
                        for a in range(S):
                            for b in range(S):
                                im.putpixel((ox + x * S + a, oy + y * S + b), colors[v])
    im.save(path)


def make(root, variants=None):
    """Everything the generator computes, without writing: pictures (after the touch-ups of `variants`), palette, tiles, busts."""
    import dracula_touchups as T0
    variants = T0.RETAINED if variants is None else tuple(variants)
    pics, boxes = build(root)
    if variants == ('none',):                    # the art of Castlevania-MD as it was before the touch-ups
        variants = ()
    if variants:
        import dracula_touchups as T
        T.apply(pics, boxes, variants, E)
    pal, err = palette_of(pics, {11: 10} if variants else None)
    tiles = tiles_of(pics, pal)
    unique, index = bust_of(pics, pal)
    assert len(unique) <= 256 and len(index) == 65 * 16
    return pics, boxes, pal, err, tiles, unique, index


def main():
    args = sys.argv[1:]
    opt = {}
    for k in ('--preview', '--variant', '--out-dir'):
        if k in args:
            i = args.index(k)
            opt[k] = args[i + 1]
            del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    variants = tuple(v for v in opt['--variant'].split(',') if v) if '--variant' in opt else None
    out = Path(opt['--out-dir']) if '--out-dir' in opt else GEN
    pics, boxes, pal, err, tiles, unique, index = make(args[0], variants)
    out.mkdir(parents=True, exist_ok=True)
    write(tiles, pal, unique, index, out, face_of(variants))
    print('%d unique bust tiles' % len(unique))
    print('%d tiles = %d B, palette %s, colour error %.1f/255' % (len(tiles) // 8, len(tiles) * 4, ' '.join('%03X' % w for w in pal), err))
    if '--preview' in opt:
        preview(pics, tiles, pal, opt['--preview'], unique, index)


if __name__ == '__main__':
    main()

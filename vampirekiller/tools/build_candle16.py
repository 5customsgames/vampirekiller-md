#!/usr/bin/env python3
"""Candle blobs (objects 1A and 1C) and courtyard torch flames in the 16-bit art (research/gfx16.md, section "Bougies et
torches 16 bits").

usage: build_candle16.py <castlevania-md checkout> [--preview FILE.png]

Writes sgdk/src/generated/candle16_md.c/.h: tile arrays of the SAME layout as the MSX arrays, so the code, the sprite
tables, the hit boxes, the VRAM cells and the number of tiles and transfers stay those of the MSX port (only the picture
of the cells changes, no cost per frame):

- vk_candle16_blob_c_tiles[64] / vk_candle16_blob_a_tiles[64]: object 1C (stages 7 to 9, white) and object 1A (stages 4 to
  6, blue) of the candles and blocks of object 15: two cells of four tiles (UL, LL, UR, LR), odd pose then even pose, as
  vk_ghost_tiles[n] / vk_ghost_a_tiles (ghost_md.c, ghost_a_md.c). Castlevania-MD has no such creature (its b3_ghost
  flies), so the blob is drawn by hand on the MSX silhouette (outline kept, body shaded as a gel sphere lit from the
  upper left, 2 x 2 ordered dither between the levels). They are drawn with PAL2 like the MSX blob (bank 1 of the sprite
  list) and read ONLY the entries that every PAL2 of the rooms where the blob appears holds with the same colour:
  1C 2 (222), 12 (AAA), 13 (444 in the stages 7 to 9) and 14 (EEE); 1A 2, 14 and 15 (E00, the blue): no palette
  changes, no free entry taken from the enemies.
- vk_candle16_flame_tiles[224]: the 7 frames (A, A, B, B, A, B, A) of vk_flame_fx_tiles (flame_fx_md.h), the flames of the
  torches of the courtyard (room_view.c vk_draw_targets: frame = (flame_clock >> 3) & 3, one frame per 8 ticks, torch B
  four ticks ahead; the tiles are loaded ONCE per screen by vk_load_whip_graphics). Frames A and B are the flames of the
  braziers of Castlevania-MD (obj_0 and obj_1, rows 0 to 15 of the 16 x 32 picture; the lower half is the brazier foot
  already under the torches, build_gfx16.py courtyard_pictures). Drawn with PAL1 (VK_PAL_ITEM, vk_item16_palette).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_enemies16 as be   # noqa: E402
import build_items16 as I      # noqa: E402

GEN = ROOT / 'sgdk/src/generated'
BLOB_ENTRIES_C = (2, 12, 13, 14)         # PAL2 entries the blobs may read (same colour in every PAL2 of their rooms):
BLOB_ENTRIES_A = (2, 14, 15)             # 1C in the stages 7 to 9, 1A in the stages 4 to 6 (entry 13 is 444 / 666 there)
# (stage, rooms with a blob) after ghostBase of enemies_ghost.inc (the pose base of the rooms, 0 = none)
GHOST_ROOMS = {4: range(6), 5: range(6), 6: range(6), 7: (0, 1, 2, 3, 5, 6, 7, 8), 8: (0, 1, 3, 4, 5, 6, 7),
               9: (0, 1, 2, 3, 5, 6, 7)}
FLAME_FRAMES = 'AABBABA'


def msx_cells(name, var, variant=None):
    w = be.nums((GEN / name).read_text(), var)
    if variant is not None:
        w = w[variant * 64:variant * 64 + 64]
    return [be.Msx.cell(w, c) for c in range(2)]


def bayer(x, y):
    return ((x & 1) + 2 * (y & 1)) * 0.25 + 0.125      # 2 x 2 ordered threshold in (0, 1)


def blob(cell, levels, spot=0):
    """Shaded blob on the silhouette of an MSX cell (indices 0 / 2 / body). `levels`: (threshold of t, entry) from the
    light to the shadow; between two levels the dither mixes them over a band of 0.12 of t."""
    pts = [(x, y) for y in range(16) for x in range(16) if cell[y][x]]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts) + 1
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts) + 1
    w, h = x1 - x0, y1 - y0
    fill = {p for p in pts}

    def edge(x, y):
        return any((x + dx, y + dy) not in fill for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    out = [[0] * 16 for _ in range(16)]
    for x, y in pts:
        if edge(x, y):
            out[y][x] = 2
            continue
        u, v = (x + .5 - x0) / w, (y + .5 - y0) / h
        t = 0.55 * u + 0.75 * v - 0.1          # 0 at the upper left, 1.2 at the lower right
        k = 0
        for i, (thr, _) in enumerate(levels[1:], 1):
            if t + (bayer(x, y) - .5) * 0.22 >= thr:
                k = i
        out[y][x] = levels[k][1]
    if spot:                                    # the specular highlight: a short bar and a dot on the upper left
        sx, sy = x0 + int(w * .22), y0 + int(h * .3)
        for dx, dy in ((0, 0), (1, 0), (0, 1)):
            if out[sy + dy][sx + dx] not in (0, 2):
                out[sy + dy][sx + dx] = spot
    return out


# (threshold of t, entry): 14 white, 12 AAA, 13 444 for the white blob; 14 highlight, 15 blue, 2 black for the blue one
LEVELS_C = [(0, 14), (0.62, 12), (0.95, 13)]
LEVELS_A = [(0, 15), (0.80, 2)]


def blobs():
    c = [blob(cell, LEVELS_C) for cell in msx_cells('ghost_md.c', 'vk_ghost_tiles', 0)]
    a = [blob(cell, LEVELS_A, 14) for cell in msx_cells('ghost_a_md.c', 'vk_ghost_a_tiles')]
    return c, a


def flames(cv):
    """The 16 x 16 indices (PAL1) of frames A and B: rows 0 to 15 of Castlevania-MD obj_0 / obj_1."""
    out = {}
    for name, n in (('A', 0), ('B', 1)):
        img = cv.pose(n)
        assert len(img) == 32 and len(img[0]) == 16
        out[name] = [[0 if p is None else I.nearest(p) for p in row] for row in img[:16]]
    return out


def fmt(vals, width, per=8):
    f = '0x%%0%dX' % width
    return '\n'.join('    ' + ','.join(f % v for v in vals[i:i + per]) + ',' for i in range(0, len(vals), per))


LEVELS_B = [(0, 8), (0.80, 2)]            # object 1B: red (entry 8, 20E in every PAL2 of its rooms), black dither, white glint


def msx_blob_b():
    """The two MSX cells of object 1B (stage 11 cells A0 / A4, late pool slots 4 / 5): one image for both pose bases."""
    w = be.nums((GEN / 'stage11_enemies_md.c').read_text(), 'vk_stage11_ghost_tiles')
    assert w[:64] == w[64:128], 'the two pose bases of the stage 11 blob differ'
    return w[:64]


def blob_b():
    """Object 1B (the red blob of the candles of object 15, stages 11 to 18) on the MSX silhouette, the same shading as
    object 1A with the red of entry 8: black outline (2), red body (8) with a black dither shadow, white glint (14)."""
    return [blob(cell, LEVELS_B, 14) for cell in [be.Msx.cell(msx_blob_b(), c) for c in range(2)]]


def blob_b_cells():
    """The two cells as 32 words each: what vk_candle16_blob_b_tiles holds and what slots 4 / 5 of the late pools take."""
    return [be.cell_tiles(c) for c in blob_b()]


def words_of(cells):
    return [w for c in cells for w in be.cell_tiles(c)]


def write(cblob, ablob, fl, bblob):
    flame_words = [w for k in FLAME_FRAMES for w in be.cell_tiles(fl[k])]
    arrays = [('vk_candle16_blob_c_tiles', words_of(cblob), 'object 1C (stages 7 to 9), as vk_ghost_tiles[n]'),
              ('vk_candle16_blob_a_tiles', words_of(ablob), 'object 1A (stages 4 to 6), as vk_ghost_a_tiles'),
              ('vk_candle16_blob_b_tiles', words_of(bblob), 'object 1B (stages 11 to 18), as vk_stage11_ghost_tiles[n]'),
              ('vk_candle16_flame_tiles', flame_words, 'courtyard torches, as vk_flame_fx_tiles (frames A A B B A B A), PAL1')]
    h = ['/* Generated by tools/build_candle16.py (research/gfx16.md). Same layout as ghost_md.h, ghost_a_md.h and flame_fx_md.h. */',
         '#ifndef VK_CANDLE16_MD_H', '#define VK_CANDLE16_MD_H', '#include <genesis.h>']
    c = ['/* Generated by tools/build_candle16.py. */', '#include "candle16_md.h"']
    for name, words, comment in arrays:
        h.append('extern const u32 %s[%d];   /* %s */' % (name, len(words), comment))
        c.append('const u32 %s[%d] = {\n%s\n};' % (name, len(words), fmt(words, 8)))
    h.append('#endif')
    (GEN / 'candle16_md.h').write_text('\n'.join(h) + '\n')
    (GEN / 'candle16_md.c').write_text('\n'.join(c) + '\n')
    return sum(len(w) for _, w, _ in arrays) * 4


def preview(cblob, ablob, fl, path, bblob):
    from PIL import Image, ImageDraw
    S = 6
    pal2 = {0: None, 2: (0x22, 0x22, 0x22), 12: (0xAA, 0xAA, 0xAA), 13: (0x44, 0x44, 0x44), 14: (0xEE, 0xEE, 0xEE),
            15: (0, 0, 0xEE), 8: (0xEE, 0, 0x22)}
    pal1 = [None] + [tuple(v * 36 for v in I.P1[i]) for i in range(1, 16)]
    items = [('1C a', cblob[0], pal2), ('1C b', cblob[1], pal2), ('1A a', ablob[0], pal2), ('1A b', ablob[1], pal2),
             ('1B a', bblob[0], pal2), ('1B b', bblob[1], pal2),
             ('flame A', fl['A'], pal1), ('flame B', fl['B'], pal1)]
    im = Image.new('RGB', (len(items) * (16 * S + 8), 16 * S + 24), (118, 118, 118))
    d = ImageDraw.Draw(im)
    for n, (name, rows, pal) in enumerate(items):
        ox = n * (16 * S + 8) + 4
        d.text((ox, 2), name, fill=(255, 255, 0))
        d.rectangle([ox, 16, ox + 16 * S - 1, 16 + 16 * S - 1], fill=(70, 70, 70))
        for y in range(16):
            for x in range(16):
                col = pal[rows[y][x]] if rows[y][x] else None
                if col:
                    d.rectangle([ox + x * S, 16 + y * S, ox + x * S + S - 1, 16 + y * S + S - 1], fill=col)
    im.save(path)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cv = be.CV(sys.argv[1])
    cblob, ablob = blobs()
    fl = flames(cv)
    size = write(cblob, ablob, fl, blob_b())
    print('candle16: %d B of data' % size)
    if '--preview' in sys.argv:
        preview(cblob, ablob, fl, sys.argv[sys.argv.index('--preview') + 1], blob_b())


if __name__ == '__main__':
    main()

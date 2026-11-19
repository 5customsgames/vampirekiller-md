#!/usr/bin/env python3
"""Common enemies of block 2 (stages 4 to 6) in the 16-bit art (research/gfx16.md, section "Ennemis 16 bits (bloc 2)").

usage: build_enemies16_block2.py <castlevania-md checkout> [--preview FILE.png]

Same method as tools/build_enemies16.py (block 1): the code, the sprite table, the hit boxes and the VRAM cells stay
those of the MSX port, only the picture of some cells of the stage 4/5 and stage 6 blocks (vk_stage4_enemy_tiles,
vk_stage6_enemy_tiles: pattern N is tile N - 0x40, a cell is four tiles, both MSX layers already composed in cell N)
changes. Unlike block 1 the 16-bit cells are stored alone (a pool of cells and, per block, the list of the cells it
overwrites): actors.c loads the MSX block as before, then these cells over it, so the cells that stay MSX (crushers,
object 1A, platform) cost nothing.

- Pictures (Castlevania-MD, src/block2.c), all facing left like the MSX left cells; the right cells
  are their mirror:
    object 08 (medusa head)  poses 71 72 / 73 74 = cells 40 48 / 50 58   b2_medusa0, b2_medusa1
    object 06 (armour knight) top 80 / A0, bottoms 88 90 98 / A8 B0 B8  b2_knight1 top, bottoms of b2_knight0, 1, 2
                              (MSX cycle 50 51 52 51 = NES cycle 0 1 2 1)
    object 07 (bat, stage 6) poses 16 17 / 18 19 = cells A0 A8 / B0 B8   b2_rbat0, b2_rbat2
    object 0A (statue)       44 / 4C, flashing 54 / 5C                    b2_pillar, b2_pillar_flash (bone pillar)
    its fireball             cell 60                                      8 x 8 red sphere (no trail: both directions)
- Placement: knight and statue (16 x 32) laid with their feet on the lowest row of the MSX picture of that pose, the
  others centred on it; always centred on its columns.
- Palette (PAL2 of the rooms of stages 4 to 6 but the stage 6 crusher room and boss room, vk_enemy16b2_palette): as in
  block 1, the entries other PAL2 content reads (1, 2, 3, 7, 8, 12, 13, 14, 15: objects, key, door, HUD boxes, text,
  object 1A) keep their MSX colour; 4, 5, 6, 9, 10, 11 take the 16-bit colours. The crushers of stage 6 room 1 read
  4, 6 and 11: that room keeps the MSX palette and the MSX cells (it has no other enemy).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_enemies16 as B  # noqa: E402
import build_items16 as I  # noqa: E402

ROOT = B.ROOT
GEN = B.GEN


class Block(B.CV):
    """Sprites of a Castlevania-MD block file (src/blockN.c): b2_* poses on block2_tiles, block2_palette."""

    def __init__(self, root, n):
        self.text = (Path(root) / ('src/block%d.c' % n)).read_text()
        self.tiles = B.nums(self.text, 'block%d_tiles' % n)
        self.pal = [B.lvl(w) for w in B.nums(self.text, 'block%d_palette' % n)]

    def sprite(self, name, rows=None):
        """Picture of pose `name`; `rows` = (first, last) keeps the 8 x 16 entries whose dy is in that range."""
        m = re.search(r'static const SimonSprite %s\[\d+\] = \{(.*?)\};' % name, self.text, re.S)
        ents = [tuple(int(v, 0) for v in e.split(',')) for e in re.findall(r'\{([^{}]+)\}', m.group(1))]
        if rows:
            ents = [e for e in ents if rows[0] <= e[1] <= rows[1]]
        return self.draw(ents)

    def draw(self, ents, x0=None, y0=None):
        x0 = min(e[0] for e in ents) if x0 is None else x0
        y0 = min(e[1] for e in ents) if y0 is None else y0
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


MSX_ARRAYS = {'s4': 'vk_stage4_enemy_tiles', 's6': 'vk_stage6_enemy_tiles'}
MSX_FILES = {'s4': 'stage4_enemies_md.c', 's6': 'stage6_enemies_md.c'}


def msx_words(blk):
    return B.nums((GEN / MSX_FILES[blk]).read_text(), 'const (?:unsigned long|u32) ' + MSX_ARRAYS[blk])


def cell_of(pattern):
    return (pattern - 0x40) // 4


# Eye sockets of the two skulls of the bone pillar (the black pixels of b2_pillar_flash, x, y on the 16 x 32 picture)
EYES = [(2, 2), (3, 2), (2, 3), (11, 2), (12, 2), (9, 3), (10, 3), (11, 3), (12, 3), (10, 4), (11, 4),
        (3, 18), (4, 18), (3, 19), (4, 19), (5, 19), (6, 19), (4, 20), (5, 20), (12, 18), (13, 18), (13, 19)]
EYE_CORE = (7, 7, 7)                         # white-hot sockets (fixed entry 14, MSX white)
EYE_GLOW = (7, 5, 0)                         # orange glow on the bone around them


def lit_eyes(img):
    """The "eyes lit" pose of the statue: the sockets white, a one pixel glow around them. The dark red of b2_pillar_flash alone
    could hardly be told from the normal pose on the red wall of the stage 6."""
    out = [r[:] for r in img]
    for x, y in EYES:
        assert img[y][x] == (0, 0, 0), (x, y)
    for x, y in EYES:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            u, v = x + dx, y + dy
            if 0 <= v < len(img) and 0 <= u < len(img[0]) and img[v][u] is not None and (u, v) not in EYES:
                out[v][u] = EYE_GLOW
    for x, y in EYES:
        out[y][x] = EYE_CORE
    return out


def pictures(b2):
    """[(name, picture, mode, size, (block, [(pattern, canvas x, canvas y)]) for the reference and the writes)]."""
    out = []

    def job(name, img, mode, size, blocks, cells, crop=True):
        if crop:
            img = B.crop(img)
        out.append(dict(name=name, img=img, mode=mode, size=size, blocks=blocks, cells=cells))

    def both(name, img, mode, size, blocks, left, right, crop=True):
        job(name, img, mode, size, blocks, left, crop)
        job(name + ' R', B.mirror(B.crop(img) if crop else img), mode, size, blocks, right, crop)

    # object 08, medusa head (stages 4, 5 and 6 rooms 3, 4)
    both('medusa0', b2.sprite('b2_medusa0'), 'centre', (16, 16), ('s4', 's6'), [(0x40, 0, 0)], [(0x50, 0, 0)])
    both('medusa1', b2.sprite('b2_medusa1'), 'centre', (16, 16), ('s4', 's6'), [(0x48, 0, 0)], [(0x58, 0, 0)])
    # object 06, armour knight (stages 4 and 5): top of b2_knight1 (top at dy 0) and the three bottoms
    top = b2.sprite('b2_knight1', (0, 15))
    for k, (lb, rb) in enumerate(((0x88, 0xA8), (0x90, 0xB0), (0x98, 0xB8))):
        bottom = b2.sprite('b2_knight%d' % k, (16, 16))
        img = [r[:] for r in top] + [r[:] for r in bottom]
        both('knight%d' % k, img, 'feet', (16, 32), ('s4',), [(0x80, 0, 0), (lb, 0, 16)], [(0xA0, 0, 0), (rb, 0, 16)],
             crop=False)
    # object 07, bat (stage 6 room 0)
    both('rbat0', b2.sprite('b2_rbat0'), 'centre', (16, 16), ('s6',), [(0xA0, 0, 0)], [(0xB0, 0, 0)])
    both('rbat2', b2.sprite('b2_rbat2'), 'centre', (16, 16), ('s6',), [(0xA8, 0, 0)], [(0xB8, 0, 0)])
    # object 0A, statue = bone pillar (stage 6 room 2), and its fireball
    job('pillar', b2.sprite('b2_pillar'), 'feet', (16, 32), ('s6',), [(0x44, 0, 0), (0x4C, 0, 16)])
    job('pillar_flash', lit_eyes(b2.sprite('b2_pillar_flash')), 'feet', (16, 32), ('s6',), [(0x54, 0, 0), (0x5C, 0, 16)])
    # obj_47 has a trail (it moves right) and the MSX cell serves both directions: an 8 x 8 sphere (build_items16.sphere, as
    # the fireball of the stage 3 boss), the size of the MSX ball (7 x 7); dark red rim, red, orange, light core: the reds
    # of obj_47 (4,0,0), (5,1,1) would fall on the dull entry 224, the bright red of the MSX ball is a fixed entry (20E)
    job('fire', I.sphere([(4, 0, 0), (7, 0, 1), (7, 0, 1), (6, 3, 1), (7, 5, 4)], 8), 'centre', (16, 16), ('s6',),
        [(0x60, 0, 0)])
    return out


def laid(jobs):
    """Each job's picture on its canvas, placed against the MSX picture of the same cells (first block)."""
    res = []
    for j in jobs:
        words = msx_words(j['blocks'][0])
        cw, ch = j['size']
        ref = B.ref_box(B.canvas_of([(x, y, B.Msx.cell(words, cell_of(p))) for p, x, y in j['cells']]))
        res.append((j, B.place(j['img'], cw, ch, ref, j['mode'])))
    return res


def stage_palettes():
    """MSX palettes of the rooms that take vk_enemy16b2_palette (stages 4 to 6, not 6/1 nor the boss room 6/5)."""
    t = (GEN / 'rooms.c').read_text()
    m = re.search(r'vk_palettes\[\]\[16\] = \{(.*?)\n\};', t, re.S)
    allp = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    st = re.search(r'vk_stages\[18\] = \{(.*?)\};', t, re.S)
    stages = [tuple(int(x) for x in re.findall(r'\d+', e)) for e in re.findall(r'\{([^{}]*)\}', st.group(1))]
    pals = []
    for s in (4, 5, 6):
        first, count, _ = stages[s - 1]
        for r in range(count):
            if s == 6 and r in (1, 5):
                continue
            pals.append(allp[(first + r) * 16:(first + r) * 16 + 16])
    return pals


def build_palette(pics):
    pals = stage_palettes()
    for p in pals:
        assert [p[i] for i in B.FIXED] == [pals[0][i] for i in B.FIXED], 'fixed MSX colours differ between rooms'
    pal = [0] * 16
    for i in B.FIXED:
        pal[i] = pals[0][i]
    colours = {}
    for j, img in pics:
        for row in img:
            for p in row:
                if p is not None:
                    colours[p] = colours.get(p, 0) + 1
    free, err = B.choose_free(colours, [B.lvl(pal[i]) for i in B.FIXED])
    for i, c in zip(B.FREE, free):
        pal[i] = B.word(c)
    return pal, err


def build(b2):
    pics = laid(pictures(b2))
    pal, err = build_palette(pics)
    pool, lists = [], {'s4': [], 's6': []}
    for j, img in pics:
        for p, x, y in j['cells']:
            rows = [[0 if img[y + dy][x + dx] is None else B.to_index(pal, img[y + dy][x + dx])
                     for dx in range(16)] for dy in range(16)]
            tiles = B.cell_tiles(rows)
            if tiles not in pool:
                pool.append(tiles)
            k = pool.index(tiles)
            for blk in j['blocks']:
                old = dict(lists[blk])
                assert old.get(p, k) == k, 'cell %02X of %s written twice with other pixels' % (p, blk)
                if p not in old:
                    lists[blk].append((p, k))
    for blk in lists:
        lists[blk].sort()
    return pool, lists, pal, err


def write(pool, lists, pal):
    h = ['/* Generated by tools/build_enemies16_block2.py (Castlevania-MD art, research/gfx16.md). Cells of the stage 4/5 and',
         ' * stage 6 enemy blocks (same layout as vk_stage4_enemy_tiles / vk_stage6_enemy_tiles: pattern N is tile N - 0x40),',
         ' * loaded by actors.c (room_cells) over the MSX block in 16-bit mode, stages 4 to 6. */',
         '#ifndef VK_ENEMIES16B2_MD_H', '#define VK_ENEMIES16B2_MD_H', '#include <genesis.h>',
         '/* PAL2 of those rooms: the MSX colours other content uses keep their entries; the free ones hold the 16-bit colours. */',
         'extern const u16 vk_enemy16b2_palette[16];',
         '/* 16 x 16 cells, four tiles each (column by column, as the MSX blocks). */',
         '#define VK_ENEMY16B2_CELLS %d' % len(pool),
         'extern const u32 vk_enemy16b2_cells[%d];' % (len(pool) * 32),
         '/* Per block: pairs (pattern of the cell in the block, cell of vk_enemy16b2_cells), ended by 0. */',
         'extern const u8 vk_enemy16b2_stage4[%d];   /* stages 4 and 5 */' % (2 * len(lists['s4']) + 1),
         'extern const u8 vk_enemy16b2_stage6[%d];' % (2 * len(lists['s6']) + 1),
         '#endif']
    c = ['/* Generated by tools/build_enemies16_block2.py. */', '#include "enemies16b2_md.h"',
         'const u16 vk_enemy16b2_palette[16] = {\n%s\n};' % B.fmt(pal, 4),
         'const u32 vk_enemy16b2_cells[%d] = {\n%s\n};' % (len(pool) * 32, B.fmt([w for cell in pool for w in cell], 8))]
    for blk, name in (('s4', 'vk_enemy16b2_stage4'), ('s6', 'vk_enemy16b2_stage6')):
        vals = [v for p, k in lists[blk] for v in (p, k)] + [0]
        c.append('const u8 %s[%d] = {\n%s\n};' % (name, len(vals), B.fmt(vals, 2, 16)))
    (GEN / 'enemies16b2_md.h').write_text('\n'.join(h) + '\n')
    (GEN / 'enemies16b2_md.c').write_text('\n'.join(c) + '\n')


def preview(pool, lists, pal, path):
    """MSX cell (its room palette) next to the 16-bit cell, for every cell overwritten."""
    from PIL import Image, ImageDraw
    S = 4
    msxpal = stage_palettes()[0]
    mp16 = [(0, 0, 0)] + [tuple(v * 36 for v in B.lvl(pal[i])) for i in range(1, 16)]
    mpm = [(0, 0, 0)] + [tuple(v * 36 for v in B.lvl(msxpal[i])) for i in range(1, 16)]
    rows = [(blk, p, B.Msx.cell(msx_words(blk), cell_of(p)), B.Msx.cell(pool[k], 0)) for blk in lists for p, k in lists[blk]]
    cols = 6
    nrow = (len(rows) + cols - 1) // cols
    im = Image.new('RGB', (cols * (36 * S + 8), nrow * (18 * S + 14)), (90, 100, 120))
    d = ImageDraw.Draw(im)
    for n, (blk, p, a, b) in enumerate(rows):
        ox, oy = (n % cols) * (36 * S + 8), (n // cols) * (18 * S + 14)
        d.text((ox, oy), '%s %02X' % (blk, p), fill=(255, 255, 255))
        for dx, px, mp in ((0, a, mpm), (17 * S + 4, b, mp16)):
            for y in range(16):
                for x in range(16):
                    if px[y][x]:
                        d.rectangle([ox + dx + x * S, oy + 12 + y * S, ox + dx + x * S + S - 1, oy + 12 + y * S + S - 1],
                                    fill=mp[px[y][x]])
    im.save(path)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    b2 = Block(sys.argv[1], 2)
    pool, lists, pal, err = build(b2)
    write(pool, lists, pal)
    data = len(pool) * 128 + 32 + sum(2 * len(v) + 1 for v in lists.values())
    print('cells %d (stage 4/5: %d, stage 6: %d), data %d B, mean colour error %.1f/255, palette %s' % (
        len(pool), len(lists['s4']), len(lists['s6']), data, err, ' '.join('%03X' % w for w in pal)))
    if '--preview' in sys.argv:
        preview(pool, lists, pal, sys.argv[sys.argv.index('--preview') + 1])


if __name__ == '__main__':
    main()

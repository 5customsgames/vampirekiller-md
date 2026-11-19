#!/usr/bin/env python3
"""Common enemies of block 3 (stages 7 to 9) in the 16-bit art (research/gfx16.md, section "Ennemis 16 bits (bloc 3)").

usage: build_enemies16_block3.py <castlevania-md checkout> [--preview FILE.png]

Same method as tools/build_enemies16_block2.py: the code, the sprite table, the hit boxes and the VRAM cells stay those
of the MSX port, only the picture of the cells of the stage 7, 8 and 9 blocks (vk_stage7/8/9_enemy_tiles: pattern N is
tile N - 0x40, a cell is four tiles, both MSX layers already composed in cell N) changes. The 16-bit cells are stored once
(a pool of cells and, per block, the list of the cells it overwrites); actors.c loads the MSX block as before, then these
cells over it. The pool is in pattern order, so every block is one run of consecutive cells (one transfer).

- Pictures (Castlevania-MD, src/block3.c), all facing left like the MSX left cells; the right cells are their mirror
  (Castlevania-MD mirrors the same poses when the monster goes right):
    object 08 (medusa head, stage 8 room 1, stage 9 rooms 0-3)  poses 71 72 / 73 74 = cells 40 48 / 50 58   b3_medusa0, 1
    object 0A (statue, stage 8 rooms 6-7, stage 9 rooms 1, 2, 4) 44 / 4C, flashing 54 / 5C       b3_pillar, b3_pillar_flash
    its fireball                                                  cell 60      8 x 8 red sphere (as block 2)
    object 0B (hopper: skeleton)  poses 47 48 (left) = 64/68 6C/70, 49 4A (right) = 74/78 7C/80   b3_skel0, b3_skel1
    its bone (D700 type 4)        poses 4B 4C 4D = cells 98 9C A0 (both directions)              b3_bone0, 1, 2
    object 0C (leaper: raven)     poses 87 88 (left) = 84 88, 8A 8B (right) = 90 94, rest 89 = 8C
                                                                  b3_raven0, b3_raven1 (wings up, down), b3_raven_perch
    object 0D (flea: fleaman, stages 7 and 9) poses 67 68 (left) = A4 A8, 6A 6B (right) = AC B0  b3_flea_stand, b3_flea_jump
- Placement: skeleton and statue (16 x 32) laid with their feet on the lowest row of the MSX picture of that pose, the
  others centred on it; always centred on its columns.
- Kept MSX: object 1C (the white blob of the candles of object 15, cells B4 and B8 loaded after the block, colours 2 and
  14: Castlevania-MD's b3_ghost flies, it is not the same creature), the stage 9 boss (room 7).
- Palette (PAL2 of the rooms of stages 7 to 9 but the stage 9 boss room, vk_enemy16b3_palette): as in blocks 1 and 2, the
  entries other PAL2 content reads (1, 2, 3, 7, 8, 12, 13, 14, 15: objects, key, door, HUD boxes, text, object 1C) keep
  their MSX colour; 4, 5, 6, 9, 10, 11 take the 16-bit colours. Unlike stages 1 to 6, the rooms of stages 7 to 9 do not
  all have the same entry 7 (66C or 26C): two palettes, the same but for entry 7, chosen by the MSX entry 7 of the room
  (gfx16.c); no 16-bit pixel takes entry 7.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_enemies16 as B  # noqa: E402
import build_enemies16_block2 as T  # noqa: E402
import build_items16 as I  # noqa: E402

ROOT = B.ROOT
GEN = B.GEN
BLOCKS = ('s7', 's8', 's9')
VARIABLE = 7                     # fixed entry whose MSX colour differs between the rooms: no 16-bit pixel uses it


def msx_words(blk):
    n = blk[1]
    return B.nums((GEN / ('stage%s_enemies_md.c' % n)).read_text(), r'const (?:unsigned long|u32) vk_stage%s_enemy_tiles' % n)


def cell_of(pattern):
    return (pattern - 0x40) // 4


def pictures(b3):
    """[dict(name, img, mode, size, blocks, cells=[(pattern, canvas x, canvas y)])]."""
    out = []

    def job(name, img, mode, size, blocks, cells, crop=True):
        if crop:
            img = B.crop(img)
        out.append(dict(name=name, img=img, mode=mode, size=size, blocks=blocks, cells=cells))

    def both(name, img, mode, size, blocks, left, right):
        job(name, img, mode, size, blocks, left)
        job(name + ' R', B.mirror(B.crop(img)), mode, size, blocks, right)

    s89, s789, s79 = ('s8', 's9'), BLOCKS, ('s7', 's9')
    # object 08, medusa head (cells as in block 2)
    both('medusa0', b3.sprite('b3_medusa0'), 'centre', (16, 16), s89, [(0x40, 0, 0)], [(0x50, 0, 0)])
    both('medusa1', b3.sprite('b3_medusa1'), 'centre', (16, 16), s89, [(0x48, 0, 0)], [(0x58, 0, 0)])
    # object 0A, statue = bone pillar, and its eyes lit before a shot
    job('pillar', b3.sprite('b3_pillar'), 'feet', (16, 32), s89, [(0x44, 0, 0), (0x4C, 0, 16)])
    job('pillar_flash', b3.sprite('b3_pillar_flash'), 'feet', (16, 32), s89, [(0x54, 0, 0), (0x5C, 0, 16)])
    # its fireball: the 8 x 8 sphere of block 2 (red of the fixed entry 8 = the MSX ball, orange and light core)
    job('fire', I.sphere([(4, 0, 0), (7, 0, 1), (7, 0, 1), (6, 3, 1), (7, 5, 4)], 8), 'centre', (16, 16), s89, [(0x60, 0, 0)])
    # object 0B, skeleton: two walking poses, 16 x 32 (top cell, bottom cell)
    for k, (left, right) in enumerate(((0x64, 0x74), (0x6C, 0x7C))):
        both('skel%d' % k, b3.sprite('b3_skel%d' % k), 'feet', (16, 32), s789,
             [(left, 0, 0), (left + 4, 0, 16)], [(right, 0, 0), (right + 4, 0, 16)])
    # object 0C, raven: rest (one cell, both directions), two flying poses
    job('raven_perch', b3.sprite('b3_raven_perch'), 'centre', (16, 16), s789, [(0x8C, 0, 0)])
    both('raven0', b3.sprite('b3_raven0'), 'centre', (16, 16), s789, [(0x84, 0, 0)], [(0x90, 0, 0)])
    both('raven1', b3.sprite('b3_raven1'), 'centre', (16, 16), s789, [(0x88, 0, 0)], [(0x94, 0, 0)])
    # the bone, poses 4B (upright), 4C (/), 4D (\): the same cells in both directions, as on the MSX
    for k, p in enumerate((0x98, 0x9C, 0xA0)):
        job('bone%d' % k, b3.sprite('b3_bone%d' % k), 'centre', (16, 16), s789, [(p, 0, 0)])
    # object 0D, fleaman: 67 / 6A waiting (stand), 68 / 6B jumping
    both('flea_stand', b3.sprite('b3_flea_stand'), 'feet', (16, 16), s79, [(0xA4, 0, 0)], [(0xAC, 0, 0)])
    both('flea_jump', b3.sprite('b3_flea_jump'), 'feet', (16, 16), s79, [(0xA8, 0, 0)], [(0xB0, 0, 0)])
    return out


def laid(jobs):
    """Each job's picture on its canvas, placed against the MSX picture of the same cells (its last block)."""
    res = []
    for j in jobs:
        words = msx_words(j['blocks'][-1])
        cw, ch = j['size']
        ref = B.ref_box(B.canvas_of([(x, y, B.Msx.cell(words, cell_of(p))) for p, x, y in j['cells']]))
        res.append((j, B.place(j['img'], cw, ch, ref, j['mode'])))
    return res


def stage_palettes():
    """{(stage, room): MSX palette} of the rooms that take vk_enemy16b3_palette (stages 7 to 9, not the boss room 9/7)."""
    t = (GEN / 'rooms.c').read_text()
    m = re.search(r'vk_palettes\[\]\[16\] = \{(.*?)\n\};', t, re.S)
    allp = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    st = re.search(r'vk_stages\[18\] = \{(.*?)\};', t, re.S)
    stages = [tuple(int(x) for x in re.findall(r'\d+', e)) for e in re.findall(r'\{([^{}]*)\}', st.group(1))]
    pals = {}
    for s in (7, 8, 9):
        first, count, _ = stages[s - 1]
        for r in range(count):
            if s == 9 and r == 7:
                continue
            pals[(s, r)] = allp[(first + r) * 16:(first + r) * 16 + 16]
    return pals


def to_index(pal, c):
    return min((i for i in range(1, 16) if i != VARIABLE), key=lambda i: (B.dist(B.lvl(pal[i]), c), i))


def build_palette(pics):
    """Two palettes (the two MSX values of entry 7), the same 16-bit colours in the free entries."""
    pals = list(stage_palettes().values())
    fixed = [i for i in B.FIXED if i != VARIABLE]
    for p in pals:
        assert [p[i] for i in fixed] == [pals[0][i] for i in fixed], 'fixed MSX colours differ between rooms'
    sevens = sorted({p[VARIABLE] for p in pals})
    assert len(sevens) == 2, sevens
    pal = [0] * 16
    for i in fixed:
        pal[i] = pals[0][i]
    colours = {}
    for j, img in pics:
        for row in img:
            for p in row:
                if p is not None:
                    colours[p] = colours.get(p, 0) + 1
    free, err = B.choose_free(colours, [B.lvl(pal[i]) for i in fixed])
    for i, c in zip(B.FREE, free):
        pal[i] = B.word(c)
    out = []
    for v in sevens:
        q = pal[:]
        q[VARIABLE] = v
        out.append(q)
    return out, err


def build(b3):
    pics = laid(pictures(b3))
    pals, err = build_palette(pics)
    cells = {}                                   # pattern -> tiles
    blocks = {blk: set() for blk in BLOCKS}
    for j, img in pics:
        for p, x, y in j['cells']:
            rows = [[0 if img[y + dy][x + dx] is None else to_index(pals[0], img[y + dy][x + dx])
                     for dx in range(16)] for dy in range(16)]
            tiles = B.cell_tiles(rows)
            assert cells.get(p, tiles) == tiles, 'cell %02X written twice with other pixels' % p
            cells[p] = tiles
            for blk in j['blocks']:
                blocks[blk].add(p)
    order = sorted(cells)                        # pattern order: each block is one run of the pool
    pool = [cells[p] for p in order]
    lists = {blk: [(p, order.index(p)) for p in sorted(blocks[blk])] for blk in BLOCKS}
    return pool, lists, pals, err


def write(pool, lists, pals):
    h = ['/* Generated by tools/build_enemies16_block3.py (Castlevania-MD art, research/gfx16.md). Cells of the stage 7, 8 and 9',
         ' * enemy blocks (same layout as vk_stage7/8/9_enemy_tiles: pattern N is tile N - 0x40), loaded by actors.c (room_cells)',
         ' * over the MSX block in 16-bit mode, stages 7 to 9 (not the stage 9 boss room). */',
         '#ifndef VK_ENEMIES16B3_MD_H', '#define VK_ENEMIES16B3_MD_H', '#include <genesis.h>',
         '/* PAL2 of those rooms: the MSX colours other content uses keep their entries; the free ones hold the 16-bit colours.',
         ' * Two palettes, which differ only in entry 7 (the MSX rooms have 66C or 26C there): gfx16.c takes the one of the room. */',
         'extern const u16 vk_enemy16b3_palette[2][16];',
         '/* 16 x 16 cells, four tiles each (column by column, as the MSX blocks), in pattern order. */',
         '#define VK_ENEMY16B3_CELLS %d' % len(pool),
         'extern const u32 vk_enemy16b3_cells[%d];' % (len(pool) * 32),
         '/* Per block: pairs (pattern of the cell in the block, cell of vk_enemy16b3_cells), ended by 0. */']
    for blk in BLOCKS:
        h.append('extern const u8 vk_enemy16b3_stage%s[%d];' % (blk[1], 2 * len(lists[blk]) + 1))
    h.append('#endif')
    c = ['/* Generated by tools/build_enemies16_block3.py. */', '#include "enemies16b3_md.h"',
         'const u16 vk_enemy16b3_palette[2][16] = {\n%s\n};' % ',\n'.join('{\n%s\n}' % B.fmt(p, 4) for p in pals),
         'const u32 vk_enemy16b3_cells[%d] = {\n%s\n};' % (len(pool) * 32, B.fmt([w for cell in pool for w in cell], 8))]
    for blk in BLOCKS:
        vals = [v for p, k in lists[blk] for v in (p, k)] + [0]
        c.append('const u8 vk_enemy16b3_stage%s[%d] = {\n%s\n};' % (blk[1], len(vals), B.fmt(vals, 2, 16)))
    (GEN / 'enemies16b3_md.h').write_text('\n'.join(h) + '\n')
    (GEN / 'enemies16b3_md.c').write_text('\n'.join(c) + '\n')


def preview(pool, lists, pals, path):
    """MSX cell (its room palette) next to the 16-bit cell, for every cell of the pool."""
    from PIL import Image, ImageDraw
    S = 4
    rooms = stage_palettes()
    mp16 = [(0, 0, 0)] + [tuple(v * 36 for v in B.lvl(pals[0][i])) for i in range(1, 16)]
    seen, rows = set(), []
    for blk in ('s9', 's7', 's8'):
        msxpal = rooms[(int(blk[1]), 0)]
        mpm = [(0, 0, 0)] + [tuple(v * 36 for v in B.lvl(msxpal[i])) for i in range(1, 16)]
        for p, k in lists[blk]:
            if (p, blk == 's7') in seen or (blk == 's8' and p in {q for q, _ in lists['s9']}):
                continue
            seen.add((p, blk == 's7'))
            rows.append((blk, p, B.Msx.cell(msx_words(blk), cell_of(p)), B.Msx.cell(pool[k], 0), mpm))
    cols = 6
    nrow = (len(rows) + cols - 1) // cols
    im = Image.new('RGB', (cols * (36 * S + 8), nrow * (18 * S + 14)), (90, 100, 120))
    d = ImageDraw.Draw(im)
    for n, (blk, p, a, b, mpm) in enumerate(rows):
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
    b3 = T.Block(sys.argv[1], 3)
    pool, lists, pals, err = build(b3)
    write(pool, lists, pals)
    data = len(pool) * 128 + 64 + sum(2 * len(v) + 1 for v in lists.values())
    print('cells %d (stage 7: %d, stage 8: %d, stage 9: %d), data %d B, mean colour error %.1f/255, palette %s / entry 7 %03X' % (
        len(pool), len(lists['s7']), len(lists['s8']), len(lists['s9']), data, err,
        ' '.join('%03X' % w for w in pals[0]), pals[1][VARIABLE]))
    if '--preview' in sys.argv:
        preview(pool, lists, pals, sys.argv[sys.argv.index('--preview') + 1])


if __name__ == '__main__':
    main()

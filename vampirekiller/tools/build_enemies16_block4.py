#!/usr/bin/env python3
"""Common enemies of block 4 (stages 10 to 12) in the 16-bit art (research/gfx16.md, section "Ennemis 16 bits (bloc 4)").

usage: build_enemies16_block4.py <castlevania-md checkout> [--preview FILE.png]

Same method as tools/build_enemies16_block3.py: the code, the sprite table, the hit boxes and the VRAM cells stay those of
the MSX port, only the picture of the cells changes. Five MSX layouts are kept:
  - the type 5 blocks of stages 10 and 11 (vk_stage10/11_enemy_tiles: pattern N is tile N - 0x40, both MSX layers already
    composed in cell N): the 16-bit cells are stored once (pool vk_enemy16b4_cells, in pattern order); the blank MSX cells
    between them are stored blank, so the cells of a stage are ONE run from pattern 40 (VK_ENEMY16B4_STAGE1x_CELL / _CELLS).
    gfx16.c (vk_gfx16_enemy_block) loads that run IN PLACE of the MSX cells, then the MSX cells after it: as many tiles as
    the MSX block, two transfers (with one transfer per run, as in block 3, the room entry after the stage 10 -> 11 jump
    of the scenario took one frame more);
  - the type 4 block of stage 10 (vk_stage10_bat_tiles, layout of vk_enemy4_tiles: two layers N, N + 1 per pose) and the
    zombie block (vk_enemy_tiles, stage 11 room 0): whole arrays of the same layout, layer N + 1 empty;
  - the late enemy pool of stage 12 (late_graphics_words, cells 0 to 5 are the only ones the stage 12 rooms load): the
    first 6 pool cells, the 16-bit dragon and shot in cells 0 to 3, cells 4 and 5 (object 1B) copied as they are.

- Pictures (Castlevania-MD: src/block4.c, and src/level.c for the fishman, its drop and the zombie that block 4 does not
  have), facing left like the MSX left cells; the right cells are their mirror:
    stage 10, object 03 / 21h (fishman)  top 40 (poses 0F 10), bottoms 44 (0F) 48 (10)    obj_44 top, obj_44 / obj_45 bottom
                                         fire 4C / 50 (pose 11)                           obj_46 (mouth open)
                                         right: 54 / 58 / 5C, fire 64 / 68                 their mirror
               its shot (D700 type 1)    cell 60                                          8 x 8 red sphere (as blocks 2, 3)
               its drop (object 20h)     cell 90                                          obj_49
               object 04 (bat, room 0)   poses 0 2 4, right 6 8 10                         level.c obj_42, obj_43, obj_41 (the
                                         red bat of Castlevania-MD's caves; block 4's blue b4_rbat vanished on the blue
                                         16-bit cave)
    stage 11, object 0F (eagle)          left column 40/44 (6D, 8D), 4C/54 (6E) + wing column 48/50 (6D), 58/60 (6E), 68/70 (8D)
                                         b4_eagle0 (6D, 8D), b4_eagle1 (6E), whole 32 x 32 picture on four cells
               objects 0D / 23h (flea)   stand / jump 80 84, right 88 8C                  b4_flea_stand, b4_flea_jump
               object 0E (bone dragon)   closed head 90, body 94, open head 98            b4_dragon0, two b4_vert, b4_dragon1
               its shot                  cell 9C                                          the 8 x 8 red sphere
               zombies (room 0)          vk_enemy_tiles layout                            obj_6 / obj_7 (as block 1)
    stage 12, object 0E and its shot     late pool cells 0 1 2 (90 94 98) and 3           as stage 11
- Kept MSX: object 1B (the blob of the candles of object 15, stage 11 cells A0 / A4 loaded after the block, stage 12 pool
  cells 4 / 5: b4_ghost of the NES game flies, it is not the same creature), the stage 10 platform (it has its own 16-bit
  version, platform16), the stage 12 boss (room 6).
- Palette: as in blocks 1 to 3 the entries other PAL2 content reads (1, 2, 3, 7, 8, 12, 13, 14, 15: objects, key, door, HUD
  boxes, text, object 1B) keep their MSX colour; 4, 5, 6, 9, 10, 11 take the 16-bit colours. Entry 7 is CAE (stage 10),
  000 (stage 11 room 0) or 66C (stage 11 rooms 1-5, stage 12): one palette per group of rooms, each with the colours of the
  enemies of that group only (stage 10: fishman and bat; stage 11 room 0: zombies; stage 11 rooms 1-5: eagle, flea,
  dragon; stage 12: dragon), which is also the best fit (a shared palette would give more error and less contrast).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_enemies16 as B  # noqa: E402
import build_candle16 as C16  # noqa: E402
import build_enemies16_block2 as T  # noqa: E402
import build_items16 as I  # noqa: E402

ROOT = B.ROOT
GEN = B.GEN
GROUPS = ('s10', 's11z', 's11', 's12')       # palettes: vk_enemy16b4_palette[0..3]
GAP_MAX = 9                                  # blank MSX gaps of at most this many cells are stored as blank cells
LATE_CELLS = 6                               # the late pool cells the stage 12 rooms load
SPHERE = [(4, 0, 0), (7, 0, 1), (7, 0, 1), (6, 3, 1), (7, 5, 4)]


def msx_block(stage):
    return B.nums((GEN / ('stage%d_enemies_md.c' % stage)).read_text(), r'const (?:unsigned long|u32) vk_stage%d_enemy_tiles' % stage)


def msx_bat():
    return B.nums((GEN / 'stage10_enemies_md.c').read_text(), r'const (?:unsigned long|u32) vk_stage10_bat_tiles')


def msx_zombie():
    # without the /* pattern 40 */ comments of enemy_sprites_md.c (B.Msx().words would read their numbers as words)
    words = B.nums(re.sub(r'/\*.*?\*/', '', B.Msx().text, flags=re.S), r'const (?:unsigned long|u32) vk_enemy_tiles')
    assert len(words) == 12 * 32
    return words


def late_text():
    return (GEN / 'late_graphics.inc').read_text()


def late_words():
    t = late_text().split('late_graphics_words')[1]
    return [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{8})', t)]


def late_stage12():
    """{(type, pattern): pool cell} of the stage 12 rooms, and the set of pool cells they load."""
    t = late_text()
    rooms = [tuple(map(int, x.split(','))) for x in
             re.findall(r'\{(\d+,\d+,\d+,\d+)\}', re.search(r'late_graphics_rooms\[7\]\[12\]=\{(.*?)\};', t).group(1))]
    cells = [tuple(map(int, x.split(','))) for x in
             re.findall(r'\{(\d+,\d+,\d+)\}', re.search(r'late_graphics_cells\[\]=\{(.*?)\};', t).group(1))]
    slots = [int(x) for x in re.search(r'late_graphics_slots\[\]=\{(.*?)\};', t).group(1).split(',')]
    where, used = {}, set()
    for first, tiles, cfirst, n in rooms[:12]:
        sl = slots[first:first + tiles // 4]
        used |= set(sl)
        for typ, pat, c in cells[cfirst:cfirst + n]:
            assert where.get((typ, pat), sl[c]) == sl[c]
            where[(typ, pat)] = sl[c]
    return where, used


def room_palettes():
    """{(stage, room): MSX palette} of the rooms that take vk_enemy16b4_palette (stages 10 to 12, not the stage 12 boss room)."""
    t = (GEN / 'rooms.c').read_text()
    m = re.search(r'vk_palettes\[\]\[16\] = \{(.*?)\n\};', t, re.S)
    allp = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    st = re.search(r'vk_stages\[18\] = \{(.*?)\};', t, re.S)
    stages = [tuple(int(x) for x in re.findall(r'\d+', e)) for e in re.findall(r'\{([^{}]*)\}', st.group(1))]
    pals = {}
    for s in (10, 11, 12):
        first, count, _ = stages[s - 1]
        for r in range(count):
            if s == 12 and r == 6:
                continue
            pals[(s, r)] = allp[(first + r) * 16:(first + r) * 16 + 16]
    return pals


def group_of(stage, room):
    """The palette of a room: the choice of vk_gfx16_pal2 (gfx16.c). The rooms of the bone dragon (stage 11 room 5, stage 12)
    share one; stage 11 rooms 1 to 4 (eagle, flea) have theirs."""
    return 's10' if stage == 10 else 's12' if stage == 12 or room == 5 else 's11' if room else 's11z'


# ---- pictures ------------------------------------------------------------------------------------------------

def blank():
    return [[None] * 16 for _ in range(16)]


def side_by_side(a, b):
    return [ra + rb for ra, rb in zip(a, b)]


def jobs(b4, cv):
    """[dict(name, img, mode, size, target, group, cells=[(cell, x, y)], ref=[(cell, x, y)] or None, layered)]

    target: 's10' / 's11' (pattern N of the block), 'bat10' / 'zomb11' (cell c of the array, MSX layers c, c + 1),
    'late12' (pool cell). `img` is laid on the canvas against the MSX picture of the `ref` cells (default: `cells`),
    `img` already a canvas when mode is None."""
    out = []

    def job(name, img, mode, size, target, cells, ref=None, crop=True, group=None):
        if mode and crop:
            img = B.crop(img)
        out.append(dict(name=name, img=img, mode=mode, size=size, target=target, cells=cells, ref=ref or cells,
                        group=group or TARGET_GROUP[target]))

    def both(name, img, mode, size, target, left, right, crop=True):
        job(name, img, mode, size, target, left, crop=crop)
        job(name + ' R', B.mirror(B.crop(img) if crop else img), mode, size, target, right, crop=False)

    # stage 10: fishman (16 x 32, top + bottom), fire pose, shot, drop
    fish_a, fish_b, fish_fire = cv.pose(44), cv.pose(45), cv.pose(46)
    both('fish0F', fish_a, 'feet', (16, 32), 's10', [(0x40, 0, 0), (0x44, 0, 16)], [(0x54, 0, 0), (0x58, 0, 16)], crop=False)
    both('fish10', fish_b, 'feet', (16, 32), 's10', [(0x48, 0, 16)], [(0x5C, 0, 16)], crop=False)
    out[-2]['ref'] = [(0x40, 0, 0), (0x48, 0, 16)]
    out[-1]['ref'] = [(0x54, 0, 0), (0x5C, 0, 16)]
    both('fish_fire', fish_fire, 'feet', (16, 32), 's10', [(0x4C, 0, 0), (0x50, 0, 16)], [(0x64, 0, 0), (0x68, 0, 16)])
    job('shot10', I.sphere(SPHERE, 8), 'centre', (16, 16), 's10', [(0x60, 0, 0)])
    job('drop', cv.pose(49), 'feet', (16, 16), 's10', [(0x90, 0, 0)])
    # stage 10 room 0: bat, wings flat / half / wide (cells 0 2 4, right 6 8 10 mirrored) = obj_42, obj_43, obj_41 as in block 1
    # (the blue b4_rbat of block 4, tried first, hardly showed on the blue rock of the 16-bit cave; this one is dark red and
    # lilac, and has the three poses)
    for obj, left, right in ((42, 0, 6), (43, 2, 8), (41, 4, 10)):
        both('bat%d' % left, cv.pose(obj), 'centre', (16, 16), 'bat10', [(left, 0, 0)], [(right, 0, 0)])
    # stage 11: eagle. MSX cells: head (X - 16, Y - 22, pose 8D Y - 24) shared by the three poses + wing column (X, Y - 30 /
    # Y - 14) per pose. One head cell for all poses left the left half of the 16-bit eagle (its second wing, its body) frozen
    # while the right half flapped (tester, 2026-11): in 16-bit mode the eagle is drawn as a 32 x 32 canvas of four cells
    # (top left, bottom left, top right, bottom right) per pose, the left column in cells that the MSX layout leaves blank
    # (44 / 4C / 54 / 5C / 64) and that actors.c (show_enemy_sprites) shows through two extra sprite entries. Poses 6D and 8D
    # have the same picture (b4_eagle0) and share the left cells 40 / 44; 6E (b4_eagle1) has 4C / 54.
    e0, e1 = b4.sprite('b4_eagle0'), b4.sprite('b4_eagle1')
    assert len(e0) == len(e1) == 32 and len(e0[0]) == len(e1[0]) == 32
    for name, img, left, (top, bottom) in (('eagle6D', e0, (0x40, 0x44), (0x48, 0x50)), ('eagle6E', e1, (0x4C, 0x54), (0x58, 0x60)),
                                           ('eagle8D', e0, (0x40, 0x44), (0x68, 0x70))):
        job(name, img, None, (32, 32), 's11', [(left[0], 0, 0), (left[1], 0, 16), (top, 16, 0), (bottom, 16, 16)])
    # stage 11: flea (objects 0D and 23h)
    both('flea_stand', b4.sprite('b4_flea_stand'), 'feet', (16, 16), 's11', [(0x80, 0, 0)], [(0x88, 0, 0)])
    both('flea_jump', b4.sprite('b4_flea_jump'), 'feet', (16, 16), 's11', [(0x84, 0, 0)], [(0x8C, 0, 0)])
    # bone dragon (stage 11 room 5; stage 12, where the late pool takes the same cells: see build()): closed head, body (two
    # vertebrae), open head; its shot. Palette of the dragon rooms (s12).
    vert = B.crop(b4.sprite('b4_vert'))
    body = side_by_side(vert, vert)
    job('dragon_closed', b4.sprite('b4_dragon0'), 'centre', (16, 16), 's11', [(0x90, 0, 0)], group='s12')
    job('dragon_body', body, 'centre', (16, 16), 's11', [(0x94, 0, 0)], group='s12')
    job('dragon_open', b4.sprite('b4_dragon1'), 'centre', (16, 16), 's11', [(0x98, 0, 0)], group='s12')
    job('shot', I.sphere(SPHERE, 8), 'centre', (16, 16), 's11', [(0x9C, 0, 0)], group='s12')
    # stage 11 room 0: zombies, the jobs of block 1 (vk_enemy_tiles layout, type B mirrored)
    for base, mir in ((0, False), (6, True)):
        for obj, write, ref in ((6, [(base, 0, 0), (base + 2, 0, 16)], [(base, 0, 0), (base + 2, 0, 16)]),
                                (7, [(base + 4, 0, 16)], [(base, 0, 0), (base + 4, 0, 16)])):
            img = cv.pose(obj)
            job('zombie%d%s' % (obj, ' R' if mir else ''), B.mirror(img) if mir else img, 'feet', (16, 32), 'zomb11', write,
                ref=ref, crop=False)
    return out


TARGET_GROUP = {'s10': 's10', 'bat10': 's10', 's11': 's11', 'zomb11': 's11z'}
EAGLE_LEFT = (0x40, 0x44, 0x4C, 0x54)         # stage 11 left column of the eagle: 40 / 44 (6D, 8D), 4C / 54 (6E); 44, 4C, 54 are blank on the MSX
DRAGON = (0x90, 0x94, 0x98, 0x9C)            # stage 11 cells of the dragon and its shot = late pool cells 0 to 3 of stage 12


def msx_cell(target, c):
    """The MSX picture (colour numbers) of cell c of a target, both layers."""
    if target in ('s10', 's11'):
        return B.Msx.cell(msx_block(int(target[1:])), (c - 0x40) // 4)
    if target == 'late12':
        return B.Msx.cell(late_words(), c)
    words = msx_bat() if target == 'bat10' else msx_zombie()
    return B.Msx().layers(words, c, c + 1)


def laid(js):
    res = []
    for j in js:
        if j['mode'] is None:
            res.append((j, j['img']))
            continue
        cw, ch = j['size']
        ref = B.ref_box(B.canvas_of([(x, y, msx_cell(j['target'], c)) for c, x, y in j['ref']]))
        res.append((j, B.place(j['img'], cw, ch, ref, j['mode'])))
    return res


# ---- palettes ------------------------------------------------------------------------------------------------

ALL_COLOURS = [(r, g, b) for r in range(8) for g in range(8) for b in range(8)]


def refine(colours, fixed, free):
    """The free entries of B.choose_free (colours of the pictures) moved to any of the 512 MD colours while the weighted
    error goes down (block 4 only: blocks 1 to 3 keep their palettes)."""
    def total(f):
        cents = fixed + list(f)
        return sum(k * min(B.dist(c, q) for q in cents) ** .5 for c, k in colours.items())
    best = total(free)
    improved = True
    while improved:
        improved = False
        for i in range(len(free)):
            for c in ALL_COLOURS:
                if c in free:
                    continue
                t = free[:]
                t[i] = c
                v = total(t)
                if v < best - 1e-9:
                    free, best, improved = t, v, True
    return free, best / sum(colours.values())


def build_palettes(pics):
    rooms = room_palettes()
    out, errs, counts = {}, {}, {}
    for g in GROUPS:
        pals = [p for (s, r), p in rooms.items() if group_of(s, r) == g]
        for p in pals:
            assert [p[i] for i in B.FIXED] == [pals[0][i] for i in B.FIXED], ('fixed MSX colours differ between rooms', g)
        pal = [0] * 16
        for i in B.FIXED:
            pal[i] = pals[0][i]
        colours, seen = {}, set()
        for j, img in pics:                      # the pixels of the cells written (each cell once)
            for c, x, y in j['cells']:
                if j['group'] != g or (j['target'], c) in seen:
                    continue
                seen.add((j['target'], c))
                for row in img[y:y + 16]:
                    for p in row[x:x + 16]:
                        if p is not None:
                            colours[p] = colours.get(p, 0) + 1
        free, err = B.choose_free(colours, [B.lvl(pal[i]) for i in B.FIXED])
        free, err = refine(colours, [B.lvl(pal[i]) for i in B.FIXED], free)
        for i, c in zip(B.FREE, free):
            pal[i] = B.word(c)
        out[g], errs[g], counts[g] = pal, err, sum(colours.values())
    return out, errs, counts


# ---- cells ---------------------------------------------------------------------------------------------------

def build(b4, cv):
    pics = laid(jobs(b4, cv))
    pals, errs, counts = build_palettes(pics)
    cells = {t: {} for t in TARGET_GROUP}
    for j, img in pics:
        pal = pals[j['group']]
        for c, x, y in j['cells']:
            rows = [[0 if img[y + dy][x + dx] is None else B.to_index(pal, img[y + dy][x + dx])
                     for dx in range(16)] for dy in range(16)]
            tiles = B.cell_tiles(rows)
            assert cells[j['target']].get(c, tiles) == tiles, 'cell %s %02X written twice with other pixels' % (j['target'], c)
            cells[j['target']][c] = tiles
    # type 5 blocks: pool in pattern order, blank MSX gaps of one cell between 16-bit cells filled with a blank cell
    pool, lists = [], {}
    for blk in ('s10', 's11'):
        words = msx_block(int(blk[1:]))
        pats = sorted(cells[blk])
        full = []
        for a, b in zip(pats, pats[1:] + [None]):
            full.append(a)
            gap = range(a + 4, b, 4) if b is not None else ()
            if len(gap) <= GAP_MAX and not any(any(words[((p - 0x40) // 4) * 32:((p - 0x40) // 4 + 1) * 32]) for p in gap):
                full.extend(gap)
        lists[blk] = []
        for p in full:
            lists[blk].append((p, len(pool)))
            pool.append(cells[blk].get(p, [0] * 32))
        # one run from pattern 40: the room loads it in one transfer, then the MSX cells after it (gfx16.c)
        assert [p for p, k in lists[blk]] == list(range(0x40, 0x40 + 4 * len(full), 4)), blk
    # Stage 12: the late pool cells its rooms load are 0 to 5 (late_graphics.inc): the dragon (closed head, body, open head)
    # and its shot in 0 to 3, object 1B in 4 and 5. Cells 0 to 3 are the stage 11 cells 90 to 9C (same palette): the pool
    # goes on with the two MSX cells of object 1B, and vk_enemy16b4_cells + 32 * VK_ENEMY16B4_LATE_CELL stands for
    # late_graphics_words in the stage 12 rooms (same slots, same transfers).
    where, used = late_stage12()
    assert [where[(19, 0x90)], where[(19, 0x94)], where[(19, 0x98)], where[(10, 0x60)], where[(10, 0xF0)]] == [0, 1, 2, 3, 3]
    assert used == set(range(LATE_CELLS)), used
    late = [k for p, k in lists['s11'] if p == DRAGON[0]][0]
    assert [p for p, k in lists['s11'][-4:]] == list(DRAGON) and lists['s11'][-4][1] == late and late + 4 == len(pool)
    lw = late_words()
    for c in range(4, LATE_CELLS):
        pool.append(C16.blob_b_cells()[c - 4])      # object 1B (cells 4, 5): the 16-bit blob (build_candle16.py)
    arrays = {}
    for t in ('bat10', 'zomb11'):
        arrays[t] = [w for c in range(12) for w in cells[t].get(c, [0] * 32)]
    err = sum(errs[g] * counts[g] for g in GROUPS) / sum(counts.values())
    return pool, lists, arrays, pals, errs, err, late


def write(pool, lists, arrays, pals, late):
    h = ['/* Generated by tools/build_enemies16_block4.py (Castlevania-MD art, research/gfx16.md). Common enemies of stages 10',
         ' * to 12 (not the stage 12 boss room) in 16-bit mode, in the layouts of the MSX arrays they replace. */',
         '#ifndef VK_ENEMIES16B4_MD_H', '#define VK_ENEMIES16B4_MD_H', '#include <genesis.h>',
         '/* PAL2 of those rooms: the MSX colours other content uses keep their entries; the free ones hold the 16-bit colours.',
         ' * One palette per group of rooms: [0] stage 10, [1] stage 11 room 0 (zombies), [2] stage 11 rooms 1-4 (eagle, flea),',
         ' * [3] stage 11 room 5 and stage 12 (bone dragon). */',
         'extern const u16 vk_enemy16b4_palette[4][16];',
         '/* Cells of the type 5 blocks of stages 10 and 11 (pattern N is tile N - 0x40), 16 x 16, four tiles each, in pattern',
         ' * order; then the two MSX cells of object 1B of the stage 12 late pool. */',
         '#define VK_ENEMY16B4_CELLS %d' % len(pool),
         'extern const u32 vk_enemy16b4_cells[%d];' % (len(pool) * 32),
         '/* Per block: its 16-bit cells are one run of the pool, patterns 40, 44, ... (the blank MSX cells between them',
         ' * stored blank): first pool cell and number of cells; the MSX cells after the run are loaded as they are. */']
    for blk in ('s10', 's11'):
        h.append('#define VK_ENEMY16B4_STAGE%s_CELL %d' % (blk[1:], lists[blk][0][1]))
        h.append('#define VK_ENEMY16B4_STAGE%s_CELLS %d' % (blk[1:], len(lists[blk])))
    h += ['/* Same layout as vk_stage10_bat_tiles (stage 10 room 0) and vk_enemy_tiles (zombies, stage 11 room 0). */',
          'extern const u32 vk_enemy16b4_bat_tiles[%d];' % len(arrays['bat10']),
          'extern const u32 vk_enemy16b4_zombie_tiles[%d];' % len(arrays['zomb11']),
          '/* Stage 12: the late pool cells its rooms load are 0 to %d (dragon, its shot, object 1B); from this cell on, the pool' % (LATE_CELLS - 1),
          ' * holds them in that order (16-bit dragon and shot, MSX object 1B): it stands for late_graphics_words. */',
          '#define VK_ENEMY16B4_LATE_CELL %d' % late,
          '#define VK_ENEMY16B4_LATE_CELLS %d' % LATE_CELLS,
          '#endif']
    c = ['/* Generated by tools/build_enemies16_block4.py. */', '#include "enemies16b4_md.h"',
         'const u16 vk_enemy16b4_palette[4][16] = {\n%s\n};' % ',\n'.join('{\n%s\n}' % B.fmt(pals[g], 4) for g in GROUPS),
         'const u32 vk_enemy16b4_cells[%d] = {\n%s\n};' % (len(pool) * 32, B.fmt([w for cell in pool for w in cell], 8))]
    for t, name in (('bat10', 'bat_tiles'), ('zomb11', 'zombie_tiles')):
        c.append('const u32 vk_enemy16b4_%s[%d] = {\n%s\n};' % (name, len(arrays[t]), B.fmt(arrays[t], 8)))
    (GEN / 'enemies16b4_md.h').write_text('\n'.join(h) + '\n')
    (GEN / 'enemies16b4_md.c').write_text('\n'.join(c) + '\n')


def data_size(pool, lists, arrays):
    return (len(pool) * 128 + 4 * 32 +
            sum(4 * len(a) for a in arrays.values()))


def preview(pool, lists, arrays, pals, path):
    """MSX cell (its room palette) next to the 16-bit cell (the palette of its rooms), for every drawn cell."""
    from PIL import Image, ImageDraw
    S = 4
    rooms = room_palettes()
    rows = []

    def rgb(pal):
        return [(0, 0, 0)] + [tuple(v * 36 for v in B.lvl(pal[i])) for i in range(1, 16)]
    for blk in ('s10', 's11'):
        words = msx_block(int(blk[1:]))
        for p, k in lists[blk]:
            room = (10, 1) if blk == 's10' else (11, 5) if p in DRAGON else (11, 2)
            if any(pool[k]):
                rows.append(('%s %02X' % (blk, p), B.Msx.cell(words, (p - 0x40) // 4), B.Msx.cell(pool[k], 0),
                             rgb(rooms[room]), rgb(pals[group_of(*room)])))
    for t, words, room in (('bat10', msx_bat(), (10, 0)), ('zomb11', msx_zombie(), (11, 0))):
        for c in range(0, len(arrays[t]) // 32, 2):
            rows.append(('%s %d' % (t, c), B.Msx().layers(words, c, c + 1), B.Msx.cell(arrays[t], c),
                         rgb(rooms[room]), rgb(pals[group_of(*room)])))
    cols = 6
    nrow = (len(rows) + cols - 1) // cols
    im = Image.new('RGB', (cols * (36 * S + 8), nrow * (18 * S + 14)), (90, 100, 120))
    d = ImageDraw.Draw(im)
    for n, (lab, a, b, pa, pb) in enumerate(rows):
        ox, oy = (n % cols) * (36 * S + 8), (n // cols) * (18 * S + 14)
        d.text((ox, oy), lab, fill=(255, 255, 255))
        for dx, px, mp in ((0, a, pa), (17 * S + 4, b, pb)):
            for y in range(16):
                for x in range(16):
                    if px[y][x]:
                        d.rectangle([ox + dx + x * S, oy + 12 + y * S, ox + dx + x * S + S - 1, oy + 12 + y * S + S - 1],
                                    fill=mp[px[y][x]])
    im.save(path)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    b4, cv = T.Block(sys.argv[1], 4), B.CV(sys.argv[1])
    pool, lists, arrays, pals, errs, err, late = build(b4, cv)
    write(pool, lists, arrays, pals, late)
    print('pool %d cells (stage 10: %d, stage 11: %d, late from %d), data %d B, mean colour error %.1f/255 (%s)' % (
        len(pool), len(lists['s10']), len(lists['s11']), late, data_size(pool, lists, arrays), err,
        ', '.join('%s %.1f' % (g, errs[g]) for g in GROUPS)))
    for g in GROUPS:
        print('  palette %-4s %s' % (g, ' '.join('%03X' % w for w in pals[g])))
    if '--preview' in sys.argv:
        preview(pool, lists, arrays, pals, sys.argv[sys.argv.index('--preview') + 1])


if __name__ == '__main__':
    main()

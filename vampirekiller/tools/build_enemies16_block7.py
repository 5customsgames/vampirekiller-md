#!/usr/bin/env python3
"""Common enemies of block 7 (stage 18, not the final boss room and not object 1B) in the 16-bit art
(research/gfx16.md, section "Ennemis 16 bits (bloc 7)").

usage: build_enemies16_block7.py <castlevania-md checkout> [--preview FILE.png] [--board FILE.png] [--orient]

Same method as tools/build_enemies16_block6.py (late enemy pool, pictures stored by pool slot, so a room loads the same slots with
the same transfers and tile count from vk_enemy16b7_cells instead of late_graphics_words). Stage 18 has two common enemies, both
already drawn for stage 17:
    raw 10 (internal 20) axe knight + its axe (internal 21): rooms 1, 2 and 8, pool slots 42 to 66, as stage 17 rooms 3 to 5
    raw 0D (internal 14) flea: rooms 3 to 7, pool slots 38 to 41, as stage 17 rooms 2 and 6 to 10
    object 1B (internal 15, slots 4 and 5, rooms 3 and 4): kept MSX.
The pictures are those of block 6 (b6_flea_*, b5_axek / b5_kaxe, sphere of the axe), laid on the MSX poses the same way. The
palettes differ: the MSX room palette of stage 18 has entry 8 = 226 (888 at stages 16 and 17), so the entries the other PAL2 content
reads are not the same colours and the block 6 cells (indices into the block 6 palettes) cannot be reused as they are. Two palettes,
one per kind of rooms, each with the colours of its enemy only: [0] rooms 3 to 7 (flea, entry 7 = 66C), [1] rooms 1, 2 and 8
(axe knight, axe, entry 7 = 26C). Room 0 (no cell), rooms 9 to 11 (boss, no common enemy) stay MSX.
"""
import functools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_enemies16 as B  # noqa: E402
import build_candle16 as C16  # noqa: E402
import build_enemies16_block2 as T  # noqa: E402
import build_enemies16_block5 as T5  # noqa: E402
import build_enemies16_block6 as B6  # noqa: E402

ROOT = B.ROOT
GEN = B.GEN
STAGE = 18
SLOTS = 67                                   # pool slots 0 .. 66 are stored (stage 18 uses 4, 5 and 38 to 66)
VARIABLE = 7
GROUPS = 2
KIND = {14: 'flea', 20: 'axe', 21: 'axe'}
GROUP_OF_KIND = {'flea': 0, 'axe': 1}
GROUP_KINDS = {g: [k for k, v in GROUP_OF_KIND.items() if v == g] for g in range(GROUPS)}
FREE = B.FREE


def group_of(room):
    """The palette of a room: the choice of vk_gfx16_pal2 (gfx16.c)."""
    return 1 if room in (1, 2, 8) else 0


@functools.lru_cache(maxsize=None)
def enemy_rooms():
    """{room: [(type, pattern, slot)]} of the rooms of stage 18 that load cells."""
    rooms, cells, slots = T5.late_tables()
    out = {}
    for r in range(12):
        first, tiles, cf, n = rooms[(STAGE - 12) * 12 + r]
        if tiles:
            sl = slots[first:first + tiles // 4]
            out[r] = [(ty, p, sl[c]) for ty, p, c in cells[cf:cf + n]]
    return out


@functools.lru_cache(maxsize=None)
def slot_map():
    where = {}
    for lst in enemy_rooms().values():
        for ty, p, slot in lst:
            assert where.setdefault((ty, p), slot) == slot, (ty, p)
    return where


@functools.lru_cache(maxsize=None)
def room_info():
    """{room: (MSX palette, group, kinds)} of the rooms with an enemy of the block (not a room with object 1B only)."""
    pal = T5.msx_palettes()
    info = {}
    for r, lst in enemy_rooms().items():
        kinds = {KIND[ty] for ty, _, _ in lst if ty in KIND}
        if not kinds:
            continue
        assert {GROUP_OF_KIND[k] for k in kinds} == {group_of(r)}, (r, kinds)
        info[r] = (pal(STAGE, r), group_of(r), kinds)
    return info


@functools.lru_cache(maxsize=None)
def group_fixed():
    out = {}
    for g in range(GROUPS):
        pals = [p for p, gg, k in room_info().values() if gg == g]
        for p in pals:
            assert [p[i] for i in B.FIXED] == [pals[0][i] for i in B.FIXED], ('fixed MSX colours differ in group', g)
        out[g] = ({i: pals[0][i] for i in B.FIXED if i != VARIABLE}, pals[0][VARIABLE])
    return out


def jobs(b6, b5, b4, cv):
    """The jobs of block 6 for the flea and the axe knight (same pictures, same cells: same pool slots at stage 18)."""
    out = [j for j in B6.jobs(b6, b5, b4, cv) if j['kind'] in GROUP_OF_KIND]
    assert {j['kind'] for j in out} == set(GROUP_OF_KIND)
    return out


def msx_cell(ty, p):
    return B.Msx.cell(T5.pool_words(), slot_map()[(ty, p)])


def msx_canvas(j):
    return B.canvas_of([(x, y, msx_cell(ty, p)) for ty, p, x, y in j['ref']])


def laid(js):
    res = []
    for j in js:
        cw, ch = j['size']
        ref = B.ref_box(msx_canvas(j))
        res.append((j, B.place(j['img'], cw, ch, ref, j['mode']), ref))
    return res


def histograms(pics):
    hist, seen = {}, set()
    for j, img, ref in pics:
        for ty, p, x, y in j['cells']:
            if (ty, p) in seen:
                continue
            seen.add((ty, p))
            h = hist.setdefault(j['kind'], {})
            for row in img[y:y + 16]:
                for c in row[x:x + 16]:
                    if c is not None:
                        h[c] = h.get(c, 0) + 1
    return hist


def build_palettes(pics):
    hist = histograms(pics)
    pals, allowed, errs = [], [], {}
    for g in range(GROUPS):
        fixed, seven = group_fixed()[g]
        base = [B.lvl(w) for w in fixed.values()] + [B.lvl(seven)]
        merged = {}
        for k in GROUP_KINDS[g]:
            for c, n in hist[k].items():
                merged[c] = merged.get(c, 0) + n
        free, _ = T5.optimise(len(FREE), lambda f: T5.err_of(merged, base + list(f)), merged)
        pal = [0] * 16
        for i, w in fixed.items():
            pal[i] = w
        pal[VARIABLE] = seven
        for i, col in zip(FREE, free):
            pal[i] = B.word(col)
        pals.append(pal)
        idx = sorted(set(fixed) | {VARIABLE} | set(FREE))
        allowed.append(idx)
        for k in GROUP_KINDS[g]:
            errs[k] = T5.err_of(hist[k], [B.lvl(pal[i]) for i in idx]) / sum(hist[k].values())
    return pals, allowed, errs, hist


def build(b6, b5, b4, cv):
    pics = laid(jobs(b6, b5, b4, cv))
    pals, allowed, errs, hist = build_palettes(pics)
    words = T5.pool_words()
    smap = slot_map()
    pool = [[0] * 32 for s in range(SLOTS)]
    pool[4], pool[5] = C16.blob_b_cells()                       # object 1B (slots 4, 5): the 16-bit blob (build_candle16.py)
    written = {}
    for j, img, ref in pics:
        g = GROUP_OF_KIND[j['kind']]
        for ty, p, x, y in j['cells']:
            rows = [[0 if img[y + dy][x + dx] is None else T5.to_index(pals[g], img[y + dy][x + dx], allowed[g])
                     for dx in range(16)] for dy in range(16)]
            tiles = B.cell_tiles(rows)
            assert written.get((ty, p), tiles) == tiles, 'cell %d %02X written twice with other pixels' % (ty, p)
            written[(ty, p)] = tiles
            pool[smap[(ty, p)]] = tiles
        for ty, p in j['blanks']:
            assert written.get((ty, p), [0] * 32) == [0] * 32, 'cell %d %02X blank and drawn' % (ty, p)
            written[(ty, p)] = [0] * 32
            pool[smap[(ty, p)]] = [0] * 32
    by_slot = {}
    for key, s in smap.items():
        if key in written:
            assert by_slot.setdefault(s, written[key]) == written[key], ('slot %d shared with other pixels' % s, key)
    return pool, pals, allowed, errs, hist, written, pics


def write(pool, pals):
    h = ['/* Generated by tools/build_enemies16_block7.py (Castlevania-MD art, research/gfx16.md). Common enemies of stage 18',
         ' * in 16-bit mode, in the layout of the late enemy pool they replace. */',
         '#ifndef VK_ENEMIES16B7_MD_H', '#define VK_ENEMIES16B7_MD_H', '#include <genesis.h>',
         '/* PAL2 of those rooms: the MSX colours other content uses keep their entries; the free ones hold the 16-bit colours.',
         ' * [0] stage 18 rooms 3 to 7 (flea), [1] rooms 1, 2 and 8 (axe knight). */',
         'extern const u16 vk_enemy16b7_palette[%d][16];' % GROUPS,
         '/* The late pool of the rooms of stage 18, in the order of late_graphics_words (cell N is the pool slot N of',
         ' * late_graphics_slots, 4 tiles of 8 words): slots 38 to 66 with the 16-bit pictures, slots 4 and 5 (object 1B) as',
         ' * they are, the others blank. */',
         '#define VK_ENEMY16B7_SLOTS %d' % SLOTS,
         'extern const u32 vk_enemy16b7_cells[%d];' % (SLOTS * 32),
         '#endif']
    c = ['/* Generated by tools/build_enemies16_block7.py. */', '#include "enemies16b7_md.h"',
         'const u16 vk_enemy16b7_palette[%d][16] = {\n%s\n};' % (GROUPS, ',\n'.join('{\n%s\n}' % B.fmt(p, 4) for p in pals)),
         'const u32 vk_enemy16b7_cells[%d] = {\n%s\n};' % (SLOTS * 32, B.fmt([w for cell in pool for w in cell], 8))]
    (GEN / 'enemies16b7_md.h').write_text('\n'.join(h) + '\n')
    (GEN / 'enemies16b7_md.c').write_text('\n'.join(c) + '\n')


def data_size():
    return SLOTS * 128 + GROUPS * 32


def rgb(pal):
    return [(0, 0, 0)] + [tuple(v * 36 for v in B.lvl(pal[i])) for i in range(1, 16)]


def _room_of():
    room_of = {}
    for r, (p, g, kinds) in room_info().items():
        room_of.setdefault(g, p)
    return room_of


def preview(pool, pals, path):
    from PIL import Image, ImageDraw
    S = 4
    smap = slot_map()
    room_of = _room_of()
    words = T5.pool_words()
    rows = []
    for (ty, p), slot in sorted(smap.items(), key=lambda kv: kv[1]):
        if ty not in KIND:
            continue
        g = GROUP_OF_KIND[KIND[ty]]
        rows.append(('t%d %02X g%d' % (ty, p, g), B.Msx.cell(words, slot), B.Msx.cell(pool[slot], 0), rgb(room_of[g]), rgb(pals[g])))
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


def board(pool, pals, pics, path):
    """One row per pose: the MSX picture, the 16-bit picture on a dark wall, the 16-bit picture on mid grey with the outline (red)
    of the MSX silhouette."""
    from PIL import Image, ImageDraw
    S = 4
    smap = slot_map()
    room_of = _room_of()
    cellw, cellh = 100 * S, 36 * S + 16
    cols = 3
    items = [(j, img) for j, img, ref in pics]
    nrow = (len(items) + cols - 1) // cols
    im = Image.new('RGB', (cols * (cellw + 6) + 6, nrow * cellh + 6), (110, 110, 120))
    d = ImageDraw.Draw(im)
    for n, (j, img) in enumerate(items):
        g = GROUP_OF_KIND[j['kind']]
        ox, oy = (n % cols) * (cellw + 6) + 4, (n // cols) * cellh + 4
        d.text((ox, oy), j['name'], fill=(255, 255, 255))
        new = B.canvas_of([(x, y, B.Msx.cell(pool[smap[(ty, p)]], 0)) for ty, p, x, y in j['cells']])
        old = msx_canvas(j)
        mpal, npal = rgb(room_of[g]), rgb(pals[g])
        w, h = max(len(new[0]), len(old[0])), max(len(new), len(old))
        sil = {(x, y) for y, r in enumerate(old) for x, v in enumerate(r) if v}
        for k, (canv, pal, bg) in enumerate(((old, mpal, (70, 70, 80)), (new, npal, (70, 70, 80)), (new, npal, (150, 150, 160)))):
            bx = ox + k * (w * S + 8)
            d.rectangle([bx, oy + 12, bx + w * S - 1, oy + 12 + h * S - 1], fill=bg)
            for y, r in enumerate(canv):
                for x, v in enumerate(r):
                    if v:
                        d.rectangle([bx + x * S, oy + 12 + y * S, bx + x * S + S - 1, oy + 12 + y * S + S - 1], fill=pal[v])
            if k == 2:
                for (x, y) in sil:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        if (x + dx, y + dy) not in sil:
                            d.rectangle([bx + x * S + (S - 1 if dx > 0 else 0), oy + 12 + y * S + (S - 1 if dy > 0 else 0),
                                         bx + x * S + (S - 1 if dx >= 0 else 0), oy + 12 + y * S + (S - 1 if dy >= 0 else 0)],
                                        fill=(255, 0, 0))
    im.save(path)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    b6, b5, b4, cv = T.Block(root, 6), T.Block(root, 5), T.Block(root, 4), B.CV(root)
    if '--orient' in sys.argv:
        for j, img, ref in laid(jobs(b6, b5, b4, cv)):
            m = B.mirror([r[:] for r in img])
            print('%-14s iou %.2f mirrored %.2f' % (j['name'], T5.iou(img, msx_canvas(j)), T5.iou(m, msx_canvas(j))))
        return
    pool, pals, allowed, errs, hist, written, pics = build(b6, b5, b4, cv)
    write(pool, pals)
    tot = sum(sum(h.values()) for h in hist.values())
    err = sum(errs[k] * sum(hist[k].values()) for k in hist) / tot
    print('pool %d slots, data %d B, mean colour error %.1f/255 (%s)' % (
        SLOTS, data_size(), err, ', '.join('%s %.1f' % (k, errs[k]) for k in sorted(errs))))
    for g, p in enumerate(pals):
        print('  palette %d %s' % (g, ' '.join('%03X' % w for w in p)))
    if '--preview' in sys.argv:
        preview(pool, pals, sys.argv[sys.argv.index('--preview') + 1])
    if '--board' in sys.argv:
        board(pool, pals, pics, sys.argv[sys.argv.index('--board') + 1])


if __name__ == '__main__':
    main()

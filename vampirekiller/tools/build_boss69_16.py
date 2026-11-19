#!/usr/bin/env python3
"""Bosses of the stages 6 (giant Medusa head) and 9 (two mummies) in the 16-bit art (research/gfx16.md, section
"Boss des stages 6 et 9 en 16 bits").

usage: build_boss69_16.py <castlevania-md checkout> [--preview FILE.png]

Writes sgdk/src/generated/boss69_16_md.c/.h, arrays of the SAME layout as the MSX ones (boss6_md.c, boss9_md.c): the code
(poses, cells, positions, hit boxes, SAT, blink timing, loading) is the MSX one, only the pictures change.

- Stage 6 (vk_boss6_tiles, 8 cells of 16 x 16 = two poses of 32 x 32, then 4 snake cells; vk_orb6_tiles, 3 poses of
  32 x 32): Castlevania-MD block 2 (b2_mboss0, the Medusa head; its second pose b2_mboss1 is the ghost-white flash of that
  game, not used). Pose 2C is the same head with its two blue tones of hair swapped (the hair shimmers as the MSX one wriggles
  between the two poses). Fireball = the snake of block 2 (b2_snake0, b2_snake1; the MSX fireball is a snake too), the right
  cells are the mirror. Orb = obj_56 / obj_57 of level.c (as the stage 3 orb), standing on the lowest row of the MSX orb.
- Stage 9 (vk_boss9_tiles = 6 poses x 3 cells, then 2 fireball cells; vk_boss9_16_flash = the same 18 body cells in the
  blinking colours): b3_mummy0..2 (left, poses 33..35; mirrored for 36..38), blink = b3_mummyf0..2 (the orange bandages),
  fireball = b3_bandage and its mirror. The MSX recolours the cells at run time; the 16-bit blink cells are in ROM (72 tiles, 2 304 bytes), so the blink costs nothing.
- Palettes (PAL2 of the boss room, replacing the MSX one): the 9 entries other PAL2 content reads (1, 2, 3, 7, 8, 12, 13,
  14, 15) keep the MSX colour of the room; the others take the colours of the pictures that fit best (greedy + swaps).
  Stage 9 loads the orb of stage 6 too (actors.c), so it has its own copy (vk_orb9_16_tiles) drawn with its palette; entry 5 = 006
  there too. Stage 6: the orb writes entries 5 and 7 of PAL2 to 006 and 00A when it appears (actors.c): entry 5 already holds 006,
  and the orb is drawn with entry 7 = 00A; no body pixel uses entry 7 (it changes at that moment).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_enemies16 as E  # noqa: E402
import build_enemies16_block2 as T  # noqa: E402

GEN = E.GEN
FIXED = E.FIXED


def arr(file, name):
    return E.nums((GEN / file).read_text(), 'const (?:unsigned long|u32) ' + name)


def msx_room_palette(stage, room):
    t = (GEN / 'rooms.c').read_text()
    m = re.search(r'vk_palettes\[\]\[16\] = \{(.*?)\n\};', t, re.S)
    allp = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    st = re.search(r'vk_stages\[18\] = \{(.*?)\};', t, re.S)
    stages = [tuple(int(x) for x in re.findall(r'\d+', e)) for e in re.findall(r'\{([^{}]*)\}', st.group(1))]
    first = stages[stage - 1][0]
    return allp[(first + room) * 16:(first + room) * 16 + 16]


def msx_cell_rows(words, first):
    """Cell of 4 tiles (UL, LL, UR, LR) starting at tile `first` -> 16 x 16 indices."""
    out = [[0] * 16 for _ in range(16)]
    for t in range(4):
        cx, cy = (t // 2) * 8, (t % 2) * 8
        for y in range(8):
            w = words[(first + t) * 8 + y]
            for x in range(8):
                out[cy + y][cx + x] = (w >> (28 - 4 * x)) & 15
    return out


def msx_tiles(words, first, cols, rows):
    out = [[0] * (cols * 8) for _ in range(rows * 8)]
    i = first
    for c in range(cols):
        for r in range(rows):
            for y in range(8):
                w = words[i * 8 + y]
                for x in range(8):
                    out[r * 8 + y][c * 8 + x] = (w >> (28 - 4 * x)) & 15
            i += 1
    return out


def to_tiles(rows, cols, nrows):
    """rows of indices -> tiles column by column (as the MSX arrays)."""
    out = []
    for c in range(cols):
        for r in range(nrows):
            for y in range(8):
                out.append(sum(rows[r * 8 + y][c * 8 + x] << (28 - 4 * x) for x in range(8)))
    return out


def sub(rows, x, y, w, h):
    return [r[x:x + w] for r in rows[y:y + h]]


def swap_colours(img, a, b):
    return [[b if p == a else a if p == b else p for p in row] for row in img]


def nearest(pal, c, allowed):
    return min(allowed, key=lambda i: (E.dist(E.lvl(pal[i]), c), i))


def pal_for(room_pal, extra, pics, free):
    """PAL2: fixed entries from the room, `extra` {entry: colour word}, free entries chosen for the pictures."""
    pal = [0] * 16
    for i in FIXED:
        pal[i] = room_pal[i]
    for i, w in extra.items():
        pal[i] = w
    colours = {}
    for img in pics:
        for row in img:
            for p in row:
                if p is not None:
                    colours[p] = colours.get(p, 0) + 1
    E.FREE = tuple(free)
    fixed = [E.lvl(pal[i]) for i in list(FIXED) + list(extra)]
    chosen, err = E.choose_free(colours, fixed)
    for i, c in zip(free, chosen):
        pal[i] = E.word(c)
    return pal, err


def fmt(vals, width):
    f = '0x%%0%dX' % width
    return '\n'.join('    ' + ','.join(f % v for v in vals[i:i + 8]) + ',' for i in range(0, len(vals), 8))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cvroot = sys.argv[1]
    cv = E.CV(cvroot)
    b2, b3 = T.Block(cvroot, 2), T.Block(cvroot, 3)
    boss6 = arr('boss6_md.c', 'vk_boss6_tiles')
    orb6 = arr('boss6_md.c', 'vk_orb6_tiles')
    boss9 = arr('boss9_md.c', 'vk_boss9_tiles')
    assert len(boss6) == 48 * 8 and len(orb6) == 48 * 8 and len(boss9) == 80 * 8

    # ================= stage 6 pictures (levels or None on canvases) =================
    head = b2.sprite('b2_mboss0')
    assert (len(head[0]), len(head)) == (32, 32)
    blues = sorted({p for r in head for p in r if p and p[2] > p[0] + 2}, key=lambda c: sum(c))
    assert len(blues) >= 2, blues
    head2 = swap_colours(head, blues[-1], blues[-2])             # the two lightest blue tones swapped
    heads = [head, head2]
    snake = [b2.sprite('b2_snake0'), b2.sprite('b2_snake1')]
    shots6 = []
    for k, s in enumerate(snake + [E.mirror(x) for x in snake]):        # poses 27, 28 left; 29, 2A right
        ref = E.ref_box(msx_tiles(boss6, 32 + 4 * k, 2, 2))
        shots6.append(E.place(E.crop(s), 16, 16, ref, 'centre'))
    oref = E.ref_box(msx_tiles(orb6, 0, 4, 4))
    orbs6 = [E.place(E.crop(cv.pose(o)), 32, 32, oref, 'feet') for o in (56, 57, 56)]

    # ================= stage 9 pictures =================
    mum = [b3.sprite('b3_mummy%d' % k) for k in range(3)]
    mumf = [b3.sprite('b3_mummyf%d' % k) for k in range(3)]
    for im in mum + mumf:
        assert (len(im[0]), len(im)) == (16, 48)
    band = b3.sprite('b3_bandage')
    shots9 = []
    for k, s in enumerate((band, E.mirror(band))):
        ref = E.ref_box(msx_tiles(boss9, 72 + 4 * k, 2, 2))
        shots9.append(E.place(E.crop(s), 16, 16, ref, 'centre'))
    bodies9 = [m for m in mum] + [E.mirror(m) for m in mum]          # poses 33..35, 36..38
    flash9 = [m for m in mumf] + [E.mirror(m) for m in mumf]

    # ================= palettes =================
    p6 = msx_room_palette(6, 5)
    p9 = msx_room_palette(9, 7)
    pal6_extra = {5: 0x006}
    post6 = {5: 0x006, 7: 0x00A}                                   # what the orb writes (actors.c)
    pal6, err6 = pal_for(p6, pal6_extra, heads + shots6 + orbs6, (4, 6, 9, 10, 11))
    pal9, err9 = pal_for(p9, pal6_extra, bodies9 + flash9 + shots9 + orbs6, (4, 6, 9, 10, 11))
    pal6_post, pal9_post = pal6[:], pal9[:]
    for i, w in post6.items():
        pal6_post[i] = w
        pal9_post[i] = w

    def mapper(pal, avoid=()):
        allowed = [i for i in range(1, 16) if i not in avoid]
        cache = {}

        def idx(p):
            if p is None:
                return 0
            if p not in cache:
                cache[p] = nearest(pal, p, allowed)
            return cache[p]
        return idx
    body6 = mapper(pal6, avoid=(7,))
    orb_idx = mapper(pal6_post)
    orb9_idx = mapper(pal9_post)
    i9 = mapper(pal9)

    # ================= tiles =================
    t6 = []
    for pose in range(2):
        for i in range(4):                                  # UL, LL, UR, LR of the 32 x 32 head
            cell = sub(heads[pose], 16 * (i >> 1), 16 * (i & 1), 16, 16)
            t6 += to_tiles([[body6(p) for p in r] for r in cell], 2, 2)
    for s in shots6:
        t6 += to_tiles([[body6(p) for p in r] for r in s], 2, 2)
    o6 = []
    for o in orbs6:
        o6 += to_tiles([[orb_idx(p) for p in r] for r in o], 4, 4)
    o9 = []
    for o in orbs6:
        o9 += to_tiles([[orb9_idx(p) for p in r] for r in o], 4, 4)
    t9, f9 = [], []
    for out, imgs in ((t9, bodies9), (f9, flash9)):
        for im in imgs:
            for part in range(3):
                out += to_tiles([[i9(p) for p in r] for r in sub(im, 0, 16 * part, 16, 16)], 2, 2)
    for s in shots9:
        t9 += to_tiles([[i9(p) for p in r] for r in s], 2, 2)
    assert len(t6) == 48 * 8 and len(o6) == 48 * 8 and len(t9) == 80 * 8 and len(f9) == 72 * 8

    (GEN / 'boss69_16_md.h').write_text('\n'.join([
        '/* Generated by tools/build_boss69_16.py (Castlevania-MD art, research/gfx16.md). Same layout as vk_boss6_tiles,',
        ' * vk_orb6_tiles, vk_boss9_tiles (boss6_md.h, boss9_md.h); loaded in their place by actors.c in 16-bit mode. */',
        '#ifndef VK_BOSS69_16_MD_H', '#define VK_BOSS69_16_MD_H', '#include <genesis.h>',
        '/* PAL2 of the boss rooms: the MSX colours other content reads keep their entries. */',
        'extern const u16 vk_boss6_16_palette[16];   /* stage 6: entry 5 = 006 (what the orb writes), orb drawn with entry 7 = 00A */',
        'extern const u16 vk_boss9_16_palette[16];',
        'extern const u32 vk_boss6_16_tiles[384];   /* as vk_boss6_tiles */',
        'extern const u32 vk_orb6_16_tiles[384];    /* as vk_orb6_tiles */',
        'extern const u32 vk_orb9_16_tiles[384];    /* the same orb with the entries of the stage 9 palette (the orb6 tiles are loaded at stage 9 too) */',
        'extern const u32 vk_boss9_16_tiles[640];   /* as vk_boss9_tiles */',
        'extern const u32 vk_boss9_16_flash[576];   /* the 6 poses x 12 tiles in the blinking colours (replaces the run-time recolouring) */',
        '#endif', '']))
    (GEN / 'boss69_16_md.c').write_text('\n'.join([
        '/* Generated by tools/build_boss69_16.py. */', '#include "boss69_16_md.h"',
        'const u16 vk_boss6_16_palette[16] = {\n%s\n};' % fmt(pal6, 4),
        'const u16 vk_boss9_16_palette[16] = {\n%s\n};' % fmt(pal9, 4),
        'const u32 vk_boss6_16_tiles[384] = {\n%s\n};' % fmt(t6, 8),
        'const u32 vk_orb6_16_tiles[384] = {\n%s\n};' % fmt(o6, 8),
        'const u32 vk_orb9_16_tiles[384] = {\n%s\n};' % fmt(o9, 8),
        'const u32 vk_boss9_16_tiles[640] = {\n%s\n};' % fmt(t9, 8),
        'const u32 vk_boss9_16_flash[576] = {\n%s\n};' % fmt(f9, 8), '']))
    print('stage 6: palette %s error %.1f; stage 9: palette %s error %.1f; %d bytes' % (
        ' '.join('%03X' % w for w in pal6), err6, ' '.join('%03X' % w for w in pal9), err9,
        (384 * 3 + 640 + 576) * 4))
    if '--preview' in sys.argv:
        preview(sys.argv[sys.argv.index('--preview') + 1], (boss6, orb6, boss9), (t6, o6, t9, f9), p6, p9, pal6, pal6_post, pal9)


def preview(path, msx, new, p6, p9, pal6, pal6_post, pal9):
    from PIL import Image
    boss6, orb6, boss9 = msx
    t6, o6, t9, f9 = new
    S = 4

    def col(pal):
        return [(0, 0, 0)] + [tuple(v * 36 for v in E.lvl(pal[i])) for i in range(1, 16)]

    def items(b6, ob6, b9, fl):
        L = []
        for pose in range(2):
            c = [[0] * 32 for _ in range(32)]
            for i in range(4):
                t = msx_tiles(b6, (pose * 4 + i) * 4, 2, 2)
                for y in range(16):
                    for x in range(16):
                        c[(i & 1) * 16 + y][(i >> 1) * 16 + x] = t[y][x]
            L.append(c)
        L += [msx_tiles(b6, 32 + 4 * k, 2, 2) for k in range(4)]
        L += [msx_tiles(ob6, 16 * k, 4, 4) for k in range(3)]
        for src in (b9, fl):
            for p in range(6) if src is not None else []:
                c = [[0] * 16 for _ in range(48)]
                for part in range(3):
                    t = msx_tiles(src, (p * 3 + part) * 4, 2, 2)
                    for y in range(16):
                        for x in range(16):
                            c[part * 16 + y][x] = t[y][x]
                L.append(c)
            if src is b9:
                L += [msx_tiles(b9, 72 + 4 * k, 2, 2) for k in range(2)]
        return L
    msxcol = {i: c for i, c in enumerate(col(p6))}
    rows = [(items(boss6, orb6, boss9, None), col(p6)), (items(t6, o6, t9, f9), col(pal6)), (items(t6, o6, t9, f9), col(pal6_post))]
    # row 3 is the 16-bit orb with the entries the orb event writes; row 2 shows the body with the room palette
    # stage 9 uses its own palette: redraw those items with pal9
    W = max(sum(len(i[0]) * S + 8 for i in r[0]) for r in rows) + 20
    im = Image.new('RGB', (W, 3 * 52 * S), (60, 70, 90))
    msxpal9 = col(p9)
    for r, (its, cols) in enumerate(rows):
        x0 = 0
        for k, it in enumerate(its):
            c = cols
            if k >= 9:
                c = msxpal9 if r == 0 else col(pal9)
            for y, row in enumerate(it):
                for x, v in enumerate(row):
                    if v:
                        for a in range(S):
                            for b in range(S):
                                im.putpixel((x0 + x * S + a, r * 52 * S + y * S + b), c[v])
            x0 += len(it[0]) * S + 8
    im.save(path)


if __name__ == '__main__':
    main()

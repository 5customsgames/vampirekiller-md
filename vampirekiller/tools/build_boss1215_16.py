#!/usr/bin/env python3
"""Bosses of the stages 12 (Frankenstein and Igor) and 15 (Death and its sickles) in the 16-bit art (research/gfx16.md,
section "Boss des stages 12 et 15 16 bits").

usage: build_boss1215_16.py <castlevania-md checkout> [--preview FILE.png]

Writes sgdk/src/generated/boss1215_16_md.c/.h: tiles of the SAME layout as vk_boss12_tiles (15 cells of 4 tiles: Frankenstein
3 poses x 3 cells of 16 x 16, Igor 6 poses x 1 cell), vk_boss15_tiles (11 cells: Death 6 cells, sickles 4, the ball of the first
frames), the shot of the stage 12 (4 tiles, replaces vk_boss_tiles + 28 * 8) and one PAL2 per boss room. The code (poses,
cells, positions, hit boxes, SAT, timing) is the MSX one: only the pictures change.

- Pictures (Castlevania-MD): Frankenstein b4_frank0 / 1 / 2 (the walk is 79 7A 7B 7A = frank 2 0 1 0, as main.c frank_seq),
  Igor = the flea: stand b4_flea_stand (poses 67 and 69, 6A and 6C), jump b4_flea_jump (68, 6B), the right poses mirrored;
  Death b5_death (the 40 x 48 picture fills exactly the 6 MSX cells), sickles b5_sickle3, 0, 1, 2 (poses 7D..80: the same turn, one step later), the balls
  (stage 12 shot, Death's first-frame ball) = red / white sphere of build_items16.sphere.
- Palette: the entries other PAL2 content reads (FIXED) keep the MSX colour of the room; the six free ones (4 5 6 9 10 11)
  take the colours of the pictures that fit best. The orb of the end of the fight rewrites the entries 5 and 7 of PAL2
  (actors.c) as in MSX mode: the body is gone by then.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_enemies16 as E  # noqa: E402
import build_enemies16_block2 as B2  # noqa: E402
import build_enemies16_block5 as T5  # noqa: E402
import build_items16 as I  # noqa: E402

GEN = E.GEN
FREE = (4, 5, 6, 9, 10, 11)


def arr(name, f):
    return E.nums((GEN / f).read_text(), 'const (?:unsigned long|u32|u16) ' + name)


def cell_rows(words, c):
    return E.Msx.cell(words, c)


def poses(header, rx):
    t = (GEN / header).read_text()
    return [tuple(int(v) for v in m) for m in re.findall(rx, t)]


def pieces(img, w, h, cw, ch):
    return img


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    b4, b5 = B2.Block(root, 4), B2.Block(root, 5)
    w12, w15 = arr('vk_boss12_tiles', 'boss12_md.c'), arr('vk_boss15_tiles', 'boss15_md.c')
    wshot = arr('vk_boss_tiles', 'boss_md.c')[28 * 8:32 * 8]
    pal = T5.msx_palettes()
    P12, P15 = pal(12, 6), pal(15, 9)

    # ---- stage 12: cells of vk_boss12_tiles -------------------------------------------------------------------
    p12 = poses('boss12_poses.h', r'\{(\d+),(\d+),\{\{(-?\d+),(-?\d+),(\d+),(\d+)\}')   # first cell of each pose
    cell12 = {}                                       # pose -> [(cell index, canvas y)]
    for line in (GEN / 'boss12_poses.h').read_text().splitlines():
        m = re.match(r'\s*\{(\d+),(\d+),\{(.*)\}\},', line)
        if m:
            cs = [tuple(int(v) for v in c) for c in re.findall(r'\{(-?\d+),(-?\d+),(\d+),(\d+)\}', m.group(3))]
            cell12[int(m.group(1))] = [(c[3] // 4, k * 16) for k, c in enumerate(cs)]
    pics12 = {}                                       # cell -> (rows of levels 16 x 16, ref box rows)
    frank = {0x79: 2, 0x7A: 0, 0x7B: 1}
    for pose, k in frank.items():
        img = b4.sprite('b4_frank%d' % k)
        assert (len(img[0]), len(img)) == (16, 48), (len(img[0]), len(img))
        for c, y in cell12[pose]:
            pics12[c] = [r[:] for r in img[y:y + 16]]
    for pose, name, mir in ((0x67, 'stand', 0), (0x68, 'jump', 0), (0x69, 'stand', 0),
                            (0x6A, 'stand', 1), (0x6B, 'jump', 1), (0x6C, 'stand', 1)):
        img = b4.sprite('b4_flea_' + name)
        img = E.mirror(img) if mir else img
        assert (len(img[0]), len(img)) == (16, 16)
        pics12[cell12[pose][0][0]] = img
    ball = I.sphere([(2, 0, 0), (4, 0, 0), (5, 1, 1), (5, 1, 1), (7, 5, 4)])
    shot_ref = E.ref_box(E.Msx.cell(wshot, 0))
    pics12['shot'] = E.place(ball, 16, 16, shot_ref, 'centre')

    # ---- stage 15 ---------------------------------------------------------------------------------------------
    cells15 = [tuple(int(v) for v in c) for c in re.findall(r'\{(-?\d+),(-?\d+),(\d+),(\d+)\}', (GEN / 'boss15_poses.h').read_text())]
    assert len(cells15) == 11
    death = b5.sprite('b5_death')
    assert (len(death[0]), len(death)) == (40, 48), (len(death[0]), len(death))
    pics15 = {}
    for i in range(6):
        dy, dx = cells15[i][0], cells15[i][1]
        x, y = dx + 24, dy + 47
        pics15[i] = [row[x:x + 16] for row in death[y:y + 16]]
        assert all(len(r) == 16 for r in pics15[i])
    # nothing of the picture lies outside the cells
    covered = {(cells15[i][1] + 24 + a, cells15[i][0] + 47 + b) for i in range(6) for a in range(16) for b in range(16)}
    lost = [(x, y) for y, r in enumerate(death) for x, p in enumerate(r) if p is not None and (x, y) not in covered]
    assert not lost, lost
    for k in range(4):
        img = b5.sprite('b5_sickle%d' % ((k + 3) % 4))     # the MSX turn starts one step before the MD one (checked on the board)
        assert (len(img[0]), len(img)) == (16, 16)
        pics15[6 + k] = img
    ball15 = I.sphere([(3, 3, 4), (5, 5, 6), (6, 6, 7), (7, 7, 7), (7, 7, 7)], 8)
    ref = E.ref_box(E.Msx.cell(w15, 10))
    pics15[10] = E.place(ball15, 16, 16, ref, 'centre')

    # the death flame (F4 and F8, 2 cells of 4 tiles; shared bank, already 16-bit in PAL1) re-indexed on the PAL2 of each room
    fl = arr('vk_item16_death_flame_tiles', 'items16_md.c')
    ipal = arr('vk_item16_palette', 'items16_md.c')
    flame = []
    for c in range(2):
        cell = E.Msx.cell(fl, c)
        flame.append([[E.lvl(ipal[v]) if v else None for v in r] for r in cell])

    def palette(msx_pal, pics):
        out = [0] * 16
        for i in E.FIXED:
            out[i] = msx_pal[i]
        colours = {}
        for img in pics:
            for row in img:
                for p in row:
                    if p is not None:
                        colours[p] = colours.get(p, 0) + 1
        E.FREE = FREE
        free, err = E.choose_free(colours, [E.lvl(out[i]) for i in E.FIXED])
        for i, c in zip(FREE, free):
            out[i] = E.word(c)
        return out, err

    pal12, err12 = palette(P12, list(pics12.values()) + flame)
    pal15, err15 = palette(P15, list(pics15.values()) + flame)

    def tiles(img, pal):
        rows = [[0 if p is None else E.to_index(pal, p) for p in r] for r in img]
        return E.cell_tiles(rows)

    t12 = []
    for c in range(15):
        t12 += tiles(pics12[c], pal12)
    tshot = tiles(pics12['shot'], pal12)
    t15 = []
    for c in range(11):
        t15 += tiles(pics15[c], pal15)
    f12 = tiles(flame[0], pal12) + tiles(flame[1], pal12)
    f15 = tiles(flame[0], pal15) + tiles(flame[1], pal15)
    assert len(t12) == 480 and len(t15) == 352 and len(tshot) == 32

    def fmt(vals, width):
        f = '0x%%0%dX' % width
        return '\n'.join('    ' + ','.join(f % v for v in vals[i:i + 8]) + ',' for i in range(0, len(vals), 8))
    (GEN / 'boss1215_16_md.h').write_text('\n'.join([
        '/* Generated by tools/build_boss1215_16.py (Castlevania-MD art, research/gfx16.md). Same layout as vk_boss12_tiles,',
        ' * vk_boss15_tiles (boss12_md.h, boss15_md.h) and the stage 3 fireball (vk_boss_tiles + 28 * 8); loaded in their place',
        ' * by actors.c in 16-bit mode, boss rooms of the stages 12 and 15. */',
        '#ifndef VK_BOSS1215_16_MD_H', '#define VK_BOSS1215_16_MD_H', '#include <genesis.h>',
        '/* PAL2 of the boss rooms: the MSX colours other content uses keep their entries; the free ones hold the 16-bit colours. */',
        'extern const u16 vk_boss12_16_palette[16];', 'extern const u16 vk_boss15_16_palette[16];',
        'extern const u32 vk_boss12_16_tiles[480];', 'extern const u32 vk_boss12_16_shot_tiles[32];',
        'extern const u32 vk_boss15_16_tiles[352];', 'extern const u32 vk_boss12_16_flame_tiles[64];   /* as vk_death_flame_tiles, on the PAL2 of the room */',
        'extern const u32 vk_boss15_16_flame_tiles[64];', '#endif', '']))
    (GEN / 'boss1215_16_md.c').write_text('\n'.join([
        '/* Generated by tools/build_boss1215_16.py. */', '#include "boss1215_16_md.h"',
        'const u16 vk_boss12_16_palette[16] = {\n%s\n};' % fmt(pal12, 4),
        'const u16 vk_boss15_16_palette[16] = {\n%s\n};' % fmt(pal15, 4),
        'const u32 vk_boss12_16_tiles[480] = {\n%s\n};' % fmt(t12, 8),
        'const u32 vk_boss12_16_shot_tiles[32] = {\n%s\n};' % fmt(tshot, 8),
        'const u32 vk_boss15_16_tiles[352] = {\n%s\n};' % fmt(t15, 8),
        'const u32 vk_boss12_16_flame_tiles[64] = {\n%s\n};' % fmt(f12, 8),
        'const u32 vk_boss15_16_flame_tiles[64] = {\n%s\n};' % fmt(f15, 8), '']))
    print('boss12 %d + shot 4 + boss15 %d tiles = %d B, error %.1f / %.1f' % (60, 44, (60 + 4 + 44) * 32, err12, err15))
    print('pal12', ' '.join('%03X' % w for w in pal12)); print('pal15', ' '.join('%03X' % w for w in pal15))
    if '--preview' in sys.argv:
        from PIL import Image
        S = 4

        def col(p, i):
            return tuple(v * 36 for v in E.lvl(p[i]))

        def draw(im, words, pp, x0, y0, items):
            """items: (cell, x, y) of 16 x 16 cells; returns nothing."""
            for c, cx, cy in items:
                cell = E.Msx.cell(words, c)
                for y in range(16):
                    for x in range(16):
                        v = cell[y][x]
                        if v:
                            for a in range(S):
                                for b in range(S):
                                    im.putpixel((x0 + (cx + x) * S + a, y0 + (cy + y) * S + b), col(pp, v))
        poses12 = [[(cell12[p][k][0], 0, 16 * k) for k in range(3)] for p in (0x79, 0x7A, 0x7B)] + \
                  [[(cell12[p][0][0], 0, 0)] for p in (0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C)]
        poses12.append([(('shot'), 0, 0)])
        poses15 = [[(i, cells15[i][1] + 24, cells15[i][0] + 47) for i in range(6)]] + [[(6 + k, 0, 0)] for k in range(4)] + [[(10, 0, 0)]]
        im = Image.new('RGB', (10 * 48 * S + 20, 4 * 52 * S + 20), (60, 70, 90))
        y0 = 4
        for ws, ps, pm, p16, shot in ((w12, poses12, P12, pal12, (wshot, tshot)), (w15, poses15, P15, pal15, None)):
            for words, pp in ((ws, pm), (t12 if ws is w12 else t15, p16)):
                x0 = 4
                for items in ps:
                    if items[0][0] == 'shot':
                        draw(im, shot[0] if pp is pm else tshot, pp, x0, y0, [(0, 0, 0)])
                    else:
                        draw(im, words, pp, x0, y0, items)
                    x0 += 44 * S
                y0 += 52 * S
        im.save(sys.argv[sys.argv.index('--preview') + 1])


if __name__ == '__main__':
    main()

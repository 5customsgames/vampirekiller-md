"""16-bit candle blobs (objects 1A, 1C) and courtyard torch flames (tools/build_candle16.py, research/gfx16.md): arrays of the
layout of the MSX ones (same cells, same tile counts, so the same transfers), the blobs keep the MSX silhouette and read only the
PAL2 entries that every PAL2 of their rooms holds with the same colour, the flames are drawn with PAL1 (item palette)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import build_candle16 as T  # noqa: E402
from test_enemies16 import arrays, used  # noqa: E402

B = T.be
NEW = arrays(GEN / 'candle16_md.c')
CV = ROOT.parent / 'castlevania'


def msx_flames():
    return [int(v, 16) for v in re.findall(r'0x([0-9A-F]{8})UL', (GEN / 'flame_fx_md.h').read_text())]


def test_layout_of_the_msx_arrays():
    ghost = B.nums((GEN / 'ghost_md.c').read_text(), 'vk_ghost_tiles')
    assert len(NEW['vk_candle16_blob_c_tiles']) == len(ghost) // 3 == 64
    assert len(NEW['vk_candle16_blob_a_tiles']) == len(arrays(GEN / 'ghost_a_md.c')['vk_ghost_a_tiles']) == 64
    assert len(NEW['vk_candle16_flame_tiles']) == len(msx_flames()) == 224


def test_generated_file_is_current():
    cblob, ablob = T.blobs()
    assert NEW['vk_candle16_blob_c_tiles'] == T.words_of(cblob)
    assert NEW['vk_candle16_blob_a_tiles'] == T.words_of(ablob)
    if CV.exists():
        assert NEW['vk_candle16_flame_tiles'] == [w for k in T.FLAME_FRAMES for w in B.cell_tiles(T.flames(B.CV(CV))[k])]


def mask(words):
    return [[1 if B.Msx.cell(words, c)[y][x] else 0 for y in range(16) for x in range(16)] for c in range(len(words) // 32)]


def test_blobs_keep_the_msx_silhouette():
    ghost = B.nums((GEN / 'ghost_md.c').read_text(), 'vk_ghost_tiles')
    for v in range(3):              # the three pose bases hold the same image
        assert mask(ghost[v * 64:v * 64 + 64]) == mask(NEW['vk_candle16_blob_c_tiles'])
    assert mask(arrays(GEN / 'ghost_a_md.c')['vk_ghost_a_tiles']) == mask(NEW['vk_candle16_blob_a_tiles'])


def palettes16(name, var):
    m = re.search(r'%s\[[^\]]*\](?:\[\d+\])?\s*=\s*\{(.*?)\n\};' % var, (GEN / name).read_text(), re.S)
    v = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    return [v[i:i + 16] for i in range(0, len(v), 16)]


def test_blob_entries_are_fixed_in_every_pal2_of_their_rooms():
    c, a = used(NEW['vk_candle16_blob_c_tiles']), used(NEW['vk_candle16_blob_a_tiles'])
    assert c <= set(T.BLOB_ENTRIES_C) and a <= set(T.BLOB_ENTRIES_A), (c, a)
    t = (GEN / 'rooms.c').read_text()
    allp = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', re.search(r'vk_palettes\[\]\[16\] = \{(.*?)\n\};', t, re.S).group(1))]
    stages = [tuple(int(x) for x in re.findall(r'\d+', e))
              for e in re.findall(r'\{([^{}]*)\}', re.search(r'vk_stages\[18\] = \{(.*?)\};', t, re.S).group(1))]
    b2 = palettes16('enemies16b2_md.c', 'vk_enemy16b2_palette')
    b3 = palettes16('enemies16b3_md.c', 'vk_enemy16b3_palette')
    for group, entries, blocks, want in (((4, 5, 6), T.BLOB_ENTRIES_A, b2, {2: 0x222, 14: 0xEEE, 15: 0xE00}),
                                         ((7, 8, 9), T.BLOB_ENTRIES_C, b3, {2: 0x222, 12: 0xAAA, 13: 0x444, 14: 0xEEE})):
        pals = list(blocks)                                       # the 16-bit palettes of the block ...
        for s in group:
            for r in T.GHOST_ROOMS[s]:                            # ... and the MSX room palettes (rooms outside the block)
                pals.append(allp[(stages[s - 1][0] + r) * 16:(stages[s - 1][0] + r) * 16 + 16])
        assert len(pals) > 15
        for i in entries:
            assert len({p[i] for p in pals}) == 1, (group, i, sorted({p[i] for p in pals}))
        assert {i: pals[0][i] for i in want} == want


def test_flames_frames_and_palette():
    f = NEW['vk_candle16_flame_tiles']
    frames = [tuple(f[i:i + 32]) for i in range(0, 224, 32)]
    assert len(set(frames)) == 2 and frames[0] != frames[2]
    msx = msx_flames()
    msx_frames = [tuple(msx[i:i + 32]) for i in range(0, 224, 32)]
    assert [frames.index(x) for x in frames] == [msx_frames.index(x) for x in msx_frames]      # same A / B order
    assert used(f) <= set(range(1, 16)) and len(used(f)) >= 6
    cells = [B.Msx.cell(f, k) for k in range(7)]
    assert all(any(any(r) for r in c) for c in cells)
    # every flame fits its 16 x 16 sprite and has pixels on its second and last rows (the picture of the brazier of CV-MD)
    assert any(cells[0][1]) and any(cells[0][15])


def test_code_uses_the_16_bit_arrays_only_in_16_bit_mode():
    a = (ROOT / 'sgdk/src/actors.c').read_text()
    h = (ROOT / 'sgdk/src/gfx16.h').read_text()
    r = (ROOT / 'sgdk/src/room_view.c').read_text()
    assert 'VK_BLOB_C_TILES(vk_ghost_tiles[' in a and 'VK_BLOB_A_TILES(vk_ghost_a_tiles)' in a
    assert 'VDP_loadTileData(VK_FLAME_TILES, FLAME_TILE_INDEX,' in a
    assert '(vk_gfx16_on ? vk_candle16_blob_c_tiles : (msx))' in h and '(vk_gfx16 ? vk_candle16_flame_tiles : vk_flame_fx_tiles)' in h
    assert 'TILE_ATTR_FULL(vk_gfx16 ? PAL1 : PAL2, TRUE, FALSE, FALSE,' in r


# ---- object 1B (red blob of the candles of object 15, stages 11 to 18) ----

GHOST_B_ROOMS = {11: (0, 5), 12: (7, 8, 9), 14: (1, 4), 16: (0,), 17: (3, 5, 9), 18: (3, 4)}


def test_blob_b_layout_and_silhouette():
    w = NEW['vk_candle16_blob_b_tiles']
    msx = B.nums((GEN / 'stage11_enemies_md.c').read_text(), 'vk_stage11_ghost_tiles')
    assert len(w) == 64 and len(msx) == 128
    assert mask(msx[:64]) == mask(msx[64:]) == mask(w)            # both pose bases of the stage 11 blob hold the MSX image
    assert T.msx_blob_b() == msx[:64]
    assert w == T.words_of(T.blob_b())


def test_blob_b_is_in_slots_4_and_5_of_the_late_pools():
    cells = T.blob_b_cells()
    assert [w for c in cells for w in c] == NEW['vk_candle16_blob_b_tiles']
    for name, var, first in (('enemies16b5_md.c', 'vk_enemy16b5_cells', 4), ('enemies16b6_md.c', 'vk_enemy16b6_cells', 4),
                             ('enemies16b7_md.c', 'vk_enemy16b7_cells', 4),
                             ('enemies16b4_md.c', 'vk_enemy16b4_cells', 41 + 4)):    # stage 12: pool cells 4, 5 from cell 41
        pool = arrays(GEN / name)[var]
        assert pool[first * 32:first * 32 + 32] == cells[0] and pool[first * 32 + 32:first * 32 + 64] == cells[1], name


def test_blob_b_entries_are_fixed_in_every_pal2_of_its_rooms():
    assert used(NEW['vk_candle16_blob_b_tiles']) == {2, 8, 14}
    t = (GEN / 'rooms.c').read_text()
    allp = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', re.search(r'vk_palettes\[\]\[16\] = \{(.*?)\n\};', t, re.S).group(1))]
    stages = [tuple(int(x) for x in re.findall(r'\d+', e))
              for e in re.findall(r'\{([^{}]*)\}', re.search(r'vk_stages\[18\] = \{(.*?)\};', t, re.S).group(1))]
    pals = []
    for name, var in (('enemies16b4_md.c', 'vk_enemy16b4_palette'), ('enemies16b5_md.c', 'vk_enemy16b5_palette'),
                      ('enemies16b6_md.c', 'vk_enemy16b6_palette'), ('enemies16b7_md.c', 'vk_enemy16b7_palette')):
        pals += palettes16(name, var)
    for s, rooms in GHOST_B_ROOMS.items():            # the MSX room palettes (stage 16 room 0 keeps its own)
        for r in rooms:
            pals.append(allp[(stages[s - 1][0] + r) * 16:(stages[s - 1][0] + r) * 16 + 16])
    assert len(pals) > 25
    for i, v in ((2, 0x222), (8, 0x20E), (14, 0xEEE)):
        assert {p[i] for p in pals} == {v}, (i, sorted({p[i] for p in pals}))


def test_code_loads_blob_b_in_16_bit_mode_only():
    a = (ROOT / 'sgdk/src/actors.c').read_text()
    h = (ROOT / 'sgdk/src/gfx16.h').read_text()
    g = (ROOT / 'sgdk/src/gfx16.c').read_text()
    assert 'VK_BLOB_B_TILES(vk_stage11_ghost_tiles[' in a
    assert '(vk_gfx16_on ? vk_candle16_blob_b_tiles : (msx))' in h
    assert 'vk_gfx16_on && stage == 16 && room == 0' in g

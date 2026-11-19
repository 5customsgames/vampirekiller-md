"""16-bit common enemies of block 5 (tools/build_enemies16_block5.py, research/gfx16.md): in 16-bit mode PAL2 of the rooms of
stages 13 to 15 that load enemy cells (stage 13; stage 14 rooms 0-7; stage 15 rooms 1-4 and 6-8) is one of the three
vk_enemy16b5_palette (entry 7 of the MSX palette: CAE, 66C, 26C). It may only change the entries no other PAL2 content of those
rooms uses (objects, key, door, HUD boxes, text, object 1B): those keep the MSX colour of every room of the class. The 16-bit
cells are stored by pool slot (late_graphics_slots), so a room loads the same slots with the same transfers from
vk_enemy16b5_cells as from late_graphics_words; object 1B (slots 4, 5) is the 16-bit blob of build_candle16.py."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import build_enemies16_block5 as T  # noqa: E402
from test_enemies16 import OTHER, arrays, used  # noqa: E402

B = T.B
SRC = (GEN / 'enemies16b5_md.c').read_text()
HDR = (GEN / 'enemies16b5_md.h').read_text()
NEW = arrays(GEN / 'enemies16b5_md.c')['vk_enemy16b5_cells']


def cell(words, c):
    return words[c * 32:(c + 1) * 32]


def palettes():
    m = re.search(r'vk_enemy16b5_palette\[3\]\[16\] = \{(.*?)\n\};', SRC, re.S)
    v = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    assert len(v) == 48
    return [v[i * 16:(i + 1) * 16] for i in range(3)]


def c_predicate(stage, room):
    """vk_gfx16_enemies_b5 (gfx16.c), without the vk_gfx16_on test."""
    return stage == 13 or (stage == 14 and room < 8) or (stage == 15 and 1 <= room <= 8 and room != 5)


def test_free_entries_unused_by_other_pal2_content():
    seen = set()
    for f in OTHER:
        for name, words in arrays(GEN / f).items():
            seen |= used(words)
    lw = T.pool_words()
    seen |= used(lw[4 * 32:6 * 32])                                         # object 1B (stage 14 rooms 1 and 4), MSX
    assert seen <= set(B.FIXED), seen - set(B.FIXED)
    assert used(NEW) <= set(range(1, 16))


def test_object_1b_and_stage12_slots():
    lw = T.pool_words()
    assert len(NEW) == T.SLOTS * 32 == define('VK_ENEMY16B5_SLOTS') * 32
    import build_candle16 as C16
    assert [cell(NEW, 4), cell(NEW, 5)] == C16.blob_b_cells()               # object 1B: the 16-bit blob (build_candle16.py)
    assert not any(NEW[:4 * 32])                                            # the stage 12 dragon: block 4's cells
    assert {(ty, p) for ty, p, s in T.enemy_rooms()[(14, 1)]} >= {(15, 0xB4), (15, 0xB8)}
    assert T.slot_map()[(15, 0xB4)] == 4 and T.slot_map()[(15, 0xB8)] == 5


def define(name):
    return int(re.search(r'#define %s (\d+)' % name, HDR).group(1))


def test_every_msx_enemy_cell_is_replaced():
    lw = T.pool_words()
    smap = T.slot_map()
    for (ty, p), slot in smap.items():
        if ty not in T.KIND:
            continue
        # a drawn MSX cell becomes the 16-bit picture, or the blank second layer; no cell stays as it was
        assert cell(NEW, slot) != cell(lw, slot) or not any(cell(lw, slot)), (ty, hex(p))
    # slots 6 to 66 are exactly the cells of stages 13 to 15 (but object 1B), nothing else is in the array
    slots = {s for (ty, p), s in smap.items() if ty in T.KIND}
    assert slots == set(range(6, 67)), sorted(set(range(6, 67)) ^ slots)


def test_pose_layout_keeps_the_msx_cells():
    """The pictures are in the first layer cell of each place, the second layer (pattern + 4) is blank."""
    smap = T.slot_map()
    for ty in (22, 20):
        for base in (0x40, 0x50, 0x60, 0x70):                               # awake poses: 16 x 32, two layers
            for top, bottom in ((base, base + 8),):
                assert any(cell(NEW, smap[(ty, top)])) and any(cell(NEW, smap[(ty, bottom)])), (ty, hex(base))
            assert not any(cell(NEW, smap[(ty, base + 4)])) and not any(cell(NEW, smap[(ty, base + 12)])), (ty, hex(base))
    for base in (0x80, 0x88):                                               # rising pile
        assert any(cell(NEW, smap[(22, base)])) and not any(cell(NEW, smap[(22, base + 4)]))
    for base in (0x80, 0x88, 0x90, 0x98):                                   # axe
        assert any(cell(NEW, smap[(21, base)])) and not any(cell(NEW, smap[(21, base + 4)]))
    for p in (0x64, 0x68, 0x6C, 0x70, 0x74, 0x78, 0x7C, 0x80):             # white skeleton: composed cells
        assert any(cell(NEW, smap[(11, p)]))
    for p in (0x98, 0x9C, 0xA0, 0xF0):
        assert any(cell(NEW, smap[(13, p)]))
    for p in (0x80, 0x84, 0x88, 0x8C):
        assert any(cell(NEW, smap[(14, p)]))
    assert any(cell(NEW, smap[(21, 0xF0)]))


def tile_rows(words, c):
    return B.Msx.cell(words, c)


def test_each_pose_sits_on_its_msx_box():
    """The 16-bit picture of every pose has the foot line (standing poses) or the centre (the others) of the MSX picture of the
    same pose (as laid by the tool), within a pixel; a picture is never cut at the edge of its cells but the axe knight's shield."""
    smap = T.slot_map()
    for j, img, ref in T.laid(T.jobs(T.T.Block(ROOT.parent / 'castlevania', 5))):
        cw, ch = j['size']
        canvas = B.canvas_of([(x, y, tile_rows(NEW, smap[(ty, p)])) for ty, p, x, y in j['cells']])
        box = B.ref_box(canvas)
        assert box, j['name']
        msx = B.ref_box(B.canvas_of([(x, y, T.msx_cell(ty, p)) for ty, p, x, y in j['ref']]))
        if j['mode'] == 'feet':
            assert abs(box[3] - msx[3]) <= 1, (j['name'], box, msx)
        else:
            assert abs((box[1] + box[3]) - (msx[1] + msx[3])) <= 2, (j['name'], box, msx)
        assert abs((box[0] + box[2]) - (msx[0] + msx[2])) <= 3, (j['name'], box, msx)


def test_shared_cells_agree():
    """A pool slot shared by several (type, pattern) holds one picture (the tool asserts it); the blank layers are blank."""
    smap = T.slot_map()
    by_slot = {}
    for key, s in smap.items():
        by_slot.setdefault(s, []).append(key)
    for s, keys in by_slot.items():
        if len(keys) > 1:
            assert all(k[0] in T.KIND or k[0] == 15 for k in keys), (s, keys)


def test_palettes_keep_msx_colours_of_every_room():
    pals = palettes()
    info = T.room_info()
    assert len(info) == 12 + 8 + 7                                          # stage 13, 14 rooms 0-7, 15 rooms 1-4 and 6-8
    for pal in pals:
        assert pal[0] == 0
    for room, (msx, cls, kinds) in info.items():
        assert [pals[cls][i] for i in B.FIXED] == [msx[i] for i in B.FIXED], room
    assert {cls for msx, cls, kinds in info.values()} == {0, 1, 2}
    # the skeleton, shared by the CAE and 66C rooms: the same free entries in both palettes, and no entry 7 in its cells
    smap = T.slot_map()
    sk = [w for key, s in smap.items() if key[0] in (11, 13) for w in cell(NEW, s)]
    assert T.VARIABLE not in used(sk)
    free_used = used(sk) & set(B.FREE)
    assert all(pals[0][i] == pals[1][i] for i in free_used), free_used


def test_the_c_code_picks_the_same_rooms_and_palettes():
    gfx = (ROOT / 'sgdk/src/gfx16.c').read_text()
    assert 'stage == 13 || (stage == 14 && room < 8) || (stage == 15 && room >= 1 && room <= 8 && room != 5)' in gfx
    assert 'msx[7] == vk_enemy16b5_palette[0][7] ? 0 : msx[7] == vk_enemy16b5_palette[1][7] ? 1 : 2' in gfx
    assert set(T.room_info()) == {(s, r) for s in (13, 14, 15) for r in range(12) if c_predicate(s, r)}
    pals = palettes()
    for (s, r), (msx, cls, kinds) in T.room_info().items():
        pick = 0 if msx[7] == pals[0][7] else 1 if msx[7] == pals[1][7] else 2
        assert pick == cls, (s, r)
    actors = (ROOT / 'sgdk/src/actors.c').read_text()
    assert 'if(vk_gfx16_on)words=vk_game.stage>=13&&vk_game.stage<=15?vk_gfx16_b5_late(vk_game.stage,vk_game.room,words):words;' in actors


def test_generated_file_is_up_to_date():
    pool, pals, allowed, errs, hist, n_s, written = T.build(T.T.Block(ROOT.parent / 'castlevania', 5))
    assert [w for c in pool for w in c] == NEW
    assert palettes() == pals
    tot = sum(sum(h.values()) for h in hist.values())
    assert sum(errs[k] * sum(hist[k].values()) for k in hist) / tot < 20


class Block5(unittest.TestCase):
    """The checks above, also for `python -m unittest discover`."""

    def test_all(self):
        for name, f in sorted(globals().items()):
            if name.startswith('test_') and callable(f):
                with self.subTest(name):
                    f()

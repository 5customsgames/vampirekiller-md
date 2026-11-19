"""16-bit common enemies of block 7 (tools/build_enemies16_block7.py, research/gfx16.md): in 16-bit mode PAL2 of the rooms of
stage 18 that load enemy cells (rooms 1 to 8) is one of the two vk_enemy16b7_palette (flea rooms 3 to 7 / axe knight rooms 1, 2, 8).
It may only change the entries no other PAL2 content of those rooms uses (objects, key, door, HUD boxes, text, object 1B): those
keep the MSX colour of every room of the group. The 16-bit cells are stored by pool slot (late_graphics_slots), so a room loads the
same slots with the same transfers from vk_enemy16b7_cells as from late_graphics_words; object 1B (slots 4, 5) is the 16-bit blob of build_candle16.py."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import build_enemies16_block7 as T  # noqa: E402
from test_enemies16 import OTHER, arrays, used  # noqa: E402

B = T.B
SRC = (GEN / 'enemies16b7_md.c').read_text()
HDR = (GEN / 'enemies16b7_md.h').read_text()
NEW = arrays(GEN / 'enemies16b7_md.c')['vk_enemy16b7_cells']
CV = ROOT.parent / 'castlevania'


def cell(words, c):
    return words[c * 32:(c + 1) * 32]


def define(name):
    return int(re.search(r'#define %s (\d+)' % name, HDR).group(1))


def palettes():
    m = re.search(r'vk_enemy16b7_palette\[2\]\[16\] = \{(.*?)\n\};', SRC, re.S)
    v = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    assert len(v) == 32
    return [v[i * 16:(i + 1) * 16] for i in range(2)]


def c_predicate(stage, room):
    """vk_gfx16_enemies_b7 (gfx16.c), without the vk_gfx16_on test."""
    return stage == 18 and 1 <= room <= 8


def c_group(room):
    """The palette index of vk_gfx16_pal2 (gfx16.c)."""
    return int(room == 1 or room == 2 or room == 8)


def test_free_entries_unused_by_other_pal2_content():
    seen = set()
    for f in OTHER:
        for name, words in arrays(GEN / f).items():
            seen |= used(words)
    lw = T.T5.pool_words()
    seen |= used(lw[4 * 32:6 * 32])                                         # object 1B (stage 18 rooms 3 and 4), MSX
    assert seen <= set(B.FIXED), seen - set(B.FIXED)
    assert used(NEW) <= set(range(1, 16))


def test_slots_of_the_pool():
    lw = T.T5.pool_words()
    assert len(NEW) == T.SLOTS * 32 == define('VK_ENEMY16B7_SLOTS') * 32
    import build_candle16 as C16
    assert [cell(NEW, 4), cell(NEW, 5)] == C16.blob_b_cells()               # object 1B: the 16-bit blob (build_candle16.py)
    assert {(ty, p, s) for ty, p, s in T.enemy_rooms()[3]} >= {(15, 0xB4, 4), (15, 0xB8, 5)}
    loaded = {s for lst in T.enemy_rooms().values() for ty, p, s in lst}
    assert loaded == {4, 5} | set(range(38, 67)), sorted(loaded)
    blank = [s for s in range(T.SLOTS) if s not in loaded]
    assert all(not any(cell(NEW, s)) for s in blank), blank


def test_every_msx_enemy_cell_is_replaced():
    lw = T.T5.pool_words()
    for (ty, p), slot in T.slot_map().items():
        if ty not in T.KIND:
            continue
        assert cell(NEW, slot) != cell(lw, slot) or not any(cell(lw, slot)), (ty, hex(p))
    slots = {s for (ty, p), s in T.slot_map().items() if ty in T.KIND}
    assert slots == set(range(38, 67)), sorted(slots)


def test_pose_layout_keeps_the_msx_cells():
    """The pictures are in the first layer cell of each place, the second layer (pattern + 4) is blank."""
    smap = T.slot_map()
    for base in (0x40, 0x50, 0x60, 0x70):                                   # axe knight: awake poses, 16 x 32, two layers
        assert any(cell(NEW, smap[(20, base)])) and any(cell(NEW, smap[(20, base + 8)])), hex(base)
        assert not any(cell(NEW, smap[(20, base + 4)])) and not any(cell(NEW, smap[(20, base + 12)])), hex(base)
    for base in (0x80, 0x88, 0x90, 0x98):                                   # its axe
        assert any(cell(NEW, smap[(21, base)])) and not any(cell(NEW, smap[(21, base + 4)]))
    assert any(cell(NEW, smap[(21, 0xF0)]))
    for p in (0x80, 0x84, 0x88, 0x8C):                                      # flea
        assert any(cell(NEW, smap[(14, p)]))


def test_each_pose_sits_on_its_msx_box():
    """The 16-bit picture of every pose has the foot line (standing poses) or the centre (the others) of the MSX picture of the
    same pose (as laid by the tool), within a pixel; a picture is never cut at the edge of its cells but the axe knight's shield."""
    smap = T.slot_map()
    b6, b5, b4, cv = (T.T.Block(CV, 6), T.T.Block(CV, 5), T.T.Block(CV, 4), B.CV(CV))
    for j, img, ref in T.laid(T.jobs(b6, b5, b4, cv)):
        canvas = B.canvas_of([(x, y, B.Msx.cell(NEW, smap[(ty, p)])) for ty, p, x, y in j['cells']])
        box = B.ref_box(canvas)
        assert box, j['name']
        msx = B.ref_box(T.msx_canvas(j))
        if j['mode'] == 'feet':
            assert abs(box[3] - msx[3]) <= 1, (j['name'], box, msx)
        else:
            assert abs((box[1] + box[3]) - (msx[1] + msx[3])) <= 2, (j['name'], box, msx)
        assert abs((box[0] + box[2]) - (msx[0] + msx[2])) <= 3, (j['name'], box, msx)


def test_shared_cells_agree():
    by_slot = {}
    for key, s in T.slot_map().items():
        by_slot.setdefault(s, []).append(key)
    for s, keys in by_slot.items():
        if len(keys) > 1:
            assert all(k[0] in T.KIND or k[0] == 15 for k in keys), (s, keys)


def test_palettes_keep_msx_colours_of_every_room():
    pals = palettes()
    info = T.room_info()
    assert sorted(info) == list(range(1, 9))
    for pal in pals:
        assert pal[0] == 0
    for room, (msx, g, kinds) in info.items():
        assert [pals[g][i] for i in B.FIXED] == [msx[i] for i in B.FIXED], room
    assert {g for msx, g, kinds in info.values()} == {0, 1}
    # a cell is only in rooms of ONE palette (flea rooms or axe knight rooms)
    for room, lst in T.enemy_rooms().items():
        if room in info:
            for ty, p, slot in lst:
                if ty in T.KIND:
                    assert T.GROUP_OF_KIND[T.KIND[ty]] == info[room][1], (room, ty)


def test_the_c_code_picks_the_same_rooms_and_palettes():
    gfx = (ROOT / 'sgdk/src/gfx16.c').read_text()
    assert 'vk_gfx16_on && stage == 18 && room >= 1 && room <= 8' in gfx
    assert 'vk_enemy16b7_palette[room == 1 || room == 2 || room == 8]' in gfx
    assert set(T.room_info()) == {r for r in range(12) if c_predicate(18, r)}
    for r, (msx, g, kinds) in T.room_info().items():
        assert c_group(r) == g, r
    # every room of stage 18 that loads cells has an enemy of the block; room 0 and rooms 9 to 11 load nothing
    assert {k for k in T.enemy_rooms() if not c_predicate(18, k)} == set()
    actors = (ROOT / 'sgdk/src/actors.c').read_text()
    assert 'if(vk_gfx16_on&&vk_game.stage==18)words=vk_gfx16_b7_late(vk_game.stage,vk_game.room,words);' in actors


def test_generated_file_is_up_to_date():
    b6, b5, b4, cv = (T.T.Block(CV, 6), T.T.Block(CV, 5), T.T.Block(CV, 4), B.CV(CV))
    pool, pals, allowed, errs, hist, written, pics = T.build(b6, b5, b4, cv)
    assert [w for c in pool for w in c] == NEW
    assert palettes() == pals
    tot = sum(sum(h.values()) for h in hist.values())
    assert sum(errs[k] * sum(hist[k].values()) for k in hist) / tot < 20


class Block7(unittest.TestCase):
    """The checks above, also for `python -m unittest discover`."""

    def test_all(self):
        for name, f in sorted(globals().items()):
            if name.startswith('test_') and callable(f):
                with self.subTest(name):
                    f()

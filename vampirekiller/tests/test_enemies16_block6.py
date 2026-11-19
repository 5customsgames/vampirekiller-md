"""16-bit common enemies of block 6 (tools/build_enemies16_block6.py, research/gfx16.md): in 16-bit mode PAL2 of the rooms of
stages 16 and 17 that load enemy cells (stage 16 rooms 1-4, 7, 8; stage 17 rooms 1-10) is one of the four
vk_enemy16b6_palette (stage 16 / stage 17 room 1 / stage 17 rooms 2 and 6-10 / stage 17 rooms 3-5). It may only change the
entries no other PAL2 content of those rooms uses (objects, key, door, HUD boxes, text, object 1B): those keep the MSX colour of
every room of the group. The 16-bit cells are stored by pool slot (late_graphics_slots), so a room loads the same slots with the
same transfers from vk_enemy16b6_cells as from late_graphics_words; object 1B stays MSX; stage 18 is not touched."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import build_enemies16_block6 as T  # noqa: E402
from test_enemies16 import OTHER, arrays, used  # noqa: E402

B = T.B
SRC = (GEN / 'enemies16b6_md.c').read_text()
HDR = (GEN / 'enemies16b6_md.h').read_text()
NEW = arrays(GEN / 'enemies16b6_md.c')['vk_enemy16b6_cells']
CV = ROOT.parent / 'castlevania'


def cell(words, c):
    return words[c * 32:(c + 1) * 32]


def define(name):
    return int(re.search(r'#define %s (\d+)' % name, HDR).group(1))


def palettes():
    m = re.search(r'vk_enemy16b6_palette\[4\]\[16\] = \{(.*?)\n\};', SRC, re.S)
    v = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    assert len(v) == 64
    return [v[i * 16:(i + 1) * 16] for i in range(4)]


def c_predicate(stage, room):
    """vk_gfx16_enemies_b6 (gfx16.c), without the vk_gfx16_on test."""
    return (stage == 16 and 1 <= room <= 8 and room not in (5, 6)) or (stage == 17 and 1 <= room <= 10)


def c_group(stage, room):
    """The palette index of vk_gfx16_pal2 (gfx16.c)."""
    return 0 if stage == 16 else 1 if room == 1 else 3 if 3 <= room <= 5 else 2


def test_free_entries_unused_by_other_pal2_content():
    seen = set()
    for f in OTHER:
        for name, words in arrays(GEN / f).items():
            seen |= used(words)
    lw = T.T5.pool_words()
    seen |= used(lw[4 * 32:6 * 32])                                         # object 1B (stage 17 rooms 3, 5, 9), MSX
    assert seen <= set(B.FIXED), seen - set(B.FIXED)
    assert used(NEW) <= set(range(1, 16))


def test_slots_of_the_pool():
    lw = T.T5.pool_words()
    smap = T.slot_map()
    assert len(NEW) == T.SLOTS * 32 == define('VK_ENEMY16B6_SLOTS') * 32
    import build_candle16 as C16
    assert [cell(NEW, 4), cell(NEW, 5)] == C16.blob_b_cells()               # object 1B: the 16-bit blob (build_candle16.py)
    assert {(ty, p, s) for ty, p, s in T.enemy_rooms()[(17, 3)]} >= {(15, 0xB4, 4), (15, 0xB8, 5)}
    # every slot the rooms of stages 16 and 17 load is stored: 3 (the fireball), 4 and 5 (1B), 26 to 80 (stage 17 and the bat)
    loaded = {s for lst in T.enemy_rooms().values() for ty, p, s in lst}
    assert loaded == {3, 4, 5} | set(range(26, 81)), sorted(loaded)
    extra = set(T.EAGLE_EXTRA.values())                                    # 81 to 83: left column of the 16-bit eagle, after slot 80
    assert extra == {81, 82, 83} and not extra & loaded and all(any(cell(NEW, s)) for s in extra)
    blank = [s for s in range(T.SLOTS) if s not in loaded and s not in extra]
    assert all(not any(cell(NEW, s)) for s in blank), blank
    assert smap[(10, 0x60)] == smap[(10, 0xF0)] == 3 and any(cell(NEW, 3))


def test_every_msx_enemy_cell_is_replaced():
    lw = T.T5.pool_words()
    for (ty, p), slot in T.slot_map().items():
        if ty not in T.KIND:
            continue
        # a drawn MSX cell becomes the 16-bit picture, or the blank second layer; no cell stays as it was
        assert cell(NEW, slot) != cell(lw, slot) or not any(cell(lw, slot)), (ty, hex(p))
    slots = {s for (ty, p), s in T.slot_map().items() if ty in T.KIND}
    assert slots == {3} | set(range(26, 81)), sorted(slots)


def test_pose_layout_keeps_the_msx_cells():
    """The pictures are in the first layer cell of each place, the second layer (pattern + 4) is blank."""
    smap = T.slot_map()
    for base in (0x40, 0x50, 0x60, 0x70):                                   # axe knight: awake poses, 16 x 32, two layers
        assert any(cell(NEW, smap[(20, base)])) and any(cell(NEW, smap[(20, base + 8)])), hex(base)
        assert not any(cell(NEW, smap[(20, base + 4)])) and not any(cell(NEW, smap[(20, base + 12)])), hex(base)
    for base in (0x80, 0x88, 0x90, 0x98):                                   # its axe
        assert any(cell(NEW, smap[(21, base)])) and not any(cell(NEW, smap[(21, base + 4)]))
    for p in (0x64, 0x68, 0x6C, 0x70, 0x74, 0x78, 0x7C, 0x80):             # white skeleton: composed cells
        assert any(cell(NEW, smap[(11, p)]))
    for p in (0x98, 0x9C, 0xA0, 0xF0):                                      # its bone and the ball of the first frames
        assert any(cell(NEW, smap[(13, p)]))
    for p in (0x80, 0x84, 0x88, 0x8C):                                      # flea
        assert any(cell(NEW, smap[(14, p)]))
    for p in (0x40, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70):                    # eagle: head cell (left top of 6D, 8D), three wing columns
        assert any(cell(NEW, smap[(18, p)])), hex(p)
    for p in (0x44, 0x4C, 0x54):                                            # eagle: left column cells the MSX tables do not load
        assert any(cell(NEW, T.EAGLE_EXTRA[(18, p)])), hex(p)
    for p in (0x40, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70):                    # bat: two poses, body cells included
        assert any(cell(NEW, smap[(23, p)])), hex(p)
    assert any(cell(NEW, smap[(21, 0xF0)]))


def tile_rows(words, c):
    return B.Msx.cell(words, c)


def test_each_pose_sits_on_its_msx_box():
    """The 16-bit picture of every pose has the foot line (standing poses) or the centre (the others) of the MSX picture of the
    same pose (as laid by the tool), within a pixel; the bat is the MSX body cell for cell (overlap >= 0.95), the eagle covers
    its MSX silhouette (the 16-bit eagle is the 32 x 32 one of block 4); a picture is never cut at the edge of its cells but the
    axe knight's shield."""
    smap = T.slot_map()
    b6, b5, b4, cv = (T.T.Block(CV, 6), T.T.Block(CV, 5), T.T.Block(CV, 4), B.CV(CV))
    pics = T.laid(T.jobs(b6, b5, b4, cv))
    for j, img, ref in pics:
        cells = j['cells']
        canvas = B.canvas_of([(x, y, tile_rows(NEW, {**smap, **T.EAGLE_EXTRA}[(ty, p)])) for ty, p, x, y in cells])
        box = B.ref_box(canvas)
        assert box, j['name']
        if j['mode'] is None:
            msx = cells if not j['name'].startswith('eagle') else [c for c in cells if c[1] in (0x48, 0x50, 0x58, 0x60, 0x68, 0x70)] + [(18, 0x40, 0, 8)]   # eagle MSX: head + wing column
            old = B.canvas_of([(x, y, T.msx_cell(ty, p)) for ty, p, x, y in msx])
            sa = {(x, y) for y, r in enumerate(canvas) for x, v in enumerate(r) if v}
            sb = {(x, y) for y, r in enumerate(old) for x, v in enumerate(r) if v}
            ov = len(sa & sb) / len(sa | sb)
            assert ov >= (0.95 if j['kind'] == 'bat' else 0.3), (j['name'], ov)
            continue
        msx = B.ref_box(T.msx_canvas(j))
        if j['mode'] == 'feet':
            assert abs(box[3] - msx[3]) <= 1, (j['name'], box, msx)
        else:
            assert abs((box[1] + box[3]) - (msx[1] + msx[3])) <= 2, (j['name'], box, msx)
        assert abs((box[0] + box[2]) - (msx[0] + msx[2])) <= 3, (j['name'], box, msx)


def test_shared_cells_agree():
    """A pool slot shared by several (type, pattern) holds one picture (the tool asserts it); the blank layers are blank."""
    by_slot = {}
    for key, s in T.slot_map().items():
        by_slot.setdefault(s, []).append(key)
    for s, keys in by_slot.items():
        if len(keys) > 1:
            assert all(k[0] in T.KIND or k[0] == 15 for k in keys), (s, keys)


def test_palettes_keep_msx_colours_of_every_room():
    pals = palettes()
    info = T.room_info()
    assert len(info) == 6 + 10                                              # stage 16 rooms 1-4, 7, 8; stage 17 rooms 1-10
    for pal in pals:
        assert pal[0] == 0
    for room, (msx, g, kinds) in info.items():
        assert [pals[g][i] for i in B.FIXED] == [msx[i] for i in B.FIXED], room
    assert {g for msx, g, kinds in info.values()} == {0, 1, 2, 3}
    # no cell reads an entry another group's palette would give another meaning to: every cell of a group stays within the entries
    # of its palette (all of them), and a cell shared by several rooms is in rooms of ONE palette
    smap = T.slot_map()
    for (s, r), lst in T.enemy_rooms().items():
        if (s, r) not in info:
            continue
        for ty, p, slot in lst:
            if ty in T.KIND:
                assert T.GROUP_OF_KIND[T.KIND[ty]] == info[(s, r)][1], (s, r, ty)


def test_the_c_code_picks_the_same_rooms_and_palettes():
    gfx = (ROOT / 'sgdk/src/gfx16.c').read_text()
    assert ('(stage == 16 && room >= 1 && room <= 8 && room != 5 && room != 6) || (stage == 17 && room >= 1 && room <= 10)'
            in gfx)
    assert 'vk_enemy16b6_palette[stage == 16 ? 0 : room == 1 ? 1 : room >= 3 && room <= 5 ? 3 : 2]' in gfx
    assert set(T.room_info()) == {(s, r) for s in (16, 17) for r in range(12) if c_predicate(s, r)}
    for (s, r), (msx, g, kinds) in T.room_info().items():
        assert c_group(s, r) == g, (s, r)
    # the rooms that load cells but no enemy of the block (stage 16 room 0, object 1B only) stay MSX
    assert {k for k in T.enemy_rooms() if not c_predicate(*k)} == {(16, 0)}
    actors = (ROOT / 'sgdk/src/actors.c').read_text()
    assert ('if(vk_gfx16_on&&(vk_game.stage==16||vk_game.stage==17))words=vk_gfx16_b6_late(vk_game.stage,vk_game.room,words);'
            in actors)


def test_eagle_poses_have_their_own_left_column():
    """As at stage 11: the whole 32 x 32 eagle follows the pose. Left column = head cell 40 + extra cell 44 (poses 6D, 8D) or the extra
    cells 4C / 54 (pose 6E); they directly follow slot 80, the last slot of the eagle's run, so that the room loads them in the same
    transfer (actors.c, 16-bit mode)."""
    smap = {**T.slot_map(), **T.EAGLE_EXTRA}
    room = T.enemy_rooms()[(17, 7)]
    assert max(s for ty, p, s in room) == 80 and max(T.EAGLE_EXTRA.values()) == 83 and sorted(T.EAGLE_EXTRA.values()) == [81, 82, 83]
    assert T.enemy_rooms()[(17, 10)] == room
    at = lambda p: cell(NEW, smap[(18, p)])                                  # noqa: E731
    for p in (0x40, 0x44, 0x4C, 0x54, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70):
        assert any(at(p)), hex(p)
    assert at(0x40) != at(0x4C) and at(0x44) != at(0x54)
    assert at(0x48) == at(0x68) and at(0x50) == at(0x70) and at(0x48) != at(0x58)
    actors = (ROOT / 'sgdk/src/actors.c').read_text()
    assert 'vk_game.stage==17 && (vk_game.room==7 || vk_game.room==10) ? 3 : 0' in actors
    assert 'late_lut[18][0x44>>2]' in actors and '(vk_game.stage==11 || vk_game.stage==17) && Enemies_object' in actors


def test_generated_file_is_up_to_date():
    b6, b5, b4, cv = (T.T.Block(CV, 6), T.T.Block(CV, 5), T.T.Block(CV, 4), B.CV(CV))
    pool, pals, allowed, errs, hist, written, pics = T.build(b6, b5, b4, cv)
    assert [w for c in pool for w in c] == NEW
    assert palettes() == pals
    tot = sum(sum(h.values()) for h in hist.values())
    assert sum(errs[k] * sum(hist[k].values()) for k in hist) / tot < 20


class Block6(unittest.TestCase):
    """The checks above, also for `python -m unittest discover`."""

    def test_all(self):
        for name, f in sorted(globals().items()):
            if name.startswith('test_') and callable(f):
                with self.subTest(name):
                    f()

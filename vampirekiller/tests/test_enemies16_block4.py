"""16-bit common enemies of block 4 (tools/build_enemies16_block4.py, research/gfx16.md): in 16-bit mode PAL2 of the rooms of
stages 10 to 12 (but the stage 12 boss room) is one of the four vk_enemy16b4_palette (stage 10, stage 11 room 0, stage 11
rooms 1-4, the dragon rooms). It may only change the entries no other PAL2 content of those rooms uses (objects, key, door,
HUD boxes, text, object 1B): those keep the MSX colour of every room of the group. The 16-bit cells take the place of cells
of the MSX arrays (same layout): every drawn MSX cell of the type 5 blocks of stages 10 and 11 is replaced, as are the bat
of stage 10, the zombies of stage 11 room 0 and the dragon cells of the stage 12 late pool; object 1B (slots 4, 5) is the 16-bit blob of build_candle16.py."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import build_enemies16_block4 as T  # noqa: E402
from test_enemies16 import OTHER, arrays, used  # noqa: E402

B = T.B
SRC = (GEN / 'enemies16b4_md.c').read_text()
HDR = (GEN / 'enemies16b4_md.h').read_text()
NEW = arrays(GEN / 'enemies16b4_md.c')


def define(name):
    return int(re.search(r'#define %s (\d+)' % name, HDR).group(1))


def palettes():
    m = re.search(r'vk_enemy16b4_palette\[4\]\[16\] = \{(.*?)\n\};', SRC, re.S)
    v = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    assert len(v) == 64
    return dict(zip(T.GROUPS, (v[i * 16:i * 16 + 16] for i in range(4))))


def cell(words, c):
    return words[c * 32:(c + 1) * 32]


def runs():
    """{block: (first pool cell, number of cells)}: the run loaded from pattern 40 (gfx16.c)."""
    return {blk: (define('VK_ENEMY16B4_STAGE%s_CELL' % blk[1:]), define('VK_ENEMY16B4_STAGE%s_CELLS' % blk[1:]))
            for blk in ('s10', 's11')}


def test_free_entries_unused_by_other_pal2_content():
    seen = set()
    for f in OTHER:
        for name, words in arrays(GEN / f).items():
            seen |= used(words)
    ghost = B.nums((GEN / 'stage11_enemies_md.c').read_text(), r'const u32 vk_stage11_ghost_tiles\[2\]')
    assert len(ghost) == 2 * 64
    seen |= used(ghost)                                                     # object 1B of stage 11, MSX
    lw = T.late_words()
    seen |= used(lw[4 * 32:T.LATE_CELLS * 32])                              # object 1B of stage 12 (late pool cells 4, 5)
    assert seen <= set(B.FIXED), seen - set(B.FIXED)
    for name in ('vk_enemy16b4_cells', 'vk_enemy16b4_bat_tiles', 'vk_enemy16b4_zombie_tiles'):
        assert used(NEW[name]) <= set(range(1, 16)), name


def test_every_msx_enemy_cell_is_replaced():
    pool = NEW['vk_enemy16b4_cells']
    for blk, (first, n) in runs().items():
        words = T.msx_block(int(blk[1:]))
        drawn = {c for c in range(len(words) // 32) if any(cell(words, c))}
        # stage 11: the left column of the 16-bit eagle also takes the blank MSX cells 44, 4C and 54 (actors.c eagle16_cells)
        extra = {(p - 0x40) // 4 for p in T.EAGLE_LEFT if p != 0x40} if blk == 's11' else set()
        assert not extra & drawn, extra & drawn
        # the run covers patterns 40 .. 40 + 4 (n - 1): every drawn MSX cell in it is a 16-bit cell, every blank one stays blank
        for c in range(n):
            assert any(cell(pool, first + c)) == (c in drawn | extra), (blk, hex(0x40 + 4 * c))
            if c in drawn:
                assert cell(pool, first + c) != cell(words, c), (blk, hex(0x40 + 4 * c))
        after = sorted(hex(0x40 + 4 * c) for c in drawn if c >= n)
        assert after == [], (blk, after)          # no MSX enemy cell after the run (object 1B: its own array, loaded after)
    assert runs()['s10'][1] * 4 + 0x40 > 0x90                               # the drop of stage 10 (90) is in the run
    assert T.DRAGON[-1] < 0x40 + 4 * runs()['s11'][1]


def test_arrays_loaded_whole_keep_their_layout():
    for name, msx in (('vk_enemy16b4_bat_tiles', T.msx_bat()), ('vk_enemy16b4_zombie_tiles', T.msx_zombie())):
        new = NEW[name]
        assert len(new) == len(msx) == 12 * 32, name
        for c in range(0, 12, 2):                    # poses N, N + 1: the 16-bit cell is in N, layer N + 1 empty
            assert any(cell(msx, c)) or any(cell(msx, c + 1)), (name, c)
            assert any(cell(new, c)) and not any(cell(new, c + 1)), (name, c)


def test_late_pool_section():
    pool = NEW['vk_enemy16b4_cells']
    late = define('VK_ENEMY16B4_LATE_CELL')
    assert define('VK_ENEMY16B4_LATE_CELLS') == T.LATE_CELLS == 6
    first, n = runs()['s11']
    assert late == first + (T.DRAGON[0] - 0x40) // 4                        # the stage 11 dragon cells 90 94 98 9C
    lw = T.late_words()
    for c in range(4):
        assert any(cell(pool, late + c)) and cell(pool, late + c) != cell(lw, c), c
    import build_candle16 as C16
    assert [cell(pool, late + 4), cell(pool, late + 5)] == C16.blob_b_cells()   # object 1B: the 16-bit blob (build_candle16.py)
    assert len(pool) == (late + T.LATE_CELLS) * 32
    where, used_cells = T.late_stage12()
    assert used_cells == set(range(T.LATE_CELLS))


def test_palettes_keep_msx_colours_of_every_room():
    pals = palettes()
    rooms = T.room_palettes()
    assert len(rooms) == 9 + 6 + 11                                         # stage 12 without the boss room
    for g, pal in pals.items():
        assert pal[0] == 0, g
    for room, msx in rooms.items():
        pal = pals[T.group_of(*room)]
        assert [pal[i] for i in B.FIXED] == [msx[i] for i in B.FIXED], room
    assert {T.group_of(*r) for r in rooms} == set(T.GROUPS)


def test_generated_file_is_up_to_date():
    import build_enemies16_block2 as T2
    pool, ls, arrs, pals, errs, err, late = T.build(T2.Block(ROOT.parent / 'castlevania', 4), B.CV(ROOT.parent / 'castlevania'))
    assert [w for c in pool for w in c] == NEW['vk_enemy16b4_cells']
    assert arrs['bat10'] == NEW['vk_enemy16b4_bat_tiles'] and arrs['zomb11'] == NEW['vk_enemy16b4_zombie_tiles']
    assert palettes() == pals
    assert late == define('VK_ENEMY16B4_LATE_CELL')
    assert {blk: (ls[blk][0][1], len(ls[blk])) for blk in ls} == runs()
    assert err < 20


def test_rooms_of_the_c_code():
    src = (ROOT / 'sgdk/src/gfx16.c').read_text()
    assert 'stage >= 10 && stage <= 12 && !vk_boss_room(stage, room)' in src
    # the choice of the palette is group_of (tools/build_enemies16_block4.py)
    assert 'vk_enemy16b4_palette[stage == 10 ? 0 : stage == 12 || room == 5 ? 3 : room ? 2 : 1]' in src
    actors = (ROOT / 'sgdk/src/actors.c').read_text()
    # the helpers are called only in their stage: the rooms of the other stages pay nothing
    assert 'vk_game.stage == 11 ? vk_gfx16_b4_zombie(' in actors
    assert 'vk_game.stage == 10 ? vk_gfx16_b4_bat(' in actors
    assert 'vk_game.stage==12?vk_gfx16_b4_late(' in actors


def test_eagle_poses_have_their_own_left_column():
    """The whole 32 x 32 eagle follows the pose: the left column (cells 40 / 44 for poses 6D and 8D, 4C / 54 for 6E) is not the
    head cell shared by all poses of the MSX layout, which froze the second wing (tester, 2026-11)."""
    pool = NEW['vk_enemy16b4_cells']
    first = runs()['s11'][0]

    def at(p):
        return cell(pool, first + (p - 0x40) // 4)
    for p in T.EAGLE_LEFT + (0x48, 0x50, 0x58, 0x60, 0x68, 0x70):
        assert any(at(p)), hex(p)
    assert at(0x40) != at(0x4C) and at(0x44) != at(0x54)      # up and down poses differ on the left too
    assert at(0x48) == at(0x68) and at(0x50) == at(0x70)      # 8D = 6D
    assert at(0x48) != at(0x58) and at(0x50) != at(0x60)


class Block4(unittest.TestCase):
    """The checks above, also for `python -m unittest discover`."""

    def test_all(self):
        for name, f in sorted(globals().items()):
            if name.startswith('test_') and callable(f):
                with self.subTest(name):
                    f()

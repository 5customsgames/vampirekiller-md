"""16-bit common enemies of block 3 (tools/build_enemies16_block3.py, research/gfx16.md): in 16-bit mode PAL2 of the rooms of
stages 7 to 9 (but the stage 9 boss room) is vk_enemy16b3_palette[0] or [1]. It may only change the entries no other PAL2
content of those rooms uses (objects, key, door, HUD boxes, text, object 1C): those keep their MSX colour, entry 7 included
(66C or 26C depending on the room: the two palettes differ only there, and no 16-bit pixel uses it). The 16-bit cells take the
place of cells of the MSX blocks (same layout): every MSX enemy cell, never the cells of object 1C."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import build_enemies16_block3 as T  # noqa: E402
from test_enemies16 import OTHER, arrays, used  # noqa: E402

B = T.B
SRC = (GEN / 'enemies16b3_md.c').read_text()


def u8s(name):
    m = re.search(r'const u8 %s\[\d+\] = \{(.*?)\};' % name, SRC, re.S)
    return [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]


def palettes():
    m = re.search(r'vk_enemy16b3_palette\[2\]\[16\] = \{(.*?)\n\};', SRC, re.S)
    v = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
    assert len(v) == 32
    return v[:16], v[16:]


def lists():
    out = {}
    for blk in T.BLOCKS:
        v = u8s('vk_enemy16b3_stage%s' % blk[1])
        assert v[-1] == 0 and len(v) % 2 == 1
        out[blk] = list(zip(v[:-1:2], v[1:-1:2]))
    return out


def test_free_entries_unused_by_other_pal2_content():
    seen = set()
    for f in OTHER:
        for name, words in arrays(GEN / f).items():
            seen |= used(words)
    ghost = B.nums((GEN / 'ghost_md.c').read_text(), r'const u32 vk_ghost_tiles\[3\]')
    assert len(ghost) == 3 * 64
    seen |= used(ghost)                                                     # object 1C (stages 7 to 9), MSX
    assert seen <= set(B.FIXED), seen - set(B.FIXED)
    cells = arrays(GEN / 'enemies16b3_md.c')['vk_enemy16b3_cells']
    assert used(cells) <= set(range(1, 16)) - {T.VARIABLE}


def test_every_msx_enemy_cell_is_replaced():
    ls = lists()
    for blk in T.BLOCKS:
        words = T.msx_words(blk)
        drawn = {0x40 + 4 * c for c in range(len(words) // 32) if any(words[c * 32:(c + 1) * 32])}
        assert drawn == {p for p, k in ls[blk]}, (blk, sorted(hex(p) for p in drawn ^ {p for p, k in ls[blk]}))
        assert not {p for p, k in ls[blk]} & {0xB4, 0xB8, 0xBC}, blk    # cells of object 1C, loaded after the block


def test_palettes_keep_msx_colours_of_every_room():
    p0, p1 = palettes()
    assert p0[0] == p1[0] == 0
    assert [i for i in range(16) if p0[i] != p1[i]] == [T.VARIABLE]
    rooms = T.stage_palettes()
    assert len(rooms) == 9 + 8 + 8
    for room, msx in rooms.items():
        pal = (p0, p1)[msx[7] == p1[7]]                                 # the choice of vk_gfx16_pal2 (gfx16.c)
        assert [pal[i] for i in B.FIXED] == [msx[i] for i in B.FIXED], room


def test_pool_is_one_run_per_block():
    ls = lists()
    n = len(arrays(GEN / 'enemies16b3_md.c')['vk_enemy16b3_cells']) // 32
    for blk in T.BLOCKS:
        ps = ls[blk]
        assert all(b[0] == a[0] + 4 and b[1] == a[1] + 1 for a, b in zip(ps, ps[1:])), blk
        assert all(k < n for p, k in ps)


def test_generated_file_is_up_to_date():
    import build_enemies16_block2 as T2
    pool, ls, pals, err = T.build(T2.Block(ROOT.parent / 'castlevania', 3))
    assert [w for cell in pool for w in cell] == arrays(GEN / 'enemies16b3_md.c')['vk_enemy16b3_cells']
    assert list(palettes()) == pals
    assert lists() == ls


def test_rooms_of_the_c_code():
    src = (ROOT / 'sgdk/src/gfx16.c').read_text()
    assert 'stage >= 7 && stage <= 9 && !vk_boss_room(stage, room)' in src
    assert 'vk_enemy16b3_palette[msx[7] == vk_enemy16b3_palette[1][7]]' in src


class Block3(unittest.TestCase):
    """The checks above, also for `python -m unittest discover` (make test)."""

    def test_all(self):
        for name, f in sorted(globals().items()):
            if name.startswith('test_') and callable(f):
                with self.subTest(name):
                    f()

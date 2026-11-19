"""16-bit common enemies of block 2 (tools/build_enemies16_block2.py, research/gfx16.md): in 16-bit mode PAL2 of the rooms of
stages 4 to 6 (but the crusher room 6/1 and the boss room 6/5) is vk_enemy16b2_palette. It may only change the entries no
other PAL2 content of those rooms uses (objects, key, door, HUD boxes, text, object 1A): those keep their MSX colour. The
16-bit cells overwrite cells of the MSX blocks (same layout): every MSX enemy cell but the crushers, never the cells of
object 1A or of the platform."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import build_enemies16_block2 as T  # noqa: E402
from test_enemies16 import OTHER, arrays, used  # noqa: E402

B = T.B


def u8s(name):
    m = re.search(r'const u8 %s\[\d+\] = \{(.*?)\};' % name, (GEN / 'enemies16b2_md.c').read_text(), re.S)
    return [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]


def palette():
    m = re.search(r'vk_enemy16b2_palette\[16\] = \{(.*?)\};', (GEN / 'enemies16b2_md.c').read_text(), re.S)
    return [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]


def overwritten():
    out = {}
    for blk, name in (('s4', 'vk_enemy16b2_stage4'), ('s6', 'vk_enemy16b2_stage6')):
        v = u8s(name)
        assert v[-1] == 0 and len(v) % 2 == 1
        out[blk] = dict(zip(v[:-1:2], v[1:-1:2]))
    return out


def test_free_entries_unused_by_other_pal2_content():
    seen = set()
    for f in OTHER:
        for name, words in arrays(GEN / f).items():
            seen |= used(words)
    seen |= used(arrays(GEN / 'ghost_a_md.c')['vk_ghost_a_tiles'])           # object 1A (stages 4 to 6), MSX
    assert seen <= set(B.FIXED), seen - set(B.FIXED)
    # MSX cells left in the blocks: only the crushers (stage 6 room 1, which keeps the MSX palette)
    ow = overwritten()
    for blk in ('s4', 's6'):
        words = T.msx_words(blk)
        left = [0x40 + 4 * c for c in range(len(words) // 32)
                if any(words[c * 32:(c + 1) * 32]) and 0x40 + 4 * c not in ow[blk]]
        assert left == ([] if blk == 's4' else [0x64, 0x68, 0x6C, 0x70, 0x74, 0x78]), (blk, [hex(p) for p in left])


def test_palette_keeps_msx_colours_of_every_room():
    pal = palette()
    assert pal[0] == 0
    rooms = T.stage_palettes()
    assert len(rooms) == 6 + 6 + 4
    for room in rooms:
        assert [pal[i] for i in B.FIXED] == [room[i] for i in B.FIXED]


def test_cells():
    ow = overwritten()
    cells = arrays(GEN / 'enemies16b2_md.c')['vk_enemy16b2_cells']
    n = len(cells) // 32
    for blk, keep in (('s4', {0x60, 0x70, 0x74}), ('s6', {0x80, 0x84, 0x64, 0x68, 0x6C, 0x70, 0x74, 0x78})):
        assert ow[blk], blk
        for p, k in ow[blk].items():
            assert 0x40 <= p <= 0xBC and p % 4 == 0 and p not in keep, (blk, hex(p))
            assert k < n and any(cells[k * 32:(k + 1) * 32]), (blk, hex(p))
    assert used(cells) <= set(range(1, 16))
    # the medusa head is shared by both blocks
    assert all(ow['s4'][p] == ow['s6'][p] for p in (0x40, 0x48, 0x50, 0x58))


def test_rooms_of_the_c_code():
    src = (ROOT / 'sgdk/src/gfx16.c').read_text()
    assert 'stage >= 4 && stage <= 6 && !(stage == 6 && room == 1) && !vk_boss_room(stage, room)' in src

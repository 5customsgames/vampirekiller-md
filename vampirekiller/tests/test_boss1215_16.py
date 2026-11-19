"""16-bit bosses of the stages 12 and 15 (tools/build_boss1215_16.py, research/gfx16.md): same layout as the MSX arrays, the
entries other PAL2 content reads keep the MSX colour of the boss room, only free entries carry the 16-bit colours, the death
flame is re-indexed on the same PAL2, and the code loads them where the MSX arrays were loaded."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))

import build_enemies16 as B  # noqa: E402
import build_enemies16_block5 as T5  # noqa: E402


def u32(path, name):
    m = re.search(r'%s\[\d+\] = \{(.*?)\};' % name, path.read_text(), re.S)
    return [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{1,8})', m.group(1))]


def u16(path, name):
    m = re.search(r'%s\[\d+\] = \{(.*?)\};' % name, path.read_text(), re.S)
    return [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]


def used(words):
    return {(w >> (4 * k)) & 15 for w in words for k in range(8)} - {0}


F = GEN / 'boss1215_16_md.c'


def test_layout_of_the_msx_arrays():
    assert len(u32(F, 'vk_boss12_16_tiles')) == len(u32(GEN / 'boss12_md.c', 'vk_boss12_tiles')) == 480
    assert len(u32(F, 'vk_boss15_16_tiles')) == len(u32(GEN / 'boss15_md.c', 'vk_boss15_tiles')) == 352
    assert len(u32(F, 'vk_boss12_16_shot_tiles')) == 32
    for n in ('vk_boss12_16_flame_tiles', 'vk_boss15_16_flame_tiles'):
        assert len(u32(F, n)) == len(u32(GEN / 'death_flame_md.c', 'vk_death_flame_tiles')) == 64
    for name, cells in (('vk_boss12_16_tiles', 15), ('vk_boss15_16_tiles', 11)):
        w = u32(F, name)
        for c in range(cells):
            assert any(w[c * 32:(c + 1) * 32]), (name, c)       # every cell is drawn


def test_palettes_keep_the_msx_fixed_entries():
    pal = T5.msx_palettes()
    for name, (stage, room) in (('vk_boss12_16_palette', (12, 6)), ('vk_boss15_16_palette', (15, 9))):
        p, msx = u16(F, name), pal(stage, room)
        assert p[0] == 0
        assert [p[i] for i in B.FIXED] == [msx[i] for i in B.FIXED]


def test_only_valid_entries():
    for tiles, pal in (('vk_boss12_16_tiles', 'vk_boss12_16_palette'), ('vk_boss12_16_shot_tiles', 'vk_boss12_16_palette'),
                       ('vk_boss12_16_flame_tiles', 'vk_boss12_16_palette'), ('vk_boss15_16_tiles', 'vk_boss15_16_palette'),
                       ('vk_boss15_16_flame_tiles', 'vk_boss15_16_palette')):
        assert used(u32(F, tiles)) <= set(range(1, 16))


def test_wiring():
    act = (ROOT / 'sgdk/src/actors.c').read_text()
    for s in ('vk_boss12_16_tiles', 'vk_boss12_16_shot_tiles', 'vk_boss12_16_flame_tiles', 'vk_boss15_16_tiles',
              'vk_boss15_16_flame_tiles'):
        assert s in act
    g = (ROOT / 'sgdk/src/gfx16.c').read_text()
    assert 'vk_boss12_16_palette' in g and 'vk_boss15_16_palette' in g

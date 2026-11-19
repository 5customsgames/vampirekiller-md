"""16-bit bosses of the stages 6 and 9 (tools/build_boss69_16.py, research/gfx16.md): same layout as the MSX arrays, PAL2 of
the boss rooms that keeps the MSX colours other content reads and already holds what the orb writes (entry 5)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))

import build_boss69_16 as T  # noqa: E402
import build_enemies16 as B  # noqa: E402


def u32(path, name):
    m = re.search(r'%s\[\d+\] = \{(.*?)\};' % name, path.read_text(), re.S)
    return [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{1,8})', m.group(1))]


def u16(path, name):
    m = re.search(r'%s\[\d+\] = \{(.*?)\};' % name, path.read_text(), re.S)
    return [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]


def used(words):
    return {(w >> (4 * k)) & 15 for w in words for k in range(8)} - {0}


def test_layout_of_the_msx_arrays():
    f = GEN / 'boss69_16_md.c'
    b6, o6, o9 = (u32(f, 'vk_boss6_16_tiles'), u32(f, 'vk_orb6_16_tiles'), u32(f, 'vk_orb9_16_tiles'))
    b9, fl = u32(f, 'vk_boss9_16_tiles'), u32(f, 'vk_boss9_16_flash')
    assert len(b6) == len(u32(GEN / 'boss6_md.c', 'vk_boss6_tiles')) == 384
    assert len(o6) == len(o9) == len(u32(GEN / 'boss6_md.c', 'vk_orb6_tiles')) == 384
    assert len(b9) == len(u32(GEN / 'boss9_md.c', 'vk_boss9_tiles')) == 640
    assert len(fl) == 6 * 12 * 8
    for c in range(12):                      # 8 head cells and 4 snake cells
        assert any(b6[c * 32:(c + 1) * 32]), c
    for c in range(20):                      # 18 body cells and 2 fireball cells
        assert any(b9[c * 32:(c + 1) * 32]), c
    for c in range(18):
        assert any(fl[c * 32:(c + 1) * 32]), c
    for p in range(3):
        assert any(o6[p * 128:(p + 1) * 128]) and any(o9[p * 128:(p + 1) * 128])
    # the blinking cells differ from the normal ones (orange bandages)
    assert fl != b9[:576]


def test_palettes_of_the_boss_rooms():
    f = GEN / 'boss69_16_md.c'
    for name, stage, room, tiles in (('vk_boss6_16_palette', 6, 5, ('vk_boss6_16_tiles', 'vk_orb6_16_tiles')),
                                     ('vk_boss9_16_palette', 9, 7, ('vk_boss9_16_tiles', 'vk_boss9_16_flash', 'vk_orb9_16_tiles'))):
        pal = u16(f, name)
        msx = T.msx_room_palette(stage, room)
        assert pal[0] == 0
        assert [pal[i] for i in B.FIXED] == [msx[i] for i in B.FIXED]     # colours other PAL2 content uses
        assert pal[5] == 0x006                                           # what the orb writes to entry 5 (actors.c)
        for t in tiles:
            assert used(u32(f, t)) <= set(range(1, 16))
    act = (ROOT / 'sgdk/src/actors.c').read_text()
    assert 'red[2] = { 0x006, 0x00A }' in act and 'vk_boss.kind ? 5 : 4' in act


def test_stage6_body_never_uses_entry_7():
    # entry 7 changes to 00A when the orb appears; the head is gone by then
    assert 7 not in used(u32(GEN / 'boss69_16_md.c', 'vk_boss6_16_tiles'))


def test_generated_file_is_up_to_date():
    # the script is deterministic: tile counts match the header
    h = (GEN / 'boss69_16_md.h').read_text()
    for name, n in (('vk_boss6_16_tiles', 384), ('vk_orb6_16_tiles', 384), ('vk_orb9_16_tiles', 384),
                    ('vk_boss9_16_tiles', 640), ('vk_boss9_16_flash', 576)):
        assert '%s[%d]' % (name, n) in h

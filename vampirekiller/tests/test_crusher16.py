"""16-bit spiked crushers of the stage 6 room 1 (tools/build_crusher16.py, research/gfx16.md): six cells in the layout of
vk_stage6_enemy_tiles (patterns 64 to 78), PAL2 of the room = the MSX room palette with only the entries no other PAL2 content
reads changed, the same 128 tiles loaded in the room."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import build_crusher16 as T  # noqa: E402
from test_enemies16 import arrays, used  # noqa: E402

B = T.be
NEW = arrays(GEN / 'crusher16_md.c')
_c = (GEN / 'crusher16_md.c').read_text()
NEW['vk_crusher16_palette'] = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', re.search(r'vk_crusher16_palette\[16\] = \{(.*?)\};', _c, re.S).group(1))]


def test_layout_of_the_msx_cells():
    msx = B.nums((GEN / 'stage6_enemies_md.c').read_text(), 'vk_stage6_enemy_tiles')
    assert len(msx) == 128 * 8 and len(NEW['vk_crusher16_tiles']) == 24 * 8 == 6 * 32
    h = (GEN / 'crusher16_md.h').read_text()
    assert '#define VK_CRUSHER16_FIRST_TILE 0x24' in h and '#define VK_CRUSHER16_TILES 24' in h
    assert 0x24 == 0x64 - 0x40            # pattern 64 is tile 24h of the block (pattern N is tile N - 40h), 6 cells to pattern 7B
    first = 0x24 * 8
    # the cells around the run are MSX cells that stay: the run really covers the six crusher cells of the MSX arrays
    assert any(msx[first:first + 192]) and not any(msx[first + 192:first + 224])     # 7C is not a crusher cell


def test_generated_file_is_current():
    assert NEW['vk_crusher16_tiles'] == [w for c in T.cells() for w in c]
    assert NEW['vk_crusher16_palette'] == T.palette()


def cell(k):
    return B.Msx.cell(NEW['vk_crusher16_tiles'], k)


def test_chain_cut_cells_are_the_first_rows_of_the_full_cell():
    full = cell(0)
    for k, rows in ((1, 4), (2, 8), (3, 12)):
        c = cell(k)
        assert c[:rows] == full[:rows] and not any(any(r) for r in c[rows:]), k


def test_chain_has_period_four_and_stays_in_its_columns():
    full = cell(0)
    assert all(full[y] == full[y % 4] for y in range(16))
    assert all(not any(r[:5]) and not any(r[11:]) for r in full) and all(any(r) for r in full)


def test_body_sits_in_the_twelve_rows_of_the_msx_body():
    left, right = cell(4), cell(5)
    assert not any(any(r) for r in left[12:]) and not any(any(r) for r in right[12:])
    assert any(left[0][13:]) and any(right[0][:3])                 # the chain end joins the chain strip at the centre
    assert all(left[5][x] and right[5][x] for x in range(1, 16))   # the bar spans the 32 columns


def test_pal2_keeps_the_entries_other_content_reads():
    pal = NEW['vk_crusher16_palette']
    msx = T.msx_palette()
    assert len(pal) == 16
    for i in B.FIXED + (0, 10, 11):
        assert pal[i] == msx[i], i
    assert [i for i in range(16) if pal[i] != msx[i]] == [4, 5, 6, 9]
    assert used(NEW['vk_crusher16_tiles']) <= {2, 4, 5, 6, 9, 12, 13, 14}


def test_code_loads_the_crushers_in_16_bit_mode_only():
    a = (ROOT / 'sgdk/src/actors.c').read_text()
    g = (ROOT / 'sgdk/src/gfx16.c').read_text()
    assert 'if (vk_gfx16_on && vk_game.room == 1)' in a and 'vk_gfx16_crusher_block(vk_stage6_enemy_tiles, VK_STAGE6_ENEMY_TILE_COUNT' in a
    assert 'vk_gfx16_on && stage == 6 && room == 1) return vk_crusher16_palette' in g
    # the three transfers load the 128 tiles of the block
    first, n = 0x24, 24
    assert first + n < 128

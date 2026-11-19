"""16-bit door bar of the hall room 7 (tools/build_door16.py, item_view.c, research/gfx16.md): the layout of vk_door_bar_rows (48 rows
of two words), the knobs and the length of the MSX bar, only the entries 2, 13, 12, 14 of PAL2, which hold the same colour in the MSX
palette of the room and in the PAL2 of the 16-bit room."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

import build_door16 as T  # noqa: E402
from test_enemies16 import arrays, used  # noqa: E402

B = T.be
NEW = arrays(GEN / 'door16_md.c')['vk_door16_rows']


def rows(words):
    return [[(words[r * 2 + c] >> (28 - 4 * x)) & 15 for c in range(2) for x in range(8)] for r in range(48)]


def test_layout_of_the_msx_bar():
    msx = T.msx_rows()
    assert len(msx) == len(NEW) == 96
    m, n = rows(msx), rows(NEW)
    # the MSX bar: shaft on rows 0 to 46 (row 47 empty), wider knobs on rows 2-6, 18-22 and 41-45
    assert not any(m[47]) and not any(n[47])
    assert all(any(n[y]) for y in range(47)) and all(any(m[y]) for y in range(47))
    for y0 in T.COLLARS:
        for dy in range(5):
            need = 6 if dy in (1, 2, 3) else 4                 # the first and last rows of a knob are narrower
            assert sum(1 for v in m[y0 + dy] if v) >= need and sum(1 for v in n[y0 + dy] if v) >= need, (y0, dy)
    for y in (10, 30):                                              # between the knobs: the shaft only
        assert sum(1 for v in m[y] if v) == 4 and sum(1 for v in n[y] if v) == 6
    assert max(x for r in n for x in range(16) if r[x]) < 12 and min(x for r in n for x in range(16) if r[x]) >= 4


def test_generated_file_is_current():
    assert NEW == T.words(T.picture())


def test_entries_hold_the_same_colour_in_pal2_of_the_room():
    assert used(NEW) == {2, 12, 13, 14}
    t = (GEN / 'rooms.c').read_text()
    allp = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', re.search(r'vk_palettes\[\]\[16\] = \{(.*?)\n\};', t, re.S).group(1))]
    stages = [tuple(int(x) for x in re.findall(r'\d+', e))
              for e in re.findall(r'\{([^{}]*)\}', re.search(r'vk_stages\[18\] = \{(.*?)\};', t, re.S).group(1))]
    room7 = allp[(stages[0][0] + 7) * 16:(stages[0][0] + 7) * 16 + 16]          # the MSX palette (the door is only there)
    e16 = re.search(r'vk_enemy16_palette\[16\] = \{(.*?)\};', (GEN / 'enemies16_md.c').read_text(), re.S).group(1)
    pal16 = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', e16)]            # PAL2 of the 16-bit hall rooms
    for i, v in ((2, 0x222), (12, 0xAAA), (13, 0x444), (14, 0xEEE)):
        assert room7[i] == pal16[i] == v, (i, room7[i], pal16[i])


def test_code_picks_the_16_bit_bar_in_16_bit_mode_only():
    a = (ROOT / 'sgdk/src/item_view.c').read_text()
    h = (ROOT / 'sgdk/src/gfx16.h').read_text()
    assert 'vk_gfx16_on ? vk_door16_rows : (const u32 *)vk_door_bar_rows' in a and 'bar[source * 2 + col]' in a
    assert 'draw_block(DOOR_TILE_INDEX' in a              # the same palette line as the MSX bar (VK_PAL_OBJ)
    assert '#include "generated/door16_md.h"' in h

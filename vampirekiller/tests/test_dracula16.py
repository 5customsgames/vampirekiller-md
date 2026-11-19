"""16-bit Dracula (tools/build_dracula16.py, research/gfx16.md): the 96 tiles of the sprite cells and the 65 bust composites in the
layout of the MSX arrays (same cells, same tile count, same transfers), a fixed PAL2 whose entries 8 and 14 are the MSX ones, the
code uses them only in 16-bit mode."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'sgdk/src/generated'
sys.path.insert(0, str(ROOT / 'tools'))

import build_dracula16 as T  # noqa: E402

CV = ROOT.parent / 'castlevania'


def words(path, name):
    m = re.search(r'%s(?:\[[^\]]*\])+\s*=\s*\{(.*?)\n\};' % name, path.read_text(), re.S)
    return [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]+)', m.group(1))]


TILES = words(GEN / 'dracula16_md.c', 'vk_dracula16_tiles')
PAL = words(GEN / 'dracula16_md.c', 'vk_dracula16_palette')
UNIQUE = words(GEN / 'dracula16_md.c', 'vk_dracula16_bust_unique')
INDEX = [int(x) for x in re.findall(r'\d+', re.search(r'vk_dracula16_bust_index\[65\]\[16\] = \{(.*?)\n\};',
                                                   (GEN / 'dracula16_md.c').read_text(), re.S).group(1))]
MSX = words(GEN / 'dracula_md.c', 'vk_dracula_tiles')


def used(ws):
    return {(w >> (4 * k)) & 15 for w in ws for k in range(8)} - {0}


def test_layout_of_the_msx_array():
    assert len(TILES) == len(MSX) == 96 * 8
    for c in range(24):
        assert any(TILES[c * 32:(c + 1) * 32]), c    # the hood cells (2, 6) hold the red hood (touch-up 1B / 5B)


def test_generated_file_is_current():
    if not CV.exists():
        return
    pics, _, pal, _, tiles, unique, index = T.make(CV)      # with the retained touch-ups (dracula_touchups.RETAINED)
    assert PAL == pal
    assert TILES == tiles
    assert INDEX == index and UNIQUE == [w for t in unique for w in t]


def test_palette_keeps_the_entries_other_content_reads():
    init = [int(x) for x in re.findall(r'\d+', re.search(r'vk_dracula_initial_palette\[32\]=\{(.*?)\};',
                                                        (GEN / 'dracula_background.c').read_text(), re.S).group(1))]
    for i in T.FIXED:                                # Simon's silhouette (actors.c load_simon_color) reads PAL2 entries 8 and 14
        rb, g = init[2 * i], init[2 * i + 1]
        assert PAL[i] == ((rb & 7) * 2 << 8) | ((g & 7) * 2 << 4) | ((rb >> 4 & 7) * 2)
    assert PAL[0] == 0 and used(TILES) <= set(range(1, 16)) and used(UNIQUE) <= set(range(1, 16))


def test_bust_composites():
    n = len(UNIQUE) // 8
    assert len(INDEX) == 65 * 16 and max(INDEX) < n <= 256
    set_of = [int(x) for x in re.findall(r'\d+', re.search(r'vk_dracula_bust_set_of\[625\]=\{(.*?)\};',
                                                           (GEN / 'dracula_background.c').read_text(), re.S).group(1))]
    assert len([v for v in set_of if v != 255]) == 65
    # the composite of layer 1 (closed cloak, left) is the mirror image of layer 3 (right); layer 2 only draws over layer 1
    def image(s):
        img = [[0] * 32 for _ in range(32)]
        for t in range(16):
            for y in range(8):
                w = UNIQUE[INDEX[s * 16 + t] * 8 + y]
                for x in range(8):
                    img[(t % 4) * 8 + y][(t // 4) * 8 + x] = (w >> (28 - 4 * x)) & 15
        return img
    l1, l3 = image(set_of[1]), image(set_of[3])
    assert any(any(r) for r in l1) and [r[::-1] for r in l1] == l3
    both = image(set_of[1 + 2 * 5])                  # layers 1 then 2
    assert both != l1 and all(b == a or b for ra, rb in zip(l1, both) for a, b in zip(ra, rb))
    assert not any(any(r) for r in image(set_of[0]))


def test_code_uses_the_16_bit_art_only_in_16_bit_mode():
    v = (ROOT / 'sgdk/src/dracula_view.c').read_text()
    assert 'VDP_loadTileData(vk_gfx16?vk_dracula16_tiles:vk_dracula_tiles,ENEMY5_TILE_INDEX,VK_DRACULA_TILE_COUNT,CPU)' in v
    assert 'PAL_setPalette(PAL2,vk_gfx16?vk_dracula16_palette:vk_dracula_background_palette,CPU)' in v
    assert 'if(!in_credits && !vk_gfx16)PAL_setPalette(PAL2,colors,DMA_QUEUE_COPY);' in v
    assert 'if(vk_gfx16){index=vk_dracula16_bust_index[set];unique=vk_dracula16_bust_unique;}' in v


FACE_PAL = words(GEN / 'dracula16_md.c', 'vk_dracula16_face_palette')
FACE_INIT = [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', re.search(r'vk_dracula16_face_initial\[32\] = \{(.*?)\};',
                                                                      (GEN / 'dracula16_md.c').read_text(), re.S).group(1))]


def test_face_palette_is_the_regraded_msx_palette():
    """8B: same bytes format as vk_dracula_initial_palette (the fade and the pulse of entry 6 work on them), words = those bytes; only the
    skin ramp changes (the walls, the teeth, entry 14 of the credits text keep their colour)."""
    init = [int(x) for x in re.findall(r'\d+', re.search(r'vk_dracula_initial_palette\[32\]=\{(.*?)\};',
                                                         (GEN / 'dracula_background.c').read_text(), re.S).group(1))]
    assert len(FACE_INIT) == 32 and len(FACE_PAL) == 16
    for i in range(16):
        rb, g = FACE_INIT[2 * i], FACE_INIT[2 * i + 1]
        assert FACE_PAL[i] == ((rb & 7) * 2 << 8) | ((g & 7) * 2 << 4) | ((rb >> 4 & 7) * 2), i
    changed = {i for i in range(16) if FACE_INIT[2 * i:2 * i + 2] != init[2 * i:2 * i + 2]}
    assert changed == {1, 3, 4, 5, 6, 7, 11, 13}, changed
    assert FACE_INIT[28:] == init[28:] and FACE_INIT[16:18] == init[16:18]       # entries 8 (red), 14 (white credits text)


def test_code_installs_the_face_palette_in_16_bit_mode_only():
    v = (ROOT / 'sgdk/src/dracula_view.c').read_text()
    assert 'd->palette[i]=vk_gfx16?vk_dracula16_face_initial[i]:vk_dracula_initial_palette[i];' in v
    assert 'PAL_setPalette(PAL0,vk_gfx16?vk_dracula16_face_palette:vk_dracula_background_palette,CPU);' in v

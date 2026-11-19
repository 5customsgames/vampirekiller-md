#!/usr/bin/env python3
"""Convert the title screen, the introduction and the ending (tools/record_screens.py) into SGDK data: src/screens.c,
inc/screens.h.

usage: screens_to_md.py [--screens DIR] [--src DIR] [--inc DIR]

Each screen is a full NES picture (32x30 cells, put on plane A like the level: 32 px to the right, the first NES row
hidden by the vertical scroll of 8) plus the sprites of every frame, replayed as the NES game drew them. The art
is the SNES port's 16-colour tiles with the palettes it uses for these screens (00 for the title, 01 for the
introduction, 10 for the ending); each screen gets its own 4 MD palettes, shared by its background and sprite tiles.
The ending also has the credits it writes into its picture, frame by frame, and their fades: their NES palette
(background 3) gets MD palette 3 alone, its tiles keep their NES pixel values, and each step's 3 colours are given
for both arts (the 16-bit art's colour for a NES colour is the one its tiles show where the NES art shows that one). The original NES
art is written too (<screen>_tiles_nes, <screen>_palette_nes) with the same map and sprites: the NES palettes are
shared out among the MD ones the same way for both arts, and tiles by the pair (16-bit, NES).
"""
import argparse, itertools, json
from collections import Counter
from pathlib import Path
from art import ART_SUFFIX, Art16, ArtNES, pack_palette, md_word, nes_index, rgb9_from_nes
from nes_dump import tile_pixels
from sound_to_md import MUSIC

OX, OY = 32, -8                    # NES picture -> MD screen (the level's own offsets)
SNES_PAL = {"title": "00", "intro": "01", "ending": "10", "map": "09"}
TEXT = 3                           # the ending's credits: NES background palette 3, faded in and out, has MD palette 3


def title_chr_origin(chr_, prg):
    """Recover the title's exact tile sources from NES CHR load set 0.

    Matching by NES pixel bytes is ambiguous: the title's $51 is empty in the
    16-bit art, but another identical NES tile is a solid block there.
    """
    def rd(address, bank=4):
        if not 0x8000 <= address <= 0xFFFF:
            raise ValueError("invalid title CHR source address")
        offset = (len(prg) - 0x4000 + address - 0xC000 if address >= 0xC000
                  else bank * 0x4000 + address - 0x8000)
        if not 0 <= offset < len(prg):
            raise ValueError("title CHR source outside PRG")
        return prg[offset]

    def word(address):
        return rd(address) | (rd(address + 1) << 8)

    pointer = word(0xFDBB)                       # title: CHR load set 0
    origin = {}
    for _ in range(32):                         # reject malformed unterminated lists
        bank = rd(pointer)
        if bank == 0xFF:
            return origin
        source, target, size = word(pointer + 1), word(pointer + 3), word(pointer + 5)
        if target % 16 or size % 16 or target + size > len(chr_):
            raise ValueError("invalid title CHR transfer")
        data = bytes(rd(source + k, bank) for k in range(size))
        if chr_[target:target + size] != data:
            raise ValueError("recorded title CHR does not match load set 0; record the screens again")
        for k in range(0, size, 16):
            address = source + k
            actual_bank = len(prg) // 0x4000 - 1 if address >= 0xC000 else bank
            origin[(target + k) // 16] = (actual_bank, address & 0x3FFF)
        pointer += 7
    raise ValueError("unterminated title CHR transfer list")


def screen_bg_tile(name, art, tile, palette):
    # NES $40 is a flat fill reused by the title's grey frame and red ribbon.
    # Its 16-bit replacement is textured for the frame; with logo palette 0
    # that texture turns green. Tile $23 supplies the ribbon's flat red fill.
    # Keep the NES art and the frame's palette-2 uses of $40 unchanged.
    if name == "title" and art.name == "16bit" and tile == 0x40 and palette == 0:
        tile = 0x23
    return art.bg_tile(tile, palette)


def convert(name, info, d, snes, prg, chr_origin=None):
    chr_ = (d / f"{name}_chr.bin").read_bytes()
    nt = (d / f"{name}_nt.bin").read_bytes()
    pal = (d / f"{name}_pal.bin").read_bytes()
    n = SNES_PAL[name]
    # Resolve background tiles by their load addresses. Keep sprite conversion
    # unchanged so this correction does not alter the logo sprites' shading.
    origin = ({i: location for i, location in title_chr_origin(chr_, prg).items() if i >= 256}
              if name == "title" else None)
    if chr_origin is not None:
        origin = chr_origin
    arts = [Art16(chr_, pal, prg, snes, snes / f"16bit-tiles/bg_16bit_palette_{n}.bin",
                  snes / f"16bit-tiles/sprite_16bit_palette_{n}.bin", origin), ArtNES(chr_, pal)]

    # NES colour -> this art's colour, from the pixels of the screen's tiles in both arts (the NES colour itself when
    # the screen does not show it)
    def art_color(art, nes):
        if art.name == "nes":
            return rgb9_from_nes(nes)
        votes = Counter()
        for ty in range(30):
            for tx in range(32):
                attr = nt[960 + (ty // 4) * 8 + tx // 4]
                p = (attr >> (((ty // 2) & 1) * 4 + ((tx // 2) & 1) * 2)) & 3
                if p == TEXT and name == "ending":
                    continue
                t = nt[ty * 32 + tx]
                for a_, b_ in zip(arts[1].bg_tile(t, p), art.bg_tile(t, p)):
                    if a_ and b_ and a_[3] == nes & 0x3F:
                        votes[b_[:3]] += 1
        return votes.most_common(1)[0][0] if votes else rgb9_from_nes(nes)[:3]
    def text_colors(art, k):                           # the text palette at fade step k (0: as first shown)
        trio = steps[k]
        return [art_color(art, c) for c in trio]
    steps = []                                         # the text palette's colours (1-3), as first shown then each fade
    if name == "ending":
        steps.append(tuple(pal[13:16]))
        for _, trio in info["fades"]:
            if tuple(trio) not in steps:
                steps.append(tuple(trio))

    cells = []
    for ty in range(30):
        for tx in range(32):
            attr = nt[960 + (ty // 4) * 8 + tx // 4]
            cells.append((nt[ty * 32 + tx], (attr >> (((ty // 2) & 1) * 4 + ((tx // 2) & 1) * 2)) & 3))
    # the ending's credits: the cells written later, in the palettes of their places
    writes = [(f, c, (t, cells[c][1])) for f, c, t in info.get("writes", [])]
    text = TEXT if name == "ending" else None
    extra_cells = [tuple(cell) for cell in info.get("extra_cells", [])]
    all_cells = cells + [w[2] for w in writes] + extra_cells
    # sprites: the NES game's sprite 0 (tile $FF behind the background) only marks the HUD split
    frames = [[s for s in f if not (s[2] == 0xFF and s[3] & 0x20)] for f in info["frames"]]
    spr_keys = Counter(((256 if t & 1 else 0) + (t & 0xFE), at & 3) for f in frames for _, _, t, at in f)
    spr_keys.update(tuple(key) for key in info.get("extra_sprites", []))

    # ---- palettes: 8 NES palettes (4 background, 4 sprite) shared out among the 4 MD palettes
    # (the 16-bit art decides how they are shared out; its cost wins over the NES art's, which has far fewer colours)
    pixels, weights = [], []
    for art in arts:
        px_, w_ = {}, [Counter() for _ in range(8)]
        for t, p in set(all_cells):
            # the text palette changes at run time: its tiles keep the NES pixel values (1-3, MD entries 1-3)
            px_[("bg", t, p)] = ([None if v == 0 else ("v", v) for row in tile_pixels(chr_, 0x1000, t) for v in row]
                                 if p == text else screen_bg_tile(name, art, t, p))
        for (ci, p) in spr_keys:
            px_[("spr", ci, p)] = art.spr_tile(ci, p) + art.spr_tile(ci + 1, p)
        for t, p in all_cells:
            for c in px_[("bg", t, p)]:
                if c: w_[p][c] += 1
        for (ci, p), n in spr_keys.items():
            for c in px_[("spr", ci, p)]:
                if c: w_[4 + p][c] += 1
        pixels.append(px_)
        weights.append(w_)
    used = [g for g in range(8) if any(w_[g] for w_ in weights)]
    best = None
    for assign in itertools.product(range(4), repeat=len(used)):
        if text is not None and any((g == text) != (b == 3) for g, b in zip(used, assign)):
            continue                                   # the text palette alone in MD palette 3
        cost = []
        for w_ in weights:
            bins = [set() for _ in range(4)]
            for g, b in zip(used, assign):
                bins[b] |= set(w_[g])
            cost.append(sum(max(0, len(b_) - 15) for b_ in bins))
        if best is None or cost < best[0]:
            best = (cost, assign)
    group = dict(zip(used, best[1]))
    packed, colors = [], []
    for art, w_ in zip(arts, weights):
        bin_w = [Counter() for _ in range(4)]
        for g in used:
            bin_w[group[g]].update(w_[g])
        packed.append([pack_palette(w) if w else ([], {}) for w in bin_w])
        if text is not None:
            packed[-1][3] = (text_colors(art, 0), {("v", v): v for v in (1, 2, 3)})
        backdrop = art.backdrop()
        colors.append([])
        for pal_list, _ in packed[-1]:
            row = [backdrop] + pal_list
            colors[-1] += row + [backdrop] * (16 - len(row))      # (r, g, b[, NES index]): words at writing

    # ---- tiles
    def encode(px, k, b):          # 8x8 pixels of art k in MD palette b
        out = []
        for y in range(8):
            v = 0
            for x in range(8):
                c = px[y * 8 + x]
                v = (v << 4) | (packed[k][b][1][c] if c else 0)
            out.append(v)
        return tuple(out)
    tiles, index = [((0,) * 8,) * len(arts)], {}       # each tile = its data in every art
    def add(key, b):
        data = tuple(encode(px_[key], k, b) for k, px_ in enumerate(pixels))
        if data not in index:
            index[data] = len(tiles)
            tiles.append(data)
        return index[data]
    words = {}
    for t, p in cells + extra_cells:
        if (t, p) not in words:
            key = ("bg", t, p)
            words[(t, p)] = 0 if not any(any(px_[key]) for px_ in pixels) else add(key, group[p]) | (group[p] << 13)
    bg_map = [words[c] for c in cells]
    spr_tile = {}
    for key in sorted(spr_keys):                       # top and bottom tiles must be consecutive
        ci, p = key
        b = group[4 + p]
        first = len(tiles)
        for h in (slice(0, 64), slice(64, 128)):
            tiles.append(tuple(encode(px_[("spr", ci, p)][h], k, b) for k, px_ in enumerate(pixels)))
        spr_tile[key] = first | (b << 13)

    # ---- frames: each distinct sprite list once
    lists, list_index, frame_list, entries = [], {}, [], []
    for f in frames:
        sprs = []
        for x, y, t, at in f:
            w = spr_tile[((256 if t & 1 else 0) + (t & 0xFE), at & 3)]
            w |= (0x1000 if at & 0x80 else 0) | (0x0800 if at & 0x40 else 0)
            sprs.append((x + OX, y + 1 + OY, w))
        key = tuple(sprs)
        if key not in list_index:
            list_index[key] = len(lists)
            lists.append((len(entries), len(sprs)))
            entries += sprs
        frame_list.append(list_index[key])
    stats = f"{name}: {len(tiles)} tiles, palettes " + ", ".join(
        f"{art.name} {[len(p_[0]) for p_ in pk]} (cost {c})" for art, pk, c in zip(arts, packed, best[0])) + \
        f", {len(frames)} frames, {len(lists)} sprite lists, {len(entries)} sprites, art fallbacks {arts[0].fallbacks}"
    extra = {}
    if name == "ending":
        for _, c, tp in writes:
            if tp not in words:
                key = ("bg",) + tp
                words[tp] = 0 if not any(any(px_[key]) for px_ in pixels) else add(key, group[tp[1]]) | (group[tp[1]] << 13)
        extra["writes"] = [(f, c, words[tp]) for f, c, tp in writes]
        extra["fades"] = [(f, steps.index(tuple(trio))) for f, trio in info["fades"]]
        extra["fade_colors"] = [[[md_word(c) for c in text_colors(art, k)] for k in range(len(steps))] for art in arts]
        extra["fade_nesidx"] = [list(trio) for trio in steps]
        names = dict(MUSIC)
        extra["sounds"] = [(f, f"MUS_{names[v]}" if v in names else f"SFX_{v:02X}") for f, v in info["sounds"]]
        stats += f", {len(writes)} cell writes, {len(steps)} text colours, sounds {extra['sounds']}"
    return dict(tiles=tiles, colors=colors, map=bg_map, lists=lists, entries=entries, frames=frame_list,
                arts=[art.name for art in arts], words=words, sprite_words=spr_tile, **extra), stats


def snes_card(snes):
    """the SNES port's credits card (intro_screen.asm): its skull border, tiles $E6-$E9 of its own 4bpp intro set
    (chrom-basic-intro-tiles.asm), and its 4 colours (write_intro_palette, BGR555 -> MD 3 bits each)"""
    import re
    b = []
    for line in (snes / "chrom-basic-intro-tiles.asm").read_text().splitlines():
        if line.strip().startswith(".byte"):
            b += [int(x, 16) for x in re.findall(r"\$([0-9a-fA-F]{2})", line)]
    tiles = []
    for i in range(0xE6, 0xEA):
        t = b[i * 32:(i + 1) * 32]
        rows = []
        for y in range(8):
            v = 0
            for x in range(8):
                bit = 7 - x
                v = v << 4 | ((t[2 * y] >> bit) & 1) | ((t[2 * y + 1] >> bit) & 1) << 1 \
                    | ((t[16 + 2 * y] >> bit) & 1) << 2 | ((t[17 + 2 * y] >> bit) & 1) << 3
            rows.append(v)
        tiles.append(rows)
    md = lambda c: ((c >> 12) & 7) << 9 | ((c >> 7) & 7) << 5 | ((c >> 2) & 7) << 1
    colors = [md(c) for c in (0x0000, 0x7FFF, 0x3A1F, 0x10D6)]
    return tiles, colors


def main():
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--screens", default=str(root / "tools/extracted/screens"))
    ap.add_argument("--prg", default=str(root / "tools/extracted/prg.bin"))
    ap.add_argument("--src", default=str(root / "src"))
    ap.add_argument("--inc", default=str(root / "inc"))
    a = ap.parse_args()
    d = Path(a.screens)
    info = json.loads((d / "screens.json").read_text())
    snes = root / "tools" / "extracted" / "snes"            # copied by tools/import_snes.py
    prg = Path(a.prg).read_bytes()
    out = {}
    for name in ("title", "intro", "ending"):
        out[name], stats = convert(name, info[name], d, snes, prg)
        print(stats)
    t = info["title"]

    with open(Path(a.src) / "screens.c", "w") as f:
        f.write("// generated by tools/screens_to_md.py - do not edit\n#include \"screens.h\"\n#include \"music.h\"\n\n")
        for name, s in out.items():
            for k, art in enumerate(s["arts"]):
                f.write(f"const u32 {name}_tiles{ART_SUFFIX[art]}[{len(s['tiles']) * 8}] = {{\n")
                for tile in s["tiles"]:
                    f.write("    " + ", ".join(f"0x{v:08X}" for v in tile[k]) + ",\n")
                f.write("};\n\n")
                f.write(f"const u16 {name}_palette{ART_SUFFIX[art]}[64] = {{" + ", ".join(f"0x{md_word(c):04X}" for c in s["colors"][k]) + "};\n\n")
                if art == "nes":     # each colour's NES index, for the SNES port's NES palettes (0xFF: none)
                    f.write(f"const u8 {name}_palette_nesidx[64] = {{" + ", ".join(str(nes_index(c)) for c in s["colors"][k]) + "};\n\n")
            f.write(f"const u16 {name}_map[{32 * 30}] = {{\n")
            for r in range(30):
                f.write("    " + ",".join(str(v) for v in s["map"][r * 32:(r + 1) * 32]) + ",\n")
            f.write("};\n\n")
            f.write(f"const ScreenSprite {name}_sprites[{max(1, len(s['entries']))}] = {{\n")
            for x, y, w in s["entries"]:
                f.write(f"    {{{x}, {y}, 0x{w:04X}}},\n")
            f.write("};\n\n")
            f.write(f"const ScreenList {name}_lists[{len(s['lists'])}] = {{" + ", ".join(f"{{{a_}, {n}}}" for a_, n in s["lists"]) + "};\n\n")
            f.write(f"const u16 {name}_frames[{len(s['frames'])}] = {{" + ", ".join(str(v) for v in s["frames"]) + "};\n\n")
        e = out["ending"]
        f.write(f"const ScreenWrite ending_writes[{len(e['writes'])}] = {{\n")
        for fr, c, w in e["writes"]:
            f.write(f"    {{{fr}, {c}, 0x{w:04X}}},\n")
        f.write("};\n\n")
        f.write(f"const ScreenEvent ending_fades[{len(e['fades'])}] = {{" + ", ".join(f"{{{fr}, {k}}}" for fr, k in e["fades"]) + "};\n\n")
        for k, art in enumerate(e["arts"]):
            f.write(f"const u16 ending_text{ART_SUFFIX[art]}[{len(e['fade_colors'][k])}][3] = {{" +
                    ", ".join("{" + ", ".join(f"0x{c:04X}" for c in trio) + "}" for trio in e["fade_colors"][k]) + "};\n\n")
        f.write(f"const u8 ending_text_nesidx[{len(e['fade_nesidx'])}][3] = {{" +
                ", ".join("{" + ", ".join(str(c) for c in trio) + "}" for trio in e["fade_nesidx"]) + "};\n\n")
        f.write(f"const ScreenEvent ending_sounds[{len(e['sounds'])}] = {{" + ", ".join(f"{{{fr}, {snd}}}" for fr, snd in e["sounds"]) + "};\n\n")
        card_tiles, card_colors = snes_card(snes)
        f.write("const u32 card_tiles[4 * 8] = {\n")
        for tile in card_tiles:
            f.write("    " + ", ".join(f"0x{v:08X}" for v in tile) + ",\n")
        f.write("};\n\n")
        f.write("const u16 card_palette[4] = {" + ", ".join(f"0x{c:04X}" for c in card_colors) + "};\n\n")
        f.write("const u16 title_start_cells[TITLE_START_CELLS] = {" + ", ".join(str(c) for c in t["start_cells"]) + "};\n\n")
        f.write("const u8 title_hidden[TITLE_START_FRAMES] = {" + ", ".join("1" if i in t["blink_hidden"] else "0"
                                                                     for i in range(t["start_frames"])) + "};\n")
    with open(Path(a.inc) / "screens.h", "w") as f:
        f.write(f"""// generated by tools/screens_to_md.py - do not edit
#ifndef SCREENS_H
#define SCREENS_H
#include <genesis.h>

typedef struct {{ s16 x, y; u16 attr; }} ScreenSprite;     // MD screen position of an 8x16 sprite, tile attributes
typedef struct {{ u16 first; u8 count; }} ScreenList;     // the sprites of one frame
typedef struct {{ u16 frame, cell, word; }} ScreenWrite;  // the ending: a cell of the NES picture written on that frame
typedef struct {{ u16 frame; u8 value; }} ScreenEvent;    // the ending: a fade step or a sound on that frame

#define TITLE_TILES        {len(out['title']['tiles'])}
#define TITLE_FRAMES       {len(out['title']['frames'])}
#define TITLE_LOOP         {t['loop']}      /* the title's frames loop back to this one (the bat flapping) */
#define TITLE_START_FRAMES {t['start_frames']}      /* START: PUSH START KEY blinks this long, then the introduction */
#define TITLE_START_CELLS  {len(t['start_cells'])}
#define INTRO_TILES        {len(out['intro']['tiles'])}
#define INTRO_FRAMES       {len(out['intro']['frames'])}
#define INTRO_BLACK        {info['intro']['black']}      /* black frames before the introduction shows */
#define ENDING_TILES       {len(out['ending']['tiles'])}
#define ENDING_FRAMES      {len(out['ending']['frames'])}
#define ENDING_BLACK       {info['ending']['black']}      /* black frames before the ending shows */
#define ENDING_WRITES      {len(out['ending']['writes'])}
#define ENDING_FADES       {len(out['ending']['fades'])}
#define ENDING_SOUNDS      {len(out['ending']['sounds'])}
#define ENDING_TEXT_PAL    {TEXT}      /* the MD palette of the credits (entries 1-3), the NES game's background palette 3 */
#define GAMEOVER_AFTER     {info['gameover']['after_death']}     /* frames from Simon's death to the game over screen */

extern const u32 title_tiles[];                           // 16-bit art
extern const u16 title_palette[64];
extern const u32 title_tiles_nes[];                       // NES art, same tiles at the same indices
extern const u16 title_palette_nes[64];
extern const u8 title_palette_nesidx[64];
extern const u16 title_map[32 * 30];
extern const ScreenSprite title_sprites[];
extern const ScreenList title_lists[];
extern const u16 title_frames[TITLE_FRAMES];
extern const u16 title_start_cells[TITLE_START_CELLS];   // nametable cells of PUSH START KEY
extern const u8 title_hidden[TITLE_START_FRAMES];         // 1: the text is hidden on that frame after START
extern const u32 intro_tiles[];
extern const u16 intro_palette[64];
extern const u32 intro_tiles_nes[];
extern const u16 intro_palette_nes[64];
extern const u8 intro_palette_nesidx[64];
extern const u16 intro_map[32 * 30];
extern const ScreenSprite intro_sprites[];
extern const ScreenList intro_lists[];
extern const u16 intro_frames[INTRO_FRAMES];
extern const u32 ending_tiles[];
extern const u16 ending_palette[64];
extern const u32 ending_tiles_nes[];
extern const u16 ending_palette_nes[64];
extern const u8 ending_palette_nesidx[64];
extern const u16 ending_map[32 * 30];
extern const ScreenSprite ending_sprites[];
extern const ScreenList ending_lists[];
extern const u16 ending_frames[ENDING_FRAMES];
extern const ScreenWrite ending_writes[ENDING_WRITES];   // the credits, in order
extern const ScreenEvent ending_fades[ENDING_FADES];     // value: a row of ending_text
extern const u16 ending_text[][3];                        // the credits' colours at each step (16-bit art)
extern const u16 ending_text_nes[][3];
extern const u8 ending_text_nesidx[][3];                  // their NES indices (the NES art's palettes)
extern const ScreenEvent ending_sounds[ENDING_SOUNDS];   // value: MUS_... or SFX_...
extern const u32 card_tiles[4 * 8];                       // the SNES port's credits card: skull, 2x2 tiles
extern const u16 card_palette[4];

#endif
""")


if __name__ == "__main__":
    main()

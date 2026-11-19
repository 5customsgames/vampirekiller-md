"""Tile art sources and Mega Drive palette packing.

Two art sources give the same interface (8x8 pixels as RGB triplets, None = transparent):
  ArtNES  the original 2bpp CHR data with the NES palette
  Art16   the redrawn 16-colour tiles of the SNES port (its src/16bit-tiles, copied by tools/import_snes.py), found by looking
          each CHR tile up in the PRG ROM (bank + index) and reading the matching 4bpp tile.

Colours are reduced to the MD's 3 bits per channel. Each MD palette holds 15 colours (index 0 is transparent),
so groups with more colours get their closest colours merged (weighted by how many pixels use them).
"""
from nes_dump import NES_RGB, tile_pixels

# name suffix of each art's tiles and palettes in the generated C (the GRAPHICS option picks one at run time)
ART_SUFFIX = {"16bit": "", "nes": "_nes"}

# first tile of each tile bank inside the PRG (bytes) - see castlevania-snes/utilities/parseNesFileToBanks.go
BANK_START = {0: 0x3501, 1: 8, 2: 8, 3: 8, 6: 0x3117}


def rgb9_from_555(c):
    """SNES BGR555 word -> (r, g, b) with 3 bits per channel."""
    r, g, b = c & 31, (c >> 5) & 31, (c >> 10) & 31
    return tuple(min(7, (v * 7 + 15) // 31) for v in (r, g, b))


def rgb9_from_nes(index):
    """(r, g, b, NES colour index): the index rides along so that the game can recolour the NES art with the SNES
    port's 14 NES palettes (two NES colours can give the same MD colour here and not in those)."""
    c = NES_RGB[index & 0x3F]
    return tuple(min(7, (((c >> s) & 255) + 16) >> 5) for s in (16, 8, 0)) + (index & 0x3F,)


def md_word(rgb):
    r, g, b = rgb[:3]
    return (b << 9) | (g << 5) | (r << 1)


def nes_index(rgb):
    """The NES colour index of a palette entry, 0xFF if it has none (a 16-bit art colour or a merged one)."""
    return rgb[3] if len(rgb) == 4 else 0xFF


def snes_nes_palettes(snes_src):
    """The SNES port's 14 NES palettes (src/palette_lookup.asm, in the order of its options screen), as 14 lists of
    64 MD colour words."""
    import re
    from pathlib import Path
    src = (Path(snes_src) / "palette_lookup.asm").read_text()
    out = []
    for k in range(1, 15):
        body = src.split(f"palette_{k}_lookup:", 1)[1].split("_lookup:")[0]
        b = []
        for line in body.splitlines():
            line = line.split(";")[0]
            for x in re.findall(r"\$([0-9A-Fa-f]+)", line):
                v = int(x, 16)
                b += [v & 255, v >> 8] if ".word" in line else [v]
        assert len(b) >= 128, (k, len(b))
        out.append([md_word(rgb9_from_555(b[2 * i] | b[2 * i + 1] << 8)) for i in range(64)])
    return out


class ArtNES:
    name = "nes"

    def __init__(self, chr_, nes_pal):
        self.chr, self.pal = chr_, nes_pal

    def bg_tile(self, tile, attr):
        px = tile_pixels(self.chr, 0x1000, tile)
        return [None if v == 0 else rgb9_from_nes(self.pal[attr * 4 + v]) for row in px for v in row]

    def spr_tile(self, chr_index, attr):
        px = tile_pixels(self.chr, 0, chr_index) if chr_index < 256 else tile_pixels(self.chr, 0x1000, chr_index - 256)
        return [None if v == 0 else rgb9_from_nes(self.pal[16 + attr * 4 + v]) for row in px for v in row]

    def backdrop(self):
        return rgb9_from_nes(self.pal[0])


class Art16(ArtNES):
    name = "16bit"

    def __init__(self, chr_, nes_pal, prg, snes_src, bg_palette, spr_palette, origin=None):
        super().__init__(chr_, nes_pal)
        self.origin = origin or {}      # CHR index -> (bank, offset): where the game loaded the tile from
        from pathlib import Path
        self.prg = prg
        self.banks = {n: (Path(snes_src) / f"16bit-tiles/tiles-16bit-{n}.bin").read_bytes() for n in BANK_START}
        rd = lambda p: [int.from_bytes(Path(p).read_bytes()[i:i + 2], "little") for i in range(0, 128, 2)]
        self.bgpal, self.sprpal = rd(bg_palette), rd(spr_palette)
        self.cache = {}
        self.fallbacks = 0

    @staticmethod
    def _decode(b):
        return [((b[2 * y] >> (7 - x)) & 1) | (((b[2 * y + 1] >> (7 - x)) & 1) << 1)
                | (((b[16 + 2 * y] >> (7 - x)) & 1) << 2) | (((b[17 + 2 * y] >> (7 - x)) & 1) << 3)
                for y in range(8) for x in range(8)]

    def _lookup(self, chr_index):
        """16-colour pixel values for a CHR-RAM tile, or None if the ROM has no matching tile."""
        if chr_index in self.cache:
            return self.cache[chr_index]
        tile = self.chr[chr_index * 16:chr_index * 16 + 16]
        if chr_index in self.origin:    # the SNES port's 16-bit tile sits at the same place as the NES one
            bank, off = self.origin[chr_index]
            if bank in BANK_START and off >= BANK_START[bank] and (off - BANK_START[bank]) % 16 == 0:
                k = (off - BANK_START[bank]) // 16
                self.cache[chr_index] = self._decode(self.banks[bank][k * 32:k * 32 + 32])
                return self.cache[chr_index]    # even empty: the SNES port shows it so (stage 11's eagle's NES leftovers)
        mask = [1 if ((tile[y] >> (7 - x)) & 1) | ((tile[y + 8] >> (7 - x)) & 1) else 0
                for y in range(8) for x in range(8)]
        best = None
        for bank, start in BANK_START.items():
            base = bank * 16384
            i = self.prg.find(tile, base + start, base + 16384)
            while 0 <= i < base + 16384:
                if (i - base - start) % 16 == 0:
                    k = (i - base - start) // 16
                    px = self._decode(self.banks[bank][k * 32:k * 32 + 32])
                    score = sum(1 for m, p in zip(mask, px) if m == (1 if p else 0))
                    if best is None or score > best[0]:
                        best = (score, px)
                i = self.prg.find(tile, i + 1, base + 16384)
        result = best[1] if best and any(best[1]) else None
        if any(mask) and result is None:
            self.fallbacks += 1
        self.cache[chr_index] = result
        return result

    def bg_tile(self, tile, attr):
        px = self._lookup(256 + tile)
        if px is None:
            return [c and c[:3] for c in super().bg_tile(tile, attr)]
        return [None if v == 0 else rgb9_from_555(self.bgpal[attr * 16 + v]) for v in px]

    def spr_tile(self, chr_index, attr):
        px = self._lookup(chr_index)
        if px is None:
            return [c and c[:3] for c in super().spr_tile(chr_index, attr)]
        return [None if v == 0 else rgb9_from_555(self.sprpal[attr * 16 + v]) for v in px]


# the NES font has no X (its slot, tile $F7, holds a full stop): one drawn like its Y and K, 2 px strokes
X_GLYPH = [".11...11", ".11...11", "..11.11.", "...111..", "..11.11.", ".11...11", ".11...11", "........"]


def x_glyph(art, attr):
    """The X's pixels in that art, in the commonest colour of its Y (tile $F8) in background palette attr."""
    from collections import Counter
    c = Counter(v for v in art.bg_tile(0xF8, attr) if v).most_common(1)[0][0]
    return [c if ch == "1" else None for row in X_GLYPH for ch in row]


def _dist(a, b):
    return 3 * (a[0] - b[0]) ** 2 + 4 * (a[1] - b[1]) ** 2 + 2 * (a[2] - b[2]) ** 2


def pack_palette(weights, size=15):
    """weights: {rgb: pixel count}. Returns (palette list of up to `size` colours, {rgb: index 1..size})."""
    groups = [[{c}, c, w] for c, w in weights.items()]          # members, colour, weight
    while len(groups) > size:
        best = None
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                a, b = groups[i], groups[j]
                cost = a[2] * b[2] / (a[2] + b[2]) * _dist(a[1], b[1])   # Ward-style merge cost
                if best is None or cost < best[0]:
                    best = (cost, i, j)
        _, i, j = best
        a, b = groups[i], groups[j]
        w = a[2] + b[2]
        mean = tuple(min(7, round((a[1][k] * a[2] + b[1][k] * b[2]) / w)) for k in range(3))   # (no NES index)
        groups[i] = [a[0] | b[0], mean, w]
        del groups[j]
    palette = [g[1] for g in sorted(groups, key=lambda g: -g[2])]
    index = {}
    for n, g in enumerate(sorted(groups, key=lambda g: -g[2])):
        for member in g[0]:
            index[member] = n + 1
    return palette, index

#!/usr/bin/env python3
"""Decode the rooms of the NES game straight from its ROM (no playing needed).

usage: decode_rooms.py <rom.nes> <stage> [<stage> ...] [--out DIR]

A room is what the game keeps in $28 (stage) and $46 (floor). Its map, read by the column routine at $F69E of the
fixed bank (data in bank 4):
- $FB23 + 2 * stage points to a list of map pointers, one per floor;
- a map is a run of columns of 6 bytes, one 32x32 px block per byte from the top of the play field (the first block
  row is half hidden under the HUD); the first 4 columns come before the room's x 0 and are never shown;
- $F9FA + 2 * stage points to the stage's blocks, 17 bytes each: one attribute byte (the 4 16x16 quarters' palettes,
  2 bits each, top-left first) then 4 rows of 4 tile indices.
- the scroll stops at the page (256 px) in the nibble of $FBB0 + stage (high nibble for floor 0, low nibble for the
  other floors); $FBC3 holds the left page the same way (15: none). The room is drawn up to the end of that page.
Checked against tools/record_rooms.py: the 3 rooms of stages 2 and 3 come out the same, tile for tile and palette for
palette (rows 6 to 27; the rows above are the HUD's).

Writes room_<stage>_<floor>_tiles.bin / _pal.bin in the format of record_rooms.py (30 bytes per column: NES tile
index / background palette 0-3, from the room's x 0; the map's block rows are tile rows 4 to 27, the other rows are 0)
and rooms.json (per room: map address, columns, scroll pages).
"""
import argparse, json
from pathlib import Path

ROWS = 30
LEAD = 4                                   # map columns before the room's x 0


class Rom:
    def __init__(self, data):
        self.prg = data[16:16 + data[4] * 16384]

    def rd(self, addr, bank=4):
        if addr >= 0xC000:
            return self.prg[-16384 + addr - 0xC000]
        return self.prg[bank * 16384 + addr - 0x8000]

    def word(self, addr, bank=4):
        return self.rd(addr, bank) | self.rd(addr + 1, bank) << 8

    def nibble(self, table, stage, floor):
        v = self.rd(table + stage)
        return (v >> 4 if floor == 0 else v) & 15

    def floors(self, stage):
        """floor count: the stage's pointer list runs up to the next stage's (the lists overlap) and the scroll
        table has room for 2 floors; a pointer outside the bank ends the list"""
        here, nxt = self.word(0xFB23 + 2 * stage), self.word(0xFB23 + 2 * stage + 2)
        n = min(2, (nxt - here) // 2) if nxt > here else 2
        while n > 1 and self.word(here + 2 * (n - 1)) < 0x8000:
            n -= 1
        return max(1, n)

    def room(self, stage, floor):
        mp = self.word(self.word(0xFB23 + 2 * stage) + 2 * floor)
        blocks = self.word(0xF9FA + 2 * stage)
        last = self.nibble(0xFBB0, stage, floor)
        cols = (last + 1) * 8                  # 32 px columns up to the end of the last page
        tiles, pals = [], []
        for c in range(LEAD, LEAD + cols):
            ids = [self.rd(mp + c * 6 + r) for r in range(6)]
            for tx in range(4):
                t, p = [0] * ROWS, [0] * ROWS
                for br, b in enumerate(ids):
                    d = blocks + 17 * b
                    attr = self.rd(d)
                    for ty in range(4):
                        t[4 + br * 4 + ty] = self.rd(d + 1 + ty * 4 + tx)
                        p[4 + br * 4 + ty] = (attr >> ((((ty // 2) << 1) | (tx // 2)) * 2)) & 3
                tiles += t
                pals += p
        left = self.nibble(0xFBC3, stage, floor)
        return bytes(tiles), bytes(pals), dict(map=mp, blocks=blocks, columns=cols * 4,
                                               last_page=last, first_page=None if left == 15 else left)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("stages", type=int, nargs="+")
    ap.add_argument("--out", default=str(Path(__file__).parent / "extracted" / "rooms"))
    a = ap.parse_args()
    rom = Rom(Path(a.rom).read_bytes())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    info = {}
    for s in a.stages:
        for f in range(rom.floors(s)):
            t, p, meta = rom.room(s, f)
            (out / f"room_{s}_{f}_tiles.bin").write_bytes(t)
            (out / f"room_{s}_{f}_pal.bin").write_bytes(p)
            info[f"{s}_{f}"] = meta
            print(f"stage {s} floor {f}: map ${meta['map']:04X}, {meta['columns']} columns, pages "
                  f"{meta['first_page']}..{meta['last_page']}")
    (out / "rooms.json").write_text(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()

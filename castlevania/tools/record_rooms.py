#!/usr/bin/env python3
"""Play stages 2 and 3 of the NES game with a fixed list of inputs and record the background of each room.

usage: record_rooms.py <rom.nes> [--out DIR]
A room is what the game keeps in $28 (stage) and $46 (floor: stage 2 has the upper room, 1, and the underground, 0,
joined by stairs). Simon is kept at full health and the enemy slots are emptied every frame (so the stage 3 boss
never shows up; its screen is the last one of stage 3). Only columns that are on screen while the game is in normal
play (state 5/6) with the display on are kept, so stale nametable columns are never recorded.
Writes room_<stage>_<floor>_tiles.bin / _pal.bin (30 bytes per column, NES tile index / background palette 0-3,
columns left to right from the room's x 0) to DIR (default tools/extracted/level1).
"""
import argparse
from pathlib import Path
from nes_dump import Machine

KEYS = {"A": 1, "B": 2, "S": 8, "U": 16, "D": 32, "L": 64, "R": 128, ".": 0}
# found by playing: title + intro, the courtyard and the hall up to the exit door, then stage 2 (down to the
# underground on the left, across it jumping the water, up the stairs on its right, out by the upper room's door) and
# stage 3 up to the boss screen
SCRIPT = """
.*300 S*4 .*796
R*2061 U*200 R*130 .*460
R*480 U*160 R*6 BR R*120 R*4 L*60 D*250 L*130 D*400
R*20 R*107 AR R*45 R*17 AR R*191 AR R*690
AL L*30 .*10 L*16 U*240 R*90 U*200 AR R*150
.*420 R*1200 L*10 AR R*30 .*10 U*128 R*40
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--out", default=str(Path(__file__).parent / "extracted" / "level1"))
    a = ap.parse_args()
    m = Machine(Path(a.rom).read_bytes())
    m.mpu.reset()
    m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    ram = m.mem._subject

    rooms = {}
    room, cam, prev = None, 0, None
    for tok in SCRIPT.split():
        keys, _, n = tok.partition("*")
        pad = 0
        for ch in keys:
            pad |= KEYS[ch]
        for _ in range(int(n or 1)):
            m.pad = pad
            m.frame()
            ram[0x45] = 0x40
            for i in range(4, 14):
                ram[0x434 + i] = 0
            if ram[0x28] < 2 or (ram[0x18], ram[0x19]) != (5, 6) or not m.mask:
                prev = None
                continue
            key = (ram[0x28], ram[0x46])
            tot = (m.ctrl & 1) * 256 + m.scroll_x
            if key != room:
                room, cam = key, tot          # a new room starts at the game's own scroll (0, or kept by the stairs)
            elif prev is not None:
                d = (tot - prev) % 512
                cam += d if d < 256 else d - 512
            prev = tot
            cols_t, cols_p = rooms.setdefault(key, ({}, {}))
            for i in range(32 + (1 if cam % 8 else 0)):
                c = cam // 8 + i
                n_, tx = (c % 64) // 32, c % 32
                base = n_ * 1024
                cols_t[c] = bytes(m.nt[base + ty * 32 + tx] for ty in range(30))
                cols_p[c] = bytes((m.nt[base + 960 + (ty // 4) * 8 + tx // 4] >> (((ty // 2) & 1) * 4 + ((tx // 2) & 1) * 2)) & 3
                                  for ty in range(30))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for (stage, floor), (cols_t, cols_p) in sorted(rooms.items()):
        hi = max(cols_t)
        missing = [c for c in range(hi + 1) if c not in cols_t]
        (out / f"room_{stage}_{floor}_tiles.bin").write_bytes(b"".join(cols_t.get(c, bytes(30)) for c in range(hi + 1)))
        (out / f"room_{stage}_{floor}_pal.bin").write_bytes(b"".join(cols_p.get(c, bytes(30)) for c in range(hi + 1)))
        print(f"stage {stage} floor {floor}: {hi + 1} columns, {len(missing)} missing {missing[:8]}")
    print(f"end: stage {ram[0x28]} state {ram[0x18]}/{ram[0x19]} x {ram[0x38c]} y {ram[0x354]}")


if __name__ == "__main__":
    main()

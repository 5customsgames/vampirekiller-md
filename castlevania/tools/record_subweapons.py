#!/usr/bin/env python3
"""Trace a sub-weapon throw in the NES game, frame by frame.

usage: record_subweapons.py <rom.nes> <code> [frames]
code is the sub-weapon id the game keeps in $015B (8 dagger, 9 cross, 11 holy water, 13 axe, 15 stopwatch; only
the stopwatch costs 5 hearts). Simon stands in the courtyard with 20 hearts and presses UP + B on frame 0.
Prints the fields of the sub-weapon's object slot ($14 of the 28-slot object table, one array every $1C bytes;
the columns are array base + $14). Array bases: $354 y (centre), $38C x (centre, screen), $3A8 x fraction, $3C4/$3E0 vertical speed (8.8, positive = up),
$3FC/$418 horizontal speed, $31C sprite frame, $568 timer, $584 weapon kind (0 dagger, 1 cross, 3 holy water, 5 axe).
These traces give the speeds, gravity and timings used in src/main.c.
"""
import sys
from pathlib import Path
from nes_dump import Machine

SLOT = 0x14
B, UP = 2, 16


def main():
    rom = Path(sys.argv[1]).read_bytes()
    code = int(sys.argv[2], 0)
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 140
    m = Machine(rom)
    m.mpu.reset()
    m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    ram = m.mem._subject

    def step(pad):
        m.pad = pad
        ram[0x45] = 0x40                       # keep Simon's health full
        m.frame()

    for f in range(1100):                      # title screen, START, intro walk
        step(8 if 300 <= f < 304 else 0)
    for _ in range(60):
        step(0)
    ram[0x15B] = code
    ram[0x71] = 20
    step(0)

    bases = [0x300 + k * 0x1C for k in range(32) if 0x300 + k * 0x1C < 0x7E0]
    rows = []
    for f in range(frames):
        step(UP | B if f < 2 else 0)
        rows.append([ram[0x71]] + [ram[b + SLOT] for b in bases])
    cols = [0] + [j + 1 for j in range(len(bases)) if len(set(r[j + 1] for r in rows)) > 1]
    names = ["hearts"] + [f"${b + SLOT:03X}" for b in bases]
    print("frame " + " ".join(f"{names[j]:>6}" for j in cols))
    for f, r in enumerate(rows):
        print(f"{f:5d} " + " ".join(f"{r[j]:6d}" for j in cols))


if __name__ == "__main__":
    main()

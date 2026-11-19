#!/usr/bin/env python3
"""Walk Simon to the right through a stage and record the background as one long tile map.

usage: record_level.py <rom.nes> [--out DIR] [--max-frames N]
Simon is kept at full health ($0045) so he survives. Writes to DIR (default tools/extracted/level1):
  world_tiles.bin  30 bytes per column (NES tile index), columns left to right
  world_pal.bin    30 bytes per column (NES background palette 0-3)
  gate_tiles.bin, gate_pal.bin  the same for the castle gate screen (world x 512-767): the courtyard's scroll stops
                   there, and the hall is then loaded at the same scroll, so the world map only keeps the hall's columns
  chr.bin, palette.bin  video state at the end (and chr_changes.txt if the pattern table changed)
Needs py65, run it with the venv python.
"""
import argparse, hashlib
from pathlib import Path
from nes_dump import Machine, dump

HEALTH = 0x45


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--out", default=str(Path(__file__).parent / "extracted" / "level1"))
    ap.add_argument("--max-frames", type=int, default=9000)
    ap.add_argument("--start", type=int, default=300, help="frame at which Start is pressed")
    a = ap.parse_args()

    m = Machine(Path(a.rom).read_bytes())
    m.mpu.reset()
    m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    ram = m.mem._subject

    cols_t, cols_p = {}, {}
    absx, prev, still, chr_hash, changes = None, None, 0, None, []
    gate, gate_seen = None, 0
    ground = a.start + 800  # frames until gameplay starts (title -> intro -> stage 1)
    for f in range(a.max_frames):
        pad = 0
        if a.start <= f < a.start + 4:
            pad = 8                      # start
        elif f >= ground:
            pad = 0x80                   # right
        m.pad = pad
        m.frame()
        if f >= ground - 200:
            ram[HEALTH] = 0x40
        if f < ground:
            continue
        tot = (m.ctrl & 1) * 256 + m.scroll_x
        if prev is None:
            absx, prev = tot, tot
        else:
            d = (tot - prev) % 512
            absx += d if d < 256 else d - 512
            still = still + 1 if d == 0 else 0
            prev = tot
        if gate is None and absx - (absx % 512) == 512 and tot % 512 == 0:
            gate_seen += 1                # the courtyard's last screen, standing still: nametable 0 is the gate
            if gate_seen == 40:
                gate = [(bytes(m.nt[ty * 32 + tx] for ty in range(30)),
                         bytes((m.nt[960 + (ty // 4) * 8 + tx // 4] >> (((ty // 2) & 1) * 4 + ((tx // 2) & 1) * 2)) & 3
                               for ty in range(30))) for tx in range(32)]
        h = hashlib.md5(m.chr).hexdigest()
        if h != chr_hash:
            changes.append((f, h))
            chr_hash = h
        first = absx // 8
        for i in range(32):
            c = (tot // 8 + i) % 64
            n, tx = c // 32, c % 32
            base = n * 1024
            t = bytes(m.nt[base + ty * 32 + tx] for ty in range(30))
            p = bytes((m.nt[base + 960 + (ty // 4) * 8 + tx // 4] >> (((ty // 2) & 1) * 4 + ((tx // 2) & 1) * 2)) & 3
                      for ty in range(30))
            cols_t[first + i], cols_p[first + i] = t, p
        if still > 400:
            break
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lo, hi = min(cols_t), max(cols_t)
    (out / "world_tiles.bin").write_bytes(b"".join(cols_t[c] for c in range(lo, hi + 1)))
    (out / "world_pal.bin").write_bytes(b"".join(cols_p[c] for c in range(lo, hi + 1)))
    (out / "gate_tiles.bin").write_bytes(b"".join(t for t, _ in gate))
    (out / "gate_pal.bin").write_bytes(b"".join(p_ for _, p_ in gate))
    (out / "chr.bin").write_bytes(m.chr)
    (out / "palette.bin").write_bytes(m.pal)
    (out / "chr_changes.txt").write_text("\n".join(f"{f} {h}" for f, h in changes))
    dump(m, out / "last")
    missing = [c for c in range(lo, hi + 1) if c not in cols_t]
    print(f"frames={f} columns {lo}..{hi} ({hi - lo + 1} cols, {len(missing)} missing)  chr changes: {len(changes)}")


if __name__ == "__main__":
    main()

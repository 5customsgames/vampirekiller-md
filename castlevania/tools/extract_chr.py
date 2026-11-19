#!/usr/bin/env python3
"""Dump the CHR data of an iNES ROM to indexed PNG sheets (stdlib only).

usage: extract_chr.py <rom.nes> [outdir]
The ROM itself is never copied into the repo; output goes to tools/extracted/.
"""
import struct, sys, zlib
from pathlib import Path

PAL = [(0, 0, 0), (96, 96, 96), (176, 176, 176), (255, 255, 255)]

def decode_tile(b):
    rows = []
    for y in range(8):
        lo, hi = b[y], b[y + 8]
        rows.append([((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1) for x in range(8)])
    return rows

def write_png(path, w, h, pix):
    raw = b"".join(b"\x00" + bytes(pix[y * w:(y + 1) * w]) for y in range(h))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    plte = b"".join(bytes(c) for c in PAL)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
                     + chunk(b"PLTE", plte)
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

def main():
    rom = Path(sys.argv[1]).read_bytes()
    out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "extracted")
    out.mkdir(parents=True, exist_ok=True)
    if rom[:4] != b"NES\x1a":
        sys.exit("not an iNES file")
    prg, chr_ = rom[4] * 16384, rom[5] * 8192
    off = 16 + (512 if rom[6] & 4 else 0)
    print(f"PRG {prg // 1024}K  CHR {chr_ // 1024}K  mapper {(rom[6] >> 4) | (rom[7] & 0xF0)}")
    data = rom[off:off + prg]
    (out / "prg.bin").write_bytes(data)
    if chr_:
        data, bank_size = rom[off + prg:off + prg + chr_], 4096
    else:
        print("CHR-RAM game: rendering PRG banks as tile sheets")
        bank_size = 16384
    # tile data start offsets inside each PRG bank (from castlevania-snes/utilities/parseNesFileToBanks.go)
    starts = {} if chr_ else {0: 0x3501, 1: 8, 2: 8, 3: 8, 6: 0x3117}
    for bank in range(len(data) // bank_size):
        if not chr_ and bank not in starts:
            continue
        base = bank * bank_size + starts.get(bank, 0)
        n = (bank_size - starts.get(bank, 0)) // 16
        rows = (n + 15) // 16
        pix = [0] * (128 * rows * 8)
        for i in range(n):
            t = decode_tile(data[base + i * 16:base + i * 16 + 16])
            tx, ty = (i % 16) * 8, (i // 16) * 8
            for y in range(8):
                for x in range(8):
                    pix[(ty + y) * 128 + tx + x] = t[y][x]
        write_png(out / f"{'chr' if chr_ else 'prg'}_{bank:02d}.png", 128, rows * 8, pix)
    print(f"wrote sheets to {out}")

main()

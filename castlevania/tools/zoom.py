#!/usr/bin/env python3
"""Crop and enlarge a region of one of our PNGs (8-bit RGB, no filter): zoom.py in.png out.png x y w h scale"""
import struct, sys, zlib
src, dst, x0, y0, w, h, sc = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:8])
d = open(src, "rb").read()
i, idat, W, H = 8, b"", 0, 0
while i < len(d):
    n = struct.unpack(">I", d[i:i + 4])[0]
    t = d[i + 4:i + 8]
    if t == b"IHDR":
        W, H = struct.unpack(">II", d[i + 8:i + 16])
    if t == b"IDAT":
        idat += d[i + 8:i + 8 + n]
    i += 12 + n
raw = zlib.decompress(idat)
row = W * 3 + 1
out = b""
for y in range(h):
    line = b"".join(raw[(y0 + y) * row + 1 + (x0 + x) * 3:(y0 + y) * row + 4 + (x0 + x) * 3] * sc for x in range(w))
    out += (b"\x00" + line) * sc
def ch(t, dd):
    return struct.pack(">I", len(dd)) + t + dd + struct.pack(">I", zlib.crc32(t + dd) & 0xFFFFFFFF)
open(dst, "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w * sc, h * sc, 8, 2, 0, 0, 0))
                      + ch(b"IDAT", zlib.compress(out)) + ch(b"IEND", b""))

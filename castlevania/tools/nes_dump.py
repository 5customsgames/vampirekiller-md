#!/usr/bin/env python3
"""Run a mapper-2 (UNROM) NES ROM headless and dump its video state.

usage: nes_dump.py <rom.nes> <frames> [--press BTN@FRAME+LEN ...] [--out DIR]
  BTN is one of a b select start up down left right
  e.g.  nes_dump.py rom.nes 900 --press start@120+4 --press start@300+4

Writes to DIR (default tools/extracted/dump): chr.bin (8K CHR-RAM), nametables.bin (2K),
palette.bin (32), oam.bin (256), screen.png (both nametables, no scroll applied).
This is a rough PPU model, enough to observe what the game loads, not a playable emulator.
Needs py65 (pip install py65).
"""
import argparse, json, struct, zlib
from pathlib import Path
from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

FRAME_CYCLES, VBLANK_CYCLES, SPRITE0_AT = 29780, 2273, 7000
BUTTONS = ["a", "b", "select", "start", "up", "down", "left", "right"]

# standard 2C02 colours (RGB)
NES_RGB = [
    0x666666, 0x002A88, 0x1412A7, 0x3B00A4, 0x5C007E, 0x6E0040, 0x6C0600, 0x561D00,
    0x333500, 0x0B4800, 0x005200, 0x004F08, 0x00404D, 0x000000, 0x000000, 0x000000,
    0xADADAD, 0x155FD9, 0x4240FF, 0x7527FE, 0xA01ACC, 0xB71E7B, 0xB53120, 0x994E00,
    0x6B6D00, 0x388700, 0x0C9300, 0x008F32, 0x007C8D, 0x000000, 0x000000, 0x000000,
    0xFFFEFF, 0x64B0FF, 0x9290FF, 0xC676FF, 0xF36AFF, 0xFE6ECC, 0xFE8170, 0xEA9E22,
    0xBCBE00, 0x88D800, 0x5CE430, 0x45E082, 0x48CDDE, 0x4F4F4F, 0x000000, 0x000000,
    0xFFFEFF, 0xC0DFFF, 0xD3D2FF, 0xE8C8FF, 0xFBC2FF, 0xFEC4EA, 0xFECCC5, 0xF7D8A5,
    0xE4E594, 0xCFEF96, 0xBDF4AB, 0xB3F3CC, 0xB5EBF2, 0xB8B8B8, 0x000000, 0x000000,
]


class Machine:
    def __init__(self, rom):
        assert rom[:4] == b"NES\x1a" and ((rom[6] >> 4) | (rom[7] & 0xF0)) == 2, "need UNROM (mapper 2)"
        self.prg = rom[16:16 + rom[4] * 16384]
        self.vertical = bool(rom[6] & 1)
        self.chr = bytearray(8192)
        self.nt = bytearray(2048)
        self.pal = bytearray(32)
        self.oam = bytearray(256)
        self.ctrl = self.mask = 0
        self.vblank = self.spr0 = False
        self.latch = False
        self.scroll_x = self.scroll_y = 0
        self.vaddr = 0
        self.rbuf = 0
        self.oamaddr = 0
        self.pad = 0
        self.shift = 0
        self.strobe = False
        self.mem = ObservableMemory()
        self.mpu = MPU(memory=self.mem)
        self.bank = 0
        self.load_bank(0)
        self.mem.write(0xC000, list(self.prg[-16384:]))
        m = self.mem
        m.subscribe_to_read(range(0x2000, 0x4000), self.ppu_read)
        m.subscribe_to_write(range(0x2000, 0x4000), self.ppu_write)
        m.subscribe_to_write(range(0x4014, 0x4015), self.oam_dma)
        m.subscribe_to_read(range(0x4016, 0x4017), self.pad_read)
        m.subscribe_to_write(range(0x4016, 0x4017), self.pad_write)
        m.subscribe_to_read(range(0x4015, 0x4016), lambda a: 0)
        m.subscribe_to_write(range(0x8000, 0x10000), self.rom_write)
        # internal RAM mirrors
        for base in (0x800, 0x1000, 0x1800):
            m.subscribe_to_read(range(base, base + 0x800), lambda a: m._subject[a & 0x7FF])
            m.subscribe_to_write(range(base, base + 0x800), self.ram_mirror)

    def load_bank(self, b):
        self.bank = b % (len(self.prg) // 16384)
        self.mem.write(0x8000, list(self.prg[self.bank * 16384:(self.bank + 1) * 16384]))

    def rom_write(self, addr, value):
        # UNROM: any write to $8000-$FFFF selects the switchable bank (the game writes via $C000+Y)
        self.load_bank(value & 0x0F)
        if addr < 0xC000:
            return self.prg[self.bank * 16384 + (addr - 0x8000)]
        return self.prg[-16384 + (addr - 0xC000)]

    def ram_mirror(self, addr, value):
        self.mem._subject[addr & 0x7FF] = value
        return self.mem._subject[addr]

    def oam_dma(self, addr, value):
        page = value << 8
        data = [self.mem._subject[page + i] if page < 0x2000 else 0 for i in range(256)]
        self.oam[:] = bytes(data)
        self.mpu.processorCycles += 513

    def pad_write(self, addr, value):
        s = value & 1
        if self.strobe and not s:
            self.shift = self.pad
        self.strobe = bool(s)

    def pad_read(self, addr):
        if self.strobe:
            return self.pad & 1 | 0x40
        bit = self.shift & 1
        self.shift = (self.shift >> 1) | 0x80
        return bit | 0x40

    # --- PPU ---
    def nt_index(self, a):
        a = (a - 0x2000) & 0xFFF
        n = a >> 10
        n = (n >> 1) if self.vertical is False else (n & 1)  # horizontal mirrors 0=1,2=3; vertical 0=2,1=3
        return n * 1024 + (a & 0x3FF)

    def vram_read(self, a):
        a &= 0x3FFF
        if a < 0x2000:
            return self.chr[a]
        if a < 0x3F00:
            return self.nt[self.nt_index(a)]
        i = a & 0x1F
        return self.pal[i & 0x0F if i & 3 == 0 else i]

    def vram_write(self, a, v):
        a &= 0x3FFF
        if a < 0x2000:
            self.chr[a] = v
        elif a < 0x3F00:
            self.nt[self.nt_index(a)] = v
        else:
            i = a & 0x1F
            self.pal[i & 0x0F if i & 3 == 0 else i] = v

    def ppu_read(self, addr):
        r = addr & 7
        if r == 2:
            v = (0x80 if self.vblank else 0) | (0x40 if self.spr0 else 0)
            self.vblank = False
            self.latch = False
            return v
        if r == 4:
            return self.oam[self.oamaddr]
        if r == 7:
            v = self.rbuf
            self.rbuf = self.vram_read(self.vaddr)
            if self.vaddr & 0x3FFF >= 0x3F00:
                v = self.rbuf
            self.vaddr = (self.vaddr + (32 if self.ctrl & 4 else 1)) & 0x7FFF
            return v
        return 0

    def ppu_write(self, addr, value):
        r = addr & 7
        if r == 0:
            self.ctrl = value
        elif r == 1:
            self.mask = value
        elif r == 3:
            self.oamaddr = value
        elif r == 4:
            self.oam[self.oamaddr] = value
            self.oamaddr = (self.oamaddr + 1) & 0xFF
        elif r == 5:
            if not self.latch:
                self.scroll_x = value
            else:
                self.scroll_y = value
            self.latch = not self.latch
        elif r == 6:
            if not self.latch:
                self.vaddr = (value & 0x3F) << 8 | (self.vaddr & 0xFF)
            else:
                self.vaddr = (self.vaddr & 0x3F00) | value
            self.latch = not self.latch
        elif r == 7:
            self.vram_write(self.vaddr, value)
            self.vaddr = (self.vaddr + (32 if self.ctrl & 4 else 1)) & 0x7FFF
        return self.mem._subject[addr] if r != 2 else None

    def run_until(self, cycles):
        mpu = self.mpu
        while mpu.processorCycles < cycles:
            mpu.step()

    def frame(self):
        mpu = self.mpu
        start = mpu.processorCycles
        self.vblank, self.spr0 = True, False
        if self.ctrl & 0x80:
            mpu.nmi()
        self.run_until(start + VBLANK_CYCLES)
        self.vblank = False
        self.run_until(start + SPRITE0_AT)
        self.spr0 = True
        self.run_until(start + FRAME_CYCLES)


def tile_pixels(chr_, base, idx):
    o = base + idx * 16
    return [[((chr_[o + y] >> (7 - x)) & 1) | (((chr_[o + y + 8] >> (7 - x)) & 1) << 1) for x in range(8)]
            for y in range(8)]


def write_png(path, w, h, rgb):
    raw = b"".join(b"\x00" + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def render(m):
    """Both horizontal nametables side by side (nametable 0/1 for vertical mirroring), then sprites."""
    bgbase = 0x1000 if m.ctrl & 0x10 else 0
    sprbase = 0x1000 if m.ctrl & 0x08 else 0
    W, H = 512, 240
    img = bytearray(W * H * 3)

    def col(i):
        c = NES_RGB[m.pal[i] & 0x3F]
        return (c >> 16) & 255, (c >> 8) & 255, c & 255

    for n in range(2):
        for ty in range(30):
            for tx in range(32):
                base = m.nt_index(0x2000 + n * 0x400) & ~0x3FF
                tile = m.nt[base + ty * 32 + tx]
                attr = m.nt[base + 960 + (ty // 4) * 8 + tx // 4]
                shift = ((ty // 2) & 1) * 4 + ((tx // 2) & 1) * 2
                pal = (attr >> shift) & 3
                px = tile_pixels(m.chr, bgbase, tile)
                for y in range(8):
                    for x in range(8):
                        c = px[y][x]
                        r, g, b = col(0 if c == 0 else pal * 4 + c)
                        o = ((ty * 8 + y) * W + n * 256 + tx * 8 + x) * 3
                        img[o:o + 3] = bytes((r, g, b))
    tall = bool(m.ctrl & 0x20)  # 8x16 sprites: bit0 of the tile index picks the pattern table
    for s in range(63, -1, -1):
        y, t, a, x = m.oam[s * 4:s * 4 + 4]
        if y >= 0xEF:
            continue
        rows = []
        if tall:
            base = 0x1000 if t & 1 else 0
            rows = tile_pixels(m.chr, base, t & 0xFE) + tile_pixels(m.chr, base, (t & 0xFE) + 1)
        else:
            rows = tile_pixels(m.chr, sprbase, t)
        hh = len(rows)
        for yy in range(hh):
            for xx in range(8):
                sx = 7 - xx if a & 0x40 else xx
                sy = hh - 1 - yy if a & 0x80 else yy
                c = rows[sy][sx]
                if c == 0 or x + xx >= 256 or y + 1 + yy >= H:
                    continue
                r, g, b = col(16 + (a & 3) * 4 + c)
                o = ((y + 1 + yy) * W + x + xx) * 3
                img[o:o + 3] = bytes((r, g, b))
    return W, H, img


def sheets(m):
    """Both 4K pattern tables side by side (256x128), tinted with sprite palette 0 (left) / bg palette 0 (right)."""
    W, H = 256, 128
    img = bytearray(W * H * 3)
    for half in range(2):
        pal = [m.pal[0]] + [m.pal[(16 if half == 0 else 0) + k] for k in (1, 2, 3)]
        for i in range(256):
            px = tile_pixels(m.chr, half * 0x1000, i)
            for y in range(8):
                for x in range(8):
                    c = NES_RGB[pal[px[y][x]] & 0x3F]
                    o = (((i // 16) * 8 + y) * W + half * 128 + (i % 16) * 8 + x) * 3
                    img[o:o + 3] = bytes(((c >> 16) & 255, (c >> 8) & 255, c & 255))
    return W, H, img


def dump(m, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "chr.bin").write_bytes(m.chr)
    (out / "nametables.bin").write_bytes(m.nt)
    (out / "palette.bin").write_bytes(m.pal)
    (out / "oam.bin").write_bytes(m.oam)
    (out / "state.json").write_text(json.dumps({"ctrl": m.ctrl, "scroll_x": m.scroll_x, "scroll_y": m.scroll_y,
                                                "vertical": m.vertical}))
    w, h, img = render(m)
    write_png(out / "screen.png", w, h, img)
    w, h, img = sheets(m)
    write_png(out / "sheets.png", w, h, img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("frames", type=int)
    ap.add_argument("--press", action="append", default=[], help="BTN@FRAME+LEN")
    ap.add_argument("--snap", type=int, action="append", default=[], help="also dump at this frame (to OUT/snap_N)")
    ap.add_argument("--out", default=str(Path(__file__).parent / "extracted" / "dump"))
    a = ap.parse_args()
    presses = []
    for p in a.press:
        b, rest = p.split("@")
        f, ln = rest.split("+")
        presses.append((BUTTONS.index(b.lower()), int(f), int(f) + int(ln)))
    m = Machine(Path(a.rom).read_bytes())
    m.mpu.reset()
    m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    out = Path(a.out)
    for f in range(a.frames):
        m.pad = sum(1 << b for b, s, e in presses if s <= f < e)
        m.frame()
        if f + 1 in a.snap:
            dump(m, out / f"snap_{f + 1}")
    dump(m, out)
    print(f"frame {a.frames}  PC={m.mpu.pc:04X}  bank={m.bank}  ctrl={m.ctrl:02X} mask={m.mask:02X}  -> {out}")


if __name__ == "__main__":
    main()

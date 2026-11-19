#!/usr/bin/env python3
"""Force each candle item code in the NES game and record which item appears.

usage: force_codes.py <rom.nes> [out.json]
Hooks the NES item-drop routine at $EB7E (the place that reads the candle's code from $0584,X), replaces the code,
and watches which object type is created ($EF04) and which sprites appear. Slow: about 25 s per code.
"""
import json, sys
from pathlib import Path
from nes_dump import Machine

ROM = Path(sys.argv[1]).read_bytes()
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "extracted" / "item_codes.json")
CODES = [0x00, 0x01, 0x11, 0x21, 0x31, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
         0x12, 0x13, 0x14, 0x0D]


def run(code, subweapon=0):
    m = Machine(ROM)
    mpu = m.mpu
    mpu.reset()
    mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    ram = m.mem._subject
    st = {"absx": 0, "prev": None, "n": 0}
    seen_types = []

    def frame(pad):
        m.pad = pad
        ram[0x45] = 0x40
        start = mpu.processorCycles
        m.vblank, m.spr0 = True, False
        if m.ctrl & 0x80:
            mpu.nmi()
        for stage, limit in ((0, 2273), (1, 7000), (2, 29780)):
            while mpu.processorCycles < start + limit:
                if mpu.pc == 0xEB7E and m.bank == m.bank:       # about to read the candle's item code
                    if st.get("force"):
                        ram[0x584 + mpu.x] = code
                        ram[0x72] = 0
                        ram[0x15B] = subweapon
                if mpu.pc == 0xEF04 and st.get("force"):         # object type being created
                    seen_types.append(mpu.a)
                mpu.step()
            if stage == 0:
                m.vblank = False
            if stage == 1:
                m.spr0 = True
        tot = (m.ctrl & 1) * 256 + m.scroll_x
        if st["prev"] is not None:
            d = (tot - st["prev"]) % 512
            st["absx"] += d if d < 256 else d - 512
        st["prev"] = tot

    for f in range(1100):
        frame(8 if 300 <= f < 304 else 0)
    st["prev"] = (m.ctrl & 1) * 256 + m.scroll_x

    def sprites():
        return [(st["absx"] + m.oam[i * 4 + 3], m.oam[i * 4], m.oam[i * 4 + 1], m.oam[i * 4 + 2])
                for i in range(1, 64) if m.oam[i * 4] < 0xEF]

    def anchor():
        c = [x for x, y, t, a in sprites() if t in (8, 16, 24, 52, 42)]
        return min(c) if c else None
    cx, cy = 796, 176
    alive = lambda: any(t in (0x40, 0x50) and abs(x - cx) <= 4 and abs(y - cy) <= 2 for x, y, t, a in sprites())
    n = 0
    while not alive() and n < 4000:
        frame(0x80)
        n += 1
    n = 0
    while n < 600:
        a = anchor()
        if a is None:
            frame(0)
        elif a < cx - 30:
            frame(0x80)
        elif a > cx + 24:
            frame(0x40)
        else:
            break
        n += 1
    for _ in range(25):
        frame(0)
    st["force"] = True
    seen = {}
    for i in range(110):
        frame(2 if i == 0 else 0)
        for x, y, t, a in sprites():
            known = (t in (0x40, 0x50, 0x70, 0x91, 0x93, 0x95, 0xFE, 0xFF) or (t < 0x60 and t % 2 == 0)
                     or 0x80 <= t <= 0x8B or (0xB0 <= t <= 0xCF and t % 2 == 0 and False))
            if abs(x - cx) <= 24 and cy - 10 <= y <= 214 and not known and y > 60:
                seen[(t, a)] = seen.get((t, a), 0) + 1
    items = sorted((hex(t), a) for (t, a), k in seen.items() if k >= 15)
    return {"code": code, "subweapon": subweapon, "types": sorted(set(hex(t) for t in seen_types)), "sprites": items}


result = []
for code in CODES:
    r = run(code)
    result.append(r)
    print(r, flush=True)
    OUT.write_text(json.dumps(result, indent=1))

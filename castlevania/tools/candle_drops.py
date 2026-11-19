#!/usr/bin/env python3
"""For each wall candle of stage 1, walk Simon next to it in the headless NES, break it and record the dropped item.

usage: candle_drops.py <rom.nes> [out.json]
Candles on the floor (y 176) are whipped standing, candles at y 144 with a jump-whip; higher ones are unreachable
without stairs and are skipped. Needs py65, run with the venv python. Slow (about 20 s per candle).
"""
import json, sys
from pathlib import Path
from nes_dump import Machine

ROM = Path(sys.argv[1]).read_bytes()
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "extracted" / "candle_drops.json")
WALL_X = [540, 604, 668, 732, 796, 859, 923, 987, 1051, 1115, 1179, 1243, 1307, 1371, 1435, 1499, 1563, 1627, 1691, 1755, 1819, 1883, 1947, 2011]
WALL_Y = [176, 144, 176, 144, 176, 144, 176, 144, 176, 144, 80, 176, 48, 80, 176, 80, 176, 176, 176, 176, 176, 144, 80, 48]
CANDLES = [(x, y) for x, y in zip(WALL_X, WALL_Y) if y in (176, 144) and x >= 604]
SIMON_TILES = {8, 16, 24, 52, 42}
JUMP, WHIP, RIGHT, LEFT = 1, 2, 0x80, 0x40


def run(cx, cy):
    m = Machine(ROM)
    m.mpu.reset()
    m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    ram = m.mem._subject
    st = {"absx": 0, "prev": None}

    def step(pad):
        m.pad = pad
        ram[0x45] = 0x40
        m.frame()
        tot = (m.ctrl & 1) * 256 + m.scroll_x
        if st["prev"] is not None:
            d = (tot - st["prev"]) % 512
            st["absx"] += d if d < 256 else d - 512
        st["prev"] = tot

    for f in range(1100):
        step(8 if 300 <= f < 304 else 0)
    st["prev"] = (m.ctrl & 1) * 256 + m.scroll_x

    def sprites():
        return [(st["absx"] + m.oam[i * 4 + 3], m.oam[i * 4], m.oam[i * 4 + 1], m.oam[i * 4 + 2])
                for i in range(1, 64) if m.oam[i * 4] < 0xEF]

    def anchor():
        c = [x for x, y, t, a in sprites() if t in SIMON_TILES]
        return min(c) if c else None

    def candle_alive():
        return any(t in (0x40, 0x50) and abs(x - cx) <= 4 and abs(y - cy) <= 2 for x, y, t, a in sprites())

    # the hall only exists once the castle-entrance scene is over: walk until this candle is on screen
    n = 0
    while not candle_alive() and n < 4000:
        step(RIGHT)
        n += 1
    # then stand next to it: left of it facing right, or right of it facing left
    n = 0
    while n < 600:
        a = anchor()
        if a is None:
            step(0)
        elif a < cx - 30:
            step(RIGHT)
        elif a > cx + 24:
            step(LEFT)
        else:
            break
        n += 1
    side = LEFT if (anchor() or 0) > cx else RIGHT
    for _ in range(25):
        step(0)
    if cy == 176:
        for i in range(70):
            step(WHIP if i == 0 else 0)
    else:                                                  # jump, whip near the top of the arc
        for i in range(70):
            step(JUMP if i == 0 else (WHIP if i == 10 else 0))
    # watch what appears around the candle after the whip (Simon stays put; his own tiles are even and < 0x60)
    destroyed = False
    seen = {}
    for _ in range(110):
        step(0)
        if not candle_alive():
            destroyed = True
        for x, y, t, a in sprites():
            known = (t in (0x40, 0x50, 0x70, 0x91, 0x93, 0x95, 0xFE, 0xFF) or (t < 0x60 and t % 2 == 0)
                     or 0x80 <= t <= 0x8B or (0xB0 <= t <= 0xCF and t % 2 == 0))
            if abs(x - cx) <= 24 and cy - 10 <= y <= 214 and not known and y > 60:
                seen[(t, a)] = seen.get((t, a), 0) + 1
    items = sorted((hex(t), a) for (t, a), n_ in seen.items() if n_ >= 15)
    return {"destroyed": destroyed, "items": items}


result = []
for cx, cy in CANDLES:
    r = run(cx, cy)
    result.append({"x": cx, "y": cy, **r})
    print(cx, cy, r, flush=True)
    OUT.write_text(json.dumps(result, indent=1))

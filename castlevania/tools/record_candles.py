#!/usr/bin/env python3
"""Record the wall candles of the NES game (object type $28) while playing the input list of record_rooms.py.

usage: record_candles.py <rom.nes> [out.json]
For every candle seen, writes [stage, floor, x, y, code]: x = room x of its centre (the object table keeps screen x:
room x = scroll + screen x, taken only while the candle is on screen ($300 = 0), and the most frequent value is
kept since it wobbles by a pixel while the screen moves), y = its centre ($354) and code = its item code ($584).
Stage 1's hall is included (stage 1, floor 0) to check the result against tools/extracted/candle_codes_true.json. Default output: tools/extracted/candles_rooms.json
"""
import json, sys
from pathlib import Path
from nes_dump import Machine
from record_rooms import SCRIPT, KEYS

CANDLE = 0x28


def main():
    m = Machine(Path(sys.argv[1]).read_bytes())
    out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "extracted" / "candles_rooms.json")
    m.mpu.reset()
    m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    ram = m.mem._subject
    from collections import Counter
    seen = Counter()                            # (stage, floor, y, code, room x) -> frames
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
            for i in range(4, 14):              # enemies (the candles use the slots after them)
                if ram[0x434 + i] != CANDLE:
                    ram[0x434 + i] = 0
            if ram[0x28] < 1 or (ram[0x18], ram[0x19]) != (5, 6) or not m.mask:
                prev = None
                continue
            key = (ram[0x28], ram[0x46])
            tot = (m.ctrl & 1) * 256 + m.scroll_x
            if key != room:
                room, cam = key, tot
            elif prev is not None:
                d = (tot - prev) % 512
                cam += d if d < 256 else d - 512
            prev = tot
            for i in range(1, 28):
                sx = ram[0x38C + i]
                y = ram[0x354 + i]
                # candles further than a screen away stay in the table with a screen x that wraps; the game marks
                # them with $300 = 1 (not drawn)
                if ram[0x434 + i] == CANDLE and 16 <= sx < 240 and ram[0x300 + i] == 0:
                    seen[(key[0], key[1], y, ram[0x584 + i], cam + sx)] += 1
    # one candle = a cluster of room x within 4 px for the same stage, floor and y: keep the most seen x, and the
    # most seen code (a slot shows code 0 for a few frames when the game puts the candle in it)
    rows, codes = [], []
    for k, n in seen.most_common():
        for r, c in zip(rows, codes):
            if r[:2] == list(k[:2]) and r[3] == k[2] and abs(r[2] - k[4]) <= 4:
                c[k[3]] += n
                break
        else:
            rows.append([k[0], k[1], k[4], k[2], k[3]])
            codes.append(Counter({k[3]: n}))
    for r, c in zip(rows, codes):
        r[4] = c.most_common(1)[0][0]
        if len(c) > 1:
            print("codes seen for", r[:4], dict(c))
    rows.sort()
    out.write_text(json.dumps(rows))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()

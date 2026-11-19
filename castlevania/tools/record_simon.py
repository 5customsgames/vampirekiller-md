#!/usr/bin/env python3
"""Record Simon's sprite poses and jump trajectory from the NES game.

usage: record_simon.py <rom.nes> [--out simon.json]
Poses are lists of [dx, dy, tile, attr]: dx is relative to the anchor sprite (the left leg sprite, which
stays put whatever the pose), dy relative to the standing top (OAM y = 160). Sprites are 8x16.
Also records the jump (dy per frame, whether Simon is curled up) and the whip timeline.
Needs py65, run it with the venv python.
"""
import argparse, json
from pathlib import Path
from nes_dump import Machine

HEALTH = 0x45
STAND_Y = 160
ANCHOR_TILES = (8, 16, 24, 52)
A, B, DOWN, RIGHT = 1, 2, 32, 128


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--out", default=str(Path(__file__).parent / "extracted" / "simon.json"))
    a = ap.parse_args()
    m = Machine(Path(a.rom).read_bytes())
    m.mpu.reset()
    m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    ram = m.mem._subject

    def step(pad):
        m.pad = pad
        ram[HEALTH] = 0x40
        m.frame()

    tlim = [0x60]

    def simon():
        """Simon's sprites: even tile < 0x80, deduplicated (flicker draws some twice)."""
        found = set()
        for s in range(1, 64):
            y, t, at, x = m.oam[s * 4:s * 4 + 4]
            if y < 0xEF and t < tlim[0] and not t & 1 and 100 < y < 200:
                found.add((x, y, t, at))
        anchors = [e for e in found if e[2] in ANCHOR_TILES]
        if not anchors:
            return None
        ax = min(e[0] for e in anchors)
        return sorted([e[0] - ax, e[1] - STAND_Y, e[2], e[3]] for e in found), ax

    for f in range(1100):
        step(8 if 300 <= f < 304 else 0)
    for _ in range(60):
        step(0)

    poses = {}
    poses["stand"] = simon()[0]

    # walking: the two distinct walk frames
    for f in range(40):
        step(RIGHT)
        s = simon()
        if s and any(e[2] == 10 for e in s[0]):
            poses.setdefault("walk1", s[0])
        if s and any(e[2] == 18 for e in s[0]):
            poses.setdefault("walk2", s[0])
    for _ in range(40):
        step(0)

    # crouch: curled-up legs
    for _ in range(8):
        step(DOWN)
    poses["crouch"] = simon()[0]
    for _ in range(20):
        step(0)

    # jump trajectory (A pressed on frame 0), top-of-sprite offset and curled state per frame
    jump = []
    for f in range(120):
        step(A if f == 0 else 0)
        s = simon()
        top = min(e[1] for e in s[0]) if s else 0
        curled = bool(s and any(e[2] == 50 for e in s[0]))
        if f > 5 and s and s[1] is not None and top == 0 and not curled:
            break
        jump.append([top, int(curled)])
    for _ in range(20):
        step(0)

    # whip timeline: record every distinct pose with how many frames it lasts
    whip, last = [], None
    for f in range(40):
        step(B if f == 0 else 0)
        s = simon()
        cur = s[0] if s else None
        if cur == poses["stand"] and f > 3:
            break
        if cur != last:
            whip.append({"frames": 1, "sprites": cur})
            last = cur
        else:
            whip[-1]["frames"] += 1
    whip = [w for w in whip if w["sprites"] and w["sprites"] != poses["stand"]]

    # crouching whip: hold DOWN until Simon is curled up, whip while still holding it, record until he is back to the crouch pose
    def crouch_whip(step_fn):
        for _ in range(20):
            step_fn(0)
        out, last = [], None
        for f in range(70):
            step_fn(DOWN | (B if f == 10 else 0))
            if f < 10:
                continue
            s_ = simon()
            cur = s_[0] if s_ else None
            if cur == poses["crouch"] and f > 14:
                break
            if cur != last:
                out.append({"frames": 1, "sprites": cur})
                last = cur
            else:
                out[-1]["frames"] += 1
        for _ in range(20):
            step_fn(0)
        return [w for w in out if w["sprites"] and w["sprites"] != poses["crouch"]]

    cwhip = crouch_whip(step)

    # --- upgraded whip: break the 2nd brazier (world x 216) and pick up what it drops, then record the whip again ---
    m2 = Machine(Path(a.rom).read_bytes())
    m2.mpu.reset()
    m2.mpu.pc = m2.mem[0xFFFC] | (m2.mem[0xFFFD] << 8)
    ram2 = m2.mem._subject
    st = {"absx": 0, "prev": None}

    def step2(pad):
        m2.pad = pad
        ram2[HEALTH] = 0x40
        m2.frame()
        tot = (m2.ctrl & 1) * 256 + m2.scroll_x
        if st["prev"] is not None:
            d = (tot - st["prev"]) % 512
            st["absx"] += d if d < 256 else d - 512
        st["prev"] = tot

    def sprites2():
        return [(st["absx"] + m2.oam[i * 4 + 3], m2.oam[i * 4], m2.oam[i * 4 + 1]) for i in range(1, 64) if m2.oam[i * 4] < 0xEF]

    def simon_x2():
        c = [x for x, y, t in sprites2() if t in ANCHOR_TILES]
        return min(c) if c else None

    for f in range(1100):
        step2(8 if 300 <= f < 304 else 0)
    st["prev"] = (m2.ctrl & 1) * 256 + m2.scroll_x
    for _ in range(60):                      # walk to the first two braziers, whipping each in range
        step2(0)
    f = 0
    while (simon_x2() or 0) < 216 - 30 and f < 1500:
        step2(RIGHT)
        f += 1
    for i in range(80):
        step2(B if i == 5 else 0)
    f = 0
    while any(t in (0xC1, 0xC3) for _, _, t in sprites2()) and f < 400:   # walk over the item to collect it
        step2(RIGHT)
        f += 1
    for _ in range(60):
        step2(0)
    m = m2
    tlim[0] = 0x70

    def long_whip():
        out, last = [], None
        for f in range(40):
            step2(B if f == 0 else 0)
            s2 = simon()
            cur = s2[0] if s2 else None
            if f > 3 and cur and len(cur) == 4 and not any(e[2] >= 26 for e in cur):
                break
            if cur != last:
                out.append({"frames": 1, "sprites": cur})
                last = cur
            else:
                out[-1]["frames"] += 1
        out = [w for w in out if w["sprites"] and len(w["sprites"]) > 4 or w is out[-1]]
        return [w for w in out if w["sprites"]]
    whip2 = long_whip()
    cwhip2 = crouch_whip(step2)
    # the longest chain ($70 = 2, a second upgrade: its whip level is poked)
    ram2[0x70] = 2
    for _ in range(30):
        step2(0)
    whip3 = long_whip()
    cwhip3 = crouch_whip(step2)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"poses": poses, "jump": jump, "whip": whip, "whip2": whip2, "cwhip": cwhip, "cwhip2": cwhip2,
                                          "whip3": whip3, "cwhip3": cwhip3}, indent=1))
    print(f"poses: {list(poses)}  jump frames: {len(jump)}  whip phases: {[w['frames'] for w in whip]}  whip2: {[w['frames'] for w in whip2]}  crouch whip: {[w['frames'] for w in cwhip]} / {[w['frames'] for w in cwhip2]}  whip3: {[w['frames'] for w in whip3]} / {[w['frames'] for w in cwhip3]}")


if __name__ == "__main__":
    main()

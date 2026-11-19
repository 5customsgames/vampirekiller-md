#!/usr/bin/env python3
"""Record Simon's poses on a staircase of the NES game (first flight of the hall, rising to the right).

usage: record_stairs.py <rom.nes> [--out stairs.json]
Poses are lists of [dx, dy, tile, attr]: dx relative to the anchor (the left leg sprite, tiles 16/56/52/76 are legs),
dy relative to the top of the body. Also records the climb speed and the whip timeline on the stairs,
before and after the whip upgrade. Needs py65, run it with the venv python.
"""
import argparse, json
from pathlib import Path
from nes_dump import Machine

HEALTH = 0x45
UP, DOWN, WHIP, RIGHT = 0x10, 0x20, 2, 0x80
SIMON_T = set(range(2, 0x70, 2)) - {0x40, 0x50}
LEG_T = (16, 56, 52, 76)


class Run:
    def __init__(self, rom):
        self.m = Machine(rom)
        m = self.m
        m.mpu.reset()
        m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
        self.ram = m.mem._subject
        self.absx, self.prev = 0, None
        for f in range(1100):
            self.step(8 if 300 <= f < 304 else 0)
        self.prev = (m.ctrl & 1) * 256 + m.scroll_x

    def step(self, pad):
        m = self.m
        m.pad = pad
        self.ram[HEALTH] = 0x40
        m.frame()
        tot = (m.ctrl & 1) * 256 + m.scroll_x
        if self.prev is not None:
            d = (tot - self.prev) % 512
            self.absx += d if d < 256 else d - 512
        self.prev = tot

    def sprites(self):
        m = self.m
        return [(self.absx + m.oam[i * 4 + 3], m.oam[i * 4], m.oam[i * 4 + 1], m.oam[i * 4 + 2])
                for i in range(1, 64) if m.oam[i * 4] < 0xEF]

    def simon(self, tmax=0x60):
        return sorted(set((x, y, t, a) for x, y, t, a in self.sprites()
                          if t in SIMON_T and t < tmax and 100 < y < 216 and x > 0))

    def pose(self, tmax=0x60):
        """sprites as [dx, dy, tile, attr] relative to the left leg sprite, dy relative to the top of the body."""
        s = self.simon(tmax)
        legs = [e for e in s if e[2] in LEG_T]
        if not s or not legs:
            return None, None
        ax = min(e[0] for e in legs)
        ay = min(e[1] for e in s)
        return sorted([x - ax, y - ay, t, a] for x, y, t, a in s), (ax, ay)

    def anchor(self):
        c = [x for x, y, t, a in self.sprites() if t in (8, 16, 24, 52, 42)]
        return min(c) if c else None


def timeline(run, press_frame, frames, tmax, stop_pose, pad_extra=0):
    """press the whip button and record each distinct pose with its duration, until `stop_pose` is seen again."""
    out, last = [], None
    for f in range(frames):
        run.step(pad_extra | (WHIP if f == press_frame else 0))
        if f < press_frame:
            continue
        cur = run.pose(tmax)[0]
        if cur == stop_pose and f > press_frame + 3:
            break
        if cur != last:
            out.append({"frames": 1, "sprites": cur})
            last = cur
        elif out:
            out[-1]["frames"] += 1
    return [w for w in out if w["sprites"] and w["sprites"] != stop_pose]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--out", default=str(Path(__file__).parent / "extracted" / "stairs.json"))
    a = ap.parse_args()
    rom = Path(a.rom).read_bytes()
    r = Run(rom)
    n = 0
    while (r.anchor() or 0) < 1113 and n < 3500:
        r.step(RIGHT)
        n += 1
    for _ in range(20):
        r.step(0)

    poses, track = {}, []
    # climb up (UP held): note the two alternating poses and the movement
    for i in range(160):
        r.step(UP)
        p, pos = r.pose()
        if p and pos:
            track.append((i, pos[0], pos[1], json.dumps(p)))
    seen = []
    for i, x, y, p in track:
        if p not in seen:
            seen.append(p)
    # the two climbing poses are the ones that alternate while moving; the top-of-flight pose is the standing one
    poses["up_a"] = json.loads(seen[0]) if seen else None
    for p in seen:
        if json.loads(p) != poses["up_a"]:
            poses.setdefault("up_b", json.loads(p))
    # pose changes over time (to measure the animation rate) and path
    changes = [(i, x, y) for k, (i, x, y, p) in enumerate(track) if k == 0 or p != track[k - 1][3]]
    print("pose changes (frame, x, y):", changes[:14])

    # back to the middle of the flight: idle pose and whip
    for _ in range(0):
        r.step(0)
    r2 = Run(rom)
    n = 0
    while (r2.anchor() or 0) < 1113 and n < 3500:
        r2.step(RIGHT)
        n += 1
    for _ in range(20):
        r2.step(0)
    for _ in range(60):
        r2.step(UP)
    for _ in range(30):
        r2.step(0)
    idle = r2.pose()[0]
    poses["idle"] = idle
    whip = timeline(r2, 5, 70, 0x60, idle)

    # descending: from the top of the flight hold DOWN and record the poses
    for _ in range(120):
        r2.step(UP)
    for _ in range(10):
        r2.step(0)
    seen = []
    for i in range(140):
        r2.step(DOWN)
        p = r2.pose()[0]
        if p and p not in seen:
            seen.append(p)
    poses["down_poses"] = seen

    # upgraded whip: break the 2nd brazier (world x 216), pick up the whip, come back to the stairs, whip on them
    r3 = Run(rom)

    def pos3():
        return r3.anchor() or 0
    n = 0
    while pos3() < 216 - 30 and n < 2500:
        r3.step(RIGHT)
        n += 1
    for i in range(80):
        r3.step(WHIP if i == 5 else 0)
    n = 0
    while any(t in (0xC1, 0xC3) for x, y, t, a in r3.sprites()) and n < 400:
        r3.step(RIGHT)
        n += 1
    n = 0
    while pos3() < 1113 and n < 4000:
        r3.step(RIGHT)
        n += 1
    for _ in range(20):
        r3.step(0)
    for _ in range(60):
        r3.step(UP)
    for _ in range(30):
        r3.step(0)
    idle2 = r3.pose(0x70)[0]
    whip2 = timeline(r3, 5, 70, 0x70, idle2)

    # climb speed: world x/y after a long climb
    out = {"poses": poses, "whip": whip, "whip2": whip2, "idle_check": idle2 == idle}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print("poses:", {k: (len(v) if v else v) for k, v in poses.items()})
    print("whip phases:", [w["frames"] for w in whip], "whip2:", [w["frames"] for w in whip2])


if __name__ == "__main__":
    main()

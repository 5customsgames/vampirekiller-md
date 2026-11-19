#!/usr/bin/env python3
"""The rooms of GRAPH 16B as shown, from generated/gfx16_md.c (research/gfx16.md, rom-budget.md 2.4).

Each room (stages 1 to 18 and the three courtyard screens) is rendered from the pool, its slots, its
map and its PAL0 palette: every pixel is the 9-bit colour of its palette entry, or "transparent" for
index 0 (the planes behind and the backdrop show there). Every slot is rendered too, not only the
map (the game draws slots by number: hidden blocks, restored cells), and msx[c] is checked to name
the same colour. CRAM order and VRAM tile data may differ; what is on screen may not.

  check_gfx16_render.py OLD.c NEW.c          compare two generated files, room by room
  check_gfx16_render.py --hashes FILE.c      print the fingerprint of every room (JSON)
  check_gfx16_render.py --check JSON FILE.c  compare with fingerprints saved earlier
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from lz4w_pack import unpack  # noqa: E402
GENERATED = ROOT / 'sgdk/src/generated/gfx16_md.c'


def parse(path):
    text = Path(path).read_text()
    words = [int(v, 16) for v in re.findall(r'0x([0-9A-F]{8})',
                                            re.search(r'vk_gfx16_pool\[\d+\] = \{(.*?)\};', text, re.S).group(1))]
    pool = [tuple(words[i:i + 8]) for i in range(0, len(words), 8)]
    rooms = {}
    for m in re.finditer(r'static const u16 (g16_\w+?)_slots\[(\d+)\] = \{(.*?)\};', text, re.S):
        name = m.group(1)
        cells = re.search(name + r'_map\[\d+\](?: __attribute__\(\(aligned\(2\)\)\))? = \{(.*?)\};', text, re.S).group(1)
        r = re.search(r'static const VKGfx16Room ' + name + r' = \{\w+, \w+, (\d+), \{([^}]*)\}, \{([^}]*)\}\};', text)
        rooms[name] = {'slots': [int(v) for v in re.findall(r'\d+', m.group(3))],
                       'map': list(unpack(bytes(int(v) for v in re.findall(r'\d+', cells)))),   # packed in LZ4W
                       'count': int(r.group(1)),
                       'palette': [int(v, 16) for v in r.group(2).split(',')],
                       'msx': [int(v) for v in r.group(3).split(',')]}
    return pool, rooms


def shown(pool, room):
    """(slots as shown, map, msx colours): -1 = transparent, else the CRAM word."""
    pal = room['palette']
    slots = []
    for s in room['slots']:
        slots.append(tuple(-1 if v == 0 else pal[v] for row in pool[s] for v in
                           ((row >> (28 - 4 * x)) & 15 for x in range(8))))
    if room['count'] != len(slots) or max(room['map']) >= len(slots):
        raise ValueError('slot count')
    return slots, room['map'], [pal[i] if i else 0 for i in room['msx']]


def screen(slots, cells):
    """The 256 x 176 picture of the map."""
    out = []
    for cy in range(22):
        for y in range(8):
            for cx in range(32):
                out.extend(slots[cells[cy * 32 + cx]][y * 8:y * 8 + 8])
    return out


def fingerprint(pool, room):
    slots, cells, msx = shown(pool, room)
    h = hashlib.sha256()
    h.update(repr((slots, cells, msx)).encode())
    return h.hexdigest()[:24]


def compare(old, new):
    (pa, ra), (pb, rb) = parse(old), parse(new)
    bad = []
    if sorted(ra) != sorted(rb):
        bad.append(f'rooms differ: {sorted(set(ra) ^ set(rb))}')
    pixels = 0
    for name in sorted(set(ra) & set(rb)):
        sa, ca, ma = shown(pa, ra[name])
        sb, cb, mb = shown(pb, rb[name])
        a, b = screen(sa, ca), screen(sb, cb)
        pixels += len(a)
        diff = sum(x != y for x, y in zip(a, b))
        if diff:
            bad.append(f'{name}: {diff} pixels differ')
        if sa != sb:
            bad.append(f'{name}: {sum(x != y for x, y in zip(sa, sb))} slots differ')
        if ma != mb:
            bad.append(f'{name}: msx colours differ')
    print(f'{len(ra)} rooms, {pixels} pixels compared; pool {len(pa)} -> {len(pb)} tiles '
          f'({32 * len(pa)} -> {32 * len(pb)} bytes)')
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('files', nargs='*', type=Path)
    ap.add_argument('--hashes', action='store_true')
    ap.add_argument('--check', type=Path)
    a = ap.parse_args()
    if a.hashes or a.check:
        path = a.files[0] if a.files else GENERATED
        pool, rooms = parse(path)
        prints = {name: fingerprint(pool, r) for name, r in sorted(rooms.items())}
        if a.hashes:
            print(json.dumps(prints, indent=1, sort_keys=True))
            return 0
        want = json.loads(a.check.read_text())
        bad = [n for n in sorted(set(want) | set(prints)) if want.get(n) != prints.get(n)]
        print(f'{len(prints)} rooms, {len(bad)} differ' + (': ' + ' '.join(bad) if bad else ''))
        return 1 if bad else 0
    bad = compare(*a.files)
    for line in bad:
        print(line)
    print('identical' if not bad else f'{len(bad)} differences')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

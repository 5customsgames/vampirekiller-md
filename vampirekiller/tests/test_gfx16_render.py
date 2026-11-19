"""GRAPH 16B rooms as shown (tools/check_gfx16_render.py, research/gfx16.md, rom-budget.md 2.4): every room of
stages 1 to 18 and the courtyard screens, rendered from generated/gfx16_md.c (pool, slots, map, PAL0; index 0
transparent), must match the fingerprints of tests/data/gfx16_render.json, taken from the data before the shared
palette indices (pool of 6071 tiles). A change of the 16-bit art on purpose updates them:
  python3 tools/check_gfx16_render.py --hashes > tests/data/gfx16_render.json"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from check_gfx16_render import GENERATED, fingerprint, parse  # noqa: E402


class Gfx16Render(unittest.TestCase):
    def test_rooms_shown_as_before(self):
        pool, rooms = parse(GENERATED)
        want = json.loads((ROOT / 'tests/data/gfx16_render.json').read_text())
        self.assertEqual(sorted(want), sorted(rooms))
        for name, room in rooms.items():
            self.assertEqual(fingerprint(pool, room), want[name], name)

    def test_pool_is_shared(self):
        pool, rooms = parse(GENERATED)
        self.assertEqual(len(pool), len(set(pool)))      # every tile once
        self.assertLessEqual(len(pool), 2300)             # shared palette indices (6071 before)
        for name, room in rooms.items():
            self.assertEqual(room['palette'][0], 0, name)  # entry 0: black, the backdrop of colour 0


if __name__ == '__main__':
    unittest.main()

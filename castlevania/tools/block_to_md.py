#!/usr/bin/env python3
"""Turn a block of NES stages after the first (stages 4-6 = block 2, ...) into SGDK data, straight from the ROM.

usage: block_to_md.py <rom.nes> [--block 2]
Writes src/block<N>.c and inc/block<N>.h, with both arts (block<N>_tiles / _palette: 16-bit, block<N>_tiles_nes /
_palette_nes: the NES game's) sharing one tile map, as tools/level_to_md.py does. Run with the venv python after tools/level_to_md.py, whose
tools/extracted/fixed_layout.json says what the first FIXED_TILES tiles hold (the empty tile, the sprites, the HUD
and its font): they are drawn again here with the block's art and palettes, at the same indices, so the poses, the
HUD and the text of block 1 stay valid. The block's background tiles follow them.

From the ROM (fixed bank unless said otherwise):
- CHR: the stage's set is $C8B0[stage]; the loader at $FD23 copies the entries of the list at $FDBB + 2 * set
  (bank, source, CHR address, length; $FF ends it) over what is already in CHR-RAM, so they are laid over block 1's
  CHR (tools/extracted/level1/chr.bin), as in the NES game.
- background palettes: palette commands at $CE28 (block 1), then one every 19 bytes ($3F $00, 16 colours, $FE);
  the sprite palettes are those of block 1 (the same colours in the ROM).
- rooms: tools/decode_rooms.py; the rooms are laid side by side in the world, stage by stage, floor 0 first.
- collision: the NES game's collision map ($05A0) marks the tiles $60-$6B as solid: a solid tile with a non solid
  one above it is a surface Simon stands on.
"""
import argparse, json
from collections import Counter
from pathlib import Path
from art import ART_SUFFIX, Art16, ArtNES, _dist, md_word, nes_index, pack_palette, x_glyph
from decode_rooms import Rom

ROWS = 30
BLOCKS = {2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12), 5: (13, 14, 15), 6: (16, 17), 7: (18,)}
# stage 18 has its own CHR ($C8B0: set 9, loaded over stage 17's) and palette (the next entry of $CE28): block 7 here                 # NES stages ($28) of each block
# the rooms (stage, floor) from left to right in the world: in block 2 the way out of stages 4 and 5 is a door at the
# left end of their floor 1 (exit table at $FC12: y | floor, screen x), and the next stage starts at the right end of
# its floor 0, so each of those floors 0 lies just left of the room before it. In block 3 the way out of stages 7 and
# 8 is a door at the right end of their floor 1, and stages 8 and 9 start at the left end of their floor 0 (stage 7 at
# the right end of its floor 0, checked in the NES game)
ORDER = {2: [(4, 0), (5, 0), (4, 1), (6, 0), (5, 1), (6, 1)],
         3: [(7, 0), (7, 1), (8, 0), (8, 1), (9, 0)],
         # block 4: stage 10 starts at the left of its floor 0 ($CA0C) and leaves it on the right ($FC12); stages 11
         # and 12 start at their left end
         4: [(10, 0), (11, 0), (12, 0)],
         # block 5: stage 13 starts at the left of its floor 0 and leaves its floor 1 on the right; stage 14 starts in
         # the last screen of its floor 0 and leaves its floor 1 on the left; stage 15 starts at the right end of its
         # floor 0 ($CA0C: y & F8 | page, x & FE | floor; $FC12: y & FE | floor, screen x), so that it lies just left of
         # stage 14's floor 1, as in block 2
         5: [(13, 0), (13, 1), (14, 0), (15, 0), (14, 1), (15, 1)],
         # block 6: stage 16 starts at the right end of its floor 0 and leaves it through an archway at its left end
         # (the castle gate's cutscene, $CF53); stage 17 starts at the right end of its floor 0 and leaves its floor 1
         # at its left end (x 0x10 of $FC12), where stage 18 is loaded at once (checked in the NES game)
         6: [(16, 0), (17, 0), (17, 1)],
         7: [(18, 0), (18, 1)]}
# rooms left out: stage 10's floor 1 is a copy of the first screen of its floor 0, which neither the start ($CA0C)
# nor the exit table ($FC12) uses
UNUSED = {(10, 1)}
COL0 = {2: 512, 3: 992, 4: 1632, 5: 2144, 6: 2784, 7: 3168}                 # the block's first world column (after the previous block's)
# the SNES port's 16-bit layouts of the block (level-layouts/<dir>): the NES addresses in bank 4 of the room layout
# and of the tile groups they replace (measured: they match the NES data there but for some scenery)
SNES_LAYOUTS = {"level-2": (0x8855, 0x8B25), "level-3": (0x8DC6, 0x9156), "level-4": (0x945B, 0x975B),
                "level-5": (0x9B41, 0x9ED1), "level-6": (0xA207, 0xA537), "dracula": (0xA904, 0xA9F4)}

# the SNES port's palettes of the block: its background and sprite palettes at the same index (palette_updates.asm)
SNES_PAL = {2: ("level-layouts/level-2/palette.bin", "16bit-tiles/sprite_16bit_palette_03.bin"),
            3: ("level-layouts/level-3/palette.bin", "16bit-tiles/sprite_16bit_palette_04.bin"),
            4: ("level-layouts/level-4/palette.bin", "16bit-tiles/sprite_16bit_palette_05.bin"),
            5: ("level-layouts/level-5/palette.bin", "16bit-tiles/sprite_16bit_palette_06.bin"),
            6: ("level-layouts/level-6/palette.bin", "16bit-tiles/sprite_16bit_palette_07.bin"),
            7: ("level-layouts/dracula/palette.bin", "16bit-tiles/sprite_16bit_palette_08.bin")}
SOLID = range(0x60, 0x6C)
# rooms whose first pages the camera never shows although the scroll tables allow them: stage 4 starts at scroll 256
# with Simon at x 64 on the screen, walled in between screen x 16 and 232 (checked in the NES game), so the camera
# never moves and page 0 holds leftovers
FIRST_X = {(4, 0): 256,
           # stage 14 starts at page 4 of its floor 0 ($CA0C), and the screen stays there (checked in the NES game)
           (14, 0): 1024}
# the block's own sprites (CHR tiles $80-$FF of the first pattern table are the block's), as the NES game draws them
# facing left: (dx, dy, tile, attr) from the anchor, 8 px left of the centre and at OAM y 16 above it (knight)
BLOCK_POSES = {2: [
    # the armour knight (object type 8), 4 walking poses of 17 frames: its head bobs a pixel
    ("KNIGHT0", [(0, 1, 0x80, 1), (8, 1, 0x82, 1), (0, 16, 0x84, 1), (8, 16, 0x86, 1)]),
    ("KNIGHT1", [(0, 0, 0x80, 1), (8, 0, 0x82, 1), (0, 16, 0x88, 1), (8, 16, 0x8A, 1)]),
    ("KNIGHT2", [(0, 1, 0x80, 1), (8, 1, 0x82, 1), (0, 16, 0x8C, 1), (8, 16, 0x8E, 1)]),
    ("KNIGHT3", [(0, 0, 0x80, 1), (8, 0, 0x82, 1), (0, 16, 0x88, 1), (8, 16, 0x8A, 1)]),
    # the red bat (object type 7): hanging asleep, then 3 flying poses (shown 9 frames each in the order 0 1 2 1); anchor 8 px
    # left of the centre, OAM y 8 above it
    ("RBAT_SLEEP", [(0, 0, 0x9C, 1), (8, 0, 0x9C, 65)]),
    ("RBAT0", [(0, 0, 0x90, 1), (8, 0, 0x92, 1)]),
    ("RBAT1", [(0, 0, 0x94, 1), (8, 0, 0x96, 1)]),
    ("RBAT2", [(0, 0, 0x98, 1), (8, 0, 0x9A, 1)]),
    # the Medusa head (object type 6): 2 poses of 9 frames, facing left; anchor 8 px left of the centre, 8 above it
    ("MEDUSA0", [(0, 0, 0xE8, 2), (8, 0, 0xEA, 2)]),
    ("MEDUSA1", [(0, 0, 0xEC, 2), (8, 0, 0xEE, 2)]),
    # the ghost (object type 0x0D): 2 poses of 9 frames, facing left; anchor 8 px left of the centre, 8 above it
    ("GHOST0", [(0, 1, 0xB0, 1), (8, 1, 0xB2, 1)]),
    ("GHOST1", [(0, 1, 0xB0, 1), (8, 1, 0xB4, 1)]),
    # the bone pillar (object type 0x0E): two skulls, the lower one mirrored; anchor 8 px left of the centre, 16 above
    ("PILLAR", [(0, 1, 0xE0, 1), (8, 1, 0xE2, 1), (0, 17, 0xE2, 65), (8, 17, 0xE0, 65)]),
    # ... flashing before it spits: sprite palette 3 on odd frames ($338)
    ("PILLAR_FLASH", [(0, 1, 0xE0, 3), (8, 1, 0xE2, 3), (0, 17, 0xE2, 67), (8, 17, 0xE0, 67)]),
    # the Medusa boss (object type 0x1B): two symmetric 32x32 poses of 9 frames; anchor 16 px left of the centre, 16
    # above it
    ("MBOSS0", [(0, 1, 0xD8, 2), (8, 1, 0xDA, 2), (16, 1, 0xDA, 66), (24, 1, 0xD8, 66),
                (0, 17, 0xDC, 2), (8, 17, 0xDE, 2), (16, 17, 0xDE, 66), (24, 17, 0xDC, 66)]),
    ("MBOSS1", [(0, 1, 0xD0, 1), (8, 1, 0xD2, 1), (16, 1, 0xD2, 65), (24, 1, 0xD0, 65),
                (0, 17, 0xD4, 1), (8, 17, 0xD6, 1), (16, 17, 0xD6, 65), (24, 17, 0xD4, 65)]),
    # her snakes (object type 9): 2 poses of 9 frames (the second one mirrored), facing left; anchor 8 px left of the
    # centre, 10 above it
    ("SNAKE0", [(0, 0, 0xF4, 2), (8, 0, 0xF6, 2)]),
    ("SNAKE1", [(-2, 1, 0xF6, 66), (6, 1, 0xF4, 66)]),
    # the moving platform (slots 0x17..): 4 sprites of tile 0x72 from 16 px left of its centre, at OAM y = its top
    ("PLATFORM", [(0, 0, 0x72, 0), (8, 0, 0x72, 0), (16, 0, 0x72, 0), (24, 0, 0x72, 0)]),
]}
# the hidden treasures of blocks 2 and 3 (NES table at $FC38) other than the money bag and the 1UP, whose palette cycles
# through the 4 sprite palettes every 2 frames ($338); anchor 8 px left of the centre, OAM y 8 above it, as the bag:
# item 2 (a crown, NES pose $DF) and item 3 (a chest, $E0), 2000 points each, and the spinning item 4 (4000 points), 4
# poses of 8 frames ($A79B: $E1 + frame / 8 & 3). TR<item>_<palette>, TR4_<pose><palette>
BLOCK_POSES[2] += [("TR2_%d" % p, [(0, 0, 0xA0, p), (8, 0, 0xA2, p)]) for p in range(4)]
BLOCK_POSES[2] += [("TR3_%d" % p, [(0, 0, 0xA4, p), (8, 0, 0xA6, p)]) for p in range(4)]
BLOCK_POSES[2] += [
    ("TR4_%d%d" % (k, p), [(dx, 0, t, a + p) for dx, t, a in pose])
    for k, pose in enumerate([[(4, 0xB8, 0), (8, 0xBA, 0)], [(4, 0xB6, 0)], [(4, 0xBA, 64), (8, 0xB8, 64)], [(4, 0xBC, 0)]])
    for p in range(4)
]
# then, once taken, their points ($A7B8: pose $63 "1000" for the bag, $AD "2000", $AE "4000"), 16 px further right, in
# the same cycling palettes. PTS<points>_<palette>
BLOCK_POSES[2] += [("PTS%d_%d" % (n, p), [(0, 0, t, p), (8, 0, 0xC7, p)])
                   for n, t in ((1000, 0xC9), (2000, 0xCB), (4000, 0xCD)) for p in range(4)]
# block 3 draws the objects it shares with block 2 (Medusa heads, ghosts, bone pillars) with the same CHR tiles: the
# same list, so the B2_ pose numbers work in both blocks, then its own
BLOCK_POSES[3] = BLOCK_POSES[2] + [
    # the fleaman (object type 0x0C): standing ($4C0 = 0x3C) and jumping (0x3D), facing left; hidden while it waits
    # (0x4D, the two poses in turn every 9 frames, behind the background); anchor 8 px left of the centre, 8 above it
    ("FLEA_STAND", [(1, 1, 0x78, 3), (9, 1, 0x7A, 3)]),
    ("FLEA_JUMP", [(1, 1, 0x7C, 3), (9, 1, 0x7E, 3)]),
    # the raven (object type 0x0F): perched (0x14), then flying (0x13) in 3 poses of 9 frames shown 0 1 2 1, facing left
    ("RAVEN_PERCH", [(1, 1, 0xAC, 3), (9, 1, 0xAE, 3)]),
    ("RAVEN0", [(1, 0, 0xA0, 3), (9, 0, 0xA2, 3)]),
    ("RAVEN1", [(1, 0, 0xA4, 3), (9, 0, 0xA6, 3)]),
    ("RAVEN2", [(1, 0, 0xA8, 3), (9, 0, 0xAA, 3)]),
    # the white skeleton (object type 0x10): 2 walking poses of 16 frames, facing left; anchor 8 px left of the centre,
    # 16 above it
    ("SKEL0", [(0, 1, 0x80, 1), (8, 1, 0x82, 1), (0, 17, 0x84, 1), (8, 17, 0x86, 1)]),
    ("SKEL1", [(0, 1, 0x88, 1), (8, 1, 0x8A, 1), (0, 17, 0x8C, 1), (8, 17, 0x8E, 1)]),
    # its bone (object type 0x24): 3 poses of 9 frames, flying right; anchor 8 px left of the centre, 8 above it
    ("BONE0", [(3, 4, 0x92, 1)]),
    ("BONE1", [(0, 3, 0x94, 1), (8, 3, 0x96, 1)]),
    ("BONE2", [(0, 3, 0x96, 65), (8, 3, 0x94, 65)]),
    # the mummies (object type 0x1A, stage 9's boss): 3 walking poses of 17 frames shown 0 1 2 1, facing left; anchor 8 px
    # left of the centre, 24 above it; then the same in sprite palette 3, which flashes before a throw ($338 = 0x43)
    ("MUMMY0", [(0, 1, 0xD0, 1), (8, 1, 0xD2, 1), (0, 17, 0xD4, 1), (8, 17, 0xD6, 1), (0, 33, 0xD8, 1), (8, 33, 0xDA, 1)]),
    ("MUMMY1", [(0, 1, 0xDC, 1), (8, 1, 0xDE, 1), (0, 17, 0xC0, 1), (8, 17, 0xC2, 1), (0, 33, 0xC4, 1), (8, 33, 0xC6, 1)]),
    ("MUMMY2", [(0, 1, 0xC8, 1), (8, 1, 0xCA, 1), (0, 17, 0xCC, 1), (8, 17, 0xCE, 1), (0, 33, 0xF0, 1), (8, 33, 0xF2, 1)]),
    ("MUMMYF0", [(0, 1, 0xD0, 3), (8, 1, 0xD2, 3), (0, 17, 0xD4, 3), (8, 17, 0xD6, 3), (0, 33, 0xD8, 3), (8, 33, 0xDA, 3)]),
    ("MUMMYF1", [(0, 1, 0xDC, 3), (8, 1, 0xDE, 3), (0, 17, 0xC0, 3), (8, 17, 0xC2, 3), (0, 33, 0xC4, 3), (8, 33, 0xC6, 3)]),
    ("MUMMYF2", [(0, 1, 0xC8, 3), (8, 1, 0xCA, 3), (0, 17, 0xCC, 3), (8, 17, 0xCE, 3), (0, 33, 0xF0, 3), (8, 33, 0xF2, 3)]),
    # their bandages (object type 0x22), flying left; anchor 8 px left of the centre, 8 above it
    ("BANDAGE", [(0, 0, 0xF4, 1), (8, 0, 0xF6, 1)]),
]
# block 4: block 3's list for now, so that the B2_ indices stay valid (its own enemies come after)
BLOCK_POSES[4] = BLOCK_POSES[3] + [
    # the eagle (object type 0x12, NES pose 0x53): 2 wing poses of 17 frames, facing left; anchor 8 px left of the
    # centre, 16 above it (so that mirroring keeps the centre)
    ("EAGLE0", [(dx, dy, t + 2 * k + 8 * (dy > 0), 1) for dy in (0, 16) for k, dx in enumerate((-6, 2, 10, 18))
                for t in (0xB0,)]),
    ("EAGLE1", [(dx, dy, t + 2 * k + 8 * (dy > 0), 1) for dy in (0, 16) for k, dx in enumerate((-6, 2, 10, 18))
                for t in (0xC0,)]),
    # the bone dragon (object types 0x14 to 0x16), facing left: its head, mouth shut (NES pose 0x5A) and open (0x2D), and
    # one vertebra (0x2E), which its base shows too; anchor 8 px left of the centre, 8 above it
    ("DRAGON0", [(-2, 0, 0xD0, 1), (6, 0, 0xD2, 1)]),
    ("DRAGON1", [(-2, 0, 0xD4, 1), (6, 0, 0xD6, 1)]),
    ("VERT", [(2, 0, 0xD8, 1)]),
    # Frankenstein (object type 0x1C, stage 12's boss, NES pose 0x25): 3 walking poses of 25 frames shown 2 0 1 0,
    # facing left; anchor 8 px left of the centre, 24 above it
    ("FRANK0", [(0, 1, 0xE6, 1), (8, 1, 0xE8, 1), (0, 17, 0xEA, 1), (8, 17, 0xEC, 1), (0, 33, 0xEE, 1), (8, 33, 0xF0, 1)]),
    ("FRANK1", [(0, 1, 0xDA, 1), (8, 1, 0xDC, 1), (0, 17, 0xDE, 1), (8, 17, 0xE0, 1), (0, 33, 0xE2, 1), (8, 33, 0xE4, 1)]),
    ("FRANK2", [(0, 1, 0xF2, 1), (8, 1, 0xF4, 1), (0, 17, 0xF6, 1), (8, 17, 0xF8, 1), (0, 33, 0xFA, 1), (8, 33, 0xE4, 1)]),
    # Igor (object type 0x1F) has the fleaman's poses, and one more while it falls (NES pose 0x3E)
    ("IGOR_FALL", [(1, 1, 0x78, 3), (9, 1, 0x7E, 3)]),
]

# block 5: block 4's list, so that the indices stay valid, then its own enemies
BLOCK_POSES[5] = BLOCK_POSES[4] + [
    # the red skeleton (object type 0x13, NES poses 0x02, 0x56, 0x57, 0x54): 2 walking poses of 17 frames, facing left;
    # anchor 8 px left of the centre, 16 above it
    ("RSK0", [(0, 1, 0x80, 3), (8, 1, 0x82, 3), (0, 17, 0x84, 3), (8, 17, 0x86, 3)]),
    ("RSK1", [(0, 1, 0x88, 3), (8, 1, 0x8A, 3), (0, 17, 0x8C, 3), (8, 17, 0x8E, 3)]),
    # falling apart and getting up, facing left; facing right, the head (0x70) moves but is not mirrored: its own pose
    ("RSK_FALL0", [(0, 17, 0x9A, 67), (8, 9, 0x70, 3), (8, 17, 0x98, 67)]),
    ("RSK_FALL0R", [(8, 17, 0x9A, 3), (0, 9, 0x70, 3), (0, 17, 0x98, 3)]),
    ("RSK_FALL1", [(0, 17, 0x9A, 67), (8, 17, 0x98, 67)]),
    ("RSK_DOWN", [(0, 17, 0x9E, 67), (8, 17, 0x9C, 67)]),
    # the axe knight (object type 0x0A, NES pose 0x15): 2 walking poses of 17 frames, facing left, 24 px wide;
    # anchor 8 px left of the centre, 16 above it
    ("AXEK0", [(dx, dy, t, 1) for dy, ts in ((1, (0xA0, 0xA2, 0xA4)), (17, (0xA6, 0xA8, 0xAA))) for dx, t in zip((-4, 4, 12), ts)]),
    ("AXEK1", [(dx, dy, t, 1) for dy, ts in ((1, (0xA0, 0xA2, 0xA4)), (17, (0xAC, 0xAE, 0x90))) for dx, t in zip((-4, 4, 12), ts)]),
    # its axe (type 0x27, pose 0x16): 4 turns of 4 frames, thrown left; anchor 8 px left of the centre, 8 above it
    ("KAXE0", [(0, 1, 0xB9, 65), (8, 1, 0xB7, 65)]),
    ("KAXE1", [(0, 1, 0xB7, 1), (8, 1, 0xB9, 1)]),
    ("KAXE2", [(0, 1, 0xB7, 129), (8, 1, 0xB9, 129)]),
    ("KAXE3", [(0, 1, 0xB9, 193), (8, 1, 0xB7, 193)]),
    # Death (object type 0x18, stage 15's boss, NES pose 0x58), facing left, 40 px wide; anchor 8 px left of the
    # centre, 24 above it
    ("DEATH", [(dx, dy, t, 1) for dy, row in ((1, ((-4, 0xD0), (4, 0xD2), (12, 0xD4), (20, 0xD6))),
                                              (17, ((-4, 0xD8), (4, 0xDA), (12, 0xDC))),
                                              (33, ((-12, 0xDE), (-4, 0xF0), (4, 0xF2), (12, 0xF4)))) for dx, t in row]),
    # its sickles (type 0x0B, pose 0x59): 4 turns of 3 frames, flying right; anchor 8 px left of the centre, 8 above it
    ("SICKLE0", [(0, 1, 0xF6, 3), (8, 1, 0xF8, 3)]),
    ("SICKLE1", [(0, 1, 0xFA, 3), (8, 1, 0xFC, 3)]),
    ("SICKLE2", [(0, 1, 0xF8, 195), (8, 1, 0xF6, 195)]),
    ("SICKLE3", [(0, 1, 0xFC, 195), (8, 1, 0xFA, 195)]),
]
BLOCK_POSES[6] = BLOCK_POSES[5] + [
    # stage 16's giant bat (object type 0x1E, NES pose 0x4A): wings out, then up, 9 frames each; anchor 8 px left of
    # the centre, 8 above it
    ("GBAT0", [(-16, 1, 0xD0, 3), (-8, 1, 0xD2, 3), (0, 1, 0xD4, 3), (0, 17, 0xD6, 3),
               (8, 1, 0xD4, 67), (8, 17, 0xD6, 67), (16, 1, 0xD2, 67), (24, 1, 0xD0, 67)]),
    ("GBAT1", [(-8, 1, 0xD8, 3), (0, 1, 0xDA, 3), (0, 17, 0xDC, 3), (8, 1, 0xDA, 67), (8, 17, 0xDC, 67), (16, 1, 0xD8, 67)]),
]
BLOCK_POSES[7] = BLOCK_POSES[5] + [
    # Dracula (object type 0x1D, stage 18's boss), facing left: anchor 8 px left of the centre, at the centre's y.
    # Standing (NES poses 0x23, 0x29) and with the cape open (0x2A), 24 and 32 px wide
    ("DRAC", [(-8, -23, 0xE0, 3), (-8, -7, 0xE6, 3), (-8, 9, 0xE8, 3), (0, -23, 0xE2, 3), (0, -7, 0xE6, 3), (0, 9, 0xE8, 3), (8, -23, 0xE4, 3), (8, -7, 0xE4, 3), (8, 9, 0xEA, 3)]),
    ("DRAC_OPEN", [(-8, -23, 0xE0, 3), (-8, -7, 0xE6, 3), (-8, 9, 0xE6, 3), (0, -23, 0xEC, 3), (0, -7, 0xF2, 3), (0, 9, 0xF8, 3), (8, -23, 0xEE, 3), (8, -7, 0xF4, 3), (8, 9, 0xF4, 3), (16, -23, 0xF0, 3), (16, -7, 0xF6, 3), (16, 9, 0xFA, 3)]),
    # its head (object type 4 in slot 8, pose 0x4E), 10 px left of the centre and 35 above it; flying off at the end of
    # the first fight (type 0x35): the same sprite
    ("DRAC_HEAD", [(-2, -34, 0xFC, 1)]),
    # the monster of the second fight (NES poses 0x36 standing, 0x31 crouching, 0x32 and 0x33 jumping low and high,
    # 0x34 landing, 0x35 spitting), 48 px wide
    ("MON", [(-16, -39, 0x80, 2), (-16, -23, 0x8C, 2), (-16, -7, 0xB4, 2), (-16, 9, 0xB8, 2), (-8, -39, 0x82, 2), (-8, -23, 0x8E, 2), (-8, -7, 0xB6, 2), (-8, 9, 0xBA, 2), (0, -39, 0x84, 2), (0, -23, 0x90, 2), (8, -39, 0x86, 2), (8, -23, 0x92, 2), (8, -7, 0xBC, 2), (16, -39, 0x88, 2), (16, -23, 0x94, 2), (16, -7, 0xBE, 2), (16, 9, 0xC0, 2), (24, -39, 0x8A, 2), (24, -23, 0x96, 2), (24, 9, 0xC2, 2)]),
    ("MON_CROUCH", [(-16, -39, 0x80, 2), (-16, -23, 0x8C, 2), (-16, -7, 0xB0, 2), (-8, -39, 0x82, 2), (-8, -23, 0x8E, 2), (-8, -7, 0xB2, 2), (0, -39, 0x84, 2), (0, -23, 0x90, 2), (0, -7, 0xB4, 2), (0, 9, 0xB8, 2), (8, -39, 0x86, 2), (8, -23, 0x92, 2), (8, -7, 0xB6, 2), (8, 9, 0xBA, 2), (16, -39, 0x88, 2), (16, -23, 0x94, 2), (24, -39, 0x8A, 2), (24, -23, 0x96, 2)]),
    ("MON_JUMP", [(-16, -55, 0x98, 2), (-16, -39, 0xA2, 2), (-16, -7, 0xB0, 2), (-8, -55, 0x9A, 2), (-8, -39, 0xA4, 2), (-8, -23, 0x8E, 2), (-8, -7, 0xB2, 2), (0, -39, 0xA6, 2), (0, -23, 0x90, 2), (0, -7, 0xB4, 2), (0, 9, 0xB8, 2), (8, -55, 0x9C, 2), (8, -39, 0xA8, 2), (8, -23, 0xAA, 2), (8, -7, 0xB6, 2), (8, 9, 0xBA, 2), (16, -55, 0x9E, 2), (16, -39, 0xAC, 2), (16, -23, 0xAC, 2), (24, -55, 0xA0, 2), (24, -39, 0x96, 2), (24, -23, 0xAE, 2)]),
    ("MON_HIGH", [(-16, -55, 0x98, 2), (-16, -39, 0xA2, 2), (-16, -7, 0xB0, 2), (-8, -55, 0x9A, 2), (-8, -39, 0xA4, 2), (-8, -23, 0x8E, 2), (-8, -7, 0xB2, 2), (0, -39, 0xA6, 2), (0, -23, 0x90, 2), (8, -55, 0x9C, 2), (8, -39, 0xA8, 2), (8, -23, 0xAA, 2), (8, -7, 0xB2, 66), (16, -55, 0x9E, 2), (16, -39, 0xAC, 2), (16, -23, 0xAC, 2), (16, -7, 0xB0, 66), (24, -55, 0xA0, 2), (24, -39, 0x96, 2), (24, -23, 0xAE, 2)]),
    ("MON_LAND", [(-16, -39, 0x80, 2), (-16, -23, 0x8C, 2), (-16, -7, 0xB0, 2), (-8, -39, 0x82, 2), (-8, -23, 0x8E, 2), (-8, -7, 0xB2, 2), (0, -39, 0x84, 2), (0, -23, 0x90, 2), (8, -39, 0x86, 2), (8, -23, 0x92, 2), (8, -7, 0xB2, 66), (16, -39, 0x88, 2), (16, -23, 0x94, 2), (16, -7, 0xB0, 66), (24, -39, 0x8A, 2), (24, -23, 0x96, 2)]),
    ("MON_SPIT", [(-16, -55, 0x98, 2), (-16, -39, 0xA2, 2), (-16, -7, 0xB4, 2), (-16, 9, 0xB8, 2), (-8, -55, 0x9A, 2), (-8, -39, 0x82, 2), (-8, -23, 0x8E, 2), (-8, -7, 0xB6, 2), (-8, 9, 0xBA, 2), (0, -39, 0x84, 2), (0, -23, 0x90, 2), (8, -55, 0x9C, 2), (8, -39, 0xA8, 2), (8, -23, 0xAA, 2), (8, -7, 0xBC, 2), (16, -55, 0x9E, 2), (16, -39, 0xAC, 2), (16, -23, 0xAC, 2), (16, -7, 0xBE, 2), (16, 9, 0xC0, 2), (24, -55, 0xA0, 2), (24, -39, 0x96, 2), (24, -23, 0xAE, 2), (24, 9, 0xC2, 2)]),
    # the pieces of Dracula's body when the monster comes out (type 0x21, pose 0x37), flying left
    ("DRAC_BIT", [(4, -7, 0x78, 2), (12, -7, 0x7A, 2)]),
]
# background tiles in front of the sprites (as the courtyard's gate, tools/level_to_md.py): stage 16's archway, where
# the NES game puts its 16x32 mask (tile $FE behind the background) at x 30, OAM y 96 during the cutscene. Room,
# then column, row, width, height in tiles
MASKS = {(16, 0): (3, 12, 3, 4)}


def chr_for(rom, stage, base, origin=None):
    """CHR-RAM after the stage's CHR set is loaded over base; origin (a dict) gets each loaded tile's ROM place:
    CHR index -> (bank, offset in the bank), where the SNES port keeps its 16-bit version of the tile"""
    chr_ = bytearray(base)
    lst = rom.word(0xFDBB + 2 * rom.rd(0xC8B0 + stage))
    while rom.rd(lst) != 0xFF:
        bank, src, dst, n = rom.rd(lst), rom.word(lst + 1), rom.word(lst + 3), rom.word(lst + 5)
        chr_[dst:dst + n] = bytes(rom.rd(src + i, bank) for i in range(n))
        if origin is not None:
            for k in range(0, n, 16):
                origin[(dst + k) // 16] = (bank, (src + k) & 0x3FFF)
        lst += 7
    return bytes(chr_)


def main():
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--block", type=int, default=2)
    ap.add_argument("--extracted", default=str(root / "tools/extracted"))
    ap.add_argument("--src", default=str(root / "src"))
    ap.add_argument("--inc", default=str(root / "inc"))
    a = ap.parse_args()
    ex = Path(a.extracted)
    data = Path(a.rom).read_bytes()
    rom = Rom(data)
    stages = BLOCKS[a.block]
    chr_ = (ex / "level1/chr.bin").read_bytes()
    origin = {}
    for st in sorted({16, stages[0]}) if stages[0] > 16 else (stages[0],):
        chr_ = chr_for(rom, st, chr_, origin)               # stage 18's set goes over stage 16's
    p0 = 0xCE28 + 19 * (a.block - 1)
    assert rom.rd(p0) == 0x3F and rom.rd(p0 + 18) == 0xFE
    pal = bytes(rom.rd(p0 + 2 + i) for i in range(16)) + (ex / "level1/palette.bin").read_bytes()[16:]
    fixed = json.loads((ex / "fixed_layout.json").read_text())
    nfixed = len(fixed)

    snes = root / "tools" / "extracted" / "snes"            # copied by tools/import_snes.py
    bgp, sprp = SNES_PAL[a.block]
    arts = [Art16(chr_, pal, (ex / "prg.bin").read_bytes(), snes, snes / bgp, snes / sprp, origin), ArtNES(chr_, pal)]

    # the SNES port's 16-bit mode replaces bank 4 (the rooms' layouts and tile groups, at the NES game's addresses)
    # with its own, which rearranges some of the scenery for its redrawn tiles: the 16-bit art gets its own map from
    # those (the collisions stay the NES game's)
    prg16 = bytearray(data[16:16 + data[4] * 16384])
    for lv, (lay, grp) in SNES_LAYOUTS.items():
        for addr, f in ((lay, "level-layout.bin"), (grp, "tile-groups.bin")):
            b = (snes / "level-layouts" / lv / f).read_bytes()
            prg16[4 * 16384 + addr - 0x8000:4 * 16384 + addr - 0x8000 + len(b)] = b
    rom16 = Rom(data[:16] + bytes(prg16))

    # the rooms, side by side
    rooms, wt, wp, wt16, wp16 = [], b"", b"", b"", b""
    assert sorted(ORDER[a.block]) == [(st, fl) for st in stages for fl in range(rom.floors(st)) if (st, fl) not in UNUSED]
    for st, fl in ORDER[a.block]:
            t, p, meta = rom.room(st, fl)
            x0 = FIRST_X.get((st, fl), (meta["first_page"] or 0) * 256)    # nothing left of it is shown
            rooms.append((st, fl, len(wt) // ROWS, x0, meta["columns"] - x0 // 8))
            wt += t[x0 // 8 * ROWS:]
            wp += p[x0 // 8 * ROWS:]
            t16, p16, meta16 = rom16.room(st, fl)
            assert len(t16) == len(t) and meta16["columns"] == meta["columns"]
            wt16 += t16[x0 // 8 * ROWS:]
            wp16 += p16[x0 // 8 * ROWS:]
    cols = len(wt) // ROWS
    room_x = {(st, fl): (COL0[a.block] + c0) * 8 - x0 for st, fl, c0, x0, _ in rooms}   # world x of the room's x 0

    # ---- stairs: the NES game's list of flight ends per stage ($FBEC + 2 * stage, read by bank 6 at $9CBD), two
    # bytes each: y & $F0 | floor << 2 | kind (0 foot of a flight rising to the right, 2 its top, 1 and 3 the same
    # rising to the left), then x & $F8 | screen. In a room, a flight's top is (by - ty) up and as much across, 8 px
    # less to the right. A foot without a top in its room starts a flight that goes on in the room above (floor 1):
    # the NES game swaps rooms when Simon's centre passes y 48 going up (he goes on at y 207) or y 208 going down,
    # keeping his x, so the lower half ends at y 48 and the upper half, ending at a top without a foot, starts at
    # y 208. Port flights: Simon's anchor (8 px left of his centre, 7 for a left flight) and head y (16 above it) at
    # the foot, in 8 px steps (the same as block 1's, which tools/level_to_md.py finds from the tiles).
    ends = {}
    for st in stages:
        p = rom.word(0xFBEC + 2 * st, 6)
        while rom.rd(p, 6):
            b0, b1 = rom.rd(p, 6), rom.rd(p + 1, 6)
            ends.setdefault((st, b0 >> 2 & 1), []).append((b0 & 3, b0 & 0xF0, (b1 & 7) * 256 + (b1 & 0xF8)))
            p += 2
    def across(kind, dy):                               # x from the foot to the top of a flight dy high
        return dy - 8 if kind & 1 == 0 else -dy
    stairs, halves = [], []
    for (st, fl), lst in sorted(ends.items()):
        tops = [e for e in lst if e[0] & 2]
        for kind, by, bx in (e for e in lst if not e[0] & 2):
            # (stage 17's flight from x 544, y 144 has its top at 608, not 600: Simon climbs it to 607, as the others)
            # the nearest top on the line (stage 17's flight from x 224, y 176 ends at y 80: (96, 48) is a top that
            # no flight reaches, Simon stops at 80)
            top = max((t for t in tops if t[0] == kind | 2 and t[1] < by
                       and t[2] - bx in (across(kind, by - t[1]), by - t[1] if kind == 0 else None)),
                      key=lambda t: t[1], default=None)
            if top: tops.remove(top)
            ty = top[1] if top else 48
            stairs.append([st, fl, kind, bx, by, ty, -1, -1])
            if not top: halves.append(("low", len(stairs) - 1))
        for kind, ty, tx in tops:
            if fl == 0: continue                        # no room below floor 0 to come from
            by = 208
            stairs.append([st, fl, kind & 1, tx - across(kind & 1, by - ty), by, ty, -1, -1])
            halves.append(("high", len(stairs) - 1))
    for which, i in halves:                             # join the halves: same stage, same x where they meet
        if which != "low": continue
        st, fl, kind, bx, by, ty = stairs[i][:6]
        x_top = bx + (by - ty if kind == 0 else -(by - ty))
        j = next(j for w, j in halves if w == "high" and stairs[j][0] == st and stairs[j][1] != fl
                 and stairs[j][2] == kind and stairs[j][3] == x_top)
        stairs[i][6], stairs[j][7] = j, i               # link_up, link_down
    # ---- wall candles: the NES game's object list per room ($D290 + 2 * stage -> a pointer per floor -> two bytes per
    # 64 px column, read by $D196 of the fixed bank as the screen scrolls). The second byte picks the column's candle
    # ($D6C6 + 2 * n, or $D7C6 + 2 * (n & $7F) when bit 7 is set): $FF + item code (else 0), maybe $FE, then x and y.
    # Its centre is at room x 64 * (column - 1) + x (the hall's candles come out where tools/candle_codes_true.json
    # has them, and stage 4's where the NES game shows them). Port: sprite x 4 px left of the centre, y 8 above it.
    def column_record(st, fl, c, byte):
        lp = rom.word(rom.word(0xD290 + 2 * st) + 2 * fl)
        r = rom.rd(lp + 2 * c + byte)
        return rom.word((0xD7C6 if r & 0x80 else 0xD6C6) + 2 * (r & 0x7F))
    candles = []
    for st, fl, c0, x0, nc in rooms:
        for c in range(1, (x0 // 8 + nc) // 8 + 1):
            rec = column_record(st, fl, c, 1)
            if rom.rd(rec) == 0: continue
            code = 0
            if rom.rd(rec) == 0xFF: code = rom.rd(rec + 1); rec += 2
            if rom.rd(rec) == 0xFE: rec += 1
            x = 64 * (c - 1) + rom.rd(rec)
            if x >= x0:
                candles.append((room_x[(st, fl)] + x - 4, rom.rd(rec + 1) - 8, code))

    # ---- the generators of the same list (first byte of each column, records at $D6C6 / $D7C6: kind, x, y with the
    # same placement as the candles; y is the centre). Kinds $40 + n put the NES object n there (8: the armour knight).
    gens = []
    for st, fl, c0, x0, nc in rooms:
        for c in range(1, (x0 // 8 + nc) // 8 + 1):
            rec = column_record(st, fl, c, 0)
            if rom.rd(rec) == 0: continue
            x = 64 * (c - 1) + rom.rd(rec + 1)
            if x >= x0:
                gens.append((room_x[(st, fl)] + x, rom.rd(rec + 2), rom.rd(rec)))

    port_stairs = [(room_x[(st, fl)] + bx - (8 if kind == 0 else 7), by - 16, (by - ty) // 8, 1 if kind == 0 else -1, lu, ld)
                   for st, fl, kind, bx, by, ty, lu, ld in stairs]

    # ---- palettes ----
    group_bg = lambda p: 0 if p == 0 else 1
    group_spr = lambda p: 2 if p == 0 else 3
    bg_uses = Counter((wt[i], wp[i]) for i in range(len(wt)) if i % ROWS >= 4)
    bg_uses += Counter((wt16[i], wp16[i]) for i in range(len(wt16)) if i % ROWS >= 4)
    for e in fixed:
        if e and e[0] == "bg":
            bg_uses[(e[1], e[2])] += 32                         # the HUD is always on screen
    spr_key = lambda t, at: ((256 if t & 1 else 0) + (t & 0xFE), at & 3)   # 8x16 sprite: bit 0 picks the table
    block_keys = sorted({spr_key(t, at) for _, pose in BLOCK_POSES[a.block] for _, _, t, at in pose})
    # each of the block's background tiles goes to whichever of the two MD background palettes draws it best (in
    # both arts, which share the tile map), rather than NES palette 0 to one and 1 to 3 to the other: the 16-bit art
    # has some 35 colours in NES palettes 1 to 3 and a dozen in 0. The fixed tiles (the HUD's) keep their palette.
    fixed_bg = {(e[1], e[2]) for e in fixed if e and e != "mask" and e[0] == "bg"}
    # the block's own sprites (its enemies: 35 to 40 colours in the 16-bit art) may take any of the four palettes, the
    # background ones too: a sprite's pixel counts SPR_W map cells (a guess at how much an enemy shows)
    SPR_W = 16
    keys = {**{k: n for k, n in bg_uses.items()}, **{("s",) + k: SPR_W for k in block_keys}}
    def pixels(art, key):
        if key[0] == "s":
            return [c for part in (0, 1) for c in art.spr_tile(key[1] + part, key[2])]
        return art.bg_tile(*key)
    options = lambda key: (0, 1, 2, 3) if key[0] == "s" else (0, 1)
    assign = {}
    gk = lambda t, p: assign.get((t, p), group_bg(p))
    gs = lambda ci, p: assign.get(("s", ci, p), group_spr(p))
    def all_weights(art):
        weights = [Counter() for _ in range(4)]
        for key, n in keys.items():
            for c in pixels(art, key):
                if c: weights[assign[key]][c] += n
        for e in fixed:
            if isinstance(e, list) and e[0] not in ("bg", "x"):
                for c in art.spr_tile(e[0], e[1]):
                    if c: weights[group_spr(e[1])][c] += SPR_W
        return weights
    px_cache = {}
    def refine():                       # move tiles to the palette that draws them best until none moves; total cost
        for _ in range(8):
            pals = [[pack_palette(w)[0] + [art.backdrop()] for w in all_weights(art)] for art in arts]
            costs = {}
            for key, n in keys.items():
                if key not in px_cache: px_cache[key] = [[c for c in pixels(art, key) if c] for art in arts]
                costs[key] = {g: n * sum(min(_dist(c, q) for q in pals[k][g]) for k in range(len(arts))
                                         for c in px_cache[key][k]) for g in options(key)}
            moved = 0
            for key, cg in costs.items():
                if key in fixed_bg: continue
                g = min(cg, key=lambda g: (cg[g], g != assign[key]))
                if g != assign[key]: assign[key] = g; moved += 1
            if not moved: break
        return sum(cg[assign[key]] for key, cg in costs.items())
    best = None
    from itertools import product
    for first in ((0,), (0, 1), (0, 2), (0, 3)):     # NES background palettes starting in MD palette 0
        for spr in product((0, 1, 3), repeat=3):      # and where NES sprite palettes 1 to 3 start
            assign.clear()
            assign.update({k: 0 if k[1] in first else 1 for k in bg_uses})
            assign.update({("s",) + k: spr[k[1] - 1] if k[1] else 2 for k in block_keys})
            for k in fixed_bg: assign[k] = group_bg(k[1])
            total = refine()
            if best is None or total < best[0]: best = (total, dict(assign))
    assign.clear(); assign.update(best[1])
    def art_palettes(art):
        weights = all_weights(art)
        packed = [pack_palette(w) for w in weights]
        backdrop = art.backdrop()
        colors = []
        for pal_list, _ in packed:
            row = [backdrop] + pal_list
            colors += row + [backdrop] * (16 - len(row))          # (r, g, b[, NES index]): words at writing
        return packed, colors, [f"{len(w)}->{len(p_[0])}" for w, p_ in zip(weights, packed)]
    packs = [art_palettes(art) for art in arts]

    # ---- tiles: the fixed ones first, at block 1's indices ----
    def encode(px, index):
        out = []
        for y in range(8):
            v = 0
            for x in range(8):
                c = px[y * 8 + x]
                v = (v << 4) | (index[c] if c else 0)
            out.append(v)
        return tuple(out)
    def encoded(pixels, g):        # the tile in every art: pixels(art) gives its pixels, g is its MD palette
        return tuple(encode(pixels(art), packs[k][0][g][1]) for k, art in enumerate(arts))
    def mask(packed):
        dark = 1 + min(range(len(packed[2][0])), key=lambda i: sum(packed[2][0][i]))
        return (int(f"{dark:X}" * 8, 16),) * 8
    empty = ((0,) * 8,) * len(arts)
    tiles = []
    for i, e in enumerate(fixed):
        if i == 0 or e is None:
            tiles.append(empty)
        elif e == "mask":
            tiles.append(tuple(mask(pk[0]) for pk in packs))
        elif e[0] == "bg":
            tiles.append(encoded(lambda art: art.bg_tile(e[1], e[2]), group_bg(e[2])))
        elif e[0] == "x":                                          # the font's X, drawn by tools/art.py
            tiles.append(encoded(lambda art: x_glyph(art, e[1]), group_bg(e[1])))
        else:
            tiles.append(encoded(lambda art: art.spr_tile(e[0], e[1]), group_spr(e[1])))
    # then the block's own sprites (two tiles each, top and bottom)
    sidx = {}
    for ci, p_ in block_keys:
        sidx[(ci, p_)] = len(tiles)
        tiles.append(encoded(lambda art: art.spr_tile(ci, p_), gs(ci, p_)))
        tiles.append(encoded(lambda art: art.spr_tile(ci + 1, p_), gs(ci, p_)))
    poses = []
    for name, pose in BLOCK_POSES[a.block]:
        poses.append((name, [(dx, dy, (gs(*spr_key(t, at)) << 13) | (0x800 if at & 0x40 else 0) | (0x1000 if at & 0x80 else 0),
                               sidx[spr_key(t, at)]) for dx, dy, t, at in pose]))
    tile_index = {empty: 0}
    bg_word = {}
    def bg_tile(t, p):
        if (t, p) not in bg_word:
            g = gk(t, p)
            key = encoded(lambda art: art.bg_tile(t, p), g)
            if key not in tile_index:
                tile_index[key] = len(tiles)
                tiles.append(key)
            bg_word[(t, p)] = tile_index[key] | (g << 13)
        return bg_word[(t, p)]
    def world_map(wt, wp):
        level = [0] * (cols * ROWS)
        for c in range(cols):
            for r in range(6, ROWS):                            # rows above 6 are the HUD's
                level[r * cols + c] = bg_tile(wt[c * ROWS + r], wp[c * ROWS + r])
        for st, fl, c0, x0, _ in rooms:
            if (st, fl) in MASKS:
                mc, mr, mw, mh = MASKS[(st, fl)]
                for c in range(c0 + mc - x0 // 8, c0 + mc - x0 // 8 + mw):
                    for r in range(mr, mr + mh):
                        level[r * cols + c] |= 0x8000
        return level
    level_nes = world_map(wt, wp)
    level = world_map(wt16, wp16)
    nbg = len(tiles) - nfixed

    tile = lambda c, r: wt[c * ROWS + r] if 0 <= r < ROWS else 0
    wall = [sum(1 << r for r in range(6, ROWS) if tile(c, r) in SOLID) for c in range(cols)]
    solid = [sum(1 << r for r in range(6, ROWS) if tile(c, r) in SOLID and tile(c, r - 1) not in SOLID)
             for c in range(cols)]

    n = a.block
    src, inc = Path(a.src), Path(a.inc)
    with open(src / f"block{n}.c", "w") as f:
        f.write(f'// generated by tools/block_to_md.py - do not edit\n#include "block{n}.h"\n\n')
        for k, art in enumerate(arts):
            f.write(f"const u32 block{n}_tiles{ART_SUFFIX[art.name]}[{len(tiles) * 8}] = {{\n")
            for t in tiles:
                f.write("    " + ", ".join(f"0x{v:08X}" for v in t[k]) + ",\n")
            f.write("};\n\n")
        for suffix, lv in (("", level), ("_nes", level_nes)):
            f.write(f"const u16 block{n}_map{suffix}[{len(lv)}] = {{\n")
            for r in range(ROWS):
                f.write("    " + ",".join(str(v) for v in lv[r * cols:(r + 1) * cols]) + ",\n")
            f.write("};\n\n")
        f.write(f"const u32 block{n}_solid[{cols}] = {{" + ", ".join(f"0x{v:08X}" for v in solid) + "};\n\n")
        f.write(f"const u32 block{n}_wall[{cols}] = {{" + ", ".join(f"0x{v:08X}" for v in wall) + "};\n\n")
        for k, art in enumerate(arts):
            f.write(f"const u16 block{n}_palette{ART_SUFFIX[art.name]}[64] = {{" + ", ".join(f"0x{md_word(c):04X}" for c in packs[k][1]) + "};\n\n")
            if art.name == "nes":     # each colour's NES index, for the SNES port's NES palettes (0xFF: none)
                f.write(f"const u8 block{n}_palette_nesidx[64] = {{" + ", ".join(str(nes_index(c)) for c in packs[k][1]) + "};\n\n")
        f.write(f"const Stair block{n}_stairs[BLOCK{n}_STAIRS] = {{" + ", ".join(
            f"{{{x}, {y}, {k}, {d}, {lu}, {ld}}}" for x, y, k, d, lu, ld in port_stairs) + "};\n\n")
        f.write(f"const WallCandle block{n}_wcandles[BLOCK{n}_WCANDLES] = {{" + ", ".join(
            f"{{{x}, {y}, {c}}}" for x, y, c in candles) + "};\n\n")
        f.write(f"const ObjGen block{n}_gens[BLOCK{n}_GENS] = {{" + ", ".join(
            f"{{{x}, {y}, 0x{k:02X}}}" for x, y, k in gens) + "};\n\n")
        for name, e in poses:
            f.write(f"static const SimonSprite b{n}_{name.lower()}[{len(e)}] = {{" + ", ".join(
                f"{{{dx}, {dy}, 0x{at:04X}, {t}}}" for dx, dy, at, t in e) + "};\n")
        f.write(f"const SimonPose block{n}_poses[BLOCK{n}_POSES] = {{" + ", ".join(
            f"{{{len(e)}, b{n}_{name.lower()}}}" for name, e in poses) + "};\n")
    with open(inc / f"block{n}.h", "w") as f:
        f.write(f"""// generated by tools/block_to_md.py - do not edit
#ifndef BLOCK{n}_H
#define BLOCK{n}_H
#include <genesis.h>
#include "level.h"

#define BLOCK{n}_COL0      {COL0[a.block]}    /* world column of the block's first column */
#define BLOCK{n}_COLS      {cols}
#define BLOCK{n}_STAIRS    {len(port_stairs)}
#define BLOCK{n}_WCANDLES  {len(candles)}
#define BLOCK{n}_GENS      {len(gens)}
#define BLOCK{n}_POSES     {len(poses)}
""" + "".join(f"#define B{n}_{name:<12} {i}\n" for i, (name, _) in enumerate(poses)) + f"""
#ifndef OBJGEN_DEFINED
#define OBJGEN_DEFINED
// a generator of the NES game's object list: world x and centre y of where it acts, its kind (see block_to_md.py)
typedef struct {{ s16 x; u8 y, kind; }} ObjGen;
#endif
#define BLOCK{n}_TILES     {len(tiles)}
""")
        for st, fl, c0, x0, nc in rooms:
            f.write(f"#define ROOM_{st}_{fl}_COL0   {c0}    /* world column of the NES room's x {x0}, {nc} columns */\n")
        f.write(f"""
extern const u32 block{n}_tiles[];          // 16-bit art
extern const u32 block{n}_tiles_nes[];      // NES art, same tiles at the same indices
extern const u16 block{n}_map[];            // 16-bit art: the SNES port's own layouts
extern const u16 block{n}_map_nes[];        // NES art
extern const u32 block{n}_solid[BLOCK{n}_COLS];
extern const u32 block{n}_wall[BLOCK{n}_COLS];
extern const u16 block{n}_palette[64];
extern const u16 block{n}_palette_nes[64];
extern const u8 block{n}_palette_nesidx[64];
extern const Stair block{n}_stairs[BLOCK{n}_STAIRS];
extern const WallCandle block{n}_wcandles[BLOCK{n}_WCANDLES];
extern const ObjGen block{n}_gens[BLOCK{n}_GENS];
extern const SimonPose block{n}_poses[BLOCK{n}_POSES];

#endif
""")
    print(f"block {n} (stages {stages}): {cols} cols, {nbg} bg tiles + {nfixed} fixed = {len(tiles)}; colours per MD "
          f"palette (distinct->kept) {', '.join(f'{art.name} {pk[2]}' for art, pk in zip(arts, packs))}; "
          f"rooms {[(st, fl, c0) for st, fl, c0, _, _ in rooms]}")
    if getattr(arts[0], "fallbacks", 0):
        print(f"note: {arts[0].fallbacks} tiles had no 16-bit version and use the NES art")


if __name__ == "__main__":
    main()

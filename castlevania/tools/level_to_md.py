#!/usr/bin/env python3
"""Turn the recorded level (record_level.py) and Simon (record_simon.py) into SGDK data.

usage: level_to_md.py [--rom ROM.nes] [--level DIR] [--simon JSON] [--src DIR] [--inc DIR]
Writes src/level.c and inc/level.h. Run with the venv python (imports helpers from nes_dump.py).

Both arts (see art.py) are written: the redrawn 16-colour tiles (level_tiles, level_palette) and the original NES
ones (level_tiles_nes, level_palette_nes), for the GRAPHICS option. Tiles are shared out by the pair (16-bit, NES)
so that one tile map, one set of poses and the same tile counts serve both.

Palettes: PAL0/PAL1 = background (NES palette 0 / NES palettes 1-3), PAL2/PAL3 = sprites
(NES sprite palette 0 / 1-3). Colours beyond 15 per MD palette are merged with their closest neighbours.
The picture is centred on the 320x224 MD screen (x + 32, y - 8), see main.c.
"""
import argparse, json
from collections import Counter
from pathlib import Path
from art import ART_SUFFIX, Art16, ArtNES, md_word, nes_index, pack_palette, snes_nes_palettes, x_glyph

ROWS = 30
# Parallax: the courtyard's tree canopy repeats every 32 columns, so it can live on the far plane B (a 32-column
# strip that wraps) and scroll slower than the foreground. Only these tile ids, in these rows and only in the
# courtyard columns, are moved to plane B; everything else stays on plane A.
CANOPY = {47, 18, 22, 23, 52, 64, 25, 42}
COURT_COLS = 64
FONT_TILES = list(range(0xE0, 0xFA)) + list(range(0xD0, 0xDA)) + [0xDD]   # NES font: A-Z, 0-9, '-' (no '.' in it)
GO_ROW0 = 6                   # first NES row of the game over screen kept (the HUD stays above it)
BACK_ROW0, BACK_ROWS = 6, 14
# The castle gate: the courtyard's last screen (world x 512-767), which the hall replaces at the same scroll in the NES
# game, so it is kept apart (gate_tiles.bin from record_level.py). Its first 16 columns hold the same canopy as the
# courtyard. Simon walks into the archway behind black mask sprites (tile $FE, behind the background) that the game
# puts at x 704-719, y 160-191: on the MD the gate tiles under that box get the high priority bit, and a low priority
# mask sprite in front of Simon does the same job.
GATE_COL0, GATE_COLS, GATE_BACK_COLS = 64, 32, 16
GATE_MASK = (24, 20, 2, 4)    # gate column, row, width, height (tiles) of the mask box
# tile 61 is a hanging leaf tip: on row 19 it belongs to the canopy strip, and on row 15 (above the statue) it is a
# stray tip that is removed from plane A; the strip itself is filled with plain canopy there
is_canopy = lambda t, r: t in CANOPY or (t == 61 and r == 19)               # tiles the strip is built from
leaves_front = lambda t, r: is_canopy(t, r) or (t == 61 and r == 15)       # tiles removed from plane A
SOLID_TOP = {104, 106, 107, 97, 101}   # NES tile ids of surfaces Simon can stand on (courtyard cobbles, castle bricks,
                                       # the floor bricks notched by a flight going down)
CURL_LIFT = 4                 # px the curled jump pose is drawn above Simon's position (NES RAM $354 vs OAM)
WALL = SOLID_TOP | {96, 102, 105}   # whole blocks (the tiles under those tops too): Simon cannot walk into them
# Stages 2 and 3 (record_rooms.py), appended to the world after the hall: stage 2's upper room, then stage 3 (both
# continue the hall through a door, so they follow it), then stage 2's underground (reached by stairs only)
ROOMS = [("room_2_1", "ST2_COL0"), ("room_3_0", "ST3_COL0"), ("room_2_0", "UNDER_COL0")]
# stairs: right-rising flights are chains of (12, 13, 14) tile triples going up one row per column; left-rising ones are
# chains of tile 20 (the left end of each step) going up one row per column to the left
STAIR_R, STAIR_L = (12, 13, 14), 20


def main():
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", default=str(root / "tools/extracted/candle_codes_true.json"), help="item code per wall candle")
    ap.add_argument("--rooms-candles", default=str(root / "tools/extracted/candles_rooms.json"), help="wall candles of stages 2 and 3")
    ap.add_argument("--stairs", default=str(root / "tools/extracted/stairs.json"))
    ap.add_argument("--screens", default=str(root / "tools/extracted/screens"), help="tools/record_screens.py output")
    ap.add_argument("--level", default=str(root / "tools/extracted/level1"))
    ap.add_argument("--simon", default=str(root / "tools/extracted/simon.json"))
    ap.add_argument("--src", default=str(root / "src"))
    ap.add_argument("--inc", default=str(root / "inc"))
    a = ap.parse_args()
    lv = Path(a.level)
    wt, wp = (lv / "world_tiles.bin").read_bytes(), (lv / "world_pal.bin").read_bytes()
    chr_, pal = (lv / "chr.bin").read_bytes(), (lv / "palette.bin").read_bytes()
    room_col0 = {}
    for name, define in ROOMS:
        room_col0[define] = len(wt) // ROWS
        wt += (lv / f"{name}_tiles.bin").read_bytes()
        wp += (lv / f"{name}_pal.bin").read_bytes()
    cols = len(wt) // ROWS
    gt, gp = (lv / "gate_tiles.bin").read_bytes(), (lv / "gate_pal.bin").read_bytes()
    simon = json.loads(Path(a.simon).read_text())
    stair_data = json.loads(Path(a.stairs).read_text())
    # the game over screen below the HUD (NES rows 6-29): its text and the heart cursor, in the HUD's colours
    go_nt = (Path(a.screens) / "gameover_nt.bin").read_bytes()
    go_cursor = json.loads((Path(a.screens) / "screens.json").read_text())["gameover"]["cursor"]

    snes = root / "tools" / "extracted" / "snes"            # copied by tools/import_snes.py
    prg = (lv.parent / "prg.bin").read_bytes()
    arts = [Art16(chr_, pal, prg, snes, snes / "level-layouts/level-1/palette.bin",
                  snes / "16bit-tiles/sprite_16bit_palette_02.bin"),
            ArtNES(chr_, pal)]                                          # the order of ARTS in src/main.c

    jump = simon["jump"]
    # the curled pose already carries +8 in its own dy, so remove it from the trajectory; but the NES game draws the
    # curled Simon 4 px above his position (its $354), so his position while curled is 4 px lower than the drawing
    # (CURL_LIFT, drawn back up in src/main.c)
    curl_dy = min(e[1] for e in simon["poses"]["crouch"]) - CURL_LIFT
    jump_dy = [top - (curl_dy if curled else 0) for top, curled in jump]
    jump_curled = [curled for _, curled in jump]
    # candle objects, as observed in the NES game (see tools/record_simon.py and the drop experiments in the log):
    # sprite = (dx, dy, tile, attr) relative to the object, 8x16 sprites, OAM y of the brazier head is 160
    brazier = [[(0, 0, flame, 3), (8, 0, flame, 67), (0, 16, 0x9B, 2), (8, 16, 0x9B, 66)] for flame in (0x97, 0x99)]
    sparkle = [(0, 8, 0x70, 3)]
    items = [  # 0 large heart, 1 whip upgrade, 2 dagger (sub-weapon)
        [(0, 0, 0xBF, 3), (8, 0, 0xBF, 67)],
        [(0, 0, 0xC1, 3), (8, 0, 0xC3, 3)],
        [(0, 0, 0xBD, 194), (8, 0, 0xBB, 194)],
    ]
    raw_poses = {n: s_ for n, s_ in simon["poses"].items()}
    sp = stair_data["poses"]
    def to_right_facing(pose):      # recorded facing left (attr without the flip bit): mirror it around the 16 px body
        x0 = min(e[0] for e in pose)
        return sorted([8 - (dx - x0), dy, t, at ^ 0x40] for dx, dy, t, at in pose)
    raw_poses["stair_up_a"] = sp["up_a"]
    raw_poses["stair_up_b"] = sp["up_b"]
    raw_poses["stair_down_b"] = to_right_facing(sp["down_poses"][1])
    raw_swhip = [(w["frames"], w["sprites"]) for w in stair_data["whip"]]
    raw_swhip2 = [(w["frames"], w["sprites"]) for w in stair_data["whip2"]]
    raw_whip = [(w["frames"], w["sprites"]) for w in simon["whip"]]
    raw_whip2 = [(w["frames"], w["sprites"]) for w in simon["whip2"]]
    raw_cwhip = [(w["frames"], w["sprites"]) for w in simon["cwhip"]]
    raw_cwhip2 = [(w["frames"], w["sprites"]) for w in simon["cwhip2"]]
    # level 3 (long chain): the NES cycles the sprite palette of the whip (handle and chain) every frame
    # (0, 1, 2, 3), so each recorded frame is its own phase. Set back to their level 2 palettes they fold into the
    # usual phases; the port keeps one copy of the tables per palette and picks one by the frame counter.
    CYCLED = {44: 0, 70: 1, 72: 1, 86: 1, 88: 1, 106: 1, 108: 1}   # tile: its palette in the level 2 whip
    def fold(frames, v=None):
        out = []
        for fr, sp_ in ((w["frames"], w["sprites"]) for w in frames):
            sp_ = [[dx, dy, t, (at & ~3) | CYCLED[t] if t in CYCLED else at] for dx, dy, t, at in sp_]
            if out and out[-1][1] == sp_: out[-1] = (out[-1][0] + fr, sp_)
            else: out.append((fr, sp_))
        return out
    def cycled(phases, v):
        return [(fr, [[dx, dy, t, (at & ~3) | v if t in CYCLED else at] for dx, dy, t, at in sp_]) for fr, sp_ in phases]
    raw_whip3, raw_cwhip3 = fold(simon["whip3"]), fold(simon["cwhip3"])
    def longer(phases):   # level 3 = level 2 with the tip pushed 16 px further and two chain links in its place,
        out = []          # as measured standing and crouching; the stairs were not recorded at level 3
        for fr, sp_ in phases:
            tip = [e for e in sp_ if e[2] == 106]
            sp_ = [e for e in sp_ if e[2] != 106] + [[e[0] + k, e[1], 108 if k < 16 else 106, e[3]] for e in tip for k in (0, 8, 16)]
            out.append((fr, sp_))
        return out
    assert [(f, sorted(x)) for f, x in longer(raw_whip2)] == [(f, sorted(x)) for f, x in raw_whip3], "whip3 != whip2 + 16 px"
    assert [(f, sorted(x)) for f, x in longer(raw_cwhip2)] == [(f, sorted(x)) for f, x in raw_cwhip3], "cwhip3 != cwhip2 + 16 px"
    # tiles of the whip itself (normal and chain whip); throwing a sub-weapon plays the same swing without them
    whip_tiles = {30, 32, 36, 38, 46, 48, 70, 72, 86, 88, 106, 108}
    def no_whip(phases):
        return [(fr, [e for e in s_ if e[2] not in whip_tiles]) for fr, s_ in phases]
    for sw in (raw_swhip, raw_swhip2):  # only 3 phases were recorded on the stairs: end with 1 frame of the arm out
        while len(sw) < len(raw_whip):
            sw.append((1, no_whip(sw[-1:])[0][1]))
    raw_swhip3 = longer(raw_swhip2)
    raw_whip3, raw_cwhip3, raw_swhip3 = ([cycled(ph, v) for v in range(4)] for ph in (raw_whip3, raw_cwhip3, raw_swhip3))
    raw_throw, raw_sthrow = no_whip(raw_whip), no_whip(raw_swhip)
    zombie = [  # facing left; mirrored at run time for the other direction
        [(0, 0, 0x80, 1), (8, 0, 0x82, 1), (0, 16, 0x84, 1), (8, 16, 0x86, 1)],
        [(0, 1, 0x80, 1), (8, 1, 0x82, 1), (0, 17, 0x88, 1), (8, 17, 0x8A, 1)],
    ]
    # HUD sub-weapon frame, drawn with sprites by the NES game (anchor = top-left sprite, OAM y 22)
    hudbox = [(0, 0, 0xFB, 3), (8, 0, 0xFD, 3), (16, 0, 0xFD, 3), (24, 0, 0xFB, 67),
              (0, 16, 0x9D, 3), (8, 20, 0xFD, 3), (16, 20, 0xFD, 3), (24, 16, 0x9D, 67)]
    wall_candle = [[(0, 0, 0x40, 3)], [(0, 0, 0x50, 3)]]          # two flame frames, one 8x16 sprite each
    # black panther: sprites in a row, drawn in a 32 px box facing left; the right-facing poses are mirrored here
    def panther(tiles, w, attr=3):
        left = [(32 - w + 8 * i, 0, t, attr) for i, t in enumerate(tiles)]
        return left, [(24 - dx, dy, t, at ^ 0x40) for dx, dy, t, at in left]
    pan = [panther((0xB0, 0xB2, 0xB4), 24), panther((0xB8, 0xBA, 0xBC, 0xBE), 32),
           panther((0xC0, 0xC2, 0xC4, 0xC6), 32), panther((0xC8, 0xCA, 0xCC, 0xCE), 32)]
    panther_poses = [p_[0] for p_ in pan] + [p_[1] for p_ in pan]     # 0-3 facing left, 4-7 facing right
    flame = [[(0, 0, t, 3)] for t in (0x91, 0x93, 0x95)]            # burning effect when a candle is destroyed
    small_heart = [(0, 0, 0x9F, 3)]                                  # what a whip candle drops once the whip is upgraded
    money = [[(0, 0, 0x60, at), (8, 0, 0x62, at)] for at in (1, 2, 3)]      # purple 400, blue 700, white 100 (NES scores)
    rosary = [(0, 0, 0xAD, 2), (8, 0, 0xAF, 2)]
    holy = [(0, 0, 0xA1, 2), (8, 0, 0xA3, 2)]
    double = [(0, 0, 0xA5, 2), (8, 0, 0xA7, 2)]
    bottle = [(0, 0, 0x76, 2)]                                       # holy water in flight
    # the door between stages, drawn with sprites while it is open (the background column of the closed door is
    # cleared meanwhile): half open, then wide open; anchor = top-left sprite, OAM y 64 (observed in the NES game)
    door_half = [(0, 0, 0x77, 67), (0, 16, 0x7B, 67), (0, 32, 0x7B, 67), (8, 0, 0x75, 67), (8, 16, 0x79, 67), (8, 32, 0x79, 67)]
    door_open = [(dx, dy, t, 67) for dx, top in ((0, 0x87), (8, 0x87), (16, 0x85)) for dy, t in ((0, top), (16, 0x7B), (32, 0x7B))]
    # sub-weapons of stages 2 and 3 (tools/record_subweapons.py; item = what lies on the floor and shows in the HUD box):
    # the axe spins through 4 poses and the cross through 3, 4 frames each; anchor = 8 px left of the centre, OAM y
    # 8 above it. Potion (item code 14) and stopwatch (15) as dropped by a candle with the code forced.
    axe = [[(0, 0, a, at), (8, 0, b, at)] for a, b, at in ((0xB7, 0xB9, 1), (0xB9, 0xB7, 65), (0xB9, 0xB7, 193), (0xB7, 0xB9, 129))]
    cross = [[(0, 0, a, at), (8, 0, b, at2)] for a, b, at, at2 in ((0x4A, 0x4A, 2, 66), (0x52, 0x54, 2, 2), (0x54, 0x52, 66, 66))]
    potion = [(0, 0, 0x42, 0), (8, 0, 0x44, 0)]
    watch = [(0, 0, 0x89, 2), (8, 0, 0x8B, 2)]
    # enemies of stages 2 and 3, as the NES game draws them facing left (mirrored at run time); anchor = 8 px left of
    # the centre, OAM y 8 (bat) or 16 (fishman) above it. Bat: 3 wing poses (the game shows 1, 2, 3, 2, 9 frames
    # each); fishman: two walking poses and the one it fires from; its fireball (tile facing right, so two poses) and
    # the drops of its splash (anchor 4 px left of the centre)
    bat = [[(0, 0, a, 3), (8, 0, a + 2, 3)] for a in (0x90, 0x94, 0x98)]
    fish = [[(0, 0, 0xA0, 3), (8, 0, 0xA2, 3), (0, 16, b, 3), (8, 16, b + 2, 3)] for b in (0xA4, 0xA8)]
    fish.append([(0, 1, 0xAC, 3), (8, 1, 0xAE, 3), (0, 16, 0x8C, 3), (8, 16, 0x8E, 3)])
    fire = [[(0, 0, 0x68, 3)], [(0, 0, 0x68, 67)]]
    drop = [(0, 0, 0x9E, 1)]
    # the boss of stage 3 (phantom bat, NES object 0x19), symmetric so never mirrored; anchor = 24 px left of the
    # centre, OAM y 8 above it: asleep, then two wing poses (8 frames each). Its death flames (anchor 12 px left of
    # the centre, 16 above it after the NES game moves it 8 px down) and the orb (anchor 8 px left, 8 above)
    boss = [[(16, 0, 0xDE, 3), (24, 0, 0xDE, 67)],
            [(0, 0, 0xD0, 3), (8, 0, 0xD2, 3), (16, 0, 0xD4, 3), (24, 0, 0xD4, 67), (32, 0, 0xD2, 67), (40, 0, 0xD0, 67),
             (16, 16, 0xD6, 3), (24, 16, 0xD6, 67)],
            [(8, 0, 0xD8, 3), (16, 0, 0xDA, 3), (24, 0, 0xDA, 67), (32, 0, 0xD8, 67), (16, 16, 0xDC, 3), (24, 16, 0xDC, 67)]]
    boss_flame = [[(dx, dy, t, 3) for dy in (0, 16) for dx in (0, 8, 16)] for t in (0x91, 0x93, 0x95)]
    orb = [[(0, 0, t, 3), (8, 0, t, 67)] for t in (0x5A, 0x5C)]
    # what breakable blocks hide or leave: the pot roast (item code 5) and a piece of the broken block
    roast = [(0, 0, 0x64, 3), (8, 0, 0x66, 3)]
    debris = [(0, 0, 0x74, 1)]
    # the hidden treasures (NES table at $FC38): the 1000 point money bag and the 1UP, whose palette cycles through
    # the 4 sprite palettes (the NES game's $338, every 2 frames); anchor = 8 px left of the centre, OAM y 8 above it.
    # Once taken, the bag's '1000' (pose $63 of $A7B8, set every frame of state 5 at $A574), palettes still cycling
    treasure = [[(0, 0, a, p), (8, 0, a + 2, p)] for a in (0x60, 0xB1) for p in range(4)]
    treasure += [[(0, 0, 0xC9, p), (8, 0, 0xC7, p)] for p in range(4)]
    raw_objs = (brazier + [sparkle] + items + zombie + [hudbox] + wall_candle + panther_poses + flame + [small_heart]
                + money + [rosary, holy, double, bottle, door_half, door_open] + axe + cross + [potion, watch]
                + bat + fish + fire + [drop] + boss + boss_flame + orb + [roast, debris] + treasure)

    # ---- pass 1: which (tile, palette) pairs are used, to allocate the 4 MD palettes ----
    hud_pal = wp[23 * ROWS + 3]       # palette of the heart counter digits (NES tile ids 208..217 are '0'..'9')
    bg_uses = Counter((wt[c * ROWS + r], wp[c * ROWS + r]) for c in range(cols) for r in range(ROWS))
    bg_uses.update((gt[c * ROWS + r], gp[c * ROWS + r]) for c in range(GATE_COLS) for r in range(ROWS))
    for d in range(10):
        bg_uses[(208 + d, hud_pal)] += 1
    text_pal, heart_pal = wp[0 * ROWS + 2], wp[21 * ROWS + 3]      # the S of SCORE, the heart of the HUD
    go_pal = lambda t: heart_pal if t == 0xDC else text_pal
    go_cells = go_nt[GO_ROW0 * 32:30 * 32]
    for t in FONT_TILES:
        bg_uses[(t, text_pal)] += 1
    for t in go_cells:
        if t:
            bg_uses[(t, go_pal(t))] += 1
    def spr_key(t, at):                # 8x16 sprite: bit 0 of the tile id picks the pattern table
        return ((256 if t & 1 else 0) + (t & 0xFE), at & 3)
    all_sprites = [e for sp_ in raw_poses.values() for e in sp_] + [e for _, sp_ in raw_whip + raw_whip2 + raw_cwhip + raw_cwhip2 + raw_swhip + raw_swhip2 + sum(raw_whip3 + raw_cwhip3 + raw_swhip3, []) for e in sp_] \
        + [e for sp_ in raw_objs for e in sp_]
    spr_uses = Counter(spr_key(t, at) for _, _, t, at in all_sprites)

    group_bg = lambda p: 0 if p == 0 else 1
    group_spr = lambda p: 2 if p == 0 else 3
    def art_palettes(art):
        weights = [Counter() for _ in range(4)]
        for (t, p), n in bg_uses.items():
            for c in art.bg_tile(t, p):
                if c: weights[group_bg(p)][c] += n
        for (ci, p), n in spr_uses.items():
            for part in (0, 1):
                for c in art.spr_tile(ci + part, p):
                    if c: weights[group_spr(p)][c] += 1
        packed = [pack_palette(w) for w in weights]
        backdrop = art.backdrop()
        colors = []
        for pal_list, _ in packed:
            row = [backdrop] + pal_list
            colors += row + [backdrop] * (16 - len(row))          # (r, g, b[, NES index]): words at writing
        return packed, colors, [f"{len(w)}->{len(p_[0])}" for w, p_ in zip(weights, packed)]
    packs = [art_palettes(art) for art in arts]

    # ---- pass 2: tiles ----
    tiles = [((0,) * 8,) * len(arts)]           # tile 0 = empty; each tile = its data in every art
    tile_index = {tiles[0]: 0}
    def encode(px, index):
        out = []
        for y in range(8):
            v = 0
            for x in range(8):
                c = px[y * 8 + x]
                v = (v << 4) | (index[c] if c else 0)
            out.append(v)
        return tuple(out)
    def encoded(pixels, g):        # pixels(art): the tile's pixels in that art; g: its MD palette
        return tuple(encode(pixels(art), packs[k][0][g][1]) for k, art in enumerate(arts))
    def add_tile(data):
        if data not in tile_index:
            tile_index[data] = len(tiles)
            tiles.append(data)
        return tile_index[data]
    # sprite tiles first, so that they keep their indices in every block (tools/block_to_md.py lays the next blocks'
    # tiles out the same way and re-encodes these with the block's art and palettes): a MD 1x2 sprite uses two
    # consecutive tiles (top, bottom)
    sidx = {}
    def spr_tile(t, at):
        ci, p = spr_key(t, at)
        if (ci, p) not in sidx:
            g = group_spr(p)
            sidx[(ci, p)] = len(tiles)
            tiles.append(encoded(lambda art: art.spr_tile(ci, p), g))
            tiles.append(encoded(lambda art: art.spr_tile(ci + 1, p), g))
        return sidx[(ci, p)]

    def pose_entries(sprites):
        out = []
        for dx, dy, t, at in sprites:
            attr = (group_spr(at & 3) << 13) | (0x800 if at & 0x40 else 0) | (0x1000 if at & 0x80 else 0)
            out.append((dx, dy, attr, spr_tile(t, at)))
        return out

    poses = {n: pose_entries(s_) for n, s_ in raw_poses.items()}
    whip = [(fr, pose_entries(s_)) for fr, s_ in raw_whip]
    whip2 = [(fr, pose_entries(s_)) for fr, s_ in raw_whip2]
    cwhip = [(fr, pose_entries(s_)) for fr, s_ in raw_cwhip]
    swhip = [(fr, pose_entries(s_)) for fr, s_ in raw_swhip]
    swhip2 = [(fr, pose_entries(s_)) for fr, s_ in raw_swhip2]
    cwhip2 = [(fr, pose_entries(s_)) for fr, s_ in raw_cwhip2]
    whip3, cwhip3, swhip3 = ([[(fr, pose_entries(s_)) for fr, s_ in ph] for ph in v] for v in (raw_whip3, raw_cwhip3, raw_swhip3))
    throw = [(fr, pose_entries(s_)) for fr, s_ in raw_throw]
    sthrow = [(fr, pose_entries(s_)) for fr, s_ in raw_sthrow]
    obj_poses = [pose_entries(x) for x in raw_objs]
    # the gate's mask: 16x32 px of the darkest sprite colour (the NES tile $FE is solid black)
    def dark(pal2):
        return 1 + min(range(len(pal2)), key=lambda i: sum(pal2[i]))
    mask = tuple((int(f"{dark(pk[0][2][0]):X}" * 8, 16),) * 8 for pk in packs)
    mask_tile = len(tiles)
    tiles += [mask, mask]
    obj_poses.append([(dx, dy, 2 << 13, mask_tile) for dy in (0, 16) for dx in (0, 8)])
    nspr = len(tiles)
    sprite_layout = [None] * nspr                     # what each tile slot holds, for tools/block_to_md.py
    for (ci, p_), i in sidx.items():
        sprite_layout[i], sprite_layout[i + 1] = [ci, p_], [ci + 1, p_]
    sprite_layout[mask_tile] = sprite_layout[mask_tile + 1] = "mask"

    bg_word = {}
    def font_shade(art, px):
        """The 16-bit font is shaded row by row (white top, then pink, red, dark red), but some glyphs (F G Q V X Z,
        0 2-6, '-') have no 16-bit tile and keep the NES art's one colour: give every glyph the rows of the A."""
        if art.name != "16bit":
            return px
        ref = art.bg_tile(0xE0, text_pal)
        rows = [next((c for c in ref[y * 8:y * 8 + 8] if c), None) for y in range(8)]
        return [rows[i // 8] or c if c else c for i, c in enumerate(px)]

    def bg_tile(t, p):             # tile map word: tile index + palette bits
        if (t, p) not in bg_word:
            g = group_bg(p)
            if t in FONT_TILES and p == text_pal:
                pixels = lambda art: font_shade(art, art.bg_tile(t, p))
            else:
                pixels = lambda art: art.bg_tile(t, p)
            bg_word[(t, p)] = add_tile(encoded(pixels, g)) | (g << 13)
        return bg_word[(t, p)]

    # then the HUD and its text (the font, the game over screen): the same tiles in every block too
    hud = [bg_tile(wt[c * ROWS + r], wp[c * ROWS + r]) for r in range(1, 6) for c in range(32)]
    digits = [bg_tile(208 + d, hud_pal) for d in range(10)]
    lives_pal = wp[23 * ROWS + 4]     # palette of the 'P-03' lives counter
    digits_lives = [bg_tile(208 + d, lives_pal) for d in range(10)]
    bar_pal = wp[7 * ROWS + 3]        # health bar: tile 218 = full, 219 = empty (two blocks each)
    hud_bar = [bg_tile(218, bar_pal), bg_tile(219, bar_pal), bg_tile(0xF0, bar_pal)]   # full, empty, half ($A23B)
    ebar_pal = wp[7 * ROWS + 4]       # the enemy's (boss) bar on the next row
    hud_ebar = [bg_tile(0xDF, ebar_pal), bg_tile(219, ebar_pal), bg_tile(0xDE, ebar_pal)]
    gameover = [bg_tile(t, go_pal(t)) if t else 0 for t in go_cells]
    go_rows = [c // 32 for c, before, after in go_cursor]           # CONTINUE, then END
    go_col = go_cursor[0][0] % 32
    go_heart = bg_tile(0xDC, heart_pal)
    font = [bg_tile(t, text_pal) for t in FONT_TILES]
    x_tile = add_tile(encoded(lambda art: font_shade(art, x_glyph(art, text_pal)), group_bg(text_pal)))
    font[23] = x_tile | (group_bg(text_pal) << 13)
    nfixed = len(tiles)
    fixed_layout = sprite_layout + [None] * (nfixed - nspr)
    fixed_layout[x_tile] = ["x", text_pal]
    for (t, p_), w in bg_word.items():
        if fixed_layout[w & 0x7FF] is None:
            fixed_layout[w & 0x7FF] = ["bg", t, p_]

    level = [0] * (cols * ROWS)
    in_back = lambda c, r: c < COURT_COLS and BACK_ROW0 <= r < BACK_ROW0 + BACK_ROWS and leaves_front(wt[c * ROWS + r], r)
    for c in range(cols):
        for r in range(ROWS):
            if not in_back(c, r):
                level[r * cols + c] = bg_tile(wt[c * ROWS + r], wp[c * ROWS + r])
    # far plane strip: world columns 8..39 (one full period); cells that hold foreground things (the statue) take the
    # canopy tile found 4, 8, 12... columns away in the same row, since the pattern repeats every 4 columns
    back = []
    for r in range(BACK_ROW0, BACK_ROW0 + BACK_ROWS):
        for j in range(32):
            w = 8 + j
            src = None
            for k in range(0, 9):
                for sign in ((1,) if k == 0 else (1, -1)):
                    w2 = w + 4 * k * sign
                    if 0 <= w2 < COURT_COLS and src is None and is_canopy(wt[w2 * ROWS + r], r):
                        src = w2
            back.append(bg_tile(wt[src * ROWS + r], wp[src * ROWS + r]) if src is not None else 0)
    gate = [0] * (GATE_COLS * ROWS)
    mc, mr, mw, mh = GATE_MASK
    for c in range(GATE_COLS):
        for r in range(ROWS):
            t = gt[c * ROWS + r]
            if c < GATE_BACK_COLS and BACK_ROW0 <= r < BACK_ROW0 + BACK_ROWS and leaves_front(t, r):
                continue
            gate[r * GATE_COLS + c] = bg_tile(t, gp[c * ROWS + r]) | (0x8000 if mc <= c < mc + mw and mr <= r < mr + mh else 0)
    nbg = len(tiles) - nspr
    solid = [sum(1 << r for r in range(ROWS) if wt[c * ROWS + r] in SOLID_TOP) for c in range(cols)]
    wall = [sum(1 << r for r in range(ROWS) if wt[c * ROWS + r] in WALL) for c in range(cols)]
    gate_solid = [sum(1 << r for r in range(ROWS) if gt[c * ROWS + r] in SOLID_TOP) for c in range(GATE_COLS)]
    gate_wall = [sum(1 << r for r in range(ROWS) if gt[c * ROWS + r] in WALL) for c in range(GATE_COLS)]

    # wall candles of the hall: sprite x, OAM y and the item code read from the NES game's object slots
    # (tools/candle_codes_true.json, produced while walking through the stage; see README)
    codes_file = Path(a.codes)
    wall_candles = [(x, y, c) for x, y, c in json.loads(codes_file.read_text())]
    # stages 2 and 3 (tools/record_candles.py): [stage, floor, room x of the centre, centre y, code]; the sprite is
    # 8 px wide and 16 high, so x - 4 and y - 8 from where the room starts in level_map (its hall rows match
    # candle_codes_true.json within a pixel)
    room_x0 = {(2, 1): room_col0["ST2_COL0"] * 8, (2, 0): room_col0["UNDER_COL0"] * 8, (3, 0): room_col0["ST3_COL0"] * 8}
    wall_candles += [(room_x0[(st, fl)] + x - 4, y - 8, c)
                     for st, fl, x, y, c in json.loads(Path(a.rooms_candles).read_text()) if (st, fl) in room_x0]
    # braziers of the courtyard: x and item code (0 = chosen when it breaks, depending on hearts and whip level)
    candles = [(88, 4), (216, 0), (343, 0), (471, 4), (599, 8)]
    # stairs (see STAIR_R / STAIR_L)
    tile = lambda c, r: wt[c * ROWS + r] if 0 <= c < cols and 0 <= r < ROWS else -1
    tri = {(c, r) for c in range(cols) for r in range(ROWS) if tuple(tile(c + k, r) for k in range(3)) == STAIR_R}
    lsteps = {(c, r) for c in range(cols) for r in range(ROWS) if tile(c, r) == STAIR_L}
    stairs = []
    for c, r in sorted(tri):
        if (c - 1, r + 1) in tri:
            continue                                    # not the bottom of a flight
        n = 0
        while (c + n, r - n) in tri:
            n += 1
        # foot: Simon's anchor x = 8 * column, head y = 8 * (row - 2); one step more than the triples (the top cap)
        stairs.append([c * 8, (r - 2) * 8, n + 1, 1, -1, -1])
    for c, r in sorted(lsteps):
        if (c + 1, r + 1) in lsteps:
            continue
        n = 0
        while (c - n, r - n) in lsteps:
            n += 1
        # the lowest step sits on the floor: head y = 8 * (row - 3); measured in the NES game on the underground's
        # right flight, Simon's centre is then at 8 * column + 9. The top step is level with the floor it leads to,
        # unless that floor is a row higher (notched bricks next to it)
        top_level = tile(c - n, r - n + 1) in SOLID_TOP
        stairs.append([c * 8 + 1, (r - 3) * 8, n if top_level else n + 1, -1, -1, -1])
    # Stage 2's two rooms are joined by two flights that go through the bottom of the upper room (where only their
    # two lowest steps show) and the top of the underground. The NES game swaps rooms when Simon's centre passes y 208
    # going down (he goes on at y 49) or y 48 going up (y 207), keeping the scroll and his x on the screen: each half
    # is a flight of its room that hands Simon over to the other half (link_up / link_down), and the underground
    # halves are cut at head y 32.
    u0, d0 = room_col0["ST2_COL0"] * 8, room_col0["UNDER_COL0"] * 8
    def find(x, y):
        return next(i for i, st in enumerate(stairs) if st[0] == x and st[1] == y)
    for upper, under in ((find(u0 + 7 * 8 + 1, 192), find(d0 + 11 * 8 + 1, 64)),
                         (find(u0 + 47 * 8 + 1, 192), find(d0 + 55 * 8 + 1, 96))):
        stairs[under][2] = (stairs[under][1] - 32) // 8
        stairs[under][4], stairs[upper][5] = upper, under
    # black panthers sitting on ledges: left edge of the 32 px box and OAM y of the crouched sprite (observed)
    panthers = [(1191, 128), (1383, 96), (1447, 128)]

    (lv.parent / "fixed_layout.json").write_text(json.dumps(fixed_layout))
    src, inc = Path(a.src), Path(a.inc)
    src.mkdir(exist_ok=True)
    inc.mkdir(exist_ok=True)
    pose_names = list(poses)
    with open(src / "level.c", "w") as f:
        f.write('// generated by tools/level_to_md.py - do not edit\n#include "level.h"\n\n')
        for k, art in enumerate(arts):
            f.write(f"const u32 level_tiles{ART_SUFFIX[art.name]}[{len(tiles) * 8}] = {{\n")
            for t in tiles:
                f.write("    " + ", ".join(f"0x{v:08X}" for v in t[k]) + ",\n")
            f.write("};\n\n")
        f.write(f"const u16 level_map[{len(level)}] = {{\n")
        for r in range(ROWS):
            f.write("    " + ",".join(str(v) for v in level[r * cols:(r + 1) * cols]) + ",\n")
        f.write("};\n\n")
        f.write(f"const u32 level_solid[{cols}] = {{" + ", ".join(f"0x{v:08X}" for v in solid) + "};\n\n")
        f.write(f"const u32 level_wall[{cols}] = {{" + ", ".join(f"0x{v:08X}" for v in wall) + "};\n\n")
        f.write(f"const u16 gate_map[{len(gate)}] = {{\n")
        for r in range(ROWS):
            f.write("    " + ",".join(str(v) for v in gate[r * GATE_COLS:(r + 1) * GATE_COLS]) + ",\n")
        f.write("};\n\n")
        f.write(f"const u32 gate_solid[GATE_COLS] = {{" + ", ".join(f"0x{v:08X}" for v in gate_solid) + "};\n\n")
        f.write(f"const u32 gate_wall[GATE_COLS] = {{" + ", ".join(f"0x{v:08X}" for v in gate_wall) + "};\n\n")
        f.write(f"const u16 level_back[{BACK_ROWS * 32}] = {{\n")
        for r in range(BACK_ROWS):
            f.write("    " + ",".join(str(v) for v in back[r * 32:(r + 1) * 32]) + ",\n")
        f.write("};\n\n")
        f.write("const u16 level_hud[160] = {\n")
        for r in range(5):
            f.write("    " + ",".join(str(v) for v in hud[r * 32:(r + 1) * 32]) + ",\n")
        f.write("};\n\n")
        for k, art in enumerate(arts):
            f.write(f"const u16 level_palette{ART_SUFFIX[art.name]}[64] = {{" + ", ".join(f"0x{md_word(c):04X}" for c in packs[k][1]) + "};\n\n")
            if art.name == "nes":     # each colour's NES index, for the SNES port's NES palettes (0xFF: none)
                f.write(f"const u8 level_palette_nesidx[64] = {{" + ", ".join(str(nes_index(c)) for c in packs[k][1]) + "};\n\n")
        f.write("const u16 nes_palettes[14][64] = {\n")
        for table in snes_nes_palettes(snes):
            f.write("    {" + ", ".join(f"0x{c:04X}" for c in table) + "},\n")
        f.write("};\n\n")

        def dump(name, entries):
            f.write(f"static const SimonSprite {name}[{len(entries)}] = {{\n")
            for dx, dy, attr, tile in entries:
                f.write(f"    {{{dx}, {dy}, 0x{attr:04X}, {tile}}},\n")
            f.write("};\n")
        for n in pose_names:
            dump(f"pose_{n}", poses[n])
        for i, (_, e) in enumerate(whip):
            dump(f"whip_{i}", e)
        for i, (_, e) in enumerate(whip2):
            dump(f"whipb_{i}", e)
        for i, (_, e) in enumerate(cwhip):
            dump(f"cwhip_{i}", e)
        for i, (_, e) in enumerate(cwhip2):
            dump(f"cwhipb_{i}", e)
        for i, (_, e) in enumerate(swhip):
            dump(f"swhip_{i}", e)
        for i, (_, e) in enumerate(swhip2):
            dump(f"swhipb_{i}", e)
        for nm, ph in (("whipc", whip3), ("cwhipc", cwhip3), ("swhipc", swhip3)):
            for v, phv in enumerate(ph):
                for i, (_, e) in enumerate(phv):
                    dump(f"{nm}{v}_{i}", e)
        for i, (_, e) in enumerate(throw):
            dump(f"throw_{i}", e)
        for i, (_, e) in enumerate(sthrow):
            dump(f"sthrow_{i}", e)
        for i, e in enumerate(obj_poses):
            dump(f"obj_{i}", e)
        f.write("\nconst SimonPose simon_poses[POSE_COUNT] = {\n")
        for n in pose_names:
            f.write(f"    {{{len(poses[n])}, pose_{n}}},  // {n}\n")
        f.write("};\n\n")
        f.write(f"const SimonPhase simon_whip[WHIP_PHASES] = {{\n")
        for i, (fr, e) in enumerate(whip):
            f.write(f"    {{{fr}, {{{len(e)}, whip_{i}}}}},\n")
        f.write("};\n\n")
        f.write(f"const SimonPhase simon_whip2[WHIP_PHASES] = {{\n")
        for i, (fr, e) in enumerate(whip2):
            f.write(f"    {{{fr}, {{{len(e)}, whipb_{i}}}}},\n")
        f.write("};\n\n")
        f.write(f"const SimonPhase simon_swhip[WHIP_PHASES] = {{\n")
        for i, (fr, e) in enumerate(swhip):
            f.write(f"    {{{fr}, {{{len(e)}, swhip_{i}}}}},\n")
        f.write("};\n\n")
        f.write(f"const SimonPhase simon_swhip2[WHIP_PHASES] = {{\n")
        for i, (fr, e) in enumerate(swhip2):
            f.write(f"    {{{fr}, {{{len(e)}, swhipb_{i}}}}},\n")
        f.write("};\n\n")
        f.write(f"const SimonPhase simon_cwhip[WHIP_PHASES] = {{\n")
        for i, (fr, e) in enumerate(cwhip):
            f.write(f"    {{{fr}, {{{len(e)}, cwhip_{i}}}}},\n")
        f.write("};\n\n")
        f.write(f"const SimonPhase simon_cwhip2[WHIP_PHASES] = {{\n")
        for i, (fr, e) in enumerate(cwhip2):
            f.write(f"    {{{fr}, {{{len(e)}, cwhipb_{i}}}}},\n")
        f.write("};\n\n")
        for nm, pre, ph in (("whip3", "whipc", whip3), ("cwhip3", "cwhipc", cwhip3), ("swhip3", "swhipc", swhip3)):
            f.write(f"const SimonPhase simon_{nm}[4][WHIP_PHASES] = {{\n")
            for v, phv in enumerate(ph):
                f.write("    {" + ", ".join(f"{{{fr}, {{{len(e)}, {pre}{v}_{i}}}}}" for i, (fr, e) in enumerate(phv)) + "},\n")
            f.write("};\n\n")
        f.write(f"const SimonPhase simon_throw[WHIP_PHASES] = {{\n")
        for i, (fr, e) in enumerate(throw):
            f.write(f"    {{{fr}, {{{len(e)}, throw_{i}}}}},\n")
        f.write("};\n\n")
        f.write(f"const SimonPhase simon_sthrow[WHIP_PHASES] = {{\n")
        for i, (fr, e) in enumerate(sthrow):
            f.write(f"    {{{fr}, {{{len(e)}, sthrow_{i}}}}},\n")
        f.write("};\n\n")
        f.write(f"const SimonPose obj_poses[OBJ_POSES] = {{\n")
        for i, e in enumerate(obj_poses):
            f.write(f"    {{{len(e)}, obj_{i}}},\n")
        f.write("};\n\n")
        f.write(f"const Stair level_stairs[STAIRS] = {{" + ", ".join(f"{{{x}, {y}, {n}, {d}, {lu}, {ld}}}" for x, y, n, d, lu, ld in stairs) + "};\n\n")
        f.write(f"const WallCandle level_wcandles[WCANDLES] = {{" + ", ".join(f"{{{x}, {y}, {it}}}" for x, y, it in wall_candles) + "};\n\n")
        f.write(f"const PantherSpawn level_panthers[PANTHERS] = {{" + ", ".join(f"{{{x}, {y}}}" for x, y in panthers) + "};\n\n")
        f.write(f"const Candle level_candles[CANDLES] = {{" + ", ".join(f"{{{x}, {it}}}" for x, it in candles) + "};\n\n")
        f.write("const u16 hud_digit[10] = {" + ", ".join(str(v) for v in digits) + "};\n\n")
        f.write("const u16 hud_digit_lives[10] = {" + ", ".join(str(v) for v in digits_lives) + "};\n\n")
        f.write("const u16 hud_bar[3] = {" + ", ".join(str(v) for v in hud_bar) + "};\n\n")
        f.write("const u16 hud_ebar[3] = {" + ", ".join(str(v) for v in hud_ebar) + "};\n\n")
        f.write("const u16 font_map[" + str(len(font)) + "] = {" + ", ".join(str(v) for v in font) + "};\n\n")
        f.write(f"const u16 gameover_map[{len(gameover)}] = {{\n")
        for r in range(30 - GO_ROW0):
            f.write("    " + ",".join(str(v) for v in gameover[r * 32:(r + 1) * 32]) + ",\n")
        f.write("};\n\n")
        f.write(f"const s8 simon_jump_dy[JUMP_FRAMES] = {{{', '.join(str(v) for v in jump_dy)}}};\n")
        f.write(f"const u8 simon_jump_curled[JUMP_FRAMES] = {{{', '.join(str(v) for v in jump_curled)}}};\n")
    with open(inc / "level.h", "w") as f:
        f.write(f"""// generated by tools/level_to_md.py - do not edit
#ifndef LEVEL_H
#define LEVEL_H
#include <genesis.h>

typedef struct {{ s8 dx, dy; u16 attr; u16 tile; }} SimonSprite;
typedef struct {{ u8 count; const SimonSprite *sprites; }} SimonPose;
typedef struct {{ u8 frames; SimonPose pose; }} SimonPhase;
typedef struct {{ s16 x; u8 code; }} Candle;
typedef struct {{ s16 x, y; u8 code; }} WallCandle;
// foot: Simon's anchor x and head y; each step is 8 px up and 8 px to the side dir points to (1 right, -1 left);
// link_up / link_down: the flight Simon goes on to past the top / the foot (another room), or -1
typedef struct {{ s16 x, y; u8 steps; s8 dir, link_up, link_down; }} Stair;
typedef struct {{ s16 x, y; }} PantherSpawn;

#define LEVEL_COLS      {cols}
#define LEVEL_ROWS      {ROWS}
#define ST2_COL0        {room_col0["ST2_COL0"]}    /* world columns of stage 2's upper room, stage 3, stage 2's underground */
#define ST3_COL0        {room_col0["ST3_COL0"]}
#define UNDER_COL0      {room_col0["UNDER_COL0"]}
#define COURT_COLS      {COURT_COLS}
#define GATE_COL0       {GATE_COL0}     /* the castle gate screen replaces these world columns in the courtyard */
#define GATE_COLS       {GATE_COLS}
#define GATE_BACK_COLS  {GATE_BACK_COLS}     /* gate columns whose canopy is on the far plane */
#define GATE_MASK_X     {(GATE_COL0 + GATE_MASK[0]) * 8}    /* world x, OAM y of the mask box */
#define GATE_MASK_Y     {GATE_MASK[1] * 8}
#define BACK_ROW0       {BACK_ROW0}
#define BACK_ROWS       {BACK_ROWS}
#define GAMEOVER_ROW0   {GO_ROW0}      /* gameover_map: NES rows GAMEOVER_ROW0..29 of the game over screen */
#define GAMEOVER_ROW_CONTINUE {go_rows[0]}  /* rows and column of the heart cursor */
#define GAMEOVER_ROW_END {go_rows[1]}
#define GAMEOVER_CURSOR_COL {go_col}
#define GAMEOVER_HEART  {go_heart}
#define LEVEL_TILES     {len(tiles)}
#define FIXED_TILES     {nfixed}    /* tiles 0..FIXED_TILES-1 (the empty tile, the sprites, the HUD and its font) are the
                                same in every block, see tools/block_to_md.py */
#define POSE_COUNT      {len(pose_names)}
#define WHIP_PHASES     {len(whip)}
#define JUMP_FRAMES     {len(jump)}
#define CURL_LIFT       {CURL_LIFT}    /* the curled jump pose is drawn this many px above Simon's position */
#define CANDLES         {len(candles)}
#define WCANDLES        {len(wall_candles)}
#define STAIRS          {len(stairs)}
#define PANTHERS        {len(panthers)}
#define OBJ_POSES       {len(obj_poses)}
#define OBJ_BRAZIER0    0
#define OBJ_SPARKLE     2
#define OBJ_ITEM0       3
#define OBJ_ZOMBIE0     6
#define OBJ_HUDBOX      8
#define OBJ_WCANDLE0    9
#define OBJ_FLAME0      19
#define OBJ_SMALLHEART  22
#define OBJ_MONEY0      23   /* red, blue, white */
#define OBJ_ROSARY      26
#define OBJ_HOLY        27
#define OBJ_DOUBLE      28
#define OBJ_BOTTLE      29   /* holy water in flight */
#define OBJ_DOOR_HALF   30   /* the door between stages: half open, wide open */
#define OBJ_DOOR_OPEN   31
#define OBJ_AXE0        32   /* 4 spin poses; the first is also the item */
#define OBJ_CROSS0      36   /* 3 spin poses; the second is also the item */
#define OBJ_POTION      39
#define OBJ_WATCH       40
#define OBJ_BAT0        41   /* 3 wing poses, facing left */
#define OBJ_FISH0       44   /* walk 1, walk 2, firing; facing left */
#define OBJ_FIRE        47   /* moving right, moving left */
#define OBJ_DROP        49
#define OBJ_BOSS0       50   /* asleep, wings 1, wings 2 */
#define OBJ_BFLAME0     53   /* its death flames, 3 poses */
#define OBJ_ORB0        56   /* 2 poses */
#define OBJ_ROAST       58
#define OBJ_DEBRIS      59
#define OBJ_TREASURE0   60   /* money bag in palettes 0-3, the 1UP, then its '1000' */
#define OBJ_MASK        {len(obj_poses) - 1}   /* 16x32 black box hiding Simon in the castle gate */
#define OBJ_PANTHER0    11   /* sit, stretch, run1, run2 facing left; +4 for facing right */
""")
        for i, n in enumerate(pose_names):
            f.write(f"#define POSE_{n.upper():<8} {i}\n")
        f.write("""
extern const u32 level_tiles[];             // the 16-bit art (Fiuke Bnuy's tiles of the SNES port)
extern const u32 level_tiles_nes[];         // the original NES art, same tiles at the same indices
extern const u16 level_map[];
extern const u16 gate_map[GATE_COLS * LEVEL_ROWS];
extern const u32 gate_solid[GATE_COLS];
extern const u32 gate_wall[GATE_COLS];
extern const u32 level_solid[LEVEL_COLS];   // bit r set = tile row r of that column is a standable surface
extern const u32 level_wall[LEVEL_COLS];    // bit r set = tile row r of that column is part of a solid block
extern const u16 level_back[BACK_ROWS * 32];   // far plane strip, 32 columns that wrap
extern const u16 level_hud[160];
extern const u16 level_palette[64];
extern const u16 level_palette_nes[64];
extern const u8 level_palette_nesidx[64];
extern const u16 nes_palettes[14][64];      // the SNES port's 14 NES palettes, MD colours by NES colour index
extern const SimonPose simon_poses[POSE_COUNT];
extern const SimonPhase simon_whip[WHIP_PHASES];
extern const SimonPhase simon_whip2[WHIP_PHASES];
extern const SimonPhase simon_cwhip[WHIP_PHASES];    // crouching whip
extern const SimonPhase simon_cwhip2[WHIP_PHASES];
extern const SimonPose obj_poses[OBJ_POSES];
extern const Candle level_candles[CANDLES];
extern const WallCandle level_wcandles[WCANDLES];
extern const Stair level_stairs[STAIRS];
extern const SimonPhase simon_swhip[WHIP_PHASES];     // whip on stairs
extern const SimonPhase simon_swhip2[WHIP_PHASES];
extern const SimonPhase simon_whip3[4][WHIP_PHASES];  // level 3 (long chain), one per sprite palette of its cycle
extern const SimonPhase simon_cwhip3[4][WHIP_PHASES];
extern const SimonPhase simon_swhip3[4][WHIP_PHASES];
extern const SimonPhase simon_throw[WHIP_PHASES];     // throwing a sub-weapon: the swing without the whip
extern const SimonPhase simon_sthrow[WHIP_PHASES];    // the same on the stairs
extern const PantherSpawn level_panthers[PANTHERS];
extern const u16 hud_digit[10];
extern const u16 hud_digit_lives[10];
extern const u16 hud_bar[3];          // health bar tile: full, empty, half
extern const u16 hud_ebar[3];         // the enemy's bar
extern const u16 font_map[];         // the HUD's font: A to Z, 0 to 9, '-'
extern const u16 gameover_map[];      // the game over screen below the HUD (the cursor heart included)
extern const s8 simon_jump_dy[JUMP_FRAMES];
extern const u8 simon_jump_curled[JUMP_FRAMES];

#endif
""")
    print(f"{cols} cols, {nbg} bg tiles + {len(tiles) - nbg} sprite tiles = {len(tiles)}; colours per MD palette "
          f"(distinct->kept) {', '.join(f'{art.name} {pk[2]}' for art, pk in zip(arts, packs))}; poses {pose_names}; "
          f"jump {len(jump)} frames")
    if getattr(arts[0], "fallbacks", 0):
        print(f"note: {arts[0].fallbacks} tiles had no 16-bit version and use the NES art")


if __name__ == "__main__":
    main()

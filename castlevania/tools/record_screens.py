#!/usr/bin/env python3
"""Record the NES game's title screen, its introduction, its game over screen and its ending (headless, fixed inputs).

usage: record_screens.py [--rom ROM.nes] [--out DIR]

Writes DIR/screens.json and, per screen (title, intro, gameover, ending), DIR/<screen>_chr.bin (8K CHR-RAM),
DIR/<screen>_nt.bin (the 1K nametable on show) and DIR/<screen>_pal.bin (32 bytes).
screens.json holds the sprites of every frame (OAM order, [x, y, tile, attr] with x, y as the NES draws them),
the timings measured on the way and the nametable cells that change (PUSH START KEY, the game over cursor, the
credits), with the ending's palette fades and sounds.

The run: power on, no input (the title's bat comes out of the tree, then flaps forever), START, the introduction
plays to the first frame of play; then Simon is made to die with no life left (RAM pokes: $2A lives = 1, $45
health = 0) to reach the game over screen, and SELECT moves its cursor. The ending is reached by pokes from a new game.
Needs py65 (pip install py65).
"""
import argparse, json
from pathlib import Path
from nes_dump import Machine
from decode_rooms import Rom

START, SELECT = 8, 4


def main():
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", default=str(root.parent.parent / "Castlevania (USA) (Rev 1).nes"))
    ap.add_argument("--out", default=str(root / "extracted/screens"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    m = Machine(Path(a.rom).read_bytes())
    ram = m.mem._subject
    m.mpu.reset()
    m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    frame = 0

    def step(pad=0):
        nonlocal frame
        m.pad = pad
        m.frame()
        frame += 1

    def sprites():
        return [[m.oam[k * 4 + 3], m.oam[k * 4], m.oam[k * 4 + 1], m.oam[k * 4 + 2]]
                for k in range(64) if m.oam[k * 4] < 0xEF]

    def shown_nt():
        base = m.nt_index(0x2000 + (m.ctrl & 3) * 0x400) & ~0x3FF
        return bytes(m.nt[base:base + 1024])

    def dump(name):
        assert m.ctrl & 0x20, "expected 8x16 sprites"
        (out / f"{name}_chr.bin").write_bytes(bytes(m.chr))
        (out / f"{name}_nt.bin").write_bytes(shown_nt())
        (out / f"{name}_pal.bin").write_bytes(bytes(m.pal))
        return {"ctrl": m.ctrl, "scroll": (m.ctrl & 1) * 256 + m.scroll_x}

    def changed(before):
        now = shown_nt()
        return [[i, before[i], now[i]] for i in range(960) if before[i] != now[i]]

    info = {}
    # ---- title: state $18 = 1; sub-state 0 while the bat comes out, then 1 (it flaps in a loop)
    while ram[0x18] != 1:
        step()
    title_first = frame
    title = []
    loop_at = None
    while True:
        step()
        title.append(sprites())
        if loop_at is None and ram[0x19] == 1:
            loop_at = len(title) - 1
        if loop_at is not None and len(title) - loop_at == 16:            # one flap cycle (4 poses x 4 frames)
            break
    info["title"] = dump("title")
    info["title"].update(frames=title, loop=loop_at, first_frame=title_first)

    # ---- START: PUSH START KEY blinks (state 3), the sprites stay still
    nt0 = shown_nt()
    for _ in range(4):
        step(START)
    pressed = frame - 4
    blink, cells = [], []                                                # frames (after the press) the text is hidden
    while ram[0x18] == 3:
        if shown_nt() != nt0:
            blink.append(frame - pressed)
            cells = changed(nt0)
        step()
    info["title"]["start_cells"] = [c[0] for c in cells]
    info["title"]["start_blank"] = cells[0][2] if cells else 0
    info["title"]["blink_hidden"] = blink
    info["title"]["start_frames"] = frame - pressed

    # ---- introduction: state 4; sub-state 4 runs the scene, then state 5 is the first frame of play
    intro_begin = frame
    while not (ram[0x18] == 4 and ram[0x19] == 4):
        step()
    black = frame - intro_begin
    intro = []
    while ram[0x18] == 4:
        intro.append(sprites())
        if len(intro) == 8:
            info["intro"] = dump("intro")
        step()
    info["intro"].update(frames=intro, black=black)

    # ---- game over: die with no life left
    for _ in range(30):
        step()
    ram[0x2A] = 1
    died = frame
    while ram[0x18] != 0x0D:
        ram[0x45] = 0
        step()
    info["gameover"] = {"after_death": frame - died}
    for _ in range(30):
        step()
    info["gameover"].update(dump("gameover"))
    info["gameover"]["sprites"] = sprites()
    nt0 = shown_nt()
    for _ in range(4):
        step(SELECT)
    for _ in range(10):
        step()
    info["gameover"]["cursor"] = changed(nt0)          # [cell, tile before, tile after]: CONTINUE -> END

    # ---- ending (state $18 = 15): after Dracula's tally the NES game has stage 18's CHR (sets $C8B0[16] and [18]
    # over the first one) with set 10 laid over it; here a new game gets that CHR and $18 = 15, $19 = 0 (the same
    # pictures, sounds and sprites as after a real kill, in another OAM order: checked frame by frame). Its screen
    # is still; the castle's towers are sprites that sink behind sprites of tile $FE, then the credits are written
    # into the nametable, page after page, faded in and out through background palette 3
    m = Machine(Path(a.rom).read_bytes())                # a new console (a reset alone stays on the game over)
    ram = m.mem._subject
    m.mpu.reset()
    m.mpu.pc = m.mem[0xFFFC] | (m.mem[0xFFFD] << 8)
    while ram[0x18] != 1:
        step()
    for _ in range(4):
        step(START)
    while ram[0x18] != 5:
        step()
    for _ in range(20):
        step()
    rom = Rom(Path(a.rom).read_bytes())
    def chr_set(k):
        lst = rom.word(0xFDBB + 2 * k)
        while rom.rd(lst) != 0xFF:
            bank, src, dst, n = rom.rd(lst), rom.word(lst + 1), rom.word(lst + 3), rom.word(lst + 5)
            m.chr[dst:dst + n] = bytes(rom.rd(src + i, bank) for i in range(n))
            lst += 7
    for k in (rom.rd(0xC8B0 + 16), rom.rd(0xC8B0 + 18), 10):
        chr_set(k)
    ram[0x18], ram[0x19] = 0x0F, 0
    sounds = []
    nframe = [None]
    m.mem.subscribe_to_write([0x7F6], lambda adr, v: sounds.append([nframe[0], v]) or v)
    poked = frame
    while ram[0x19] != 2:
        step()
    ending = {"black": frame - poked}
    ending.update(dump("ending"))
    frames, writes, pals = [], [], []
    nt0, pal0 = shown_nt(), bytes(m.pal)
    while ram[0x18] == 0x0F:
        nframe[0] = len(frames)
        frames.append(sprites())
        step()
        if ram[0x18] != 0x0F:                           # the ending is over: the next frame clears the screen
            break
        nt1, pal1 = shown_nt(), bytes(m.pal)
        writes += [[len(frames), c, t] for c, _, t in changed(nt0)]
        if any(nt0[i] != nt1[i] for i in range(960, 1024)):
            raise SystemExit(f"the ending changed its attributes on frame {len(frames)}, state {ram[0x18]}.{ram[0x19]}: "
                             f"{[(i, nt0[i], nt1[i]) for i in range(960, 1024) if nt0[i] != nt1[i]]}")
        if pal1 != pal0:
            assert all(pal1[i] == pal0[i] for i in range(32) if i not in (13, 14, 15)), "palette change beyond bg palette 3"
            pals.append([len(frames), list(pal1[13:16])])
        nt0, pal0 = nt1, pal1
    ending.update(frames=frames, writes=writes, fades=pals, sounds=sounds)
    info["ending"] = ending

    (out / "screens.json").write_text(json.dumps(info))
    print(f"title {len(title)} frames (loop from {loop_at}), start {info['title']['start_frames']} frames, "
          f"blank cells {len(cells)}, intro {len(intro)} frames after {black} black, game over {info['gameover']['after_death']} "
          f"frames after the death, cursor {info['gameover']['cursor']}, ending {len(frames)} frames after {ending['black']} "
          f"black, {len(writes)} cell writes, {len(pals)} fade steps, sounds {sounds}")


if __name__ == "__main__":
    main()

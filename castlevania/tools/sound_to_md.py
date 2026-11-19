#!/usr/bin/env python3
"""Record the NES game's music and sound effects, straight from its own sound engine, for src/sound.c.

usage: sound_to_md.py <rom.nes>

The sound engine sits in bank 0: $8187 starts sound A, $838A steps it by a frame (called from the NMI, $C097). It
writes the APU's registers itself every frame, with constant volumes and no hardware sweep or envelope (checked), so
replaying those writes and translating the APU's channels to the Mega Drive's chips at run time plays the same notes,
volumes and timing. Each sound is played alone from a cleared RAM; the drums are sounds 1 and 2, which the music
starts itself, so they are in its recording. A looping track is recorded until the engine's RAM ($80-$BF) comes
back to a state it had before: the stream jumps back there. A sound that does not loop ends once the engine has
stopped writing for 60 frames.

Writes src/music.c and inc/music.h (generated, not in git; played by src/sound.c): per sound, a byte stream of frames, each frame its
writes (register $4000 + r: r, value) then $FF; $FE n stands for n frames without a write.

The sound of Simon being hurt is not in the engine: $FE96 (called from the hit at $E734) plays a DPCM sample on the
APU's DMC, rate $0F (33144 Hz), from $FF40, $0B * 16 + 1 = 177 bytes. It is decoded here to 8-bit PCM at 32000 Hz
(the nearest rate of SGDK's PCM driver, which src/sound.c plays on the YM2612's DAC), as music.c's hurt_pcm.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from nes_dump import Machine

# NES sound number -> name; the music numbers and their tracks come from the SNES port's MSU-1 table (msu.asm)
MUSIC = [(0x27, "PROLOGUE"), (0x2A, "VAMPIRE_KILLER"), (0x2D, "STALKER"), (0x30, "WICKED_CHILD"),
         (0x33, "OUT_OF_TIME"), (0x36, "HEART_OF_FIRE"), (0x39, "WALKING_THE_EDGE"), (0x3C, "NOTHING_TO_LOSE"),
         (0x3F, "POISON_MIND"), (0x42, "BLACK_NIGHT"), (0x45, "VOYAGER"), (0x48, "STAGE_CLEAR"),
         (0x4B, "ALL_CLEAR"), (0x4E, "LOSE_LIFE"), (0x51, "GAME_OVER")]
SFX = list(range(0x01, 0x26)) + [0x54]
MAX_FRAMES = 12000


class Engine:
    def __init__(self, rom):
        self.m = Machine(rom)
        self.m.load_bank(0)
        ram = self.m.mem._subject
        for i in range(0x800):
            ram[i] = 0
        self.writes = []
        self.m.mem.subscribe_to_write(list(range(0x4000, 0x4014)) + [0x4015, 0x4017],
                                      lambda a, v: self.writes.append((a - 0x4000, v)) or v)

    def call(self, addr, a=0):
        c = self.m.mpu
        c.a, c.x, c.y = a, 0, 0
        c.memory[0x1FF] = c.memory[0x1FE] = 0xFF        # returns to $0000
        c.sp = 0xFD
        c.pc = addr
        n = 0
        while c.pc != 0:
            c.step()
            n += 1
            assert n < 200000, "the sound engine did not return"
        if self.m.bank != 0:
            self.m.load_bank(0)

    def state(self):
        return bytes(self.m.mem._subject[0x80:0xC0])


def record(rom, sid, looping):
    e = Engine(rom)
    e.call(0x8187, sid)
    frames, seen, loop, quiet = [], {}, None, 0
    for f in range(MAX_FRAMES):
        if f:
            e.writes = []
        e.call(0x838A)
        frames.append(e.writes)
        st = e.state()
        if looping:
            if st in seen:
                loop = seen[st] + 1
                break
            seen[st] = f
        else:
            quiet = 0 if e.writes else quiet + 1
            if quiet >= 60:
                frames = frames[:len(frames) - quiet + 1]
                break
    else:
        raise SystemExit(f"sound ${sid:02X}: no end found")
    return frames, loop


def encode(frames, loop):
    out, loop_at, i = [], 0xFFFF, 0
    while i < len(frames):
        if i == loop:
            loop_at = len(out)
        if not frames[i]:
            n = 1
            while i + n < len(frames) and not frames[i + n] and n < 255 and i + n != loop:
                n += 1
            out += [0xFE, n]
            i += n
            continue
        for r, v in frames[i]:
            out += [r, v]
        out.append(0xFF)
        i += 1
    return out, loop_at


def hurt_sample(rom):
    prg = rom[16:16 + rom[4] * 0x4000]
    data = prg[-0x4000 + 0x3F40:][:0x0B * 16 + 1]       # $FF40 in the fixed last bank
    level, levels = 0, []                                 # the DMC's level, 0 after the game's APU set-up; it then
    for b in data:                                        # keeps where the last sample left it (an approximation)
        for i in range(8):                                # each bit, low first: +2 or -2, held within 0..127
            if b >> i & 1:
                if level <= 125: level += 2
            elif level >= 2: level -= 2
            levels.append(level)
    n = len(levels) * 32000 // 33144                      # nearest sample at 32000 Hz
    out = [levels[k * 33144 // 32000] for k in range(n)]
    pad = -len(out) % 256                                 # the driver plays whole 256-byte blocks: ramp back to 0
    out += [out[-1] * (pad - k - 1) // pad for k in range(pad)]
    return bytes(min(v * 2, 127) for v in out)            # level x 2: a first guess at its loudness against the PSG


def main():
    root = Path(__file__).resolve().parent.parent
    rom = Path(sys.argv[1]).read_bytes()
    sounds = []
    for sid, name in MUSIC:
        frames, loop = record(rom, sid, name not in ("STAGE_CLEAR", "ALL_CLEAR", "LOSE_LIFE", "GAME_OVER"))
        data, loop_at = encode(frames, loop)
        print(f"music ${sid:02X} {name}: {len(frames)} frames, loop at frame {loop}, {len(data)} bytes")
        sounds.append((f"MUS_{name}", sid, data, loop_at))
    for sid in SFX:
        frames, _ = record(rom, sid, False)
        data, _ = encode(frames, None)
        sounds.append((f"SFX_{sid:02X}", sid, data, 0xFFFF))
    print(f"{len(SFX)} sound effects, {sum(len(s[2]) for s in sounds)} bytes in all")

    with open(root / "src/music.c", "w") as f:
        f.write("// generated by tools/sound_to_md.py - do not edit\n#include \"music.h\"\n\n")
        for name, sid, data, _ in sounds:
            f.write(f"static const u8 {name.lower()}[{len(data)}] = {{\n")
            for k in range(0, len(data), 24):
                f.write("    " + ",".join(str(v) for v in data[k:k + 24]) + ",\n")
            f.write("};\n")
        f.write("\nconst Sound sounds[SOUNDS] = {\n")
        for name, sid, data, loop_at in sounds:
            f.write(f"    {{ {name.lower()}, {len(data)}, {loop_at} }},     // NES sound ${sid:02X}\n")
        f.write("};\n")
        hurt = hurt_sample(rom)
        f.write(f"\nconst u8 hurt_pcm[HURT_PCM_SIZE] __attribute__((aligned(256))) = {{   // signed 8-bit, 32000 Hz\n")
        for k in range(0, len(hurt), 24):
            f.write("    " + ",".join(str(v) for v in hurt[k:k + 24]) + ",\n")
        f.write("};\n")
    with open(root / "inc/music.h", "w") as f:
        f.write("// generated by tools/sound_to_md.py - do not edit\n#ifndef MUSIC_H\n#define MUSIC_H\n"
                "#include <genesis.h>\n\n"
                "typedef struct { const u8 *data; u16 size, loop; } Sound;   // loop: byte offset, 0xFFFF: plays once\n\n")
        for k, (name, sid, _, _) in enumerate(sounds):
            f.write(f"#define {name:<24} {k}\n")
        f.write(f"#define SOUNDS                   {len(sounds)}\n\nextern const Sound sounds[SOUNDS];\n\n"
                f"#define HURT_PCM_SIZE            {len(hurt)}\n"
                "extern const u8 hurt_pcm[HURT_PCM_SIZE];   // the DPCM sample of Simon being hurt\n\n#endif\n")


if __name__ == "__main__":
    main()

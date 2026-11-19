#!/usr/bin/env python3
"""Record the inter-block castle maps from Castlevania USA Rev 1 PRG data.

Needs py65, as the other recording tools do. The SNES port keeps these NES
sequences (bank7.asm $C698-$C7E2), with palette set 09 (palette_updates.asm).
Writes tools/extracted/maps/maps.json, map_chr.bin, map_pal.bin and map_nt.bin.
"""
import argparse
import copy
import json
from pathlib import Path
from nes_dump import Machine

STAGES = (4, 7, 10, 13, 16)


def clone_machine(base, rom):
    result = Machine(rom)
    for key, value in base.__dict__.items():
        if key not in ("mem", "mpu"):
            setattr(result, key, copy.deepcopy(value))
    result.mem._subject[:] = base.mem._subject[:]
    for key in ("pc", "sp", "a", "x", "y", "p", "processorCycles"):
        setattr(result.mpu, key, getattr(base.mpu, key))
    return result


def record(prg, out):
    if len(prg) != 8 * 0x4000:
        raise ValueError("expected Castlevania USA Rev 1 PRG (128 KiB)")
    rom = b"NES\x1a" + bytes((8, 0, 0x21, 0)) + bytes(8) + prg
    base = Machine(rom)
    base.mpu.reset()
    base.mpu.pc = base.mem[0xFFFC] | base.mem[0xFFFD] << 8
    for frame in range(1800):
        base.pad = 8 if 300 <= frame < 304 else 0
        base.frame()
        if base.mem._subject[0x18] == 5:
            break
    else:
        raise RuntimeError("could not reach gameplay")
    out.mkdir(parents=True, exist_ok=True)
    scenes = []
    common_chr = common_pal = None
    for stage in STAGES:
        m = clone_machine(base, rom)
        ram = m.mem._subject
        ram[0x28], ram[0x18], ram[0x19], ram[0x1D] = stage - 1, 12, 4, 1
        m.pad = 0
        sound_requests = []
        m.mem.subscribe_to_write([0x7F6], lambda addr, value: sound_requests.append(value) or value)
        frames, columns = [], {}
        for _ in range(1800):
            sound_requests.clear()
            m.frame()
            if ram[0x18] != 12:
                break
            if ram[0x28] != 20 or ram[0x19] not in (7, 8):
                continue
            if common_chr is None:
                common_chr, common_pal = bytes(m.chr), bytes(m.pal)
                (out / "map_chr.bin").write_bytes(common_chr)
                (out / "map_pal.bin").write_bytes(common_pal)
                ntbase = m.nt_index(0x2000 + (m.ctrl & 1) * 0x400)
                (out / "map_nt.bin").write_bytes(m.nt[ntbase:ntbase + 1024])
            if bytes(m.chr) != common_chr or bytes(m.pal) != common_pal:
                raise ValueError("map art or palette changed unexpectedly")
            scroll = (m.ctrl & 1) * 256 + m.scroll_x
            if frames and scroll < frames[-1]["scroll"]:
                raise ValueError("map scroll moved backwards")
            first = scroll // 8
            for c in range(first, first + 32 + bool(scroll & 7)):
                n = (c // 32) & 1
                ntbase = m.nt_index(0x2000 + n * 0x400)
                tx = c & 31
                column = []
                for r in range(30):
                    attr = m.nt[ntbase + 960 + (r // 4) * 8 + tx // 4]
                    palette = (attr >> (((r // 2) & 1) * 4 + ((tx // 2) & 1) * 2)) & 3
                    column.append([m.nt[ntbase + r * 32 + tx], palette])
                if c in columns and columns[c] != column:
                    raise ValueError(f"map stage {stage} column {c} is animated; update recorder")
                columns[c] = column
            sprites = [[m.oam[k + 3], m.oam[k], m.oam[k + 1], m.oam[k + 2]]
                       for k in range(0, 256, 4) if m.oam[k] < 0xEF]
            frames.append(dict(scroll=scroll, sprites=sprites, sounds=list(sound_requests)))
            if ram[0x19] == 8:
                break
        else:
            raise RuntimeError("map did not finish")
        if not frames or sorted(columns) != list(range(max(columns) + 1)):
            raise ValueError("incomplete map panorama")
        scenes.append(dict(stage=stage, columns=[columns[c] for c in range(len(columns))], frames=frames))
        print(f"stage {stage}: {len(frames)} frames, {len(columns)} columns, scroll 0..{frames[-1]['scroll']}", flush=True)
    result = dict(source="Castlevania USA Rev 1; SNES bank7.asm $C698-$C7E2, palette 09", scenes=scenes)
    (out / "maps.json").write_text(json.dumps(result, separators=(",", ":")))
    return result


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prg", type=Path, default=root / "extracted/prg.bin")
    parser.add_argument("--out", type=Path, default=root / "extracted/maps")
    args = parser.parse_args()
    record(args.prg.read_bytes(), args.out)


if __name__ == "__main__":
    main()

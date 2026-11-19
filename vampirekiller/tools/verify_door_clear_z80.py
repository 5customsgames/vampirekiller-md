#!/usr/bin/env python3
"""Door / cross clear on the original Z80 code (research/door-pose-phase.md, 'Objets detruits a l'ouverture') : 7806 (door 7743 -> 774C, cross 8DBB)
is run on the ROM (kosarev/z80 emulator on the stage maps) with one object of each type in C800 block 2 at (X 120, Y 176), then one object of
each D700 type, and the result is compared to the port's expectations (tests/test_door_clear.c).

7806 calls 9A3A (CFFF = 1) on every non-empty C800 block : 9A6B, then 99F6 (block freed), 9ABE (nothing rolled : CFFF != 0 returns before CF40 and R),
9B22 (D = 9B33[type]) and 5F1D (object 1E in the first free block at (X, Y - D)). Exceptions (9A6B) : 22h erased without flame, 24h / 26h pick up
their item (8D2C), 11h (+1 = 8) and 18h (+10h = 8 when CE0B = 0) are kept, 0E makes four flames, 09 is destroyed like the others (9AA9 returns NZ
at once when CFFF != 0 ; only the weapon kill 9A3E sends it to B048). D700 objects go through 9A1A : freed, then an object 0C (A = FF) in the first
free D700 block.
Usage: verify_door_clear_z80.py [ROM]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from castle_room_objects import call
from probe import load_rom, reference_rom
import verify_death_flame_z80 as flame

# ROM type -> D = 9B33[type] for every type with a flame (the port's kTypes in tests/test_door_clear.c)
TABLE = dict(flame.EXPECTED)
TABLE.update({0x1A: 0, 0x1B: 0, 0x1C: 0, 0x1D: 0, 0x20: 0, 0x23: 0, 0x1E: 0})
KEPT = {0x11, 0x18}      # boss objects : not erased by 9A6B (11h : +1 = 8, 18h : delayed by 9AB3)


def blocks(mem, base, count):
    return [(k, mem[base + 0x80 * k], mem[base + 0x80 * k + 5], mem[base + 0x80 * k + 3]) for k in range(count) if mem[base + 0x80 * k]]


def main():
    data = load_rom(Path(sys.argv[1]) if len(sys.argv) > 1 else reference_rom())
    done = 0
    for typ in sorted(set(TABLE) | KEPT | {0x22}):
        m = flame.build(data, 13, 8)
        mem = m.memory
        b = 0xC800 + 0x80 * 2
        mem[b] = typ; mem[b + 3] = 176; mem[b + 5] = 120; mem[b + 0x7E] = 1; mem[b + 0x7F] = 1; mem[b + 0xE] = 1
        mem[0xCF40] = 1; mem[0xCE08] = 0
        call(m, 0x7806)
        c = blocks(mem, 0xC800, 7)
        assert mem[0xCF40] == 1, f'type {typ:02X}: CF40 touched'
        if typ == 0x22:
            assert c == [], f'22h: {c}'
        elif typ in KEPT:
            assert c == [(2, typ, 120, 176)], f'{typ:02X}: {c}'
        elif typ == 0x0E:
            assert c == [(k, 0x1E, 120 + 16 * k, 176) for k in range(4)], f'0E: {c}'
        else:
            assert c == [(0, 0x1E, 120, 176 - TABLE[typ])], f'type {typ:02X}: {c}, expected a flame at Y {176 - TABLE[typ]}'
            assert mem[0xC800 + 0x0B] == 0x85 and mem[0xC800 + 0x0C] == 0x10 and mem[0xC800 + 0x1F] == 0, f'{typ:02X}: flame fields'
        done += 1
    for typ in (3, 4, 9, 0x0C):
        m = flame.build(data, 13, 8)
        mem = m.memory
        b = 0xD700 + 0x80 * 2
        mem[b] = typ; mem[b + 3] = 120; mem[b + 5] = 100; mem[b + 0x7F] = 1
        call(m, 0x7806)
        d = blocks(mem, 0xD700, 8)
        assert [t for _, t, _, _ in d] == [0x0C] and not blocks(mem, 0xC800, 7), f'D700 type {typ:02X}: {d}'
    print(f'door clear 7806: {done} C800 types on the ROM (flame at (X, Y - 9B33), 0E x4, 22h gone, 11h / 18h kept, CF40 untouched), 4 D700 types -> 0C PASS')


if __name__ == '__main__':
    main()

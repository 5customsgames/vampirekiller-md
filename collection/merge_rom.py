#!/usr/bin/env python3
"""Put Castlevania-MD (linked at 0) and Vampire Killer MD (linked at VK_BASE) in one ROM.

The ROM keeps Castlevania's header (vectors, name); only the ROM end and the checksum change.
"""
from pathlib import Path
import argparse
import struct

ROM_MAX = 4 * 1024 * 1024  # no mapper: the 68000 sees 4 MiB of cartridge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vk-base", type=lambda v: int(v, 0), required=True)
    parser.add_argument("castlevania")
    parser.add_argument("vampire_killer")
    parser.add_argument("output")
    args = parser.parse_args()

    cv = bytearray(Path(args.castlevania).read_bytes())
    vk = Path(args.vampire_killer).read_bytes()
    base = args.vk_base

    if cv[0x100:0x104] != b"SEGA":
        raise SystemExit(f"{args.castlevania} : pas d'en-tete SEGA")
    if len(cv) > base:
        raise SystemExit(f"Castlevania-MD fait {len(cv):#x} octets, plus que VK_BASE {base:#x} : "
                         "augmenter VK_BASE dans collection/collection.mk")
    # Vampire Killer's own vector table: stack, then its entry point inside its image.
    stack, entry = struct.unpack_from(">II", vk, 0)
    if not base <= entry < base + len(vk):
        raise SystemExit(f"Vampire Killer n'est pas lie a {base:#x} (point d'entree {entry:#x})")
    if base + len(vk) > ROM_MAX:
        raise SystemExit(f"Vampire Killer finit a {base + len(vk):#x}, au-dela de 4 Mio (pas de mapper)")

    rom = cv + b"\xFF" * (base - len(cv)) + vk
    rom += b"\xFF" * (ROM_MAX - len(rom))
    struct.pack_into(">I", rom, 0x1A4, len(rom) - 1)
    checksum = sum(w[0] for w in struct.iter_unpack(">H", memoryview(rom)[0x200:])) & 0xFFFF
    struct.pack_into(">H", rom, 0x18E, checksum)
    Path(args.output).write_bytes(rom)
    print(f"{args.output} : Castlevania {len(cv):#x} + Vampire Killer {len(vk):#x} a {base:#x}, "
          f"{len(rom) // 1024} Kio, somme {checksum:04X}, libre {ROM_MAX - base - len(vk):#x} apres Vampire Killer")


if __name__ == "__main__":
    main()

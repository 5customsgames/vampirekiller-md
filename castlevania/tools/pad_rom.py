#!/usr/bin/env python3
"""Finish a raw Mega Drive ROM at 2 or 2.5 MiB without truncating game data."""
from pathlib import Path
import argparse
import os
import stat
import struct
import tempfile

ROM_SIZES = (2 * 1024 * 1024, 5 * 1024 * 1024 // 2)


def pad_rom(path):
    path = Path(path)
    original = path.read_bytes()
    if len(original) > ROM_SIZES[-1]:
        raise ValueError(
            f"ROM trop grande : {len(original)} octets, maximum {ROM_SIZES[-1]}. "
            "Aucune donnee n'a ete tronquee."
        )
    if len(original) < 0x200 or original[0x100:0x104] != b"SEGA":
        raise ValueError("Le fichier n'est pas une ROM Mega Drive brute avec en-tete SEGA.")
    if struct.unpack_from(">I", original, 0x1A0)[0] != 0:
        raise ValueError("L'adresse de debut de cette ROM doit etre 0.")

    rom_size = next(size for size in ROM_SIZES if len(original) <= size)
    data = bytearray(original)
    data.extend(b"\xFF" * (rom_size - len(data)))
    struct.pack_into(">I", data, 0x1A4, rom_size - 1)
    checksum = sum(word[0] for word in struct.iter_unpack(">H", memoryview(data)[0x200:])) & 0xFFFF
    struct.pack_into(">H", data, 0x18E, checksum)

    if data != original:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as f:
                temporary = Path(f.name)
                f.write(data)
            temporary.chmod(stat.S_IMODE(path.stat().st_mode))
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    return rom_size - len(original), checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()
    try:
        padding, checksum = pad_rom(args.rom)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Padding ROM : {exc}\n")
    rom_size = args.rom.stat().st_size
    size_label = "2" if rom_size == ROM_SIZES[0] else "2,5"
    print(f"{args.rom}: {rom_size} octets ({size_label} Mio), padding FF +{padding}, checksum {checksum:04X}")


if __name__ == "__main__":
    main()

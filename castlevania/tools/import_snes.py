#!/usr/bin/env python3
"""Copy what the tools take from Rumbleminze's SNES port into tools/extracted/snes, once.

usage: import_snes.py <castlevania-snes>

The 16-bit art (tiles by Fiuke Bnuy) and the SNES port's palettes and room layouts have no licence that would let
them be redistributed, and the layouts are the NES game's data reworked: like the ROM's, they stay out of git
(tools/extracted/ is ignored). After this, the other tools read tools/extracted/snes and the SNES port's checkout
is no longer needed. Copied, under the same paths as in its src/:
- 16bit-tiles/tiles-16bit-<bank>.bin       the redrawn tiles, at the places of the NES tiles in their banks
- 16bit-tiles/{bg,sprite}_16bit_palette_<n>.bin
- level-layouts/<level>/{palette,level-layout,tile-groups}.bin   its 16-bit mode's bank 4 data and palettes
- palette_lookup.asm                       the 14 NES palettes of its options
- chrom-basic-intro-tiles.asm              the introduction's tiles
"""
import shutil
import sys
from pathlib import Path

FILES = ["palette_lookup.asm", "chrom-basic-intro-tiles.asm"]
GLOBS = ["16bit-tiles/tiles-16bit-[0-9].bin", "16bit-tiles/*_16bit_palette_[0-9][0-9].bin",
         "level-layouts/*/palette.bin", "level-layouts/*/level-layout.bin", "level-layouts/*/tile-groups.bin"]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]) / "src"
    dst = Path(__file__).resolve().parent / "extracted" / "snes"
    paths = [src / f for f in FILES] + [p for g in GLOBS for p in sorted(src.glob(g))]
    missing = [p for p in paths if not p.is_file()]
    if missing or len(paths) == len(FILES):
        sys.exit(f"not a castlevania-snes checkout: {src} (missing {', '.join(str(p) for p in missing) or 'the art'})")
    for p in paths:
        out = dst / p.relative_to(src)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, out)
    print(f"{len(paths)} files, {sum(p.stat().st_size for p in paths)} bytes -> {dst}")


if __name__ == "__main__":
    main()

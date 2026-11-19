"""Motif format of the music streams (tools/music_motif.py): the players decode the same frames.

Needs the reference ROM (VK_ROM_PATH, see tools/probe.py) and the z80 module; skipped otherwise.
- the generated files (sgdk/src/generated/msx_sound_md.c, msx_fm_md.c) are what
  tools/build_msx_sound_md.py writes today;
- for every music 80..8E, PSG, FM and drums, the reference player (music_motif.decode) gives the
  frames of the plain stream, step for step, over three passes of the loop;
- native: tests/music_motif_dump.c, built once on the plain streams and once on the packed ones
  with the same psg_core.c / psg_core_fm.c / fm_core.c, writes the same PSG bytes and YM2612 pairs
  at every step: every music alone in PSG and FM mode, and pseudo-random requests (effects,
  pause, FB/FC, fade, stop, music changes, PSG/FM switch). On a plain stream the players take the
  path they had before the motif format (no code is ever read), so this is the old decoding.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

try:
    import build_msx_sound_md as build
    import extract_msx_sound as ext
    import music_motif as motif
    from probe import load_rom, reference_rom
    ROM = load_rom(reference_rom())
except Exception:  # noqa: BLE001 - missing ROM or z80 module
    ROM = None

GENERATED = ('msx_sound_md.c', 'msx_sound_md.h', 'msx_fm_md.c', 'msx_fm_md.h')
STEPS = 12500               # > 3 x 4 062 frames (music 82): every music loops at least twice
SEEDS = range(1, 9)
_cache = {}


def extracted():
    if 'x' not in _cache:
        _cache['x'] = ext.extract(ROM)
    return _cache['x']


@unittest.skipIf(ROM is None, 'reference ROM or z80 module missing')
class MotifTests(unittest.TestCase):
    def test_reference_player_gives_the_plain_frames(self):
        for sound in extracted()['sounds']:
            sid = sound['id']
            if not build.is_music(sid):
                continue
            plain = [(motif.PSG, *build.encode(sound)[:2]), (motif.FM, *build.encode_fm(sound)[:2]),
                     (motif.PSG, *build.encode_noise(sound))]
            for fmt, stream, loop in plain:
                packed, packed_loop = motif.pack(fmt, stream, loop)
                self.assertLess(len(packed), len(stream), hex(sid))
                frames = len(fmt.split(stream))
                count = 3 * frames + 64
                want = motif.decode(fmt, stream, loop, count)
                self.assertEqual(len(want), count if loop != 0xFFFF else frames, hex(sid))
                self.assertEqual(motif.decode(fmt, packed, packed_loop, count), want, (hex(sid), fmt.name))

    def test_codes_follow_the_rules(self):
        # A CALL holding a code, or a loop frame inside a CALL/RUN, makes decode() fail or differ.
        fmt = motif.PSG
        frames = [bytes((1, 0x9F)), bytes((0,)), bytes((0,)), bytes((0,)), bytes((2, 0x81, 0x02))] * 3
        stream = b''.join(frames) + b'\xff'
        packed, loop = motif.pack(fmt, stream, sum(len(f) for f in frames[:6]))
        self.assertEqual(motif.decode(fmt, packed, loop, 60),
                         motif.decode(fmt, stream, sum(len(f) for f in frames[:6]), 60))
        with self.assertRaises(ValueError):
            motif.decode(fmt, bytes((0x20, 0x00, 1, 0xFF)), 0xFFFF, 2)   # CALL to itself

    def test_generated_files_and_native_players(self):
        cc = shutil.which('cc') or shutil.which('gcc')
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, flag in (('plain', False), ('packed', True)):
                out = tmp / name / 'generated'
                build.generate(out_dir=out, summary=out / 'msx_sounds.json', motif=flag, extracted=extracted())
            for f in GENERATED:
                self.assertEqual((tmp / 'packed/generated' / f).read_text(),
                                 (ROOT / 'sgdk/src/generated' / f).read_text(),
                                 f'{f} is not up to date: run tools/build_msx_sound_md.py')
            if not cc:
                self.skipTest('no C compiler')
            src = ROOT / 'sgdk/src'
            exe = {}
            for name in ('plain', 'packed'):
                gen = tmp / name
                exe[name] = tmp / f'dump_{name}'
                subprocess.run([cc, '-std=c99', '-O1', '-Wall', '-Wextra', '-Werror', '-I', str(gen), '-I', str(src),
                                '-I', str(src / 'generated'), str(ROOT / 'tests/music_motif_dump.c'),
                                str(src / 'psg_core.c'), str(src / 'psg_core_fm.c'), str(src / 'fm_core.c'),
                                str(gen / 'generated/msx_sound_md.c'), str(gen / 'generated/msx_fm_md.c'),
                                '-o', str(exe[name])], check=True)
            runs = [['songs', str(STEPS)]] + [['events', str(seed), '60000'] for seed in SEEDS]
            for args in runs:
                got = {name: subprocess.run([str(exe[name])] + args, check=True, capture_output=True,
                                            text=True).stdout for name in exe}
                if got['plain'] != got['packed']:
                    a, b = got['plain'].splitlines(), got['packed'].splitlines()
                    first = next(i for i, (x, y) in enumerate(zip(a + [''], b + [''])) if x != y)
                    self.fail(f'{args}: line {first}: plain {a[first:first + 1]} packed {b[first:first + 1]}')
                self.assertGreater(got['plain'].count('\n'), 50000)


if __name__ == '__main__':
    unittest.main()

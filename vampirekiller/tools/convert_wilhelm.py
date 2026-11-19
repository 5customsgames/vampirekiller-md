#!/usr/bin/env python3
"""Convert the Wilhelm scream (CC0) to the SGDK PCM resource of the port: signed 8-bit mono, 11 025 Hz.

Same FFmpeg chain as castlevania/tools/convert_wilhelm.py (volume 0.9, 3 ms fade in, triangular dither), with two
ROM savings (research/rom-budget.md 2.2): 11 025 Hz instead of 22 050 (99.9 % of the energy is under 5.3 kHz) and the
decay tail cut, the sound keeping 48 blocks of 256 bytes (1.115 s, the tail after 1.1 s is at most 3/127) with a 30 ms
fade out. main.c plays it with SOUND_PCM_RATE_11025: pitch and speed are those of the 22 050 Hz version.

  python3 tools/convert_wilhelm.py /path/Wilhelm_Scream.ogg      # writes sgdk/res/audio/wilhelm.pcm and wilhelm.json
  python3 tools/convert_wilhelm.py /path/Wilhelm_Scream.ogg --check

Source: https://upload.wikimedia.org/wikipedia/commons/d/d9/Wilhelm_Scream.ogg (sha256 in wilhelm.json).
"""
from pathlib import Path
import argparse, hashlib, json, subprocess

RATE = 11025
BLOCKS = 48            # 256-byte blocks kept: the SGDK Z80 PCM driver wants address and length aligned on 256
FADE_IN = .003
FADE_OUT = .03
SOURCE_SHA256 = '360097c9715f55abcc26ab73f12f69b730c660fbf019fc63caa685bfa9b6585b'


def convert(source):
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_sha != SOURCE_SHA256:
        raise SystemExit(f'unexpected source {source}: sha256 {source_sha}')
    samples = BLOCKS * 256
    duration = samples / RATE
    process = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(source), '-t', f'{duration:.6f}', '-af',
                              f'volume=0.9,afade=t=in:d={FADE_IN},afade=t=out:st={duration - FADE_OUT:.6f}:d={FADE_OUT},'
                              f'aresample={RATE}:dither_method=triangular',
                              '-ac', '1', '-ar', str(RATE), '-c:a', 'pcm_s8', '-f', 's8', 'pipe:1'], capture_output=True, check=True)
    data = process.stdout[:samples].ljust(samples, b'\0')
    info = dict(source_page='https://commons.wikimedia.org/wiki/File:Wilhelm_Scream.ogg',
                source_url='https://upload.wikimedia.org/wikipedia/commons/d/d9/Wilhelm_Scream.ogg',
                source_license='CC0, as indicated on the Commons file page',
                source_sha256=source_sha, sha256=hashlib.sha256(data).hexdigest(),
                rate=RATE, channels=1, bits=8, signed=True, samples=samples, bytes=len(data), seconds=len(data) / RATE,
                loop=False, alignment=256, fade_out=FADE_OUT,
                tool='tools/convert_wilhelm.py (FFmpeg)')
    return data, json.dumps(info, indent=2) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('source', type=Path)
    p.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'sgdk/res/audio')
    p.add_argument('--check', action='store_true', help='compare with the committed files instead of writing them')
    a = p.parse_args()
    data, info = convert(a.source)
    if a.check:
        assert (a.out / 'wilhelm.pcm').read_bytes() == data, 'wilhelm.pcm differs'
        assert (a.out / 'wilhelm.json').read_text() == info, 'wilhelm.json differs'
        print('wilhelm: CHECK PASS')
    else:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / 'wilhelm.pcm').write_bytes(data)
        (a.out / 'wilhelm.json').write_text(info)
        print(info, end='')


if __name__ == '__main__':
    main()

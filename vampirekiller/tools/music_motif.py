#!/usr/bin/env python3
"""Motif format of the music streams (research/rom-budget.md 2.1, research/audio-driver.md 6.1).

The music streams (PSG msx_sound_80..8e, FM msx_fm_80..8e, drums msx_fm_noise_80..8e) are packed
by tools/build_msx_sound_md.py: a sequence of frames already written earlier in the same stream
becomes a CALL (the player plays those frames from there, then comes back), a run of identical
empty frames becomes a RUN (the same thing into a fixed table of empty frames, vk_psg_runs of
psg_core.c). The player decodes exactly the frames of the plain stream: same bytes, same order,
same loop frame.

Codes (the first byte of a plain frame is never one of these):

PSG streams (plain header: bits 0-4 count 0..31, bit 5 clear, bit 6 NOTE_C, bit 7 LOCK; the
converter writes at most 14 bytes a frame); a code has bit 5 set:
    0xFF                end of the stream (unchanged)
    001o oooo, o, n     CALL: the n frames (1..255) at byte offset o (13 bits, < 0x2000)
    011k kkkk           RUN: k + 1 empty frames (1..32) of header 0x00
    101k kkkk           RUN: k + 1 empty frames (1..32) of header 0x40 (NOTE_C)
    111k kkkk           RUN: k + 1 empty frames (1..31) of header 0x80 (LOCK); 0xFF is the end
    (an empty frame of header 0xC0 stays plain)
FM streams (count byte n 0..63, then n register/value pairs):
    0xFF                end of the stream (unchanged)
    0x80..0xFE, hi, lo  CALL: b - 0x7F frames (1..127) at byte offset hi:lo
    0x40..0x7F          RUN: (b & 0x3F) + 1 empty frames (count 0)

Rules kept by the packer, so that the player stays at one level and costs one test a frame:
- a CALL points at frames written as plain frames, one after the other (never at a CALL or a RUN):
  inside a CALL the player never meets a code, there is at most one return address;
- the loop frame starts a code (plain frame, CALL or RUN) of the top level: no CALL or RUN runs
  across it; after 0xFF the player jumps there and reads that code;
- a CALL or a RUN never holds the end (0xFF).
Per frame the player reads at most: 0xFF (loop), then one CALL or RUN, then one plain frame.
"""

END = 0xFF
PSG_CODE = 0x20             # bit 5 of a PSG header
PSG_CALL_OFFSET_MAX = 0x2000
PSG_RUN_HEADERS = (0x00, 0x40, 0x80)   # RUN types 1, 2, 3 (bits 7-6 of the code)
FM_CALL = 0x80
FM_RUN = 0x40
FM_RUN_MAX = 64


class Format:
    def __init__(self, name, call_size, call_max, run_size):
        self.name, self.call_size, self.call_max, self.run_size = name, call_size, call_max, run_size

    def split(self, stream):
        """Frames (bytes, header included) of a plain stream, up to its end byte."""
        frames, i = [], 0
        while stream[i] != END:
            size = 1 + self.payload(stream[i])
            frames.append(bytes(stream[i:i + size]))
            i += size
        if i != len(stream) - 1:
            raise ValueError(f'{self.name}: bytes after the end')
        return frames

    def is_code(self, first):
        return bool(first & PSG_CODE) if self.name == 'psg' else first >= 0x40

    def payload(self, first):
        if self.is_code(first):
            raise ValueError(f'{self.name}: first byte {first:02X} of a plain frame is a code')
        return first & 0x1F if self.name == 'psg' else 2 * first

    def run_max(self, frame):
        """Longest RUN of this frame, 0 if a RUN cannot repeat it."""
        if len(frame) != 1:
            return 0
        if self.name == 'fm':
            return FM_RUN_MAX
        if frame[0] not in PSG_RUN_HEADERS:
            return 0
        return 31 if frame[0] == 0x80 else 32

    def call(self, offset, frames):
        assert 1 <= frames <= self.call_max
        if self.name == 'psg':
            assert offset < PSG_CALL_OFFSET_MAX
            return bytes((PSG_CODE | offset >> 8, offset & 0xFF, frames))
        assert offset < 0x10000
        return bytes((FM_CALL + frames - 1, offset >> 8, offset & 0xFF))

    def call_ok(self, offset):
        return offset < (PSG_CALL_OFFSET_MAX if self.name == 'psg' else 0x10000)

    def run(self, frame, frames):
        assert 1 <= frames <= self.run_max(frame)
        if self.name == 'psg':
            kind = PSG_RUN_HEADERS.index(frame[0]) + 1
            return bytes((kind << 6 | PSG_CODE | (frames - 1),))
        return bytes((FM_RUN + frames - 1,))


PSG = Format('psg', 3, 255, 1)
FM = Format('fm', 3, 127, 1)


def pack(fmt, stream, loop):
    """Plain stream + loop byte offset (0xFFFF: none) -> packed stream + its loop byte offset.
    Greedy: at each frame the code that saves the most bytes (longest CALL, or RUN), else the
    plain frame."""
    frames = fmt.split(stream)
    loop_frame = None
    if loop != 0xFFFF:
        offsets, o = [], 0
        for f in frames:
            offsets.append(o)
            o += len(f)
        loop_frame = offsets.index(loop)
    out = bytearray()
    # Plain frames written so far: (content, byte offset, segment); the frames of one segment
    # follow each other in the packed stream. index: (frame, next frame) -> first of the pair.
    lit, index = [], {}
    segment = 0
    packed_loop = 0xFFFF
    i, n = 0, len(frames)
    while i < n:
        if i == loop_frame:
            packed_loop = len(out)
            segment += 1
        limit = (loop_frame if loop_frame is not None and i < loop_frame else n) - i
        best, best_code, best_len = 0, None, 0
        run_max = min(limit, fmt.run_max(frames[i]))
        if run_max:
            k = 1
            while k < run_max and frames[i + k] == frames[i]:
                k += 1
            if k - fmt.run_size > best:
                best, best_code, best_len = k - fmt.run_size, fmt.run(frames[i], k), k
        if limit >= 2:
            for j in index.get((frames[i], frames[i + 1]), ()):
                seg, offset = lit[j][2], lit[j][1]
                if not fmt.call_ok(offset):
                    continue
                k, size = 0, 0
                top = min(limit, fmt.call_max)
                while k < top and j + k < len(lit) and lit[j + k][2] == seg and lit[j + k][0] == frames[i + k]:
                    size += len(frames[i + k])
                    k += 1
                if size - fmt.call_size > best:
                    best, best_code, best_len = size - fmt.call_size, fmt.call(offset, k), k
        if best_code is not None:
            out += best_code
            segment += 1
            i += best_len
            continue
        lit.append((frames[i], len(out), segment))
        if len(lit) >= 2 and lit[-2][2] == segment:
            index.setdefault((lit[-2][0], frames[i]), []).append(len(lit) - 2)
        out += frames[i]
        i += 1
    out.append(END)
    return bytes(out), packed_loop


def decode(fmt, stream, loop, count):
    """Reference player, step for step as music_frame of psg_core.c / fm_core.c: the frames (bytes,
    header included) of `count` steps, fewer if the stream ends without a loop. A plain stream
    decodes the same way (it holds no code)."""
    out = []
    c, ret, left, table = 0, 0, 0, None
    while len(out) < count:
        if table is None:
            b = stream[c]
            if fmt.is_code(b):
                if b == END:
                    if loop == 0xFFFF:
                        return out
                    c = loop
                    b = stream[c]
                if fmt.name == 'psg' and b & PSG_CODE:
                    if b & 0xC0:
                        ret, left, table = c + 1, (b & 0x1F) + 1, PSG_RUN_HEADERS[(b >> 6) - 1]
                    else:
                        ret, left, c = c + 3, stream[c + 2], (b & 0x1F) << 8 | stream[c + 1]
                elif fmt.name == 'fm' and b >= FM_CALL:
                    ret, left, c = c + 3, b - 0x7F, stream[c + 1] << 8 | stream[c + 2]
                elif fmt.name == 'fm' and b >= FM_RUN:
                    ret, left, table = c + 1, (b & 0x3F) + 1, 0
                if table is None and fmt.is_code(stream[c]):
                    raise ValueError(f'{fmt.name}: code {stream[c]:02X} at {c} reached from a code')
        if table is not None:
            out.append(bytes((table,)))
        else:
            size = 1 + fmt.payload(stream[c])
            out.append(bytes(stream[c:c + size]))
            c += size
        if left:
            left -= 1
            if not left:
                c, table = ret, None
    return out

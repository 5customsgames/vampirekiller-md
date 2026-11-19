#!/usr/bin/env python3
"""LZ4W packing of generated data with the SGDK packer (sgdk/bin/lz4w.jar), for the generators and their checks.

pack_many(blobs) -> list of packed streams (what `lz4w_unpack(src, dest)` of SGDK reads: the stream carries
its own end marker, sgdk.lz4w.LZ4W.pack(data, 0, true) as rescomp does); every stream is checked by unpacking it
again with the jar.  unpack_many(streams) -> list of bytes.  Needs `java` and `javac` (the same as the SGDK build).

Streams are read by the 68000 with word accesses (literals, matches in the stream itself): the generated C
arrays holding them must be aligned on 2 (`ALIGN2` below).  They are padded to an even length here.
"""
import os
import subprocess
import tempfile
from pathlib import Path

GDK = Path(os.environ.get('GDK', Path(__file__).resolve().parents[2] / 'sgdk'))

JAVA = r"""
import java.nio.file.*;
import java.util.*;
public class Lz4wBatch {
    static byte[] unhex(String s) { byte[] b = new byte[s.length() / 2];
        for (int i = 0; i < b.length; i++) b[i] = (byte) Integer.parseInt(s.substring(2 * i, 2 * i + 2), 16); return b; }
    static String hex(byte[] b) { StringBuilder s = new StringBuilder(); for (byte x : b) s.append(String.format("%02x", x & 255)); return s.toString(); }
    public static void main(String[] a) throws Exception {
        List<String> out = new ArrayList<>();
        for (String line : Files.readAllLines(Paths.get(a[0]))) out.add(hex(sgdk.lz4w.LZ4W.pack(unhex(line.trim()), 0, true)));
        Files.write(Paths.get(a[1]), out);
    }
}
"""


def _pack_java(blobs):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cp = str(GDK / 'bin' / 'lz4w.jar')
        (tmp / 'Lz4wBatch.java').write_text(JAVA)
        subprocess.run(['javac', '-cp', cp, '-d', str(tmp), str(tmp / 'Lz4wBatch.java')], check=True)
        (tmp / 'in.txt').write_text(''.join(bytes(b).hex() + '\n' for b in blobs))
        subprocess.run(['java', '-cp', f'{cp}:{tmp}', 'Lz4wBatch', str(tmp / 'in.txt'), str(tmp / 'out.txt')],
                       check=True, capture_output=True)
        return [bytes.fromhex(line) for line in (tmp / 'out.txt').read_text().split('\n') if line]


def unpack(p):
    """lz4w_unpack of sgdk/src/tools_a.s: segments `LLLL MMMM OOOOOOOO` (big-endian word), LLLL literal words;
    MMMM > 0: copy MMMM + 1 words from (OOOOOOOO + 1) words back; MMMM = 0 and OOOOOOOO > 0: OOOOOOOO + 2 words
    from the long offset word that follows (bit 15: the source is the packed stream, else the output); all zero: end,
    then a last word whose bit 15 says that its low byte is one more output byte."""
    out = bytearray()
    i = 0
    while True:
        seg = (p[i] << 8) | p[i + 1]
        i += 2
        lit, mat, off = seg >> 12, (seg >> 8) & 15, seg & 255
        out += p[i:i + 2 * lit]
        i += 2 * lit
        if mat:
            src, n = len(out) - 2 * (off + 1), mat + 1
            for k in range(2 * n):
                out.append(out[src + k])
        elif off:
            v = (p[i] << 8) | p[i + 1]
            i += 2
            d = (v << 1) & 0xFFFF
            d -= 0x10000 if d & 0x8000 else 0
            n = off + 2
            if v & 0x8000:
                src = i - 2 + d
                out += p[src:src + 2 * n]
            else:
                src = len(out) - 2 + d
                for k in range(2 * n):
                    out.append(out[src + k])
        elif not lit:
            break
    w = (p[i] << 8) | p[i + 1]
    if w & 0x8000:
        out.append(w & 0xFF)
    return bytes(out)


def unpack_many(streams):
    return [unpack(s) for s in streams]


def pack_many(blobs):
    blobs = [bytes(b) for b in blobs]
    packed = _pack_java(blobs)
    for b, p in zip(blobs, unpack_many(packed)):
        if p != b:
            raise RuntimeError('LZ4W round trip failed')
    return [p + b'\0' if len(p) & 1 else p for p in packed]


def c_bytes(data, per_line=32):
    return ',\n'.join('    ' + ','.join(str(v) for v in data[i:i + per_line]) for i in range(0, len(data), per_line))

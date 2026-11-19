#!/usr/bin/env python3
"""Run a Mega Drive ROM headless in a libretro core and save a screenshot.

usage: md_shot.py <rom.bin> <out.png> [--frames N] [--press BTN@FRAME+LEN ...] [--shot FRAME ...] [--reset FRAME ...] [--wav OUT.wav] [--core PATH]
  BTN: up down left right a b c x y z mode start (MD buttons; x y z mode need a six-button pad). --shot saves OUT with _FRAME before .png
Default core: /usr/lib/libretro/genesis_plus_gx_libretro.so
"""
import argparse, ctypes as C, struct, zlib
from pathlib import Path

RETRO_ENVIRONMENT_SET_PIXEL_FORMAT = 10


class SystemAvInfo(C.Structure):
    _fields_ = [("base_width", C.c_uint), ("base_height", C.c_uint), ("max_width", C.c_uint), ("max_height", C.c_uint),
                ("aspect_ratio", C.c_float), ("fps", C.c_double), ("sample_rate", C.c_double)]


class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p), ("size", C.c_size_t), ("meta", C.c_char_p)]


def write_png(path, w, h, rgb):
    raw = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("out")
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--press", action="append", default=[])
    ap.add_argument("--shot", type=int, action="append", default=[])
    ap.add_argument("--reset", type=int, action="append", default=[], help="press RESET before this frame")
    ap.add_argument("--wav", help="also save the sound to this WAV file")
    ap.add_argument("--core", default="/usr/lib/libretro/genesis_plus_gx_libretro.so")
    a = ap.parse_args()

    core = C.CDLL(a.core)
    state = {"fmt": 0, "frame": None}

    ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
    VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
    AUDIO = C.CFUNCTYPE(C.c_size_t, C.c_int16, C.c_int16)
    BATCH = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
    POLL = C.CFUNCTYPE(None)
    INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

    ids = {"b": 0, "a": 1, "c": 8, "start": 3, "up": 4, "down": 5, "left": 6, "right": 7, "x": 10, "y": 9, "z": 11, "mode": 2}
    presses = []
    for p in a.press:
        name, rest = p.split("@")
        f, ln = rest.split("+")
        presses.append((ids[name.lower()], int(f), int(f) + int(ln)))
    cur = {"frame": 0}

    def input_state(port, device, index, bid):
        if port != 0 or device & 0xFF != 1:
            return 0
        return 1 if any(b == bid and s <= cur["frame"] < e for b, s, e in presses) else 0

    def env(cmd, data):
        if cmd == RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
            state["fmt"] = C.cast(data, C.POINTER(C.c_int)).contents.value
            return True
        return False

    def video(data, w, h, pitch):
        if data:
            state["frame"] = (w, h, C.string_at(data, pitch * h), pitch)

    audio = bytearray()

    def batch(data, n):
        if a.wav:
            audio.extend(C.string_at(data, n * 4))      # n stereo frames of 16-bit samples
        return n

    cbs = [ENV(env), VIDEO(video), AUDIO(lambda l, r: 1), BATCH(batch), POLL(lambda: None),
           INPUT(input_state)]
    core.retro_set_environment(cbs[0])
    core.retro_set_video_refresh(cbs[1])
    core.retro_set_audio_sample(cbs[2])
    core.retro_set_audio_sample_batch(cbs[3])
    core.retro_set_input_poll(cbs[4])
    core.retro_set_input_state(cbs[5])
    core.retro_init()
    data = Path(a.rom).read_bytes()
    buf = C.create_string_buffer(data, len(data))
    info = GameInfo(a.rom.encode(), C.cast(buf, C.c_void_p), len(data), None)
    if not core.retro_load_game(C.byref(info)):
        raise SystemExit("core refused the ROM")
    core.retro_set_controller_port_device(0, 0x201)   # six-button pad (Genesis Plus GX's subclass 1 of JOYPAD)
    def save(path):
        w, h, raw, pitch = state["frame"]
        rgb = bytearray()
        for y in range(h):
            row = raw[y * pitch:y * pitch + w * (4 if state["fmt"] == 1 else 2)]
            if state["fmt"] == 1:   # XRGB8888
                for x in range(w):
                    rgb += bytes((row[x * 4 + 2], row[x * 4 + 1], row[x * 4]))
            else:                   # RGB565
                for x in range(w):
                    v = row[x * 2] | (row[x * 2 + 1] << 8)
                    rgb += bytes(((v >> 11) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31))
        write_png(path, w, h, bytes(rgb))
        return w, h

    for f in range(a.frames):
        cur["frame"] = f
        if f in a.reset:
            core.retro_reset()
        core.retro_run()
        if f + 1 in a.shot:
            save(str(Path(a.out).with_suffix("")) + f"_{f + 1}.png")
    w, h = save(a.out)
    print(f"{w}x{h} fmt={state['fmt']} -> {a.out}")
    if a.wav:
        import wave
        av = SystemAvInfo()
        core.retro_get_system_av_info(C.byref(av))
        with wave.open(a.wav, "wb") as wf:
            wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(int(av.sample_rate))
            wf.writeframes(bytes(audio))
        print(f"{len(audio) // 4} audio frames at {int(av.sample_rate)} Hz -> {a.wav}")
    core.retro_unload_game()
    core.retro_deinit()


if __name__ == "__main__":
    main()

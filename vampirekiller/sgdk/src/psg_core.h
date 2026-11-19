#ifndef VK_PSG_CORE_H
#define VK_PSG_CORE_H

/* Music and effects on the one SN76489, with the channel rules of the MSX2
 * sound driver (research/audio-driver.md). No SGDK dependency: tested natively
 * (tests/test_psg_core.c); psg_player.c writes the bytes to the PSG port.
 *
 * Streams come from tools/build_msx_sound_md.py (generated/msx_sound_md.c): per
 * 60 Hz frame, a header (bits 0-5 byte count, bit 6 music note on channel C,
 * bit 7 effects locked) then the SN bytes; 0xFF ends the stream, which goes on
 * at byte `loop` or stops when loop is 0xFFFF. A frame has at most 31 bytes:
 * bit 5 of a header is clear.
 *
 * The music streams are packed in the motif format (tools/music_motif.py,
 * research/audio-driver.md): a first byte with bit 5 set is a code, read by the
 * music voice only (effects, FB and FD are plain streams):
 *   001ooooo oooooooo n   CALL: the n frames at byte offset o of the same stream,
 *                         then back after the code (one level: a CALL points at
 *                         plain frames only);
 *   tt1kkkkk (tt = 01, 10, 11)  RUN: k + 1 empty frames of header 00, 40, 80
 *                         (vk_psg_runs[tt - 1], a CALL into that table).
 * The loop frame starts a code; a CALL or a RUN never holds the end. Per frame
 * the music voice reads at most the end, one code and one plain frame.
 *
 * MSX rules kept (bank 0 request 509F, bank 14 driver 8964):
 * - an effect plays on AY channel C (SN tone 2) and the noise; music channel C
 *   is muted from the effect start (8A85) until its first note after the effect
 *   end (8AF1-8B00); the other music channels go on;
 * - an effect is accepted if no effect plays or its id >= the current one
 *   (5172-5179), and never while a music has locked effects (C0A8, 516B);
 * - FB (5276, object 0A) freezes the music channels (C098 bit 1) and loops the
 *   timed item stream on AY channel A (SN tone 0); effects still play on C. FC
 *   (52C9) gives the music back where it was;
 * - a music request ends the current effect (5118), the lock (5131) and FB (5122);
 *   request 00 stops everything (5085); FF fades the music out (C0A5/C0A6). */

typedef unsigned char VKPsgByte;
typedef unsigned short VKPsgWord;

typedef struct {
    const VKPsgByte *data;
    VKPsgWord loop;              /* byte offset of the loop frame, 0xFFFF: no loop */
} VKSoundStream;

#define VK_PSG_NO_LOOP 0xFFFF
#define VK_PSG_FRAME_END 0xFF
#define VK_PSG_NOTE_C 0x40
#define VK_PSG_LOCK 0x80
#define VK_PSG_COUNT_MASK 0x3F
#define VK_PSG_MOTIF_CODE 0x20      /* header bit 5: CALL or RUN (music streams) */
#define VK_PSG_RUN_FRAMES 64        /* frames in a row of vk_psg_runs (FM RUNs use row 0) */
/* Fade: C0A6 drops by one AY step (3 dB) every 0x3A frames; at -16 the music stops. */
#define VK_PSG_FADE_FRAMES 0x3A
#define VK_PSG_FADE_STEPS 16
/* Largest output of one frame: two streams of at most 63 bytes, plus restores. */
#define VK_PSG_OUT_MAX 160

typedef struct {
    const VKSoundStream *stream;
    const VKPsgByte *cursor;
    VKPsgByte playing;
} VKPsgVoice;

typedef struct {
    VKPsgVoice music;
    VKPsgVoice effect;
    VKPsgByte music_id;          /* MSX id of the music (80..8E), 0 for none */
    VKPsgByte effect_id;         /* C096: MSX id of the playing effect, 0 for none */
    VKPsgByte last_effect;       /* last accepted effect id (harness, sound test) */
    VKPsgWord effect_count;      /* accepted effect requests (harness) */
    VKPsgByte lock;              /* C0A8 */
    VKPsgByte c_muted;           /* music channel C (tone 2 + noise) held silent */
    VKPsgByte fade_steps;        /* -C0A6 */
    VKPsgByte fade_timer;        /* C0A5 */
    VKPsgByte tone[3][2];        /* last music latch and data byte per tone channel */
    VKPsgByte volume[4];         /* last music volume byte per channel */
    VKPsgByte noise;             /* last music noise control byte, 0 = none yet */
    VKPsgByte pending;           /* channel of the last music tone latch */
    VKPsgByte effect_new;        /* the effect starts this frame: clear its channels */
    VKPsgVoice pause;            /* FD jingle (C01A), the only voice while paused */
    VKPsgByte paused;            /* C098 bit 0 */
    VKPsgByte pause_edge;        /* 1: silence everything (FD), 2: restore (FE) */
    VKPsgVoice timer;            /* FB loop (C018), on tone 0 while timed */
    VKPsgByte timed;             /* C098 bit 1 */
    VKPsgByte timer_edge;        /* 1: music channels silent (FB), 2: restore (FC), 3: tone 0 silent */
    /* Motif format of the music stream (after the fields above: the harness reads their offsets). */
    const VKPsgByte *motif_ret;  /* where the CALL or RUN being played goes back to */
    VKPsgByte motif_left;        /* frames left in that CALL or RUN, 0: none */
} VKPsg;

/* Empty frames repeated by a RUN: rows of headers 00, 40, 80 (the FM RUNs use row 0, count 0). */
extern const VKPsgByte vk_psg_runs[3][VK_PSG_RUN_FRAMES];

void vk_psg_core_reset(VKPsg *p);
/* Requests (509F). Each returns 1 when the driver takes it. */
int vk_psg_core_music(VKPsg *p, const VKSoundStream *s, VKPsgByte id);
int vk_psg_core_effect(VKPsg *p, const VKSoundStream *s, VKPsgByte id);
void vk_psg_core_stop(VKPsg *p);
void vk_psg_core_fade(VKPsg *p);
/* FD (51C4): every channel silent, music and effect frozen, the pause jingle s
 * alone. FE (522D): the music channels come back where they were. */
void vk_psg_core_pause(VKPsg *p, const VKSoundStream *s);
void vk_psg_core_resume(VKPsg *p);
/* FB (5276): the music channels stop where they are, s loops on tone 0 and the
 * effects go on. FC (52C9): the music channels come back. FC without FB does
 * nothing here (the MSX would write back the registers saved by the last FB). */
void vk_psg_core_timer(VKPsg *p, const VKSoundStream *s);
void vk_psg_core_timer_end(VKPsg *p);
/* Bytes to silence the PSG (written by a stop). */
int vk_psg_core_silence(VKPsgByte *out);
/* One 60 Hz frame: fills out with the PSG bytes to write, returns their count. */
int vk_psg_core_frame(VKPsg *p, VKPsgByte *out);

#endif

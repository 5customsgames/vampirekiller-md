#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "psg_core.h"
#include "fm_core.h"
#include "generated/msx_fm_md.h"

/* What the sound cores write, frame by frame, for tests/test_music_motif.py: the same program is
 * compiled against the plain streams and against the motif streams (tools/music_motif.py), and
 * the two outputs must be equal. One line per 60 Hz step: "<step> <hash>" of the PSG bytes and
 * the YM2612 pairs of that step (FNV-1a, with their counts).
 *
 *   music_motif_dump songs STEPS      every music 80..8E alone, PSG mode then FM mode, STEPS steps
 *   music_motif_dump events SEED STEPS   pseudo-random requests (music, effects, pause, FB, fade,
 *                                        stop, PSG/FM switch) as psg_player.c makes them
 */
static VKPsg p;
static VKFm fm;
static int fm_mode;
static unsigned long rng;

static unsigned hash_bytes(unsigned h, const VKPsgByte *b, int n)
{
    int i;
    h = (h ^ (unsigned)n) * 16777619u;
    for (i = 0; i < n; i++) h = (h ^ b[i]) * 16777619u;
    return h;
}

static unsigned silence_pairs(unsigned h)
{
    VKPsgByte keys[6];
    return hash_bytes(h ^ 0x5A5A5A5Au, keys, vk_fm_core_silence(keys));
}

/* psg_player.c, the requests and the V-Int step, without the SGDK calls. */
static unsigned request_music(unsigned h, int id)
{
    if (fm_mode && vk_fm_music[id - 0x80].data)
    {
        if (vk_psg_core_music(&p, &vk_fm_noise[id - 0x80], (VKPsgByte)id))
        {
            if (fm.active) h = silence_pairs(h);
            vk_fm_core_start(&fm, &vk_fm_music[id - 0x80]);
        }
    }
    else if (vk_psg_core_music(&p, &vk_msx_music[id - 0x80], (VKPsgByte)id) && fm.run)
    {
        vk_fm_core_cancel(&fm);
        h = silence_pairs(h);
    }
    return h;
}

static unsigned step(void)
{
    VKPsgByte out[VK_PSG_OUT_MAX];
    unsigned h = 2166136261u;
    int n;
    fm.n = 0;
    if (!fm_mode) n = vk_psg_core_frame(&p, out);
    else if (fm.run) n = vk_fm_core_step(&fm, &p, out);
    else n = vk_psg_core_fm_frame(&p, out);
    h = hash_bytes(h, out, n);
    return hash_bytes(h, fm.out, 2 * fm.n);
}

static void reset(int mode)
{
    vk_psg_core_reset(&p);
    vk_fm_core_reset(&fm);
    fm_mode = mode;
}

static unsigned next(unsigned bound)
{
    rng = rng * 1103515245ul + 12345ul;
    return (unsigned)((rng >> 16) & 0x7FFF) % bound;
}

static unsigned random_request(unsigned h)
{
    const unsigned r = next(100);
    VKPsgByte bytes[4];
    if (r < 45)
    {
        const unsigned e = 1 + next(VK_MSX_EFFECT_SLOTS - 1);
        vk_psg_core_effect(&p, &vk_msx_effects[e], (VKPsgByte)e);
    }
    else if (r < 60) h = request_music(h, 0x80 + (int)next(VK_MSX_MUSIC_SLOTS - 1));
    else if (r < 67) vk_psg_core_pause(&p, &vk_msx_pause);
    else if (r < 75) vk_psg_core_resume(&p);
    else if (r < 80) vk_psg_core_timer(&p, &vk_msx_timed_item);
    else if (r < 86) vk_psg_core_timer_end(&p);
    else if (r < 91) vk_psg_core_fade(&p);
    else if (r < 94)
    {
        vk_psg_core_stop(&p);
        h = hash_bytes(h, bytes, vk_psg_core_silence(bytes));
        vk_fm_core_cancel(&fm);
        if (fm.inited) h = silence_pairs(h);
    }
    else if (r < 97)
    {
        vk_psg_core_music(&p, next(2) ? &vk_msx_timed_item : &vk_msx_pause, 0);
        if (fm.run) { vk_fm_core_cancel(&fm); h = silence_pairs(h); }
    }
    else
    {
        fm_mode = !fm_mode;
        if (fm_mode && !fm.inited) { fm.n = 0; vk_fm_core_init(&fm); h = hash_bytes(h, fm.out, 2 * fm.n); }
    }
    return h;
}

int main(int argc, char **argv)
{
    long s, steps;
    int id, mode;
    if (argc == 3 && !strcmp(argv[1], "songs"))
    {
        steps = atol(argv[2]);
        for (mode = 0; mode < 2; mode++)
            for (id = 0x80; id < 0x80 + VK_MSX_MUSIC_SLOTS - 1; id++)
            {
                reset(mode);
                printf("music %02X mode %d %08X\n", id, mode, request_music(0, id));
                for (s = 0; s < steps; s++) printf("%ld %08X\n", s, step());
            }
        return 0;
    }
    if (argc == 4 && !strcmp(argv[1], "events"))
    {
        rng = strtoul(argv[2], 0, 10);
        steps = atol(argv[3]);
        reset((int)(rng & 1));
        for (s = 0; s < steps; s++)
        {
            unsigned h = 0;
            while (next(30) == 0) h = random_request(h);
            printf("%ld %08X %08X\n", s, h, step());
        }
        return 0;
    }
    fprintf(stderr, "usage: music_motif_dump songs STEPS | events SEED STEPS\n");
    return 2;
}

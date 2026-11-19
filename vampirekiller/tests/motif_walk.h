#ifndef VK_TEST_MOTIF_WALK_H
#define VK_TEST_MOTIF_WALK_H
#include <assert.h>
#include "psg_core.h"

/* Frame count of a stream in the motif format (tools/music_motif.py, psg_core.h, fm_core.h), with
 * the rules the players rely on: a CALL points back at plain frames only, the loop offset starts a
 * code of the top level. fm = 1: FM stream (count byte then pairs), else a PSG stream. */
static inline int vk_test_plain_size(const VKPsgByte *c, int fm)
{
    if (fm) { assert(*c < 0x40); return 1 + 2 * *c; }
    assert(!(*c & VK_PSG_MOTIF_CODE));
    return 1 + (*c & VK_PSG_COUNT_MASK);
}

static inline int vk_test_motif_frames(const VKSoundStream *s, int fm, int codes_allowed)
{
    const VKPsgByte *c = s->data;
    int frames = 0, loop_ok = s->loop == VK_PSG_NO_LOOP;
    while (*c != VK_PSG_FRAME_END)
    {
        const VKPsgByte *here = c;
        const int code = fm ? *c >= 0x40 : (*c & VK_PSG_MOTIF_CODE) != 0;
        int call = 0, offset = 0, k;
        if ((unsigned)(c - s->data) == s->loop) loop_ok = 1;
        if (!code)
        {
            c += vk_test_plain_size(c, fm);
            frames++;
            continue;
        }
        assert(codes_allowed);
        if (fm && *c >= 0x80) { call = *c - 0x7F; offset = c[1] << 8 | c[2]; c += 3; }
        else if (!fm && !(*c & 0xC0)) { call = c[2]; offset = (*c & 0x1F) << 8 | c[1]; c += 3; }
        else { frames += (*c & (fm ? 0x3F : 0x1F)) + 1; c++; continue; }
        {
            const VKPsgByte *t = s->data + offset;
            assert(call >= 1);
            for (k = 0; k < call; k++) t += vk_test_plain_size(t, fm);
            assert(t <= here);         /* frames written before the CALL */
        }
        frames += call;
    }
    assert(loop_ok);
    return frames;
}

#endif

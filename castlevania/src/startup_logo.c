#include <genesis.h>
#include "startup_logo.h"
#include "sound.h"
#include "miku_mode.h"
#include "startup_audio.h"
#include "startup_logo_duration.h"
#include "startup_logo_data.inc"

// Acknowledge the unlock once, without replacing the audio V-Int callback.
// Only the transparent backdrop color changes; the logo's other colors stay intact.
static void startup_logo_check_code(u16 pad)
{
    bool already_enabled = MIKU_enabled();
    MIKU_code_update(pad);
    if (already_enabled || !MIKU_enabled()) return;
    u16 interval = (SYS_isPAL() ? 50 : 60) / 10;
    for (u8 phase = 0; phase < 4; phase++)
    {
        PAL_setColor(0, (phase & 1) ? 0x0000 : 0x0880);
        for (u16 frame = 0; frame < interval; frame++) SYS_doVBlankProcess();
    }
    PAL_setColor(0, 0x0000);
}

// Tiles select one of four CRAM palettes for the centered original logo.
// No raster interrupt is needed, so the audio V-Int callback stays untouched.
static void startup_logo_fade(u16 frames, bool fade_in)
{
    u16 colors[64];
    for (u16 frame = 1; frame <= frames; frame++)
    {
        u16 amount = (frame * 32) / frames;
        if (!fade_in) amount = 32 - amount;
        for (u16 i = 0; i < 64; i++)
        {
            u16 c = startup_logo_palette[i];
            u16 r = (((c >> 1) & 7) * amount) >> 5;
            u16 g = (((c >> 5) & 7) * amount) >> 5;
            u16 b = (((c >> 9) & 7) * amount) >> 5;
            colors[i] = (b << 9) | (g << 5) | (r << 1);
        }
        SYS_doVBlankProcess();
        startup_logo_check_code(JOY_readJoypad(JOY_1));
        PAL_setColors(0, colors, 64, CPU);
    }
}

void startup_logo_show(void)
{
    static const u16 black[64] = { 0 };
    const u16 fps = SYS_isPAL() ? 50 : 60;
    MIKU_reset(JOY_readJoypad(JOY_1));
    music_stop();
    SND_PCM_stopPlay();
    VDP_setEnable(FALSE);
    VDP_setScreenWidth256();
    VDP_setWindowOff();
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 0);
    VDP_setVerticalScroll(BG_A, 0);
    VDP_setVerticalScroll(BG_B, 0);
    VDP_setBackgroundColor(0);
    VDP_setSpriteFull(0, 0, 0, SPRITE_SIZE(1, 1), 0, 0);
    VDP_updateSprites(1, DMA);
    PAL_setColors(0, black, 64, DMA);
    VDP_loadTileData(startup_logo_tiles, TILE_USER_INDEX, STARTUP_LOGO_TILES, DMA);
    VDP_setTileMapDataRectEx(BG_A, startup_logo_map, TILE_USER_INDEX, 0, 0, 32, 28, 32, CPU);
    VDP_setEnable(TRUE);

    startup_logo_fade(fps / 2, TRUE);
    SND_PCM_startPlay(presented_by_5customs_pcm, sizeof(presented_by_5customs_pcm),
                      SOUND_PCM_RATE_16000, SOUND_PAN_CENTER, FALSE);
    const u16 hold = (STARTUP_VOICE_SAMPLES * fps + STARTUP_VOICE_RATE - 1) / STARTUP_VOICE_RATE + fps / 3;
    u16 prev = JOY_readJoypad(JOY_1);
    for (u16 frame = 0; frame < hold + fps * 6; frame++)
    {
        if (frame >= hold && !MIKU_code_active()) break;
        SYS_doVBlankProcess();
        u16 pad = JOY_readJoypad(JOY_1);
        startup_logo_check_code(pad);
        if (frame >= hold && !MIKU_code_active()) break;
        if (pad & ~prev & BUTTON_START) break;
        prev = pad;
    }
    startup_logo_fade((fps * 3) / 5, FALSE);
    SND_PCM_stopPlay();
    // Credits, options and gameplay use H40. Restore it while fully black.
    VDP_setScreenWidth320();
    SYS_doVBlankProcess();
}

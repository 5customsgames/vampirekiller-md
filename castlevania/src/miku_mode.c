#include "miku_mode.h"
#include "miku_sprite_data.inc"
static volatile bool enabled;
static volatile u8 voice_wait;
static u16 previous;
static u8 progress;
static u8 color_map[4][16], frame_palettes[MIKU_POSES][8];
static u32 sprite_tiles[128];
static u8 last_pose = 255, last_rows = 255;
static bool flash;
static u8 flash_bank, flash_ink;

void MIKU_reset(u16 held)
{
    enabled = FALSE; voice_wait = 0; progress = 0; previous = held;
    last_pose = last_rows = 255;
    flash = FALSE;
}
bool MIKU_enabled(void) { return enabled; }
bool MIKU_code_active(void) { return progress && !enabled; }
void MIKU_code_update(u16 pad)
{
    static const u16 code[10] = { BUTTON_UP, BUTTON_UP, BUTTON_DOWN, BUTTON_DOWN,
        BUTTON_LEFT, BUTTON_RIGHT, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_B, BUTTON_A };
    static const u8 prefix[10] = { 0, 1, 0, 0, 0, 0, 0, 0, 0, 0 };
    const u16 mask = BUTTON_UP | BUTTON_DOWN | BUTTON_LEFT | BUTTON_RIGHT |
                     BUTTON_A | BUTTON_B | BUTTON_C | BUTTON_START;
    u16 pressed = pad & ~previous & mask;
    previous = pad;
    if (!pressed || enabled) return;
    while (progress && pressed != code[progress]) progress = prefix[progress - 1];
    if (pressed == code[progress] && ++progress == 10) enabled = TRUE;
}
void MIKU_audio_frame(void) { if (voice_wait) voice_wait--; }
bool MIKU_claim_voice(bool priority)
{
    if (!enabled || (voice_wait && !priority)) return FALSE;
    voice_wait = 15;
    return TRUE;
}
static u16 distance(u16 a, u16 b)
{
    s16 r = ((a >> 1) & 7) - ((b >> 1) & 7);
    s16 g = ((a >> 5) & 7) - ((b >> 5) & 7);
    s16 blue = ((a >> 9) & 7) - ((b >> 9) & 7);
    return 3*r*r + 4*g*g + 2*blue*blue;
}
void MIKU_set_palette(const u16 *palette)
{
    u16 costs[4][16];
    u16 brightest = 0;
    flash_bank = 0; flash_ink = 1;
    for (u8 bank = 0; bank < 4; bank++)
        for (u8 index = 1; index < 16; index++)
        {
            u16 c = palette[bank*16 + index];
            u16 brightness = ((c >> 1) & 7) * 3 + ((c >> 5) & 7) * 6 + ((c >> 9) & 7);
            if (brightness > brightest) { brightest = brightness; flash_bank = bank; flash_ink = index; }
        }
    flash = FALSE;
    for (u8 bank = 0; bank < 4; bank++)
    {
        color_map[bank][0] = 0; costs[bank][0] = 0;
        for (u8 c = 1; c < 16; c++)
        {
            u16 best = 0xFFFF; u8 index = 1;
            for (u8 i = 1; i < 16; i++)
            {
                u16 d = distance(miku_colors[c], palette[bank * 16 + i]);
                if (d < best) { best = d; index = i; }
            }
            color_map[bank][c] = index; costs[bank][c] = best;
        }
    }
    for (u8 frame = 0; frame < MIKU_POSES; frame++)
        for (u8 piece = 0; piece < 8; piece++)
        {
            u32 best = 0xFFFFFFFFUL; u8 choice = 0;
            for (u8 bank = 0; bank < 4; bank++)
            {
                u32 cost = 0;
                for (u8 c = 1; c < 16; c++)
                    cost += (u32)miku_weights[(frame * 8 + piece) * 16 + c] * costs[bank][c];
                if (cost < best) { best = cost; choice = bank; }
            }
            frame_palettes[frame][piece] = choice;
        }
    last_pose = last_rows = 255;
}
void MIKU_set_flash(bool on)
{
    if (flash == on) return;
    flash = on;
    last_pose = last_rows = 255;
}
bool MIKU_render(u8 pose, u8 visible_rows)
{
    if (pose >= MIKU_POSES) pose = 0;
    if (visible_rows > 32) visible_rows = 32;
    if (pose == last_pose && visible_rows == last_rows) return FALSE;
    last_pose = pose; last_rows = visible_rows;
    for (u8 piece = 0; piece < 8; piece++)
    {
        u8 col = piece / 2, y0 = (piece & 1) * 16;
        const u8 *map = color_map[frame_palettes[pose][piece]];
        for (u8 y = 0; y < 16; y++)
        {
            u32 result = 0;
            if (y + y0 < visible_rows)
            {
                u32 row = miku_pixels[pose * 128 + (y + y0) * 4 + col];
                for (u8 x = 0; x < 8; x++)
                    {
                    u8 color = (row >> (28 - x*4)) & 15;
                    result |= (u32)(flash && color ? flash_ink : map[color]) << (28 - x*4);
                }
            }
            sprite_tiles[piece * 16 + y] = result;
        }
    }
    return TRUE;
}
const u32 *MIKU_tile_data(void) { return sprite_tiles; }
u8 MIKU_sprite_palette(u8 piece) { return piece < 8 && last_pose < MIKU_POSES ? (flash ? flash_bank : frame_palettes[last_pose][piece]) : 0; }

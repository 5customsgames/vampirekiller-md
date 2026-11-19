// Music and sound effects: replay the NES game's recorded APU writes each
// frame on the Mega Drive's PSG and FM channels. Pulse sweeps, length counters,
// volume envelopes and the triangle linear counter are modelled. Pulse duty
// remains the PSG's fixed square wave. Effects temporarily own the channels they write; music
// continues underneath.
#include "sound.h"
#include "wilhelm_audio.h"
#include "fm_music.h"
#include "miku_mode.h"
#include "miku_voice_data.inc"

#define PSG_DATA (*(vu8 *)0xC00011)

typedef struct { u8 r[0x18]; u8 len[4]; u8 lin; bool reload; u8 owned; u8 sweep_div[2]; bool sweep_reload[2]; u8 env_div[4], env_level[4]; bool env_start[4]; } Apu;   // owned: channels written (1 << ch)
typedef struct { const Sound *s; const u8 *p; u8 wait; bool on; } Player;

static Apu music_apu, sfx_apu, silent_apu;
static Player music, sfx;
static u8 music_mode = SOUND_MUSIC_FM;
static bool fm_music_mode;
static u8 fm_sfx_mask;
static bool held;                               // the music stands still and silent (the pause)

static const u8 length_table[32] = {
    10, 254, 20, 2, 40, 4, 80, 6, 160, 8, 60, 10, 14, 12, 26, 14, 12, 16, 24, 18, 48, 20, 96, 22, 192, 24, 72, 26, 16, 28, 32, 30,
};
static const u16 noise_period[16] = { 4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068 };
// NES volume 0-15 (linear) -> PSG attenuation (2 dB steps). The NES mixer weighs the noise about 2/3 of a pulse
// (0.00494 against 0.00752 per step): 2 more steps of attenuation; its triangle about like a pulse at full volume
static const u8 attenuation[16] = { 15, 12, 9, 7, 6, 5, 4, 3, 3, 2, 2, 1, 1, 1, 0, 0 };

static void apu_write(Apu *a, u8 reg, u8 v)
{
    a->r[reg] = v;
    if (reg < 0x10) a->owned |= 1 << (reg >> 2);
    if (reg == 1 || reg == 5) a->sweep_reload[reg >> 2] = TRUE;
    if (reg == 0x15)                                            // channel enables: off clears the length counter
    {
        for (u8 ch = 0; ch < 4; ch++) if (!(v & (1 << ch))) a->len[ch] = 0;
    }
    else if (reg < 0x10 && (reg & 3) == 3)                      // length counter load (if the channel is enabled)
    {
        u8 ch = reg >> 2;
        if (ch != 2) a->env_start[ch] = TRUE;
        if (a->r[0x15] & (1 << ch)) a->len[ch] = length_table[v >> 3];
        if (ch == 2) a->reload = TRUE;
    }
}

// NES pulse sweep ($4001/$4005): pulse 1 subtracts one extra on a negative
// sweep. The target also controls muting when the sweep is disabled.
static s16 sweep_target(const Apu *a, u8 ch)
{
    const u8 *r = a->r + ch * 4;
    s16 period = r[2] | ((r[3] & 7) << 8), change = period >> (r[1] & 7);
    s16 target = (r[1] & 8) ? period - change - (ch == 0) : period + change;
    return target < 0 ? 0 : target;
}

static void sweep_clock(Apu *a, u8 ch)
{
    u8 *r = a->r + ch * 4;
    u16 period = r[2] | ((r[3] & 7) << 8);
    s16 target = sweep_target(a, ch);
    if (!a->sweep_div[ch] && (r[1] & 0x80) && (r[1] & 7) && period >= 8 && target <= 0x7FF)
    {
        r[2] = target & 0xFF;
        r[3] = (r[3] & 0xF8) | ((u16)target >> 8);
    }
    if (!a->sweep_div[ch] || a->sweep_reload[ch])
    {
        a->sweep_div[ch] = (r[1] >> 4) & 7;
        a->sweep_reload[ch] = FALSE;
    }
    else a->sweep_div[ch]--;
}

// Pulse/noise volume: bit 4 selects direct volume; otherwise the low nibble
// is a decay period, not a volume. In particular the impact sound ($14) starts
// its noise envelope at 15, rather than the old quiet, flat volume of 2.
static void envelope_clock(Apu *a, u8 ch)
{
    u8 control = a->r[ch * 4];
    if (a->env_start[ch])
    {
        a->env_start[ch] = FALSE;
        a->env_level[ch] = 15;
        a->env_div[ch] = control & 15;
    }
    else if (a->env_div[ch]) a->env_div[ch]--;
    else
    {
        a->env_div[ch] = control & 15;
        if (a->env_level[ch]) a->env_level[ch]--;
        else if (control & 0x20) a->env_level[ch] = 15;
    }
}

static u8 apu_volume(const Apu *a, u8 ch)
{
    if (!a->len[ch]) return 0;
    return a->r[ch * 4] & 0x10 ? a->r[ch * 4] & 15 : a->env_level[ch];
}

// one frame: 4 quarter clocks (linear counter/envelopes), 2 half clocks (length and sweep)

static void apu_clock(Apu *a)
{
    for (u8 q = 0; q < 4; q++)
    {
        envelope_clock(a, 0);
        envelope_clock(a, 1);
        envelope_clock(a, 3);
        if (a->reload) a->lin = a->r[8] & 0x7F;
        else if (a->lin) a->lin--;
        if (!(a->r[8] & 0x80)) a->reload = FALSE;
    }
    for (u8 half = 0; half < 2; half++)
    {
        for (u8 ch = 0; ch < 4; ch++)
        {
            u8 halt = ch == 2 ? a->r[8] & 0x80 : a->r[ch * 4] & 0x20;
            if (a->len[ch] && !halt) a->len[ch]--;
        }
        sweep_clock(a, 0);
        sweep_clock(a, 1);
    }
}

static void player_start(Player *pl, Apu *a, u8 id)
{
    memset(a, 0, sizeof(Apu));
    a->r[0x15] = 0x0F;                          // the NES game enables the 4 channels once, at power-on
    pl->s = &sounds[id]; pl->p = pl->s->data; pl->wait = 0; pl->on = TRUE;
}

// one frame of a recording; returns FALSE once a sound that does not loop is over
static bool player_step(Player *pl, Apu *a)
{
    if (!pl->on) return FALSE;
    if (pl->wait) { pl->wait--; apu_clock(a); return TRUE; }
    const u8 *end = pl->s->data + pl->s->size;
    while (TRUE)
    {
        if (pl->p >= end)
        {
            if (pl->s->loop == 0xFFFF) { pl->on = FALSE; return FALSE; }
            pl->p = pl->s->data + pl->s->loop;
        }
        u8 b = *pl->p++;
        if (b == 0xFF) break;
        if (b == 0xFE) { pl->wait = *pl->p++ - 1; break; }
        apu_write(a, b, *pl->p++);
    }
    apu_clock(a);
    return TRUE;
}

// ---------------------------------------------------------------- the Mega Drive's side

static u16 psg_last[4] = { 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF };   // tone period << 4 | attenuation, as last written
static u16 fm_last = 0xFFFF;                                    // block << 11 | fnum; 0: keyed off

static void psg_set(u8 ch, u16 period, u8 att)
{
    u16 v = period << 4 | att;
    if (v == psg_last[ch]) return;
    if (ch < 3 && period != psg_last[ch] >> 4)
    {
        PSG_DATA = 0x80 | ch << 5 | (period & 15);
        PSG_DATA = (period >> 4) & 0x3F;
    }
    PSG_DATA = 0x90 | ch << 5 | att;
    psg_last[ch] = v;
}

static void fm_reg(u8 reg, u8 v) { YM2612_writeReg(0, reg, v); }
static void fm_done(void)                       // SGDK's PCM driver sets the YM2612's address to the DAC ($2A) once
{                                               // and then only writes data: point it back there before the Z80 runs
    vs8 *pb = (vs8 *)YM2612_BASEPORT;
    while (*pb < 0);
    pb[0] = 0x2A;
}

static void fm_patch(void)                      // channel 1: algorithm 7, only operator 4 sounds (a sine)
{
    static const u8 tl[4] = { 127, 127, 127, 16 };   // operator 4 at -12 dB: a first guess, to set by ear
    for (u8 op = 0; op < 4; op++)
    {
        u8 o = op * 4;
        fm_reg(0x30 + o, 0x01);                 // DT 0, MUL 1
        fm_reg(0x40 + o, tl[op]);
        fm_reg(0x50 + o, 0x1F);                 // attack rate 31
        fm_reg(0x60 + o, 0x00);
        fm_reg(0x70 + o, 0x00);
        fm_reg(0x80 + o, 0x0F);                 // sustain at full, release rate 15
        fm_reg(0x90 + o, 0x00);
    }
    fm_reg(0xB0, 0x07);
    fm_reg(0xB4, 0xC0);                         // both speakers
}

static void fm_triangle(bool on, u16 period)
{
    static bool cached;
    static u16 cached_period, cached_value;
    u16 v = 0;
    if (on && cached && period == cached_period) v = cached_value;
    else if (on)
    {
        // NES triangle: 1789773 / (32 (t + 1)) Hz; YM2612 fnum at block 0 = 144 f 2^21 / 7670453
        u32 fnum = 2202010UL / (period + 1);
        u16 block = 0;
        while (fnum >= 2048 && block < 7) { fnum >>= 1; block++; }
        if (fnum >= 2048) fnum = 2047;
        v = block << 11 | fnum;
        cached_period = period; cached_value = v; cached = TRUE;
    }
    // Keep the hardware-state check: stop/restart can invalidate fm_last
    // without changing the period cached above.
    if (v == fm_last) return;
    Z80_requestBus(TRUE);
    if (!v) fm_reg(0x28, 0x00);
    else
    {
        fm_reg(0xA4, v >> 8);
        fm_reg(0xA0, v & 0xFF);
        if (!fm_last) fm_reg(0x28, 0xF0);
    }
    fm_done();
    Z80_releaseBus();
    fm_last = v;
}

static void sound_out(void)
{
    for (u8 ch = 0; ch < 4; ch++)
    {
        bool sfx_owns = sfx.on && (sfx_apu.owned & (1 << ch));
        if (fm_music_mode && ch != 2 && !sfx_owns) continue;
        Apu *a = sfx.on && (sfx_apu.owned & (1 << ch)) ? &sfx_apu : (held || fm_music_mode) ? &silent_apu : &music_apu;
        const u8 *r = a->r + ch * 4;
        u16 t = r[2] | (r[3] & 7) << 8;
        switch (ch)
        {
        case 0:
        case 1:
        {
            u8 vol = t >= 8 && sweep_target(a, ch) <= 0x7FF ? apu_volume(a, ch) : 0;
            u16 n = t + 1;                      // PSG: 3579545 / (32 n) Hz, the NES pulse 1789773 / (16 (t + 1))
            while (n > 1023) n >>= 1;
            psg_set(ch, n, attenuation[vol]);
            break;
        }
        case 2:
            fm_triangle(a->len[2] && a->lin && t >= 2, t);
            break;
        case 3:
        {
            u8 vol = apu_volume(a, 3);
            u16 n = noise_period[r[2] & 15] >> 4;   // the PSG's noise shifts at tone 2's rate, 3579545 / (32 n)
            psg_set(2, n ? n : 1, 15);
            u8 att = attenuation[vol] + 2;
            psg_set(3, 0, att > 15 ? 15 : att);
            break;
        }
        }
    }
}

#include "menu_nes_music_data.inc"
static bool menu_music_mode;
static u8 menu_pal_phase;

static void sound_frame(void)
{
    MIKU_audio_frame();
    if (fm_music_mode)
    {
        FM_MUSIC_tick();
        player_step(&sfx, &sfx_apu);
        u8 mask = sfx.on ? sfx_apu.owned : 0;
        u8 acquired = mask & ~fm_sfx_mask;
        for (u8 ch=0;ch<4;ch++) if (acquired & (1<<ch)) psg_last[ch]=0xFFFF;
        if (acquired & 8)
        {
            // Music may have used periodic noise or a different noise clock.
            // Restore the original SFX mode and invalidate its tone-2 cache.
            PSG_DATA = 0xE7;
            psg_last[2] = 0xFFFF;
        }
        fm_sfx_mask = mask;
        sound_out();
        FM_MUSIC_apply_psg(mask);
    }
    else
    {
        if (!held)
        {
            player_step(&music, &music_apu);
            // NES menu score: advance six 60 Hz frames per five PAL V-Blanks.
            if (menu_music_mode && SYS_isPAL() && ++menu_pal_phase == 5)
            {
                menu_pal_phase = 0;
                player_step(&music, &music_apu);
            }
        }
        player_step(&sfx, &sfx_apu);
        sound_out();
    }
}

void sound_init(void)
{
    SND_PCM_loadDriver(TRUE);                   // the Z80 plays the DMC's one sample (hurt_pcm) on the DAC
    Z80_requestBus(TRUE);
    fm_patch();
    fm_reg(0x28, 0x00);
    fm_reg(0x2B, 0x80);                         // DAC on, in place of FM channel 6
    fm_done();
    Z80_releaseBus();
    PSG_DATA = 0xE0 | 0x04 | 0x03;              // white noise, clocked by tone 2
    for (u8 ch = 0; ch < 4; ch++) PSG_DATA = 0x9F | ch << 5;
    SYS_setVIntCallback(sound_frame);
}

static void stop_fm_music(void)
{
    if (menu_music_mode)
    {
        // Restore the game's normal triangle/SFX patch before returning to play.
        Z80_requestBus(TRUE);
        fm_patch();
        fm_reg(0x28, 0x00);
        fm_done();
        Z80_releaseBus();
        fm_last = 0xFFFF;
    }
    menu_music_mode = FALSE;
    menu_pal_phase = 0;
    if (!fm_music_mode) return;
    FM_MUSIC_stop();
    FM_MUSIC_apply_psg(sfx.on ? sfx_apu.owned : 0);
    fm_music_mode = FALSE;
    fm_sfx_mask = 0;
    PSG_DATA = 0xE7;
    fm_last = 0xFFFF;
    for (u8 ch=0;ch<4;ch++) psg_last[ch]=0xFFFF;
}

void sound_set_music_mode(u8 mode)
{
    SYS_disableInts();
    stop_fm_music();
    music.on = FALSE;
    memset(&music_apu,0,sizeof(Apu));
    music_mode = mode <= SOUND_MUSIC_YM2612 ? mode : SOUND_MUSIC_FM;
    SYS_enableInts();
}
u8 sound_get_music_mode(void) { return music_mode; }
void sound_set_fm(bool enabled) { sound_set_music_mode(enabled ? SOUND_MUSIC_FM : SOUND_MUSIC_ORIGINAL); }
bool sound_fm_enabled(void) { return music_mode != SOUND_MUSIC_ORIGINAL; }

void music_play_menu(void)
{
    SYS_disableInts();
    stop_fm_music();
    memset(&music_apu, 0, sizeof(Apu));
    music_apu.r[0x15] = 0x0F;
    music.s = &menu_nes_sound;
    music.p = menu_nes_sound.data;
    music.wait = 0;
    music.on = TRUE;
    menu_music_mode = TRUE;
    menu_pal_phase = 0;
    // The PSG supplies two square voices and noise. Add quiet odd harmonics
    // on the existing FM bass channel for a softer, triangle-like spectrum.
    Z80_requestBus(TRUE);
    fm_patch();
    static const u8 multiple[4] = { 1, 3, 5, 7 };
    static const u8 level[4] = { 26, 51, 63, 71 };
    for (u8 op = 0; op < 4; op++)
    {
        fm_reg(0x30 + op * 4, multiple[op]);
        fm_reg(0x40 + op * 4, level[op]);
    }
    fm_done();
    Z80_releaseBus();
    fm_last = 0xFFFF;
    SYS_enableInts();
}

void music_play(u8 id)
{
    SYS_disableInts();
    stop_fm_music();
    if (music_mode != SOUND_MUSIC_ORIGINAL && id < SFX_01)
    {
        music.on = FALSE;
        memset(&music_apu,0,sizeof(Apu));
        if (music_mode == SOUND_MUSIC_YM2612) FM_MUSIC_start_ym2612(id);
        else FM_MUSIC_start(id);
        fm_music_mode = TRUE;
        fm_sfx_mask = 0;
        FM_MUSIC_hold(held);
    }
    else player_start(&music,&music_apu,id);
    SYS_enableInts();
}
void music_stop(void)
{
    SYS_disableInts();
    stop_fm_music();
    music.on = FALSE;
    memset(&music_apu,0,sizeof(Apu));
    SYS_enableInts();
}
void sfx_play(u8 id)
{
    bool voice = FALSE;
    SYS_disableInts();
    if (id == SFX_14 && MIKU_enabled()) voice = MIKU_claim_voice(FALSE);
    else player_start(&sfx, &sfx_apu, id);
    SYS_enableInts();
    if (voice) SND_PCM_startPlay(miku_impact_pcm, sizeof(miku_impact_pcm), SOUND_PCM_RATE_16000, SOUND_PAN_CENTER, FALSE);
}
void fall_play(void)
{
    if (music_mode != SOUND_MUSIC_ORIGINAL)
        SND_PCM_startPlay(wilhelm_pcm, sizeof(wilhelm_pcm), SOUND_PCM_RATE_22050, SOUND_PAN_CENTER, FALSE);
}
void hurt_play(void)
{
    if (MIKU_claim_voice(TRUE)) SND_PCM_startPlay(miku_impact_pcm, sizeof(miku_impact_pcm), SOUND_PCM_RATE_16000, SOUND_PAN_CENTER, FALSE);
    else SND_PCM_startPlay(hurt_pcm, HURT_PCM_SIZE, SOUND_PCM_RATE_32000, SOUND_PAN_CENTER, FALSE);
}
bool music_playing(void) { return fm_music_mode ? FM_MUSIC_playing() : music.on; }
void music_hold(bool on)
{
    SYS_disableInts();
    held = on;
    if (fm_music_mode) FM_MUSIC_hold(on);
    SYS_enableInts();
}

// Four music FM voices on physical channels 1..4. Channel 0 stays available
// for the old triangle/SFX voice; channel 5 stays in DAC mode for hurt_pcm.
#include "fm_music.h"
typedef struct { const u8 *init; u32 init_size; const u8 *data; u32 size, loop; } FmTrack;
#include "fm_music_data.inc"
#include "ym2612_music_data.inc"
#define FM_PSG_DATA (*(vu8 *)0xC00011)
static const FmTrack *track;
static const u8 *position;
static bool playing, held, arranged_track;
static u8 arranged_pal_phase;
static const u8 music_channels[4] = {1,2,3,4};
static u8 carriers[4], active_keys[4];
static u16 psg_period[3], psg_applied_period[3];
static u8 psg_att[4], psg_applied_att[4], psg_noise, psg_applied_noise, psg_latch;

static void restore_address(void)
{
    vs8 *port = (vs8 *)YM2612_BASEPORT;
    while (*port < 0);
    port[0] = 0x2A;
}
static void write_key(u8 channel, bool on)
{
    YM2612_writeReg(0,0x28,(on ? 0xF0 : 0) | (channel < 3 ? channel : channel + 1));
}
static void write_carrier(u8 channel, u8 value)
{
    YM2612_writeReg(channel < 3 ? 0 : 1,0x4C + channel % 3,value);
}
static void remember_psg(u8 value)
{
    if (value & 0x80)
    {
        psg_latch = (value >> 4) & 7;
        u8 channel = psg_latch >> 1;
        if (psg_latch & 1) psg_att[channel] = value & 15;
        else if (channel == 3) psg_noise = value & 7;
        else psg_period[channel] = (psg_period[channel] & 0x3F0) | (value & 15);
    }
    else if (!(psg_latch & 1) && (psg_latch >> 1) < 3)
    {
        u8 channel = psg_latch >> 1;
        psg_period[channel] = (psg_period[channel] & 15) | ((value & 63) << 4);
    }
}
// Caller holds the Z80 bus. Return 1 at a frame, 0 at end, -1 on bad data.
static s16 commands(const u8 **p, const u8 *end)
{
    while (*p < end)
    {
        u8 command = *(*p)++;
        if (command == 0x62) return 1;
        if (command == 0x66) return 0;
        if (command == 0x50)
        {
            if (*p >= end) return -1;
            remember_psg(*(*p)++);
        }
        else if (command == 0x52 || command == 0x53)
        {
            if (end - *p < 2) return -1;
            u8 reg = *(*p)++, value = *(*p)++, port = command - 0x52;
            if (reg == 0x2A || reg == 0x2B) return -1;
            if (reg == 0x28)
            {
                u8 physical = value & 7;
                if (physical == 3 || physical == 7) return -1;
                if (physical >= 4) physical--;
                if (physical < 1 || physical > 4) return -1;
                active_keys[physical - 1] = !!(value & 0xF0);
            }
            else
            {
                u8 physical = reg % 4 + (port ? 3 : 0);
                if (physical < 1 || physical > 4) return -1;
                if ((reg & 0xFC) == 0x4C) carriers[physical - 1] = value;
            }
            YM2612_writeReg(port,reg,value);
        }
        else return -1;
    }
    return 0;
}
static void silence_fm(void)
{
    for (u8 i=0;i<4;i++)
    {
        u8 ch=music_channels[i];
        write_key(ch,FALSE);
        // Silence all operators, including release tails, before changing track.
        for (u8 op=0;op<4;op++) YM2612_writeReg(ch<3 ? 0 : 1,0x40+op*4+ch%3,127);
        active_keys[i]=0;
    }
}
static void reset_psg(void)
{
    for (u8 ch=0;ch<3;ch++) { psg_period[ch]=1; psg_applied_period[ch]=0xFFFF; }
    for (u8 ch=0;ch<4;ch++) { psg_att[ch]=15; psg_applied_att[ch]=0xFF; }
    psg_noise=7; psg_applied_noise=0xFF; psg_latch=0;
}
void FM_MUSIC_stop(void)
{
    if (track)
    {
        Z80_requestBus(TRUE); silence_fm(); restore_address(); Z80_releaseBus();
    }
    playing=FALSE; held=FALSE; arranged_pal_phase=0;
    for (u8 ch=0;ch<4;ch++) psg_att[ch]=15;
}
static void start_track(u8 id, bool arranged)
{
    if (id>=15) { FM_MUSIC_stop(); return; }
    arranged_track=arranged;
    track=arranged ? &ym_tracks[id] : &fm_tracks[id]; position=track->data; reset_psg(); held=FALSE; arranged_pal_phase=0;
    memset(active_keys,0,sizeof(active_keys));
    Z80_requestBus(TRUE);
    const u8 *p=track->init;
    commands(&p,track->init+track->init_size);
    restore_address(); Z80_releaseBus(); playing=TRUE;
}
void FM_MUSIC_start(u8 id) { start_track(id, FALSE); }
void FM_MUSIC_start_ym2612(u8 id) { start_track(id, TRUE); }

static bool tick_one_frame(void)
{
    if (!playing || held) return playing;
    Z80_requestBus(TRUE);
    s16 status=commands(&position,track->data+track->size);
    if (!status && track->loop != 0xFFFFFFFFUL && track->loop < track->size)
    {
        position=track->data+track->loop;
        status=commands(&position,track->data+track->size);
    }
    if (status<=0)
    {
        silence_fm(); playing=FALSE;
        for (u8 ch=0;ch<4;ch++) psg_att[ch]=15;
    }
    restore_address(); Z80_releaseBus();
    return playing;
}
bool FM_MUSIC_tick(void)
{
    if (!playing || held) return playing;
    bool result = tick_one_frame();
    // All newly arranged scores use 60 Hz timing. Preserve the legacy FM bank.
    if (arranged_track && SYS_isPAL() && ++arranged_pal_phase == 5)
    {
        arranged_pal_phase = 0;
        if (result) result = tick_one_frame();
    }
    return result;
}
bool FM_MUSIC_playing(void) { return playing; }
void FM_MUSIC_hold(bool on)
{
    if (!playing || held==on) { held=on; return; }
    held=on; Z80_requestBus(TRUE);
    for (u8 i=0;i<4;i++)
    {
        u8 ch=music_channels[i];
        if (on) { write_key(ch,FALSE); write_carrier(ch,127); }
        else { write_carrier(ch,carriers[i]); if (active_keys[i]) write_key(ch,TRUE); }
    }
    restore_address(); Z80_releaseBus();
}
void FM_MUSIC_apply_psg(u8 mask)
{
    // The old triangle is FM channel 0, not PSG tone 2. Only a noise SFX
    // owns PSG tone 2 as its clock; release and restore it when that SFX ends.
    mask &= 0x0B;
    if (mask & 8) mask |= 4;
    for (u8 ch=0;ch<3;ch++)
    {
        if (mask & (1<<ch)) { psg_applied_period[ch]=0xFFFF; psg_applied_att[ch]=0xFF; continue; }
        if (psg_period[ch]!=psg_applied_period[ch])
        {
            FM_PSG_DATA=0x80|(ch<<5)|(psg_period[ch]&15);
            FM_PSG_DATA=(psg_period[ch]>>4)&63;
            psg_applied_period[ch]=psg_period[ch];
        }
        u8 attenuation=held ? 15 : psg_att[ch];
        if (attenuation!=psg_applied_att[ch]) { FM_PSG_DATA=0x90|(ch<<5)|attenuation; psg_applied_att[ch]=attenuation; }
    }
    if (mask & 8) { psg_applied_noise=0xFF; psg_applied_att[3]=0xFF; return; }
    if (psg_noise!=psg_applied_noise) { FM_PSG_DATA=0xE0|psg_noise; psg_applied_noise=psg_noise; }
    u8 attenuation=held ? 15 : psg_att[3];
    if (attenuation!=psg_applied_att[3]) { FM_PSG_DATA=0xF0|attenuation; psg_applied_att[3]=attenuation; }
}

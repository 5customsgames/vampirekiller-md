// Five YM2612 FM voices and PSG, with a bounded register-event player.
// No recorded audio and no DAC sample data are used by this track.
#include "prologue_fm.h"
#include "prologue_fm_data.inc"
#define PROLOGUE_PSG_DATA (*(vu8 *)0xC00011)
static const u8 *position;
static bool playing;

// The existing PCM driver for Simon's hurt sound expects the YM address to
// point at the DAC when the Z80 is released. Selecting the address is not a
// sample write: the prologue never writes data to register $2A.
static void prologue_restore_address(void)
{
    vs8 *port = (vs8 *)YM2612_BASEPORT;
    while (*port < 0);
    port[0] = 0x2A;
}

// Caller owns the Z80 bus. The generated stream uses only these commands.
// Return 1 at a frame boundary, 0 at end, -1 on malformed data.
static s16 prologue_commands(const u8 **cursor, const u8 *end)
{
    while (*cursor < end)
    {
        u8 command = *(*cursor)++;
        if (command == 0x62) return 1;
        if (command == 0x66) return 0;
        if (command == 0x50)
        {
            if (*cursor >= end) return -1;
            PROLOGUE_PSG_DATA = *(*cursor)++;
        }
        else if (command == 0x52 || command == 0x53)
        {
            if (end - *cursor < 2) return -1;
            u8 reg = *(*cursor)++, value = *(*cursor)++;
            if (reg == 0x2A) return -1; // no PCM data in this player
            YM2612_writeReg(command - 0x52, reg, value);
        }
        else return -1;
    }
    return 0;
}

void PROLOGUE_FM_start(void)
{
    Z80_requestBus(TRUE);
    const u8 *p = prologue_init;
    prologue_commands(&p, prologue_init + sizeof(prologue_init));
    prologue_restore_address();
    Z80_releaseBus();
    position = prologue_data;
    playing = TRUE;
}

void PROLOGUE_FM_stop(void)
{
    if (!playing) return;
    Z80_requestBus(TRUE);
    const u8 *p = prologue_stop;
    prologue_commands(&p, prologue_stop + sizeof(prologue_stop));
    prologue_restore_address();
    Z80_releaseBus();
    playing = FALSE;
}

bool PROLOGUE_FM_tick(void)
{
    if (!playing) return FALSE;
    Z80_requestBus(TRUE);
    s16 status = prologue_commands(&position, prologue_data + sizeof(prologue_data));
    if (status <= 0)
    {
        const u8 *p = prologue_stop;
        prologue_commands(&p, prologue_stop + sizeof(prologue_stop));
        playing = FALSE;
    }
    prologue_restore_address();
    Z80_releaseBus();
    return playing;
}

bool PROLOGUE_FM_playing(void) { return playing; }

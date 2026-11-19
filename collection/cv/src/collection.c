#include <genesis.h>
#include "collection.h"
#include "sound.h"

#ifndef VK_BASE
#error VK_BASE must be defined (see Makefile)
#endif

bool collection_has_vk(void)
{
    const u32 entry = *(const u32 *)(VK_BASE + 4);
    return entry > VK_BASE && entry < 0x400000 && !(entry & 1);
}

void collection_launch_vk(void)
{
    music_stop();
    SYS_disableInts();
    VDP_setEnable(FALSE);
    YM2612_reset();
    PSG_reset();
    // SGDK's entry point takes the soft reset path (no RAM clear, no .data copy) when a control port
    // is set: clear them so Vampire Killer starts as on power-on. Its vector table at VK_BASE gives
    // the stack and the entry point; from its .data copy on, GAME_FLAG relays the interrupts to it.
    *(vu16 *)0xA10008 = 0;
    *(vu16 *)0xA1000A = 0;
    *(vu16 *)0xA1000C = 0;
    __asm__ volatile(
        "move.l  (%c0).l, %%sp\n\t"
        "move.l  (%c0 + 4).l, %%a0\n\t"
        "jmp     (%%a0)"
        :
        : "i"(VK_BASE)
        : "memory");
    __builtin_unreachable();
}

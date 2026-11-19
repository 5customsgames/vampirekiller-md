#ifndef VK_THANKS_H
#define VK_THANKS_H
#include <genesis.h>
/* Thank-you pages of the port, shown after the original credits of the ending (research/thanks-screen.md). */
void vk_thanks_begin(void);
/* One turn (called right after the VBlank); returns TRUE when the screen is over (START or the end of the last page). */
bool vk_thanks_tick(u16 pressed);
#endif

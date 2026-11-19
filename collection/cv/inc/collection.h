#ifndef COLLECTION_H
#define COLLECTION_H

// TRUE when Vampire Killer's vector table is at VK_BASE: FALSE in the Castlevania-only ROM
// (out/rom.bin, out/Castlevania-md.bin), whose bytes there are padding.
bool collection_has_vk(void);
// Vampire Collection MD: hand the console over to Vampire Killer MD, linked at VK_BASE (see Makefile).
// Never returns; RESET comes back to Castlevania's boot code (collection/sega_cv.s).
void collection_launch_vk(void) __attribute__((noreturn));

#endif

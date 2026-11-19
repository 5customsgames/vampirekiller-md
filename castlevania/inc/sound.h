#ifndef SOUND_H
#define SOUND_H
#include <genesis.h>
#include "music.h"

#define SOUND_MUSIC_ORIGINAL 0
#define SOUND_MUSIC_FM 1
#define SOUND_MUSIC_YM2612 2
void sound_set_music_mode(u8 mode);
u8 sound_get_music_mode(void);
void sound_set_fm(bool enabled);
bool sound_fm_enabled(void);
void sound_init(void);          // sets the chips up and plays a frame of sound at every vertical blank
void music_play(u8 id);         // MUS_... from music.h; replaces the music playing
void music_stop(void);
void music_play_menu(void);    // NES-style menu arrangement; does not change the selected game soundtrack
void sfx_play(u8 id);           // SFX_... from music.h; takes its channels from the music while it plays
bool music_playing(void);
void music_hold(bool on);
void fall_play(void);           // FM mode: Wilhelm scream on a fatal pit/water fall
void hurt_play(void);           // the NES game's DPCM sample of Simon being hurt ($FE96)       // TRUE: the music stops where it is, silent, until FALSE

#endif

#ifndef CASTLEVANIA_FM_MUSIC_H
#define CASTLEVANIA_FM_MUSIC_H
#include <genesis.h>
void FM_MUSIC_start(u8 id);
void FM_MUSIC_start_ym2612(u8 id);
void FM_MUSIC_stop(void);
bool FM_MUSIC_tick(void);
bool FM_MUSIC_playing(void);
void FM_MUSIC_hold(bool on);
void FM_MUSIC_apply_psg(u8 sfx_channels);
#endif

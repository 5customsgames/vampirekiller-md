#ifndef CASTLEVANIA_MIKU_MODE_H
#define CASTLEVANIA_MIKU_MODE_H
#include <genesis.h>
#define MIKU_POSES 17
void MIKU_reset(u16 held);
void MIKU_code_update(u16 pad);
bool MIKU_enabled(void);
bool MIKU_code_active(void);
void MIKU_audio_frame(void);
bool MIKU_claim_voice(bool priority);
void MIKU_set_palette(const u16 *palette);
void MIKU_set_flash(bool on);
bool MIKU_render(u8 pose, u8 visible_rows);
const u32 *MIKU_tile_data(void);
u8 MIKU_sprite_palette(u8 sprite);
#endif

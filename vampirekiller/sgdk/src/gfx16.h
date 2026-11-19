#ifndef VK_GFX16_H
#define VK_GFX16_H

#include <genesis.h>
#include "generated/gfx16_md.h"
#include "generated/enemies16_md.h"
#include "generated/enemies16b2_md.h"
#include "generated/enemies16b3_md.h"
#include "generated/enemies16b4_md.h"
#include "generated/enemies16b5_md.h"
#include "generated/enemies16b6_md.h"
#include "generated/enemies16b7_md.h"
#include "generated/boss3_16_md.h"
#include "generated/boss1215_16_md.h"
#include "generated/items16_md.h"
#include "generated/candle16_md.h"
#include "generated/crusher16_md.h"
#include "generated/door16_md.h"
#include "generated/object_tiles_md.h"
#include "generated/weapons_md.h"
#include "generated/loot_md.h"
#include "generated/death_flame_md.h"
#include "generated/candle_flames_md.h"

/* 16-bit graphics mode (research/gfx16.md, tools/build_gfx16.py): the castle rooms drawn with
 * the 16-bit art, cell for cell on the MSX layout. Nothing of the game logic reads it.
 *
 * vk_gfx16: the option of the title screen (0: the MSX graphics, the default).
 * vk_gfx16_on: the room on screen is drawn with the 16-bit art. PAL0 then holds the palette of
 * that art, and everything else drawn with the colours of the MSX room palette (objects on the
 * plane, sprites) takes PAL2, which holds the MSX room palette (stages 1 to 18: the same colours for the entries
 * that content uses, see vk_gfx16_enemies, vk_gfx16_enemies_b2, _b3, _b4, _b5, _b6 and _b7 below): VK_PAL_OBJ. */
extern u8 vk_gfx16;
extern u8 vk_gfx16_on;
#define VK_PAL_OBJ (vk_gfx16_on ? PAL2 : PAL0)

/* The common enemies of block 1 (stages 1 to 3: zombie, panther, bat, fishman) are drawn in the 16-bit art in
 * every room but the boss room: tools/build_enemies16.py, tiles of the same layout as the MSX arrays. Their
 * colours replace the MSX palette in PAL2 (vk_enemy16_palette): the MSX colours that other PAL2 content uses
 * keep their entries, so objects, candles, weapons and the HUD boxes look as in MSX mode. */
u8 vk_gfx16_enemies(u16 stage, u16 room);
/* The common enemies of block 2 (stages 4 to 6: medusa head 08, armour knight 06, bat 07, statue 0A and its fireball) are
 * drawn in the 16-bit art in every room but the crusher room (6/1, whose crushers read the free entries) and the boss
 * room: tools/build_enemies16_block2.py. vk_gfx16_enemy_cells loads their cells over the MSX block (same layout);
 * PAL2 is vk_enemy16b2_palette, with the same fixed entries as vk_enemy16_palette. */
u8 vk_gfx16_enemies_b2(u16 stage, u16 room);
/* The common enemies of block 3 (stages 7 to 9: medusa head 08, statue 0A and its fireball, skeleton 0B and its bone, raven 0C,
 * fleaman 0D) are drawn in the 16-bit art in every room but the stage 9 boss room: tools/build_enemies16_block3.py. Same
 * method as block 2 (same cells as the MSX block; object 1C stays MSX). PAL2 is vk_enemy16b3_palette[0] or [1], the one
 * whose entry 7 is the MSX entry 7 of the room (66C or 26C); the other fixed entries are those of vk_enemy16_palette. */
u8 vk_gfx16_enemies_b3(u16 stage, u16 room);
/* The common enemies of block 4 (stage 10: fishman 03 / 21h, its shot and drop, bat 04; stage 11: zombies, eagle 0F, flea
 * 0D / 23h, bone dragon 0E and its shot; stage 12: the dragon and its shot) are drawn in the 16-bit art in every room but the
 * stage 12 boss room: tools/build_enemies16_block4.py. Same method as block 3: the type 5 blocks of stages 10 and 11 by
 * vk_gfx16_enemy_block, the stage 10 bat and the zombies by arrays of the MSX layout, the stage 12 dragon by the late pool
 * cells (vk_enemy16b4_cells from VK_ENEMY16B4_LATE_CELL); object 1B and the platform stay as they are. PAL2 is one of the
 * four vk_enemy16b4_palette: stage 10, stage 11 room 0, stage 11 rooms 1-4, the dragon rooms (stage 11 room 5, stage 12),
 * each with the MSX colours of its rooms in the fixed entries (entry 7 is CAE, 000 or 66C). */
u8 vk_gfx16_enemies_b4(u16 stage, u16 room);
/* The common enemies of block 5 (stages 13 to 15, not the stage 15 boss: rising skeleton 09, white skeleton 0B and its bone,
 * flea 0D, axe knight 10 and its axe; object 1B stays MSX) are drawn in the 16-bit art in every room that loads enemy cells
 * (stage 13; stage 14 rooms 0 to 7; stage 15 rooms 1 to 4 and 6 to 8): tools/build_enemies16_block5.py. The late enemy
 * system loads the pool slots of the room one run at a time from late_graphics_words; in these rooms vk_gfx16_b5_late gives
 * vk_enemy16b5_cells instead (the same slots, so the same transfers and tile count). PAL2 is one of the three
 * vk_enemy16b5_palette, the one whose entry 7 is the MSX entry 7 of the room (CAE, 66C or 26C). */
u8 vk_gfx16_enemies_b5(u16 stage, u16 room);
const u32 *vk_gfx16_b5_late(u16 stage, u16 room, const u32 *msx);
/* The common enemies of block 6 (stages 16 and 17: stage 16 big bat 12h and its fireball; stage 17 skeleton 0B and its bone, flea 0D,
 * eagle 0F, axe knight 10 and its axe; object 1B stays MSX) are drawn in the 16-bit art in every room that loads their cells
 * (stage 16 rooms 1 to 4, 7, 8; stage 17 rooms 1 to 10): tools/build_enemies16_block6.py. As in block 5, vk_gfx16_b6_late gives
 * vk_enemy16b6_cells instead of late_graphics_words (the same pool slots, so the same transfers and tile count). PAL2 is one of
 * the four vk_enemy16b6_palette: stage 16, stage 17 room 1, stage 17 rooms 3 to 5, the other rooms of stage 17. Stage 18 is MSX. */
u8 vk_gfx16_enemies_b6(u16 stage, u16 room);
const u32 *vk_gfx16_b6_late(u16 stage, u16 room, const u32 *msx);
/* The common enemies of block 7 (stage 18: axe knight 10 and its axe in rooms 1, 2, 8; flea 0D in rooms 3 to 7; object 1B and the boss
 * stay MSX) are drawn in the 16-bit art: tools/build_enemies16_block7.py. As in block 6, vk_gfx16_b7_late gives vk_enemy16b7_cells
 * instead of late_graphics_words (the same pool slots). PAL2 is vk_enemy16b7_palette[1] (axe knight rooms) or [0] (flea rooms). */
u8 vk_gfx16_enemies_b7(u16 stage, u16 room);
const u32 *vk_gfx16_b7_late(u16 stage, u16 room, const u32 *msx);
/* Block 4, the arrays loaded whole (called only in stage 11, 10, 12): `msx` (vk_enemy_tiles, vk_stage10_bat_tiles, late_graphics_words) or, in those
 * rooms, the 16-bit array of the same layout (zombies of stage 11 room 0, bat of stage 10, the stage 12 late pool cells 0 to 5). */
const u32 *vk_gfx16_b4_zombie(u16 room, const u32 *msx);
const u32 *vk_gfx16_b4_bat(u16 room, const u32 *msx);
const u32 *vk_gfx16_b4_late(u16 room, const u32 *msx);
/* Load the 16-bit cells of block 2 for the stage over the type 5 block at `index` (none outside those rooms). */
void vk_gfx16_enemy_cells(u16 stage, u16 room, u16 index, TransferMethod tm);
/* Blocks 3 and 4 (stages 7 to 11): load the type 5 block of the stage (`msx`, `count` tiles) at `index` with the 16-bit cells
 * in place of the MSX ones (as many tiles as the MSX block: no longer room change) and return 1; outside those rooms return 0
 * and load nothing. */
u8 vk_gfx16_enemy_block(u16 stage, u16 room, const u32 *msx, u16 count, u16 index, TransferMethod tm);
/* The bat boss of the stage 3 (room 5, tools/build_boss3_16.py): 16-bit body, fireball and orb (vk_boss16_tiles, vk_orb16_tiles, same layout as the
 * MSX arrays). PAL2 of that room is vk_boss16_palette, whose entries 4 and 6 already hold the colours the orb writes there (006, 00A). */
u8 vk_gfx16_boss3(u16 stage, u16 room);
/* The spiked crushers of the stage 6 room 1 (tools/build_crusher16.py): in 16-bit mode that room loads its enemy block with the six
 * cells of the crushers (patterns 64 to 78, tiles 24h to 3Bh) from vk_crusher16_tiles in place of the MSX ones: the same 128 tiles,
 * in three transfers (called by actors.c only in the stage 6 room 1). PAL2 of the room is vk_crusher16_palette. */
void vk_gfx16_crusher_block(const u32 *msx, u16 count, u16 index, TransferMethod tm);
/* 16-bit art for the boss of stage 3, 6 or 9 in its room (boss3_16_md, boss69_16_md) */
u8 vk_gfx16_boss(u16 stage, u16 room);
/* Frankenstein and Igor (stage 12, room 6) and Death (stage 15, room 9) in 16 bits (tools/build_boss1215_16.py): returns the stage (12 or 15)
 * in the boss room of that stage in 16-bit mode, else 0. The arrays vk_boss12_16_tiles, vk_boss12_16_shot_tiles, vk_boss15_16_tiles and the
 * flames *_flame_tiles have the layout of the MSX ones (same loads); PAL2 of the room is vk_boss12_16_palette / vk_boss15_16_palette. */
u8 vk_gfx16_boss1215(u16 stage, u16 room);
/* PAL2 of a room: the MSX room palette `msx`, or one of the palettes above in such a room. */
const u16 *vk_gfx16_pal2(u16 stage, u16 room, const u16 *msx);

/* The candles, objects, thrown weapons, loot and flames (tools/build_items16.py): with the option on they are the 16-bit
 * pictures of the same layout as the MSX arrays, drawn with PAL1 (VK_PAL_ITEM), which then holds vk_item16_palette
 * instead of the HUD palette: the entries the HUD reads (1, 2, 8, 14, 15) are the same, the others are the colours of
 * the pictures. Everything else that uses the MSX colours (HUD boxes, text of the merchant, key, door) keeps PAL2. */
#define VK_PAL_ITEM (vk_gfx16 ? PAL1 : VK_PAL_OBJ)
/* The blobs of the candles of object 15 (objects 1A and 1C, tools/build_candle16.py) and the torches of the courtyard: in
 * 16-bit mode the same arrays as the MSX ones in the same layout (same cells, same transfers, no cost per frame). The blobs
 * keep PAL2 and read only entries that all the PAL2 of their rooms hold with the same colour; the torch flames use PAL1
 * (VK_PAL_ITEM). Object 1B (stages 11 to 18, VK_BLOB_B_TILES, vk_candle16_blob_b_tiles and slots 4, 5 of the late pools) reads PAL2 entries 2, 8, 14, fixed in all those palettes. */
#define VK_BLOB_C_TILES(msx) (vk_gfx16_on ? vk_candle16_blob_c_tiles : (msx))
#define VK_BLOB_A_TILES(msx) (vk_gfx16_on ? vk_candle16_blob_a_tiles : (msx))
#define VK_BLOB_B_TILES(msx) (vk_gfx16_on ? vk_candle16_blob_b_tiles : (msx))
#define VK_FLAME_TILES (vk_gfx16 ? vk_candle16_flame_tiles : vk_flame_fx_tiles)
const u32 *vk_item_gfx_weapon_tiles(void);            /* vk_weapon_tiles or the 16-bit frames (not inline: the sprite pass) */
const u32 *vk_item16_object(u16 object);              /* 16-bit picture of the MSX object 1..0x22 (4 tiles) */
/* The tiles to load for the MSX object 1..0x22 (vk_object_tiles), the weapons, the loot and the death flames: inline,
 * these run in the room load and in the sprite pass (one test of vk_gfx16 more than the MSX path). */
#define vk_item_gfx_object_tiles(object) (vk_gfx16 ? vk_item16_object(object) : &vk_object_tiles[((object) - 1) * 32])
#define vk_item_gfx_loot_tiles() (vk_gfx16 ? vk_item16_loot_tiles : vk_loot_tiles)
#define vk_item_gfx_death_flame_tiles() (vk_gfx16 ? vk_item16_death_flame_tiles : vk_death_flame_tiles)
/* The ball of a candle flame (colour 0: white 0E, 1: skin, 2: red 08), 4 tiles: vk_candle_flame_tiles, or a loot ball. */
#define vk_item_gfx_flame_tiles(color) (vk_gfx16 ? &vk_item16_loot_tiles[(3 - (color)) * 32] : &vk_candle_flame_tiles[(color) * 32])

/* The 16-bit data of a castle room, 0 when the option is off or the room has none. */
const VKGfx16Room *vk_gfx16_room(u16 stage, u16 room);
/* The same for a ROM scene drawn as a playfield: the courtyard screens (scenes 3..5) and hall
 * room 0 (scene 6). */
const VKGfx16Room *vk_gfx16_scene(u16 scene);
/* The cells of rows 4..25 of that scene as drawn: 16-bit ones while vk_gfx16_on, else the scene map's. */
u16 vk_scene_cell(u16 scene, u16 col, u16 row);
/* Cell i (row * 32 + col) of the 32 x 22 cells of the room as drawn (tile offset from
 * TILE_USER_INDEX), and the 8 rows of the tile behind one of those cells: the 16-bit ones while
 * vk_gfx16_on, else vk_maps / vk_tiles. */
u16 vk_room_cell(u16 stage, u16 room, u16 i);
const u32 *vk_room_tile(u16 stage, u16 room, u16 tile);

/* The `count` tiles of a 16-bit room at VRAM tile `index` (one transfer per run of tiles that
 * follow each other in vk_gfx16_pool), and its 32 x 22 cells on BG_A rows 4..25 with PAL0 from
 * TILE_USER_INDEX. */
void vk_gfx16_load_tiles(const VKGfx16Room *g, u16 index, TransferMethod tm);
void vk_gfx16_draw_map(const VKGfx16Room *g);
/* Draws a 32 x 22 map of u8 cells (MSX tile index or 16-bit slot) at rows 4..25 of BG_A, PAL0, from TILE_USER_INDEX. */
void vk_draw_map_u8(const u8 *map);
/* The 704 cells of a packed map (the map of a VKGfx16Room, or vk_maps_z + vk_maps_off[i]): unpacked in a shared RAM buffer
 * (valid until the next call with another map). vk_room_map_msx(i): the cells of the MSX room i of vk_maps_z. */
const u8 *vk_map_unpack(const u8 *packed);
const u8 *vk_room_map_msx(u16 index);

/* Simon's tiles: the arrays decoded from the MSX ROM, or with the option on their 16-bit
 * counterparts of the same layout (generated/simon16_md.h, tools/build_simon16.py). The 16-bit
 * Simon is drawn with PAL3 (vk_simon16_palette in entries 1..13), on every screen of the game. */
const u32 *vk_simon_gfx_player_tiles(void);            /* 12 poses of 12 tiles */
const u32 *vk_simon_gfx_death_tiles(void);             /* 2 x 8 tiles */
const u32 *vk_simon_gfx_stair_tiles(void);             /* 8 poses of 12 tiles */
const u32 *vk_simon_gfx_shield_tiles(u16 pose);        /* 12 tiles */
const u32 *vk_simon_gfx_attack_tiles(void);            /* 3 frames of 32 tiles */
const u32 *vk_simon_gfx_whip_tiles(int kind);          /* kind 1: long whip, 2: thrown weapons; 6 frames of 32 tiles */
const u32 *vk_simon_gfx_crouch_tiles(void);            /* 4 frames of 32 tiles */
const u32 *vk_simon_gfx_crouch_level_tiles(void);      /* 6 frames of 32 tiles */

#endif

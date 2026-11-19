#include "gfx16.h"
#include "generated/rooms.h"
#include "generated/boss69_16_md.h"
#include "generated/intro_assets.h"
#include "generated/player_assets.h"
#include "generated/simon_attack_md.h"
#include "generated/simon_crouch_md.h"
#include "generated/simon_crouch_levels_md.h"
#include "generated/whip_level1_md.h"
#include "generated/whip_level2_md.h"
#include "generated/simon16_md.h"
#include "boss.h"

u8 vk_gfx16;
u8 vk_gfx16_on;

const VKGfx16Room *vk_gfx16_room(u16 stage, u16 room)
{
    if (!vk_gfx16 || stage < 1 || stage > 18) return 0;
    return vk_gfx16_rooms[vk_stages[stage - 1].first + room];
}

u8 vk_gfx16_enemies(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && stage >= 1 && stage <= 3 && !vk_boss_room(stage, room));
}

u8 vk_gfx16_enemies_b2(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && stage >= 4 && stage <= 6 && !(stage == 6 && room == 1) && !vk_boss_room(stage, room));
}

u8 vk_gfx16_enemies_b3(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && stage >= 7 && stage <= 9 && !vk_boss_room(stage, room));
}

u8 vk_gfx16_enemies_b4(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && stage >= 10 && stage <= 12 && !vk_boss_room(stage, room));
}

/* Block 4, the arrays loaded whole. Not inlined (room_cells stays small); room_cells calls them only in stage 11, 10 or 12, so
 * the rooms of the other stages pay nothing (the stage 4 room 4 entry of zzze_gfx16_enemies_block2 ends 2 lines before the
 * VBlank: a call there made it one frame longer). */
__attribute__((noinline)) const u32 *vk_gfx16_b4_zombie(u16 room, const u32 *msx)
{
    return !room && vk_gfx16_enemies_b4(11, room) ? vk_enemy16b4_zombie_tiles : msx;
}

__attribute__((noinline)) const u32 *vk_gfx16_b4_bat(u16 room, const u32 *msx)
{
    return vk_gfx16_enemies_b4(10, room) ? vk_enemy16b4_bat_tiles : msx;
}

__attribute__((noinline)) const u32 *vk_gfx16_b4_late(u16 room, const u32 *msx)
{
    return vk_gfx16_enemies_b4(12, room) ? vk_enemy16b4_cells + 32 * VK_ENEMY16B4_LATE_CELL : msx;
}

/* Block 5: the rooms of stages 13 to 15 that load late enemy cells (late_graphics_rooms: tiles != 0). */
u8 vk_gfx16_enemies_b5(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && (stage == 13 || (stage == 14 && room < 8) || (stage == 15 && room >= 1 && room <= 8 && room != 5)));
}

__attribute__((noinline)) const u32 *vk_gfx16_b5_late(u16 stage, u16 room, const u32 *msx)
{
    return vk_gfx16_enemies_b5(stage, room) ? vk_enemy16b5_cells : msx;
}

/* Block 6: the rooms of stages 16 and 17 that load late enemy cells of the block (not the rooms with object 1B only). */
u8 vk_gfx16_enemies_b6(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && ((stage == 16 && room >= 1 && room <= 8 && room != 5 && room != 6) || (stage == 17 && room >= 1 && room <= 10)));
}

__attribute__((noinline)) const u32 *vk_gfx16_b6_late(u16 stage, u16 room, const u32 *msx)
{
    /* + stage 16 room 0: it loads only object 1B (pool slots 4 and 5, the 16-bit blob); PAL2 stays the MSX one */
    return (vk_gfx16_enemies_b6(stage, room) || (vk_gfx16_on && stage == 16 && room == 0)) ? vk_enemy16b6_cells : msx;
}

/* Block 7: the rooms of stage 18 that load late enemy cells of the block (axe knight rooms 1, 2, 8; flea rooms 3 to 7). */
u8 vk_gfx16_enemies_b7(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && stage == 18 && room >= 1 && room <= 8);
}

__attribute__((noinline)) const u32 *vk_gfx16_b7_late(u16 stage, u16 room, const u32 *msx)
{
    return vk_gfx16_enemies_b7(stage, room) ? vk_enemy16b7_cells : msx;
}

void vk_gfx16_enemy_cells(u16 stage, u16 room, u16 index, TransferMethod tm)
{
    const u8 *cell;
    if (!vk_gfx16_enemies_b2(stage, room)) return;
    /* pairs (pattern, cell of the pool): pattern N is tile N - 0x40 of the block */
    for (cell = stage == 6 ? vk_enemy16b2_stage6 : vk_enemy16b2_stage4; *cell; cell += 2)
        VDP_loadTileData(&vk_enemy16b2_cells[cell[1] * 32], (u16)(index + cell[0] - 0x40), 4, tm);
}

u8 vk_gfx16_enemy_block(u16 stage, u16 room, const u32 *msx, u16 count, u16 index, TransferMethod tm)
{
    const u8 *cell;
    u16 next = 0;   /* first tile of the block not loaded yet */
    if (stage <= 11 && vk_gfx16_enemies_b4(stage, room))
    {
        /* block 4: the 16-bit cells of a stage are one run of the pool from pattern 40 (the blank MSX cells between them
         * stored blank), then the MSX cells after it: as many tiles as the MSX block, in two transfers */
        const u16 n = 4 * (stage == 10 ? VK_ENEMY16B4_STAGE10_CELLS : VK_ENEMY16B4_STAGE11_CELLS);
        VDP_loadTileData(vk_enemy16b4_cells + 32 * (stage == 10 ? VK_ENEMY16B4_STAGE10_CELL : VK_ENEMY16B4_STAGE11_CELL), index, n, tm);
        VDP_loadTileData(msx + n * 8, (u16)(index + n), (u16)(count - n), tm);
        return 1;
    }
    if (!vk_gfx16_enemies_b3(stage, room)) return 0;
    /* pairs (pattern, cell of the pool): pattern N is tile N - 0x40 of the block. A run of cells that follow each other in
     * the block and in the pool is one transfer (the pool is in pattern order: one run per stage); the MSX tiles around the
     * runs are loaded as before, so the room loads as many tiles as in MSX mode. */
    cell = stage == 7 ? vk_enemy16b3_stage7 : stage == 8 ? vk_enemy16b3_stage8 : vk_enemy16b3_stage9;
    while (*cell)
    {
        const u16 first = (u16)(cell[0] - 0x40);
        u16 n = 1;
        while (cell[2 * n] && cell[2 * n] == cell[0] + 4 * n && cell[2 * n + 1] == cell[1] + n) n++;
        if (first > next) VDP_loadTileData(msx + next * 8, (u16)(index + next), (u16)(first - next), tm);
        VDP_loadTileData(&vk_enemy16b3_cells[cell[1] * 32], (u16)(index + first), (u16)(4 * n), tm);
        next = (u16)(first + 4 * n);
        cell += 2 * n;
    }
    if (next < count) VDP_loadTileData(msx + next * 8, (u16)(index + next), (u16)(count - next), tm);
    return 1;
}

void vk_gfx16_crusher_block(const u32 *msx, u16 count, u16 index, TransferMethod tm)
{
    VDP_loadTileData(msx, index, VK_CRUSHER16_FIRST_TILE, tm);
    VDP_loadTileData(vk_crusher16_tiles, (u16)(index + VK_CRUSHER16_FIRST_TILE), VK_CRUSHER16_TILES, tm);
    VDP_loadTileData(msx + (VK_CRUSHER16_FIRST_TILE + VK_CRUSHER16_TILES) * 8, (u16)(index + VK_CRUSHER16_FIRST_TILE + VK_CRUSHER16_TILES),
                     (u16)(count - VK_CRUSHER16_FIRST_TILE - VK_CRUSHER16_TILES), tm);
}

u8 vk_gfx16_boss3(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && stage == 3 && vk_boss_room(3, room));
}

u8 vk_gfx16_boss(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && (stage == 3 || stage == 6 || stage == 9) && vk_boss_room(stage, room));
}

u8 vk_gfx16_boss1215(u16 stage, u16 room)
{
    return (u8)(vk_gfx16_on && (stage == 12 || stage == 15) && vk_boss_room(stage, room) ? stage : 0);
}

const u16 *vk_gfx16_pal2(u16 stage, u16 room, const u16 *msx)
{
    if (vk_gfx16_boss(stage, room) && stage != 3) return stage == 6 ? vk_boss6_16_palette : vk_boss9_16_palette;
    if (vk_gfx16_boss3(stage, room)) return vk_boss16_palette;
    if (vk_gfx16_on && stage == 6 && room == 1) return vk_crusher16_palette;     /* the crusher room (no other enemy) */
    if (stage == 12 || stage == 15) {const u8 b = vk_gfx16_boss1215(stage, room); if (b) return b == 12 ? vk_boss12_16_palette : vk_boss15_16_palette;}
    if (vk_gfx16_enemies_b2(stage, room)) return vk_enemy16b2_palette;
    /* block 3: the MSX rooms of stages 7 to 9 have 66C or 26C in entry 7 (read by other content): the palette with that entry */
    if (vk_gfx16_enemies_b3(stage, room)) return vk_enemy16b3_palette[msx[7] == vk_enemy16b3_palette[1][7]];
    /* block 4: one palette per group of rooms (the enemies of the group; entry 7 of the MSX rooms is CAE, 000 or 66C) */
    if (vk_gfx16_enemies_b4(stage, room))
        return vk_enemy16b4_palette[stage == 10 ? 0 : stage == 12 || room == 5 ? 3 : room ? 2 : 1];
    /* block 5: the palette whose entry 7 is the MSX entry 7 of the room (CAE, 66C, 26C) */
    if (vk_gfx16_enemies_b5(stage, room))
        return vk_enemy16b5_palette[msx[7] == vk_enemy16b5_palette[0][7] ? 0 : msx[7] == vk_enemy16b5_palette[1][7] ? 1 : 2];
    /* block 6: one palette per group of rooms: stage 16, stage 17 room 1, rooms 3-5 (entry 7 is 26C), the other rooms */
    if (vk_gfx16_enemies_b6(stage, room))
        return vk_enemy16b6_palette[stage == 16 ? 0 : room == 1 ? 1 : room >= 3 && room <= 5 ? 3 : 2];
    /* block 7: stage 18, one palette for the axe knight rooms (1, 2, 8: entry 7 is 26C), the other for the flea rooms */
    if (vk_gfx16_enemies_b7(stage, room))
        return vk_enemy16b7_palette[room == 1 || room == 2 || room == 8];
    return vk_gfx16_enemies(stage, room) ? vk_enemy16_palette : msx;
}

const VKGfx16Room *vk_gfx16_scene(u16 scene)
{
    if (!vk_gfx16) return 0;
    if (scene >= 3 && scene <= 5) return vk_gfx16_scenes[scene - 3];
    return scene == 6 ? vk_gfx16_room(1, 0) : 0;
}

u16 vk_scene_cell(u16 scene, u16 col, u16 row)
{
    const VKGfx16Room *g = vk_gfx16_on ? vk_gfx16_scene(scene) : 0;
    return (g && row >= 4 && row < 26) ? vk_map_unpack(g->map)[(row - 4) * 32 + col] : vk_scenes[scene].map[row * 32 + col];
}

u16 vk_room_cell(u16 stage, u16 room, u16 i)
{
    const VKGfx16Room *g = vk_gfx16_on ? vk_gfx16_room(stage, room) : 0;
    return vk_map_unpack(g ? g->map : vk_maps_z + vk_maps_off[vk_stages[stage - 1].first + room])[i];
}

const u32 *vk_room_tile(u16 stage, u16 room, u16 tile)
{
    const VKGfx16Room *g = vk_gfx16_on ? vk_gfx16_room(stage, room) : 0;
    return g ? &vk_gfx16_pool[g->slots[tile] * 8] : &vk_tiles[vk_stages[stage - 1].tileset][tile * 8];
}

void vk_gfx16_load_tiles(const VKGfx16Room *g, u16 index, TransferMethod tm)
{
    /* The slots point anywhere in the pool (about 60 runs per room): one VRAM address, then
     * the tiles written by the CPU, no transfer set up per run (draw_room is timed to the image). */
    vu32 *data = (vu32 *)VDP_DATA_PORT;
    const u16 *slot = g->slots;
    u16 n = g->count;
    (void)tm;
    VDP_setAutoInc(2);
    *(vu32 *)VDP_CTRL_PORT = VDP_WRITE_VRAM_ADDR((u32)index * 32);
    while (n--)
    {
        const u32 *src = &vk_gfx16_pool[*slot++ * 8];
        *data = *src++; *data = *src++; *data = *src++; *data = *src++;
        *data = *src++; *data = *src++; *data = *src++; *data = *src;
    }
}

/* The packed maps (LZ4W, 704 bytes once unpacked) go through one RAM buffer, unpacked when a room is drawn: the rooms
 * read their cells again only for the room on screen, so the next calls find the same source. */
static u8 map_cache[704 + 2] __attribute__((aligned(2)));
static const u8 *map_cache_src;

const u8 *vk_map_unpack(const u8 *packed)
{
    if (packed != map_cache_src)
    {
        map_cache_src = 0;
        lz4w_unpack(packed, map_cache);
        map_cache_src = packed;
    }
    return map_cache;
}

const u8 *vk_room_map_msx(u16 index)
{
    return vk_map_unpack(vk_maps_z + vk_maps_off[index]);
}

void vk_gfx16_draw_map(const VKGfx16Room *g)
{
    vk_draw_map_u8(vk_map_unpack(g->map));
}

void vk_draw_map_u8(const u8 *map)
{
    vu16 *data = (vu16 *)VDP_DATA_PORT;
    const u8 *cell = map;
    const u16 base = TILE_ATTR_FULL(PAL0, FALSE, FALSE, FALSE, TILE_USER_INDEX);
    u16 row, col;
    VDP_setAutoInc(2);
    for (row = 4; row < 26; row++)
    {
        *(vu32 *)VDP_CTRL_PORT = VDP_WRITE_VRAM_ADDR((u32)VDP_getPlaneAddress(BG_A, 0, row));
        for (col = 0; col < 32; col += 4)
        {
            *data = (u16)(base + *cell++); *data = (u16)(base + *cell++);
            *data = (u16)(base + *cell++); *data = (u16)(base + *cell++);
        }
    }
}

#define PICK(msx, art) ((const u32 *)(vk_gfx16 ? (const void *)(art) : (const void *)(msx)))
const u32 *vk_simon_gfx_player_tiles(void) { return PICK(vk_player_tiles, vk_simon16_player); }
const u32 *vk_simon_gfx_death_tiles(void) { return PICK(vk_player_death_tiles, vk_simon16_death); }
const u32 *vk_simon_gfx_stair_tiles(void) { return PICK(vk_player_stair_tiles, vk_simon16_stair); }
const u32 *vk_simon_gfx_shield_tiles(u16 pose) { return PICK(vk_player_shield_tiles[pose], vk_simon16_shield[pose]); }
const u32 *vk_simon_gfx_attack_tiles(void) { return PICK(vk_simon_attack_tiles, vk_simon16_attack); }
const u32 *vk_simon_gfx_whip_tiles(int kind)
{
    return kind == 1 ? PICK(vk_whip_level1_tiles, vk_simon16_whip1) : PICK(vk_whip_level2_tiles, vk_simon16_whip2);
}
const u32 *vk_simon_gfx_crouch_tiles(void) { return PICK(vk_simon_crouch_tiles, vk_simon16_crouch); }
const u32 *vk_simon_gfx_crouch_level_tiles(void) { return PICK(vk_simon_crouch_level_tiles, vk_simon16_crouch_levels); }

/* No 16-bit picture (0xFF): the object is empty on the MSX too (0x1F, 0x20) or never shown (0x15), its MSX cell is used. */
const u32 *vk_item16_object(u16 object)
{
    const u8 cell = vk_item16_object_cell[object - 1];
    return cell == 0xFF ? &vk_object_tiles[(object - 1) * 32] : &vk_item16_object_tiles[cell * 32];
}
const u32 *vk_item_gfx_weapon_tiles(void) { return vk_gfx16 ? vk_item16_weapon_tiles : vk_weapon_tiles; }

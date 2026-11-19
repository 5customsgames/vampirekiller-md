/*
 * Door / cross clear (7806 -> 9A3A for C800, 9A1A for D700, CFFF = 1), every object type of the port.
 *
 * Expected values come from the ROM run on the Z80 emulator (tools/verify_door_clear_z80.py : 7806 with an object of each type in
 * C800 block 2 at (X 120, Y 176)): every type but 11h, 18h (boss objects) and 22h (erased without flame) becomes an object 1E at
 * (X, Y - 9B33[type]) in the first free block, CF40 and the random register are not touched (9ACC: CFFF != 0 returns before),
 * CE08 + 1. Type 0E makes four flames at (X + 16 k, Y). Nothing stays alive afterwards (the red skeleton 09 included).
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "enemies.c"

/* port type, ROM type (information), flame Y offset D, whether the port stores SAT coordinates (types 1 and 4) */
static const int kTypes[][3] = {
    { ENEMY_TYPE_A, 0x01, 0x10 },      { ENEMY_TYPE_B, 0x01, 0x10 },      { ENEMY_TYPE_4, 0x04, 0 },
    { ENEMY_TYPE_5, 0x05, 0 },         { ENEMY_TYPE_2, 0x02, 0x10 },      { ENEMY_TYPE_6, 0x06, 0x10 },
    { ENEMY_TYPE_8, 0x08, 0 },         { ENEMY_TYPE_7, 0x07, 0 },         { ENEMY_TYPE_STATUE, 0x0A, 0x10 },
    { ENEMY_TYPE_HOPPER, 0x0B, 0x10 }, { ENEMY_TYPE_LEAPER, 0x0C, 0 },    { ENEMY_TYPE_FLEA, 0x0D, 0 },
    { ENEMY_TYPE_GHOST, 0x1A, 0 },     { ENEMY_TYPE_FISH3, 0x03, 0x10 },  { ENEMY_TYPE_EAGLE, 0x0F, 0x18 },
    { ENEMY_TYPE_12, 0x12, 0x18 },     { ENEMY_TYPE_09, 0x09, 0x10 },     { ENEMY_TYPE_10, 0x10, 0x10 },
    { ENEMY_TYPE_SPLASH, 0x20, 0 },
};

static int countKind(const EnemyState *s, int flames)
{
    int i, n = 0;
    for (i = 0; i < ENEMY_MAX; i++)
        if (s->enemy[i].active && (s->enemy[i].type == ENEMY_TYPE_DEATH) == flames) n++;
    return n;
}

static Enemy *place(EnemyState *s, int type, int x, int y)
{
    Enemy *e = newObject(s, (EnemyU8)type);
    assert(e);
    if (type == ENEMY_TYPE_A || type == ENEMY_TYPE_B) { e->romBox = 1; e->x = (EnemyS16)(x - ENEMY_OBJ_X); e->y = (EnemyU8)(y - ENEMY_OBJ_Y); }
    else if (type == ENEMY_TYPE_4) { e->x = (EnemyS16)(x - ENEMY_OBJ_X); e->y = (EnemyU8)(y - ENEMY_TYPE4_OBJ_Y); }
    else { e->x = (EnemyS16)x; e->y = (EnemyU8)y; }
    return e;
}

int main(void)
{
    EnemyState s;
    size_t n;
    int i, k;
    for (n = 0; n < sizeof kTypes / sizeof kTypes[0]; n++) {
        const int type = kTypes[n][0], d = kTypes[n][2];
        EnemyU8 kills;
        Enemies_init(&s);
        Enemies_s7R = 0;                         /* a drop roll would make a 26 flame (big heart) */
        kills = deathKills;
        place(&s, type, 120, 176);
        Enemies_doorClear(&s);
        assert(deathKills == kills);             /* CF40 untouched */
        assert(Enemies_dropCount == 0 && Enemies_lootPick == 0);
        assert(countKind(&s, 0) == 0);           /* nothing survives, the red skeleton included */
        assert(countKind(&s, 1) == 1);
        for (i = 0; i < ENEMY_MAX; i++)
            if (s.enemy[i].active) {
                assert(s.enemy[i].type == ENEMY_TYPE_DEATH && s.enemy[i].x == 120 && s.enemy[i].y == 176 - d);
                assert(s.enemy[i].state == 0 && s.enemy[i].anim == ENEMY_DEATH_START && s.enemy[i].pose == ENEMY_DEATH_POSE_A);
            }
        /* no later revival: the flame lasts 16 updates and nothing comes back */
        for (k = 0; k < 40; k++) { EnemySpawnTimer t; EnemyRoomVars v; memset(&v, 0, sizeof v); Enemies_spawnTimerInit(&t); Enemies_spawnGate = 1; Enemies_frame(&s, &t, &v); }
        assert(countKind(&s, 0) == 0 && countKind(&s, 1) == 0);
        Enemies_spawnGate = 0;
    }
    /* dragon 0E: four flames (X + 16 k, Y), no drop */
    Enemies_init(&s);
    Enemies_s7R = 0;
    place(&s, ENEMY_TYPE_DRAGON, 120, 176);
    Enemies_doorClear(&s);
    assert(countKind(&s, 0) == 0 && countKind(&s, 1) == 4 && Enemies_dropCount == 0);
    for (k = 0; k < 4; k++) {
        int found = 0;
        for (i = 0; i < ENEMY_MAX; i++)
            if (s.enemy[i].active && s.enemy[i].x == 120 + 16 * k && s.enemy[i].y == 176 && s.enemy[i].state == 0) found = 1;
        assert(found);
    }
    /* D700: ball, bone and the shot of the object 10h are erased (9A1A) and leave the 0C effect, no death flame */
    {
        static const int proj[3] = { ENEMY_TYPE_FIREBALL, ENEMY_TYPE_BONE, ENEMY_TYPE_10_SHOT };
        for (n = 0; n < 3; n++) {
            int sparks = 0;
            Enemies_init(&s);
            place(&s, proj[n], 100, 120);
            Enemies_doorClear(&s);
            assert(countKind(&s, 1) == 0);
            for (i = 0; i < ENEMY_PROJECTILE_MAX; i++) {
                assert(!vk_projectiles[i].active || vk_projectiles[i].type == ENEMY_TYPE_SHIELD_SPARK);
                sparks += vk_projectiles[i].active;
            }
            for (i = 0; i < ENEMY_MAX; i++) assert(!s.enemy[i].active || s.enemy[i].type == ENEMY_TYPE_SHIELD_SPARK);
            assert(sparks <= 1);
        }
    }
    /* seven blocks mixed: the whole C800 table is cleared in one call */
    Enemies_init(&s);
    Enemies_s7R = 0;
    place(&s, ENEMY_TYPE_09, 176, 80);
    place(&s, ENEMY_TYPE_09, 64, 112);
    place(&s, ENEMY_TYPE_09, 160, 176);
    place(&s, ENEMY_TYPE_FLEA, 40, 176);   /* 3 x 4 + 2 = 14 SAT entries */
    Enemies_doorClear(&s);
    assert(countKind(&s, 0) == 0 && countKind(&s, 1) == 4);
    Enemies_s7R = -1;
    printf("door clear (7806): %d C800 types, dragon, 3 D700 types: every object destroyed, flame at (X, Y - 9B33), no drop, CF40 untouched PASS\n",
           (int)(sizeof kTypes / sizeof kTypes[0]));
    return 0;
}

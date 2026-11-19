#!/usr/bin/env python3
"""Exercise the actual airborne update cases and collision helpers with a host C compiler."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'src/main.c'
s = source.read_text()
def fn(signature):
    start = s.index(signature + '\n{')
    return s[start:s.index('\n}', start) + 2]

fixtures = ''
for block in range(2, 8):
    data = (root / f'src/block{block}.c').read_text()
    body = re.search(r'const u32 block' + str(block) + r'_wall\[.*?\] = \{(.*?)\};', data, re.S)[1]
    fixtures += f'static const uint32_t real{block}[] = {{{body}}};\n'
curve = re.search(r'const s8 simon_jump_dy\[.*?\] = \{(.*?)\};', (root / 'src/level.c').read_text())[1]
prefix = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef int16_t s16; typedef int8_t s8; typedef uint8_t u8; typedef uint16_t u16;
#define TRUE true
#define FALSE false
#define FEET 32
#define JUMP_FRAMES 42
#define HURT_FRAMES 24
#define FALL_VY 8
#define BUTTON_LEFT 1
#define BUTTON_RIGHT 2
#define BUTTON_DOWN 4
#define BUTTON_B 8
#define BUTTON_UP 16
#define JUMP_SKIP 2
enum {ST_STAND, ST_JUMP, ST_FALL, ST_WHIP, ST_HURT, ST_CROUCH, ST_WALK};
static s16 simon_x, simon_y, jump_base_y;
static s8 jump_vx;
static u8 state;
static u16 state_t, anim;
static bool drop, facing_left, air_whip;
static bool walls[30][128], floor_only, moving_platform, carry_mode;
static s16 carry_x;
static const uint32_t *real;
static int cols;
static bool wall_at(s16 x, s16 y) {
    if (x < 0 || y < 0 || y >= 224) return false;
    return real ? x/8 < cols && ((real[x/8] >> (y/8)) & 1) : x/8 < 128 && walls[y/8][x/8];
}
static bool solid_at(s16 x, s16 y) {
    return floor_only && x >= 64 && x < 80 && y == 192;
}
static s8 plat_under(s16 x, s16 feet) {
    if (carry_mode) return feet == 192 && x+8-carry_x >= -17 && x+8-carry_x <= 16 ? 0 : -1;
    return moving_platform && x+8 >= 64 && x+8 <= 96 && feet == 192 ? 0 : -1;
}
static bool try_mount(bool up) { (void)up; return false; }
static bool whip_tick(void) { return false; }
static bool start_attack(u16 pad, u16 pressed, bool crouch) { (void)pad; (void)pressed; (void)crouch; return false; }
typedef struct { u8 sec, uf, u, vf, v; s16 cx; u8 y, shift; } PlatDef;
typedef struct { u8 uf, u, vf, v; s16 x; } Plat;
static Plat plats[4];
static const PlatDef plat_defs[] = {{0,0,0,0,0,56,192,0}};
static const PlatDef *plat_def = plat_defs;
static u8 plat_n = 1, plat_sec, section;
static const struct { s16 c0; } sections[] = {{0}};
static int failures, checks;
static void check(const char *name, bool ok) {
    checks++; if (!ok) { if (failures < 12) printf("FAIL: %s\n", name); failures++; }
}
static void reset(void) {
    memset(walls, 0, sizeof(walls)); floor_only = moving_platform = carry_mode = drop = false;
    real = NULL; cols = 128; state_t = 0; state = ST_FALL;
    simon_x = 51; simon_y = 159; jump_vx = 1;
}
'''
# Copy the real state bodies, then the real post-step collision pass, if present.
cases = s[s.index('    case ST_STAND:\n', s.index('static void simon_update(')):]
cases = cases[:cases.index('    case ST_MOUNT:')]
correction = ''
marker = '    if ((previous_state == ST_JUMP'
if marker in s:
    start = s.index(marker)
    end = s.index('\n    if (state == ST_JUMP || state == ST_FALL)', start)
    correction = s[start:end]
update = '''static void step_pressed(u16 pad, u16 pressed) {
    bool left = pad & BUTTON_LEFT, right = pad & BUTTON_RIGHT;
'''
if correction:
    update += '    s16 previous_x = simon_x, previous_y = simon_y; u8 previous_state = state;\n'
update += '    switch (state) {\n' + cases + '    default: break;\n    }\n' + correction + '\n}\nstatic void step(u16 pad) { step_pressed(pad, 0); }\n'
main = r'''
int main(void) {
    // Replay a complete jump from the actual grounded input branch. The first
    // airborne frame has zero vertical displacement: it must not land again.
    for (int dir=-1;dir<=1;dir++) for (int release=0;release<2;release++) {
        reset(); for(int c=0;c<128;c++)for(int r=24;r<28;r++)walls[r][c]=true;
        state=ST_STAND; simon_x=200; simon_y=160;
        u16 pad=dir<0?BUTTON_LEFT:dir>0?BUTTON_RIGHT:0;
        step_pressed(pad|BUTTON_B,BUTTON_B);
        check("jump input starts from ground",state==ST_JUMP && simon_y==160 && simon_x==200+dir);
        for(int t=JUMP_SKIP;t<=JUMP_FRAMES;t++) {
            int expected_y=160+(t<JUMP_FRAMES?simon_jump_dy[t]:0);
            step(release?0:pad);
            check("complete jump follows recorded vertical curve",simon_y==expected_y);
            check("jump is not cancelled on flat first frame",t==JUMP_FRAMES?state==ST_STAND:state==ST_JUMP);
            int steps=t-JUMP_SKIP+2;
            if(release && t==JUMP_FRAMES)steps--;
            check("horizontal direction stays locked until landing",simon_x==200+dir*steps);
        }
        check("complete jump lands flush with floor",simon_y==160 && state==ST_STAND);
    }
    for (int dir = -1; dir <= 1; dir += 2) {
        for (int kind = 0; kind < 3; kind++) for (int speed = 2; speed <= 8; speed++) {
            reset(); floor_only = kind == 1; moving_platform = kind == 2;
            if (!kind) for (int r = 24; r < 28; r++) for (int c = 8; c < 10; c++) walls[r][c] = true;
            simon_x = kind == 2 ? (dir > 0 ? 55 : 89) : (dir > 0 ? 51 : 76);
            simon_y = 159; jump_vx = dir;
            state_t = (speed-2)*4; if (speed >= 6) { drop = true; state_t = 1; }
            step(0);
            check("diagonal descent lands on top", simon_y == 160 && state == ST_STAND);
            for (int f = 0; f < 3; f++) step(0);
            check("landing stays at surface", simon_y == 160);
        }
        // Recorded jump curve and knockback both cross the corner between x checks.
        for (int t = 29; t < JUMP_FRAMES; t++) {
            int dy = simon_jump_dy[t] - simon_jump_dy[t-1];
            if (dy < 2) continue;
            reset(); floor_only = true; state = ST_JUMP; state_t = t;
            simon_x = dir > 0 ? 51 : 76; jump_vx = dir;
            jump_base_y = 159 - simon_jump_dy[t-1]; simon_y = 159;
            step(dir > 0 ? BUTTON_RIGHT : BUTTON_LEFT);
            check("recorded jump lands after horizontal step", simon_y == 160 && state == ST_STAND);
        }
        for (int t = 14; t < HURT_FRAMES; t++) {
            if (((t-1)*(HURT_FRAMES-(t-1)))/6 <= (t*(HURT_FRAMES-t))/6) continue;
            reset(); floor_only = true; state = ST_HURT; state_t = t;
            simon_x = dir > 0 ? 51 : 76; jump_vx = dir;
            jump_base_y = 159 + ((t-1)*(HURT_FRAMES-(t-1)))/6;
            step(0);
            check("knockback lands after horizontal step", simon_y == 160 && state == ST_STAND);
        }
    }
    reset(); floor_only = true; state = ST_JUMP; state_t = 4; jump_base_y = 172; simon_y = 167;
    step(0);
    check("rising through floor does not snap onto it", simon_y == 162 && state == ST_JUMP);
    reset(); floor_only = true; simon_y = 161; step(0);
    check("already below a one-way surface does not teleport up", simon_y == 163 && state == ST_FALL);
    reset(); simon_x = 64; step(0);
    check("empty pit still falls", simon_y == 161 && state == ST_FALL);
    reset(); floor_only = true; simon_x = 64; step(0);
    check("vertical landing unchanged", simon_y == 160 && state == ST_STAND);
    reset(); for (int r=0;r<28;r++) walls[r][8] = true;
    simon_x = 48; step(0);
    check("full wall still blocks horizontal movement", simon_x == 48);
    // If a breakable block or a moving platform no longer supports Simon,
    // crouching and whipping must not hold him in mid-air.
    for (int pose=0;pose<2;pose++) {
        reset(); floor_only=true; simon_x=64; simon_y=160;
        state = pose ? ST_WHIP : ST_CROUCH;
        step(BUTTON_DOWN);
        check("supported stationary pose remains supported", simon_y==160 && state==(pose?ST_WHIP:ST_CROUCH));
        floor_only=false; air_whip=false;
        step(BUTTON_DOWN);
        check("lost support exits crouch or ground whip", state==ST_FALL && !jump_vx && drop);
        if (pose) check("whip continues as airborne attack", air_whip);
        step(BUTTON_DOWN); step(BUTTON_DOWN);
        check("lost support actually falls", simon_y>160);
    }
    // Carrying uses the actual spring update, with its phase chosen to move 1 px.
    // The platform overlaps a wall; Simon must stop while the platform goes on.
    for (int dir = -1; dir <= 1; dir += 2) {
        reset(); moving_platform = true; simon_y = 160;
        simon_x = dir > 0 ? 48 : 72;
        for (int r=0;r<24;r++) walls[r][8] = true;
        plat_sec = section = 0; plat_n = 1; plat_def = plat_defs;
        plats[0].v = dir > 0 ? 0 : 24; plats[0].vf = dir > 0 ? 128 : 0;
        plats[0].u = dir > 0 ? 64 : (u8)-64; plats[0].uf = 0;
        plats[0].x = dir > 0 ? 56 : 80;
        carry_mode = true; carry_x = plats[0].x;
        s16 before = simon_x, px = plats[0].x;
        plats_update(true);
        check("moving platform cannot carry Simon through a wall", simon_x == before);
        check("blocked rider does not stop platform", plats[0].x == px + dir);
        // Away from a wall, preserve exactly the original platform carry.
        reset(); moving_platform = true; carry_mode = true; carry_x=56; simon_y = 160; simon_x = 48;
        plats[0].v=0; plats[0].vf=128; plats[0].u=64; plats[0].uf=0; plats[0].x=56;
        plats_update(true);
        check("unobstructed platform still carries Simon", simon_x == 49);
        plats[0].v=0; plats[0].vf=128; plats[0].u=64; plats[0].uf=0; plats[0].x=56;
        before = simon_x; plats_update(false);
        check("airborne Simon is not carried", simon_x == before);
    }
    // All foot alignments, including an 8 px obstacle between shin and sole.
    for (int y=100;y<108;y++) for (int row=0;row<28;row++) {
        reset(); simon_x=48; simon_y=y; walls[row][8]=true;
        bool body = row*8 < y+FEET && (row+1)*8 > y+4;
        check("side probes cover all rows down to the soles", wall_ahead(1) == body);
        reset(); simon_x=72; simon_y=y; walls[row][8]=true;
        check("left side tests the next pixel too", wall_ahead(-1) == body);
    }
    const uint32_t *maps[] = {real2, real3, real4, real5, real6, real7};
    const int lengths[] = {sizeof(real2)/4, sizeof(real3)/4, sizeof(real4)/4,
                           sizeof(real5)/4, sizeof(real6)/4, sizeof(real7)/4};
    for (int b = 0; b < 6; b++) {
        int count = 0;
        for (int c = 2; c < lengths[b]-2; c++) for (int r = 7; r < 27; r++) {
            uint32_t above = 15u << (r-4);
            if (!(maps[b][c] & (1u<<r)) || (maps[b][c]&above)) continue;
            for (int dir = -1; dir <= 1; dir += 2) {
                int side = c-dir;
                if (maps[b][side] & (above | (1u<<r))) continue;
                reset(); real = maps[b]; cols = lengths[b];
                simon_x = dir > 0 ? c*8-13 : (c+1)*8-4;
                simon_y = r*8-33; jump_vx = dir;
                step(0);
                check("actual room corner lands without penetration", simon_y == r*8-32 && state == ST_STAND);
                count++;
                // Same real ledge, but entering below its top. Descent must not
                // put the lower legs through the side while looking for a floor.
                reset(); real = maps[b]; cols = lengths[b];
                simon_x = dir > 0 ? c*8-16 : (c+1)*8;
                simon_y = r*8-31; jump_vx = dir;
                s16 before = simon_x;
                step(0);
                check("actual ledge blocks entry from below its top", simon_x == before);

            }
        }
        printf("Block %d: %d actual platform corners\n", b+2, count);
        check("real room cases exercised", count > 0);
    }
    printf("%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / 'test.c'
    exe = Path(tmp) / 'test'
    c.write_text(prefix + fixtures + f'static const s8 simon_jump_dy[] = {{{curve}}};\n'
                 + fn('static bool headroom(void)') + fn('static bool standable(s16 y)') + fn('static bool move_down_to(s16 new_y)')
                 + (fn('static bool wall_ahead_from(s8 dir, s16 from_y)') if 'static bool wall_ahead_from(' in s else '')
                 + fn('static bool wall_ahead(s8 dir)')
                 + fn('static void plat_add(u8 *a, u8 *af, u8 b, u8 shift)')
                 + fn('static void plats_update(bool riding)') + update + main)
    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(c), '-o', str(exe)], check=True)
    sys.exit(subprocess.run([str(exe)]).returncode)

#include <genesis.h>
#include "level.h"
#include "block2.h"
#include "block3.h"
#include "block4.h"
#include "block5.h"
#include "block6.h"
#include "block7.h"
#include "screens.h"
#include "maps.h"
#include "sound.h"
#include "demo.h"
#include "startup_logo.h"
#ifdef VK_BASE                                     /* Vampire Collection build (collection/) */
#include "collection.h"
#endif
#include "miku_mode.h"
#include "miku_intro_data.inc"

// The 256x240 NES picture is centred on the 320x224 MD screen: x + 32, y - 8.
#define NES_X        32
#define HUD_ROWS     5
#define PLANE_COLS   64
#define STAND_Y      160                       // NES OAM y of Simon's head when standing
#define FEET         32                        // Simon is 32 px tall, 16 px wide
#define SCROLL_AT    120                       // Simon stops here on screen, the camera moves instead
#define MAX_SPRITES  64
#define SPARK_FRAMES 21                        // candle destruction: sparkle + flame, then the item appears
#define DEATH_FRAMES 10                        // sparkle when a zombie or panther dies

#define PLAYER_HP      64                      // 8 units per health bar tile, 8 tiles (values from the NES game)
#define INVULN_FRAMES  90
#define HURT_FRAMES    24                      // knockback hop
#define DEAD_FRAMES    97                      // to the restart, whether health, time or a fall killed him (NES game)
#ifndef START_TIME                             /* -DSTART_TIME=3: testing aid */
#define START_TIME     300                     // TIME of blocks 0 and 1 (table at $C9F6 of the NES game)
#endif
#define FALL_VY        8                       // walking off a ledge: 8 px/frame down, still 1 px/frame forwards
#define CLIMB_WAIT     18                      // ST_CLIMB: frames standing at the stage's start, then the steps
#define CLIMB_STEPS    95
#define PIT_Y          208                     // head y at which Simon is lost in a pit or the water (centre 224, $966D)
#define TIME_TICK      64                      // frames per TIME unit
#define START_LIVES    3
#define MAX_LIVES      99
#define MAX_ENEMIES    5
#define ZOMBIE_SCORE   100
#define PANTHER_SCORE  200
// castle gate cutscene, measured on the NES game (its state $18 = 10): positions are Simon's anchor (centre - 8)
#define GATE_TRIGGER   671                     // the cutscene starts once his centre passes x 678, on the floor...
#define GATE_TRIGGER_END 705                   // ...up to x 713 (the NES table at $CF9B: within 18 px of 696)
#define GATE_MASKED    688                     // from centre 696 the mask sprites hide him in the archway
#define GATE_STOP      704                     // he stops at centre 712...
#define GATE_WAIT      64                      // ...for 64 frames, then the hall is loaded
#define GATE_SPEED     0x50                    // 0.3125 px/frame, whatever the pad says
#define GATE_CAM       (GATE_COL0 * 8)         // the courtyard's scroll stops on the gate screen
// stage 16's archway, the same cutscene leftwards ($CF9B: within 18 px of centre x 54, y 112 on its first screen):
// he walks left from there, hidden from centre 54 by a 16x32 mask at x 30, OAM y 96, to centre 38, measured
#define ARCH_X0        (ROOM6(16, 0) * 8)      // world x of the archway's screen
#define ARCH_TRIGGER   (ARCH_X0 + 54 - 17 - 8)
#define ARCH_TRIGGER_END (ARCH_X0 + 54 + 17 - 8)
#define ARCH_MASKED    (ARCH_X0 + 54 - 8)
#define ARCH_STOP      (ARCH_X0 + 38 - 8)
#define ARCH_MASK_X    (ARCH_X0 + 30)
#define ARCH_MASK_Y    96
#define HALL_X         552                     // where Simon appears in the hall (centre 560), facing right
#define HALL_Y         176
#define HALL_LOAD      21                      // frames with the display off while the hall (or a room) is loaded
// the door between stages (the NES game's state 8): positions are Simon's anchor in the stage he leaves
#define DOOR_AT        228                     // he goes in once his centre passes x 236 on the screen (a door on
#define DOOR_AT_LEFT   18                      // the right), or x 26 (on the left: exit table $FC12; he then ends
                                               // at x 720 in stage 5, as in the NES game)...
#define DOOR_Y         80                      // ...standing on the floor in front of it (centre y 96 in stages 1-4)
#define DOOR_ROWS      6                       // rows of the closed door's background column, from 16 px above his head
#define MAX_SHOTS      3                       // 1 + shot_level sub-weapons in flight
// sub-weapons, measured on the NES game (slot $14 of its object table, see tools/record_subweapons.py)
#define JUMP_SKIP      2                       // see the jump's start in simon_update
#define THROW_AT       5                       // the weapon leaves the hand on the 5th frame of the arm-out phase
#define DAGGER_VX      (4 << 8)
#define HOLY_VX        0x180                   // 1.5 px/frame
#define HOLY_VY        0x180                   // thrown 1.5 px/frame upwards
#define HOLY_GRAVITY   0x21
#define FLAME_FRAMES   76
#define AXE_VX         0x200                   // 2 px/frame
#define AXE_VY         0x580                   // thrown 5.5 px/frame upwards, then 0x40 or 0x41 less each frame
#define CROSS_VX       0x200                   // 2 px/frame for 64 frames, brakes by 0x21 a frame, turns back,
#define CROSS_OUT      64                      // speeds up by 0x20 a frame up to 2 px/frame again
#define CROSS_BRAKE    0x21
#define CROSS_BACK     0x20
#define WATCH_HEARTS   5                       // the stopwatch costs 5 hearts...
#define WATCH_FRAMES   180                     // ...and stops the enemies, their arrival and TIME for 180 frames
#define POTION_FRAMES  360                     // invisibility potion: no damage for 360 frames, Simon blinks
#define ROSARY_FRAMES  30                      // the screen flashes, every enemy on it dies (no points)
// enemies of stages 2 and 3, measured on the NES game (tools: see README); speeds in 1/256 px per frame
#define GRAVITY        0x21                    // zombies walking off a ledge, fishmen, splash drops
#define BAT_VX         0x120
#define BAT_SCORE      200
#define FISH_VY        0x580                   // out of the water at 5.5 px/frame
#define FISH_VX        0xC0
#define FISH_SCORE     300
#define FIRE_VX        0x1C0
#define FIRE_SCORE     100
#define WATER_Y        192                     // a falling fishman's centre this low is back in the water
#define MAX_MONSTERS   12
// the boss of stage 3 (phantom bat, NES object 0x19, its AI in bank 5 at $80D2), measured on the NES game
#define BOSS_HP        (64 << 8)               // in 1/256: the whip takes 6 (8 once upgraded), dagger 6, axe and cross 8,
#define BOSS_HOLY      0x1C0                   // holy water 1.75 every 4 frames
#define BOSS_IMMUNE    8                       // NES $E2A9/$EEA7: frames stunned after a nonfatal direct hit
#define BOSS_X         623                     // where it sleeps in stage 3, centre y 64
#define BOSS_Y         64
#define BOSS_HW        20                      // half sizes of its box
#define BOSS_HH        10
#define BOSS_SCORE     3000
// Medusa (NES object type 0x1B, AI at $82C5 of bank 5) is a statue in the background at the left end of stage 6
// (floor 1). When the screen reaches that end ($48), 180 frames, then the statue's 4x4 tiles are erased ($FAB4) and
// she rises at 0.5 px/frame until her centre is above y 168, drops a snake, turns to Simon and floats across at
// 0.875 px/frame on a spring around 4 px below where she was ($EF13, like the Medusa heads), turning back at x 16 and
// 240, for 16, 128, 64 or 160 frames in turn ($833A, the turn picked at random when she wakes), then stays still 60
// frames and rises again. She takes half the phantom bat's damage ($E271), 8 frames apart; 64 hit points, 3000
// points, then the same flames and orb (all measured)
#define MEDUSA_BX      113                     // where she wakes, on the screen at the end of the stage, centre y 144
#define MEDUSA_BY      144
#define MEDUSA_WAKE    180
#define MEDUSA_RISE    0x80
#define MEDUSA_TOP     0xA8
#define MEDUSA_BVX     0xE0
#define MEDUSA_PAUSE   60
#define MEDUSA_HW      14                      // half sizes of her box ($E46A)
#define MEDUSA_HH      14
#define STATUE_COL     12                      // the statue's tiles: columns 12 to 15, rows 16 to 19 of the screen
#define STATUE_ROW     16
// her snakes (NES object type 9, AI at $8389): fall (gravity 0x21) onto a floor, crawl 1.5 px/frame for 24 frames,
// stop 2, crawl again, fall off the ends; one hit, 100 points, they stay when they touch Simon (all measured)
#define SNAKE_VX       0x180
#define SNAKE_CRAWL    24
#define SNAKE_SCORE    100
#define SNAKE_ANIM     9
enum { SN_FALL, SN_CRAWL, SN_STOP };
// the armour knight (NES object type 8, AI at $8456 of bank 5): walks 0.5 px/frame, turns back every 192 frames, at a
// wall 16 px ahead or where there is no floor 4 px ahead; while Simon's centre is within 4 px of its height it turns
// to him instead (every 192 frames). Damage it takes is counted as the NES game does ($584, 4 per unit of the boss's):
// it dies at 64, the whip giving 24 (32 once upgraded), the dagger 24, the axe and the cross 32, holy water 1 a frame;
// after a hit it stands still for 16 frames ($568) and no other hit counts. 400 points (all measured)
#define KNIGHT_VX      0x80
#define KNIGHT_TURN    192
#define KNIGHT_HP      64
#define KNIGHT_IMMUNE  16
#define KNIGHT_SCORE   400
#define KNIGHT_ANIM    17                      // frames per walking pose
enum { K_PATROL, K_CHASE, K_FALL };
// the ghost (NES object type 0x0D, AI at $EDBB): every 32 frames it aims at Simon's centre ($EEBB, like the phantom
// bat), 0.75 px/frame along the longer axis and 3/4 of the ratio along the other ($EDA5), through everything. It
// takes damage like the knight (dies at 64, still for 16 frames after a hit); 300 points, it stays when it touches
// Simon. Its generator (kind $0D, $84E7 of bank 6) puts it once at its place while that is within 32 px of the
// screen's left edge (kind $8D: the right edge, from 224) and Simon's centre is less than 48 px above or below it; at
// most 2 (all measured)
#define GHOST_V        0xC0
#define GHOST_AIM      32
#define GHOST_SCORE    300
#define GHOST_ANIM     9
// the bone pillar (NES object type 0x0E, AI at $F16C): turns to Simon; waits (24 frames when it comes), flashes
// 24 frames (sprite palette 3 every other frame), spits a fireball (2 px/frame straight, at its centre, 100 points when whipped), another 40 frames
// later, then waits 60, 120, 180 or 240 frames at random ($F199). Fireballs: at most 3 ($82A2 of bank 5). It dies at
// 192 damage with no pause after a hit ($E18D: 8 whip hits, 6 with a chain); 400 points (all measured)
#define PILLAR_HP      192
#define PILLAR_FIRST   24
#define PILLAR_FLASH   24
#define PILLAR_SECOND  40
#define PILLAR_SCORE   400
#define PILLAR_FIRE_VX 0x200
enum { PL_WAIT, PL_FLASH, PL_SHOOT, PL_AGAIN };
// the red bat (NES object type 7, AI at $83F3 of bank 5): asleep where it is placed until Simon's centre is less than
// 56 px below its own (or level with it) and less than 96 px across; then it flies towards him at 1.5 px/frame
// across, starting 1.5 px/frame down and slowing that by 8/256 a frame, then straight on, through the walls. One hit,
// 200 points; it dies on Simon like a bat (all measured)
#define RBAT_VX        0x180
#define RBAT_VY        0x180
#define RBAT_BRAKE     8
#define RBAT_SCORE     200
enum { RB_SLEEP, RB_SWOOP, RB_FLY };
// the Medusa head (NES object type 6, AI at $EF92): 1.25 px/frame across, a spring around the height it was given
// ($EF13: vy -= y - cy in 1/256 px, then y += vy plus the carry the subtraction left). Its generators (kind 6, and
// kind 5 on loop 2 only, $8431 of bank 6) work while their place is 8 to 248 px into the screen: 18 frames after it
// comes on screen, then every 128 frames, at most 3 heads, from the edge Simon faces, 33 px above his centre which is
// the centre line. One hit, 300 points; touching Simon does not kill it (all measured)
#define MEDUSA_VX      0x140
#define MEDUSA_WAIT    0x40                    // gen wait counted every 2nd frame, like the bat's
#define MEDUSA_FIRST   9
#define MEDUSA_SCORE   300
#define MEDUSA_ANIM    9
#define ORB_GRAVITY    0x41
// Block 3's enemies wait 60 frames where their generator put them before they move (the NES game's $54C). Their
// gravity: 0x20 / 256 px a frame, plus the borrow the NES game's SBC without SEC takes (0x21, measured)
#define B3_WAIT        61
#define B3_GRAVITY     0x21
// the fleaman (NES object type 0x0C, AI at $EFB8): hidden while it waits, then drops onto the floor below it ($EC21
// tests its centre 8 px down) and hops: 8 frames on the floor, it turns to Simon and jumps, high and short (3.5 px a
// frame up, 1 across) when he is less than 64 px away and faces it, else low and long (1 up, 2.25 across). One hit,
// 500 points (all measured)
#define FLEA_HOP_WAIT  8
#define FLEA_NEAR      0x40
#define FLEA_HIGH_VY   0x380
#define FLEA_HIGH_VX   0x100
#define FLEA_LOW_VY    0x100
#define FLEA_LOW_VX    0x240
#define FLEA_SCORE     500
enum { FL_HIDDEN, FL_FALL, FL_WAIT, FL_JUMP, FL_CARRIED };
// the eagle of stage 11 (NES object type 0x12, AI at $ECF2; generator kind 0x12, $F4D2): every 112 frames while its
// place is on the screen, from one edge of it at random (x 0x12 or 0xEE), at its y plus 32, 16, 48, 0 in turn, at
// most 3 at a time; it flies across at 1.75 px a frame for 48 frames, stops for 16, and so on, with a fleaman 16 px
// under it (state 5, $EFCA: the two fleaman poses in turn every 9 frames), which it drops when Simon is less than
// 64 px from it across (looked at every 8 frames) or once the eagle is gone. One hit, 300 points; it survives
// touching Simon (all measured)
#define EAGLE_VX       0x1C0
#define EAGLE_FLY      0x30
#define EAGLE_STOP     0x10
#define EAGLE_WAIT     0x38
#define EAGLE_ANIM     17
#define EAGLE_SCORE    300
enum { EG_FLY, EG_STOP };
// the bone dragon of stages 11 and 12 (generator kind 0x54, $8867 of bank 6: once while its place is on the screen): a
// head (NES type 0x14, AI $8ADA of bank 5), 5 vertebrae (0x15, $8BF9) and a base in the wall (0x16, $8C51), each one at
// the base's x minus its own reach. After 8 frames the head reaches out to 52 px and the vertebrae to 40, 32, 24, 16
// and 8, 1 px a frame; 8 frames later the head starts weaving. Each part keeps its y as the next part's (towards the
// base) plus its own dy, which its motion (1 up, 2 down) moves by its speed, within +-8 px; at that limit the next
// part takes over the motion at 1.75 px a frame ($8A85), which slows down by 1/8 px a frame in a vertebra until it
// stops ($8C38). The head moves at 1.75 px a frame, turns up or down after 52, 36, 60 or 28 frames at random, and
// every 32 frames heads for Simon's height (frame & 31 == 8) or, one time in two (frame & 31 == 0), opens its mouth
// for 16 frames, then spits a fireball at Simon ($EC88: 1.5 px a frame along the longer axis) if he is to its left
// and less than 40 px above or below, and closes it 16 frames later. Only the head can be hit: 192 damage ($E16A),
// standing still 16 frames after each hit; the whole dragon then burns, 1000 points (all measured). The NES game
// takes it away once the base is 368 px right of the screen (Simon gone back)
#define DRAGON_REACH   52
#define DRAGON_V       0x1C0
#define DRAGON_SLOW    0x20
#define DRAGON_DY      8
#define DRAGON_FIRE_V  0x180
#define DRAGON_HP      192
#define DRAGON_SCORE   1000
#define FRANK_X        239                     // stage 12's boss: Frankenstein, where it stands in the boss screen ($88C5),
#define FRANK_Y        184                     // its centre y
#define FRANK_V        0xC0                    // 0.75 px/frame
#define FRANK_CARRY    0x3C                    // frames it carries Igor before letting it go
#define FRANK_NEAR     0x50                    // nearer to Simon than this, it walks away from him
#define FRANK_HW       8                       // half sizes of its box ($E46A)
#define FRANK_HH       22
#define FRANK_ANIM     25
#define FRANK_SCORE    5000
// stage 15's boss: Death (NES object type 0x18, AI at $8EB8 of bank 5), all measured or read in the NES game's code.
// Out of sight at x 225, y 48 of the boss screen, it wakes 120 frames after the screen stops there, then sinks
// (2.5 px a frame down, slowing by 5/256 a frame) until there is ground 24 px under its centre, where it stops at a
// multiple of 8 and throws its sickles. It rests 144, 95, 185 or 84 frames at random; every 32 frames, if Simon is
// less than 72 px away across, it leaps at him (1.25 px a frame across, 2 up); at the end of its rest it hops a random
// way (0.75 across, 1 or 2 up). In the air it slows by 6/256 a frame, keeps within x 16 to 240 and below y 33, and
// lands on any ground 24 px under its centre. It faces Simon, takes half damage like Medusa (3 a whip hit), 7000 points.
#define DEATH_X        225
#define DEATH_Y        48
#define DEATH_FALL_V   0x280
#define DEATH_FALL_SLOW 5
#define DEATH_GRAVITY  6
#define DEATH_NEAR     0x48
#define DEATH_LEAP_VX  0x140
#define DEATH_LEAP_VY  0x200
#define DEATH_HOP_VX   0xC0
#define DEATH_FEET     24
#define DEATH_HW       12                      // half sizes of its box ($E46A)
#define DEATH_HH       22
#define DEATH_SCORE    7000
// stage 18's boss: Dracula (NES object type 0x1D, AI at $94E6 of bank 5), all measured or read in the NES game's code.
// 120 frames after the screen stops at x 0 of the room his head shows at x 225, y 224 - 26, 60 frames later he
// rises (0.5 px a frame) to y 168, 60 frames, then he shows (69 frames blinking). He opens his cape, throws 3
// fireballs at Simon (2 px a frame along the larger distance; at his centre 16 px lower, level, 16 higher), fades
// and comes back beside Simon ($96C9). Only his head takes hits, half damage, while he stands. His head off, the
// monster comes out of his body: it jumps at random, or when Simon faces it holding the whip button, and spits 3
// fireballs from its head; a quarter of the damage, then 50000 points
#define DRAC_X         225
#define DRAC_Y0        224
#define DRAC_Y         0xA8
#define DRAC_RISE      0x80
#define DRAC_SCORE     50000
#define DRAC_FLAMES    136                     // its flames (type 0x31), then the orb
#define DRAC_GRAVITY   0x30
// its sickles (type 0x0B, $8FD0), 3 at each landing (4 on the second loop), around Simon ($90A1: x + 0xA0, y + 0xB0;
// x + 0x30, y + 0x18; x + 4, y + 0xD0; the 4th x + 0x20, y + 0xE0, all in the screen's 8 bits): they blink 40 frames
// (the last one 256), then fly at Simon, 0.875 px a frame along the larger distance, for 120 frames, stop 32, aim
// again, and so on. One hit, 100 points, even while they blink; they hurt then too
#define SICKLE_APPEAR  40
#define SICKLE_V       0xE0
#define SICKLE_FLY     120
#define SICKLE_STOP    32
#define SICKLE_SCORE   100
#define SICKLE_ANIM    3
enum { SC_APPEAR, SC_AIM, SC_FLY, SC_STOP };
#define IGOR_DY        24                      // Igor sits this high above Frankenstein's centre
#define IGOR_V         0x180                   // 1.5 px/frame across
#define IGOR_STUN      0x54                    // frames it blinks, still, after a hit ($E395)
#define IGOR_LAND_WAIT 8
enum { DR_WAIT, DR_REACH, DR_READY, DR_WEAVE, DR_OPEN, DR_SHUT };
// the raven (NES object type 0x0F, AI at $8787 of bank 5): perched, turned to Simon, until its wait is over; then it
// dives towards him (down or up to his height) at 0.75 px a frame across, 1.25 to 2.5 px a frame vertically at random
// ($87E3), braking by 9/256 a frame; it hovers 24, 63, 37 or 121 frames ($881B); then, if Simon is less than 32 px
// above or below, it charges at him from 0.25 px a frame, faster by 8/256 a frame, for 61 frames at most; 8 px past
// him it turns back from 0.5 px a frame, slowing down by 8/256 a frame for 121 frames (so it ends up flying away
// backwards); else, or at the end of a charge, it dives again. One hit, 200 points (all measured)
#define RAVEN_VX       0xC0
#define RAVEN_BRAKE    9
#define RAVEN_NEAR     0x20
#define RAVEN_CHARGE   0x40
#define RAVEN_ACCEL    8
#define RAVEN_CHARGE_T 0x3D
#define RAVEN_BACK     0x80
#define RAVEN_BACK_T   0x79
#define RAVEN_SCORE    200
#define RAVEN_ANIM     9
enum { RV_PERCH, RV_DIVE, RV_HOVER, RV_CHARGE, RV_BACK };
// the white skeleton (NES object type 0x10, AI at $84FF of bank 5 in block 3): turned to Simon, it walks 1, 2, 3 or 4
// times at random ($8551), each time 16 frames at 1.5 px a frame (4 frames still in between), away from Simon when
// he is less than 72 px away, else towards him; it turns back at a wall 12 px ahead of its centre, and jumps (2.5 px a
// frame up, 1.25 across) when there is no floor under its centre. Then it throws a bone ($874F) 4 frames later and
// waits 8. One hit, 300 points; its bones (type 0x24): 0.75 px a frame across, 4.5 or 3.5 up (every other frame),
// through everything, 100 points (all measured)
#define SKEL_VX        0x180
#define SKEL_STEP      4
#define SKEL_WALK      16
#define SKEL_FAR       0x48
#define SKEL_JUMP_VX   0x140
#define SKEL_JUMP_VY   0x280
#define SKEL_THROWN    8
#define SKEL_SCORE     300
#define SKEL_ANIM      16
#define BONE_VX        0xC0
#define BONE_SCORE     100
#define BONE_ANIM      9
enum { SK_START, SK_STEP, SK_WALK, SK_THROW, SK_THROWN, SK_JUMP };
// stage 9's boss, two mummies (NES object type 0x1A, AI at $8644 of bank 5): they stand until the screen reaches the
// end of the stage ($48), then 120 frames more; they walk at 0.75 px a frame, turned to Simon, for 123, 65, 180 or 32
// frames in turn ($86CE, starting at a place of their own); every 32 frames each turns to Simon, and away from him
// when he faces it from less than 56 px; they keep 8 px inside the screen. Then 40 frames flashing (sprite palette 3
// every other 2 frames), a bandage, 8 frames, and they walk again. Each has 32 units of the ENEMY bar, which shows
// their sum ($E3A8), and takes a quarter of the damage the other bosses take ($E2CC), standing still 8 frames after a
// hit; 3000 points each; the first one leaves a flame, the second one the orb. Bandages (type 0x22, $863E): 1.5 px a
// frame across, 8 px above or below the mummy's centre (every other frame), swinging up and down like a Medusa head
// around that height ($EF13), 100 points (all from the NES game's code)
#define MUMMY_HP       (32 << 8)
#define MUMMY_WAKE     0x78
#define MUMMY_VX       0xC0
#define MUMMY_NEAR     0x38
#define MUMMY_AIM      0x28
#define MUMMY_THROWN   8
#define MUMMY_ANIM     17
#define BANDAGE_V      0x180
#define BANDAGE_SCORE  100
enum { MU_WAIT, MU_STAND, MU_WALK, MU_AIM, MU_THROWN };
// the red skeleton (block 5, NES object type 0x13, AI at $917C of bank 5): it waits 60 frames out of sight, gets up
// (50 frames: lying 26, half up 24), then walks 48 frames at 0.625 px a frame and stands 16, again and again; it
// turns back at a wall 12 px ahead of its centre and falls off a ledge. After 4, 3, 5 or 4 walks at random it turns
// to Simon. A hit (400 points) only takes it apart: 32 frames falling apart, 84 lying, 50 getting up, and it walks
// on; it is out of reach and harmless meanwhile (all measured)
#define RSKEL_VX       0xA0
#define RSKEL_WALK     0x30
#define RSKEL_STAND    0x10
#define RSKEL_HIDDEN   60
#define RSKEL_RISE     50
#define RSKEL_RISE_LOW 26                      // of which lying
#define RSKEL_DROP     32                      // falling apart: 16, 9 and 7 frames of its three poses
#define RSKEL_LIE      84
#define RSKEL_SCORE    400
#define RSKEL_ANIM     17
enum { RS_HIDDEN, RS_RISE, RS_WALK, RS_STAND, RS_DROP, RS_FALL, RS_LIE };
// the axe knight (block 5, NES object type 0x0A, AI at $90AA of bank 5): always turned to Simon, it walks 9, 11, 10
// or 12 times at random, 16 frames at 0.625 px a frame with 4 frames still in between, away from Simon when he is less
// than 80 px away, else towards him, turning back at a wall 12 px ahead of its centre or at the end of its floor
// 4 px ahead; then 16 frames later it throws an axe. Its guard takes the whip's hits from the front (and the
// sub-weapons' from the front, which stun it 8 frames) until 224 units, then breaks; hits from behind, or once the guard
// is broken, are damage: 64 units, 16 frames stunned after each, 500 points ($E208, measured: 10 whip hits, then 3).
// Its axe (type 0x27, $8DC6): from 12 px above its centre or 8 px below (at random), 1.25 px a frame for 88 frames,
// slowing 0.125 px a frame per frame to a stop, then back as fast up to 1.25 px a frame, until it is within 16 px of
// its knight; through everything; 4 turns of 4 frames; one hit, 100 points
// stage 16's giant bat (NES object type 0x1E, AI at $935E of bank 5, put by the generators $5E at $8AED of bank 6):
// it waits 60 frames where it came, then flies for 61, 37, 32 or 69 frames ($93D2, at random) towards 0x30 px right
// of Simon (the screen's 8 bits) and 0x11 above his centre: 0.75 px/frame across and 1.5 times the ratio of the
// distances down or up, or 0.75 down or up and across only the whole pixels of 1.5 times the ratio ($93AF). It then
// hovers 123, 32, 61 or 199 frames ($93EE); on 7 frames in 8, while the whip button is held with Simon within 0x14 px
// of its height and 0x58 across, it rises 8 frames at 2.5 px/frame. Then, with Simon lower by less than 0x38 px and
// nearer than 0x48 across, it swoops at 0x18 px under him for 77, 32, 40 or 63 frames ($946F): 1.75 across and twice
// the ratio down, or 2 down and 3 times the ratio across, slowing by 6/256 a frame down, after which it aims again;
// otherwise it throws a fireball at him ($EC88) and aims again 16 frames later. Its box is 20 x 10 px either side
// ($E46A); the whip's 24 (32) units a hit as the knight, dead at 192 (8 whip hits), standing still 16 frames after
// each one ($568); 3000 points. Wings out and up, 9 frames each (all measured or read in the NES game's code)
#define GBAT_WAIT      60
#define GBAT_HP        192
#define GBAT_HW        20
#define GBAT_HH        10
#define GBAT_SCORE     3000
#define GBAT_ANIM      9
enum { GB_WAIT, GB_FLY, GB_HOVER, GB_DODGE, GB_SWOOP };
#define AXEK_VX        0xA0
#define AXEK_WALK      0x10
#define AXEK_STAND     4
#define AXEK_AIM       0x10
#define AXEK_FAR       0x50
#define AXEK_GUARD     0xE0
#define AXEK_HP        0x40
#define AXEK_STUN      16
#define AXEK_SUB_STUN  8
#define AXEK_SCORE     500
#define AXEK_ANIM      17
#define KAXE_V         0x140
#define KAXE_OUT       88
#define KAXE_BRAKE     0x20
#define KAXE_HOME      16
#define KAXE_SCORE     100
#define KAXE_ANIM      4
enum { AK_START, AK_WALK, AK_STAND, AK_AIM };
enum { KA_OUT, KA_BRAKE, KA_BACK, KA_HOME };

enum { ST_STAND, ST_WALK, ST_JUMP, ST_CROUCH, ST_WHIP, ST_FALL, ST_HURT, ST_DEAD, ST_MOUNT, ST_STAIRS, ST_GATE, ST_DOOR,
       ST_CLIMB, ST_EXIT_CLIMB };
// Parts of the world (columns of level_map) with their own camera limits. The NES game loads each one as a new room;
// on the MD they all live in one long map and the camera never leaves the current part, except through a door.
// Block 2 (stages 4 to 6, tools/block_to_md.py) has its own map and tiles; its columns come after block 1's in the
// same world numbering (from BLOCK2_COL0), so that nothing placed in block 1 is ever found in block 2.
#if BLOCK2_COL0 < LEVEL_COLS
#error "block 2 must start past block 1's columns"
#endif
#if BLOCK3_COL0 < BLOCK2_COL0 + BLOCK2_COLS
#error "block 3 must start past block 2's columns"
#endif
#if BLOCK4_COL0 < BLOCK3_COL0 + BLOCK3_COLS
#error "block 4 must start past block 3's columns"
#endif
#if BLOCK5_COL0 < BLOCK4_COL0 + BLOCK4_COLS
#error "block 5 must start past block 4's columns"
#endif
#if BLOCK6_COL0 < BLOCK5_COL0 + BLOCK5_COLS
#error "block 6 must start past block 5's columns"
#endif
#if BLOCK7_COL0 < BLOCK6_COL0 + BLOCK6_COLS
#error "block 7 must start past block 6's columns"
#endif
#define B2(c)          (BLOCK2_COL0 + (c))
#define B3(c)          (BLOCK3_COL0 + (c))
#define B4(c)          (BLOCK4_COL0 + (c))
#define B5(c)          (BLOCK5_COL0 + (c))
#define B6(c)          (BLOCK6_COL0 + (c))
#define B7(c)          (BLOCK7_COL0 + (c))
enum { SEC_COURT, SEC_HALL, SEC_ST2, SEC_UNDER, SEC_ST3, SEC_ST4, SEC_ST4B, SEC_ST5, SEC_ST5B, SEC_ST6, SEC_ST6B,
       SEC_ST7, SEC_ST7B, SEC_ST8, SEC_ST8B, SEC_ST9, SEC_ST10, SEC_ST11, SEC_ST12,
       SEC_ST13, SEC_ST13B, SEC_ST14, SEC_ST14B, SEC_ST15, SEC_ST15B,
       SEC_ST16, SEC_ST17, SEC_ST17B, SEC_ST18, SEC_ST18B, SECTIONS };
// SEC_ST4B etc.: the floor 1 of the stage (the NES game's $46), above its floor 0
typedef struct { s16 c0, c1, cam0, cam1, start_x, start_y; u8 stage, time; s8 next; s8 door; u8 door_y, door_in; s8 door_dx; } Section;
// time: TIME on a restart, in hundreds (NES table at $C9F6, by $28); next: the part behind the door, at the right end
// (door 1) or the left end (door -1) of this part, where Simon's head is at door_y; the closed door is the part's
// last (first + 1 on the left, first + 2 in stage 14) background column; door_in: columns further in (block 3's doors on the right: the
// exit table $FC12 has them at screen x 0xE8 instead of 0xF0, and Simon goes in once his centre is within 4 px of it,
// $9F7A of bank 6); door_dx: px further (stage 11: $FC12 has its door at 0xF2, Simon goes in at x 238, measured;
// stage 14's door on the left is at 0x1C instead of block 2's 0x17; the MD collision
// stops Simon's anchor at x 24, so its trigger must include that pixel).
// door 2: no door but a point of the last screen (door_in: its screen x, door_y: its centre y; the exit table $FC12,
// tested by $9F7A before Simon moves: he leaves with his centre from 4 px before it to 3 px past it, measured at
// 211 for stage 10's x 208 and 238 for stage 11's 242). Finish the exit flight before the next part starts with
// Simon climbing in from under its floor (ST_CLIMB). door 3: the same point at the left end (door_in: its screen x), after which the
// next part (another block) is loaded at once, Simon at its start
static const Section sections[SECTIONS] = {
    { 0,          GATE_COL0 + GATE_COLS, 0,              GATE_CAM,             42,                 STAND_Y, 1, 3, -1,      0, 0, 0, 0 },
    { GATE_COL0,  ST2_COL0,   GATE_COL0 * 8,  ST2_COL0 * 8 - 256,   HALL_X,             HALL_Y, 1, 3, SEC_ST2, 1, DOOR_Y, 0, 0 },
    { ST2_COL0,   ST3_COL0,   ST2_COL0 * 8,   ST3_COL0 * 8 - 256,   ST2_COL0 * 8 + 40,  80,     2, 2, SEC_ST3, 1, DOOR_Y, 0, 0 },
    { UNDER_COL0, LEVEL_COLS, UNDER_COL0 * 8, LEVEL_COLS * 8 - 256, ST2_COL0 * 8 + 40,  80,     2, 2, -1,      0, 0, 0, 0 },
    { ST3_COL0,   UNDER_COL0, ST3_COL0 * 8,   UNDER_COL0 * 8 - 256, ST3_COL0 * 8 + 40,  80,     3, 1, -1,      0, 0, 0, 0 },
    // block 2: each room is a part (tools/block_to_md.py lays them out so that the doors join neighbours). Stage 4
    // starts on a screen that does not scroll (centre x 320, y 192), stages 5 and 6 at the right end of their floor 0
    // (x 720, y 96 and 128): checked in the NES game
#define ROOM(st, fl)   B2(ROOM_##st##_##fl##_COL0)
    { ROOM(4, 0), ROOM(5, 0), ROOM(4, 0) * 8, ROOM(4, 0) * 8,       ROOM(4, 0) * 8 + 56,  176, 4, 4, -1,       0, 0, 0, 0 },
    { ROOM(4, 1), ROOM(6, 0), ROOM(4, 1) * 8, ROOM(6, 0) * 8 - 256, ROOM(4, 1) * 8 + 40,  176, 4, 4, SEC_ST5,  -1, 80, 0, 0 },
    { ROOM(5, 0), ROOM(4, 1), ROOM(5, 0) * 8, ROOM(4, 1) * 8 - 256, ROOM(5, 0) * 8 + 712, 80,  5, 3, -1,       0, 0, 0, 0 },
    { ROOM(5, 1), ROOM(6, 1), ROOM(5, 1) * 8, ROOM(6, 1) * 8 - 256, ROOM(5, 1) * 8 + 40,  176, 5, 3, SEC_ST6,  -1, 112, 0, 0 },
    { ROOM(6, 0), ROOM(5, 1), ROOM(6, 0) * 8, ROOM(5, 1) * 8 - 256, ROOM(6, 0) * 8 + 712, 112, 6, 2, -1,       0, 0, 0, 0 },
    { ROOM(6, 1), B2(BLOCK2_COLS), ROOM(6, 1) * 8, B2(BLOCK2_COLS) * 8 - 256, ROOM(6, 1) * 8 + 40, 176, 6, 2, -1, 0, 0, 0, 0 },
    // block 3: stage 7 starts at the right end of its floor 0 (centre x 720, y 176), stages 8 and 9 at the left end
    // (x 48, y 144 and 112); the doors of stages 7 and 8 are at the right end of their floor 1 ($FC12: y 0x90 and
    // 0x70). Checked in the NES game
#define ROOM3(st, fl)  B3(ROOM_##st##_##fl##_COL0)
    { ROOM3(7, 0), ROOM3(7, 1), ROOM3(7, 0) * 8, ROOM3(7, 1) * 8 - 256, ROOM3(7, 0) * 8 + 712, 160, 7, 5, -1,      0, 0, 0, 0 },
    { ROOM3(7, 1), ROOM3(8, 0), ROOM3(7, 1) * 8, ROOM3(8, 0) * 8 - 256, ROOM3(7, 1) * 8 + 40,  176, 7, 5, SEC_ST8, 1, 128, 1, 0 },
    { ROOM3(8, 0), ROOM3(8, 1), ROOM3(8, 0) * 8, ROOM3(8, 1) * 8 - 256, ROOM3(8, 0) * 8 + 40,  128, 8, 4, -1,      0, 0, 0, 0 },
    { ROOM3(8, 1), ROOM3(9, 0), ROOM3(8, 1) * 8, ROOM3(9, 0) * 8 - 256, ROOM3(8, 1) * 8 + 40,  176, 8, 4, SEC_ST9, 1, 96, 1, 0 },
    { ROOM3(9, 0), B3(BLOCK3_COLS), ROOM3(9, 0) * 8, B3(BLOCK3_COLS) * 8 - 256, ROOM3(9, 0) * 8 + 40, 96, 9, 3, -1, 0, 0, 0, 0 },
    // block 4: stage 10 starts at the left of its floor 0 (centre x 80, y 144: $CA0C), stages 11 and 12 at the left
    // end (x 48, y 176). TIME 400, 300, 200 ($C9F6)
#define ROOM4(st, fl)  B4(ROOM_##st##_##fl##_COL0)
    { ROOM4(10, 0), ROOM4(11, 0), ROOM4(10, 0) * 8, ROOM4(11, 0) * 8 - 256, ROOM4(10, 0) * 8 + 72, 128, 10, 4, SEC_ST11, 2, 64, 208, 0 },
    { ROOM4(11, 0), ROOM4(12, 0), ROOM4(11, 0) * 8, ROOM4(12, 0) * 8 - 256, ROOM4(11, 0) * 8 + 40, 160, 11, 3, SEC_ST12, 1, 160, 0, 2 },
    { ROOM4(12, 0), B4(BLOCK4_COLS), ROOM4(12, 0) * 8, B4(BLOCK4_COLS) * 8 - 256, ROOM4(12, 0) * 8 + 40, 160, 12, 2, -1, 0, 0, 0, 0 },
    // block 5 ($CA0C: y & F8 | page, x & FE | floor): stage 13 starts at the left of its floor 0 (centre x 48, y 176),
    // stage 14 at x 48 of the last screen of its floor 0 (a screen that does not scroll), stage 15 at x 208 of the
    // last screen of its floor 0, facing left. The doors ($FC12): the right end of stage 13's floor 1 (x 0xE8, as
    // block 3's), the left end of stage 14's floor 1 (x 0x1C). TIME 500, 400, 300 ($C9F6)
#define ROOM5(st, fl)  B5(ROOM_##st##_##fl##_COL0)
    { ROOM5(13, 0), ROOM5(13, 1), ROOM5(13, 0) * 8, ROOM5(13, 1) * 8 - 256, ROOM5(13, 0) * 8 + 40,  160, 13, 5, -1,       0, 0, 0, 0 },
    { ROOM5(13, 1), ROOM5(14, 0), ROOM5(13, 1) * 8, ROOM5(14, 0) * 8 - 256, ROOM5(13, 1) * 8 + 40,  160, 13, 5, SEC_ST14, 1, 160, 1, 0 },
    { ROOM5(14, 0), ROOM5(15, 0), ROOM5(14, 0) * 8, ROOM5(15, 0) * 8 - 256, ROOM5(14, 0) * 8 + 40,  160, 14, 4, -1,       0, 0, 0, 0 },
    { ROOM5(14, 1), ROOM5(15, 1), ROOM5(14, 1) * 8, ROOM5(15, 1) * 8 - 256, ROOM5(14, 1) * 8 + 40,  160, 14, 4, SEC_ST15, -1, 160, 0, 6 },
    // stage 15 starts at x 256 of its room, but the NES camera never goes left of 512 (checked): its first screen is
    // not part of the stage
    { ROOM5(15, 0) + 32, ROOM5(14, 1), ROOM5(15, 0) * 8 + 256, ROOM5(14, 1) * 8 - 256, ROOM5(15, 0) * 8 + 712, 160, 15, 3, -1, 0, 0, 0, 0 },
    { ROOM5(15, 1), B5(BLOCK5_COLS), ROOM5(15, 1) * 8, B5(BLOCK5_COLS) * 8 - 256, ROOM5(15, 1) * 8 + 40, 160, 15, 3, -1, 0, 0, 0, 0 },
    // block 6: stages 16 and 17 start at the right end of their floor 0 (centre x 1504, y 176 and x 720, y 112),
    // facing left ($CA0C); stage 16 ends in the archway at its left end (ST_GATE), stage 17 at x 0x10 of its floor
    // 1 (y 0x70, $FC12: Simon's centre reached 19 when it fired). TIME 700, 600 ($C9F6). Checked in the NES game
#define ROOM6(st, fl)  B6(ROOM_##st##_##fl##_COL0)
    { ROOM6(16, 0), ROOM6(17, 0), ROOM6(16, 0) * 8, ROOM6(17, 0) * 8 - 256, ROOM6(16, 0) * 8 + 1496, 160, 16, 7, -1, 0, 0, 0, 0 },
    { ROOM6(17, 0), ROOM6(17, 1), ROOM6(17, 0) * 8, ROOM6(17, 1) * 8 - 256, ROOM6(17, 0) * 8 + 712,  96,  17, 6, -1, 0, 0, 0, 0 },
    { ROOM6(17, 1), B6(BLOCK6_COLS), ROOM6(17, 1) * 8, B6(BLOCK6_COLS) * 8 - 256, ROOM6(17, 1) * 8 + 40, 96, 17, 6, SEC_ST18, 3, 112, 0x10, 0 },
    // block 7 (stage 18, its own CHR and palette): it starts at the right end of its floor 0 (centre x 720, y 112),
    // facing left. TIME 500
#define ROOM7(st, fl)  B7(ROOM_##st##_##fl##_COL0)
    { ROOM7(18, 0), ROOM7(18, 1), ROOM7(18, 0) * 8, ROOM7(18, 1) * 8 - 256, ROOM7(18, 0) * 8 + 712, 96, 18, 5, -1, 0, 0, 0, 0 },
    { ROOM7(18, 1), B7(BLOCK7_COLS), ROOM7(18, 1) * 8, B7(BLOCK7_COLS) * 8 - 256, ROOM7(18, 1) * 8 + 40, 96, 18, 5, -1, 0, 0, 0, 0 },
};
enum { O_CANDLE, O_SPARK, O_ITEM, O_GONE };
// Breakable blocks: the NES game's table at $FC71 (one per stage; per block: row, floor and hidden item, then column
// and screen), checked by its routine at $A82D of bank 6 on one frame of each whip swing. x, y: top-left of the
// 16x16 block in the world (the hall's world x is the NES game's + 512); code: the item code it hides (5 the pot
// roast, 0x11 a purple bag, 0x0C a double shot, from the table at $AA4F); loop2: it only breaks on the second loop
typedef struct { s16 x, y; u8 sec, code; bool loop2; } Block;
static const Block blocks[] = {
    { 512 + 1008,             144, SEC_HALL,  0x11, FALSE },
    { ST2_COL0 * 8 + 256,     192, SEC_ST2,   0x05, FALSE },
    { ST2_COL0 * 8 + 256,     176, SEC_ST2,   0,    FALSE },
    { UNDER_COL0 * 8 + 464,   128, SEC_UNDER, 0,    FALSE },
    { ST3_COL0 * 8 + 688,     176, SEC_ST3,   0x0C, FALSE },
    { ROOM(4, 0) * 8 + 224,   112, SEC_ST4,   0,    FALSE },   // block 2: stage 4's floor 0 is the NES room's x 256..
    { ROOM(4, 0) * 8 + 224,   128, SEC_ST4,   0,    FALSE },
    { ROOM(4, 1) * 8 + 352,   112, SEC_ST4B,  0x0C, FALSE },
    { ROOM(4, 1) * 8 + 480,   112, SEC_ST4B,  0,    TRUE },
    { ROOM(4, 1) * 8 + 480,   128, SEC_ST4B,  0x05, TRUE },
    { ROOM(5, 1) * 8 + 624,   80,  SEC_ST5B,  0x05, FALSE },
    { ROOM(6, 0) * 8 + 704,   144, SEC_ST6,   0x05, FALSE },
    { ROOM(6, 0) * 8 + 128,   160, SEC_ST6,   0x0C, FALSE },
    { ROOM3(7, 0) * 8 + 288,  160, SEC_ST7,   0x05, FALSE },
    { ROOM3(7, 1) * 8 + 224,  128, SEC_ST7B,  0x0C, TRUE },
    { ROOM3(9, 0) * 8 + 1328, 176, SEC_ST9,   0x05, FALSE },
    { ROOM4(12, 0) * 8 + 304, 160, SEC_ST12,  0x05, FALSE },
    { ROOM4(12, 0) * 8 + 736, 160, SEC_ST12,  0x04, FALSE },
    { ROOM5(13, 1) * 8 + 432, 96,  SEC_ST13B, 0x0C, FALSE },   // block 5: stage 15's floor 0 is the NES room's x 256..
    { ROOM5(13, 1) * 8 + 1088, 160, SEC_ST13B, 0x05, FALSE },
    { ROOM5(14, 1) * 8 + 768, 64,  SEC_ST14B, 0,    FALSE },
    { ROOM5(14, 1) * 8 + 768, 80,  SEC_ST14B, 0x0C, FALSE },
    { ROOM5(15, 0) * 8 + 736, 64,  SEC_ST15,  0,    FALSE },
    { ROOM5(15, 0) * 8 + 736, 80,  SEC_ST15,  0x05, FALSE },
    { ROOM5(15, 0) * 8 + 272, 160, SEC_ST15,  0,    TRUE },
    { ROOM5(15, 0) * 8 + 272, 176, SEC_ST15,  0x0C, TRUE },
    { ROOM6(17, 1) * 8 + 480, 160, SEC_ST17B, 0,    FALSE },   // block 6: none in stages 16 and 18
    { ROOM6(17, 1) * 8 + 480, 176, SEC_ST17B, 0x05, FALSE },
    { ROOM6(17, 0) * 8 + 160, 80,  SEC_ST17,  0x0C, FALSE },
};
#define BLOCKS (sizeof(blocks) / sizeof(blocks[0]))
#define DROPS  4                               // what killed enemies leave: their flame, then maybe an item
#define MAX2(a, b)     ((a) > (b) ? (a) : (b))
#define WCANDLES_MAX MAX2(MAX2(MAX2(MAX2(WCANDLES, BLOCK4_WCANDLES), MAX2(BLOCK2_WCANDLES, BLOCK3_WCANDLES)), BLOCK5_WCANDLES), MAX2(BLOCK6_WCANDLES, BLOCK7_WCANDLES))   // the wall candles of a block
#define DROP0  (CANDLES + WCANDLES_MAX + BLOCKS)
#define NOBJS  (DROP0 + DROPS)
#define DROP_FLAME 20                          // an enemy's flame lasts 20 frames ($E3F4), then its item appears
#define NO_ITEM    0xFF                        // the code of a flame that leaves nothing
#define ROAST_HP       24                      // the pot roast gives back 24 hit points (6 blocks of the bar)
#define DEBRIS_GRAVITY 0x28
static u8 broken_block_ids[BLOCKS], broken_block_count;
static u32 blocks_broken = 0;                  // one bit per block, until the stage starts again
typedef struct { s32 x, y; s16 vx, vy; } Debris;   // pieces of a broken block: 8.8, vy > 0 is down, vx = 0 when gone
static Debris debris[4];
enum { ITEM_LARGE, ITEM_WHIP, ITEM_DAGGER, ITEM_SMALL, ITEM_MONEY_RED, ITEM_MONEY_BLUE, ITEM_MONEY_WHITE,
       ITEM_ROSARY, ITEM_HOLY, ITEM_DOUBLE, ITEM_AXE, ITEM_CROSS, ITEM_POTION, ITEM_WATCH, ITEM_ROAST };
// sub-weapon ids are the item codes of the NES game
enum { SUB_NONE = 0, SUB_DAGGER = 8, SUB_CROSS = 9, SUB_HOLY = 11, SUB_AXE = 13, SUB_WATCH = 15 };
enum { W_FREE, W_FLY, W_BURN };
enum { E_FREE, E_WALK, E_DYING };
enum { P_SIT, P_LEAP, P_RUN, P_DYING, P_GONE };

typedef struct { s16 x, y; u8 state, t, item, code; bool power; } Obj;   // power: this item holds the 'power-up on screen' flag
typedef struct { s16 x, y, vy; s8 dir; u8 state, t, fy, xf; } Enemy;   // vy, fy: falling off a ledge (1/256 px); xf: loop 2
typedef struct { s16 x, y, vy; s8 dir; u8 state, yf, xf; u16 t; } Panther;   // vy, yf: its hop off a ledge (1/256 px, up); xf: loop 2
typedef struct { s32 x, y; s16 vx, vy; s8 dir; u8 state, kind, t, last; bool hit_boss; } Shot;  // x, y: centre in 8.8 fixed point
// last: what a cross or an axe hit last (monster index + 1, 0xFF something else), which it does not hit again ($4DC)

static const u16 map_base = TILE_ATTR_FULL(PAL0, 0, 0, 0, TILE_USER_INDEX);
static const u16 blank_col[30];                // all zeros = empty tile
static bool columns_ready;
static s16 columns_first;
static s16 slot_col[PLANE_COLS];               // world column currently stored in each plane column
static u8 back_state[PLANE_COLS];              // far plane B: 0 empty, 1 canopy, 2 not written yet

static s16 simon_x = 42;                       // world x of the anchor (left leg) sprite
static s16 simon_y = STAND_Y;                  // NES OAM y of the head sprite; feet are at y + 32
static s16 jump_base_y;
static s16 cam_x = 0;
static bool facing_left = FALSE;
static u8 state = ST_STAND;
static u16 anim = 0, state_t = 0;
static s8 jump_vx = 0;
static u8 whip_phase = 0, whip_left = 0, whip_count = 0;   // whip_count: frames since the swing began
static bool whip_hit_done = FALSE;
static bool air_whip = FALSE;                  // whip swung while jumping or falling
static bool drop = FALSE;                      // falling after walking off a ledge (not after a jump or a hit)
static bool lost = FALSE;                      // fell into the water: gone from the screen until the restart
static bool whip_crouch = FALSE;               // the swing started while crouching
#ifndef START_WHIP                              /* make EXTRA_FLAGS=-DSTART_WHIP=2: testing aid, start with the long chain */
#define START_WHIP 0
#endif
static u8 whip_level = START_WHIP;
static u8 stair_id = 0;                        // flight Simon is on or walking towards
static s16 stair_pos = 0;                      // half pixels climbed: x = foot + pos/2, y = foot - pos/2
static s16 mount_x = 0;                        // where Simon walks to before stepping onto the stairs
static s8 mount_k = 0;                          // the NES game's target for it, from mount_x
static bool mount_up = TRUE;
static s8 stair_dir = 0;                       // 1 climbing, -1 descending, 0 still
static u16 stair_anim = 0;
static bool stair_whip = FALSE;                // whip swung on the stairs
#ifndef START_SUB                               /* make EXTRA_FLAGS=-DSTART_SUB=11: testing aid, start with holy water */
#define START_SUB SUB_NONE
#endif
static u8 subweapon = START_SUB;               // item code of the current sub-weapon
static bool power_flag = FALSE;                // a power-up item is lying around (the NES game's $72)
static u8 hit_counter = 0;                     // sub-weapon hits since the last sub-weapon pickup (the NES game's $79)
static u8 shot_level = 0;                      // 0 single, 1 double, 2 triple shot
static u8 other_sub = SUB_NONE;                // SNES port: a second sub-weapon held in reserve, swapped with Z
static u8 other_level = 0;                     // its multiple-shot level
static u16 hearts = 5;
static u32 score = 0;
static u16 player_hp = PLAYER_HP;
static s16 boss_hp = BOSS_HP;                  // shown by the ENEMY bar of the HUD
static bool screen_locked = FALSE;             // the boss is awake: the screen stays at the end of its stage
static s16 boss_cam;                           // the screen where the boss fight happens (world x of its left edge)
static u8 boss_sec;                            // the part of the world where the boss is
static bool statue_gone;                       // Medusa's statue tiles are erased
#define BOSS_CAM       boss_cam
static u8 lives = START_LIVES;
static u8 invuln = 0;                          // frames of invincibility left after a hit
static u16 frame_count = 0;
static Obj objs[NOBJS];                        // braziers first, then the wall candles, then what the blocks hide
static Panther panthers[PANTHERS];
static Enemy enemies[MAX_ENEMIES];
enum { M_FREE, M_BAT, M_FISH, M_FIRE, M_DROP, M_DYING, M_KNIGHT, M_RBAT, M_MEDUSA, M_GHOST, M_PILLAR, M_SNAKE,
       M_FLEA, M_RAVEN, M_SKEL, M_BONE, M_MUMMY, M_BANDAGE, M_EAGLE, M_DRAGON, M_VERT, M_IGOR,
       M_RSKEL, M_AXEK, M_KAXE, M_SICKLE, M_GBAT, M_DBIT };
enum { F_JUMP, F_LAND, F_WALK, F_AIM, F_SHOT };
// bats, fishmen, fireballs, splash drops and the armour knight: x, y = centre in 8.8 fixed point; vy > 0 is up,
// except for the bat whose vy follows the NES game's (down) and which swings around cy. hp: damage taken (knight),
// immune: frames before the next hit counts, gen: the block generator it came from
// (padded to 32 bytes: the index m - monsters is then a shift, not the 68000's slow library division)
typedef struct { s32 x, y; s16 vx, vy, cy; s8 dir; u8 kind, state, t; u16 timer; u8 hp, immune, gen, pad[9]; } Monster;
_Static_assert(sizeof(Monster) == 32, "Monster: 32 bytes");
static Monster monsters[MAX_MONSTERS];
#define OGENS_MAX      MAX2(MAX2(MAX2(BLOCK4_GENS, BLOCK5_GENS), MAX2(BLOCK2_GENS, BLOCK3_GENS)), MAX2(BLOCK6_GENS, BLOCK7_GENS))
static bool og_on[OGENS_MAX];                  // the block's object generators: their place was on the screen
static u8 og_wait[OGENS_MAX];
static u8 og_count[OGENS_MAX];                 // the NES game's $018A: eagles sent so far
static Shot shots[MAX_SHOTS];
static bool throwing = FALSE;                  // the current swing throws the sub-weapon instead of whipping
static u8 rosary_t = 0;
static u8 watch_t = 0;                         // stopwatch frames left
static u16 potion_t = 0;                       // invisibility potion frames left
// a whip upgrade stops the game for 48 frames ($7E = 24 at $E89B, counted down on every 2nd frame by $FAEF), Simon
// flashing in the sprite palettes ($338 = $7E & 3; the MD has two sprite palettes: his own for 0, the other one else)
static u8 whip_freeze = 0;
static const u8 *demo_p;                       // the title's demo playing (see demo_read), NULL: a game
static u16 pal_force = 0;                       // draw_pose: a sprite palette for all the pose's sprites (0: theirs)
static u16 time_left = START_TIME;
static u8 time_tick = 0;
static u8 section = SEC_COURT;                 // part of the world Simon is in (restarts happen at its stage's start)
#define in_hall (section != SEC_COURT)        // past the gate: braziers stay behind, wall candles and zombies are here
static u8 door_phase = 0;                      // door between stages: 0 scroll, 1 open, 2 walk in, 3 close, 4 wait, 5 scroll
static u8 gate_phase = 0;                      // 0 walk in, 1 behind the mask, 2 wait
static u8 gate_frac = 0;
static u8 hall_load = 0;
static u8 konami_idx = 0;
static bool paused = FALSE;                    // START
static bool debug_menu = FALSE;                // unlocked by the Konami code during the pause
static u8 debug_sec = SEC_HALL;                // where the debug menu warps to
#ifdef GOD_MODE                                /* make EXTRA_FLAGS=-DGOD_MODE: start invincible */
static bool god = TRUE;
#else
static bool god = FALSE;                       // debug: nothing hurts Simon
#endif
#ifdef DEBUG_POS                               /* make EXTRA_FLAGS=-DDEBUG_POS: start with Simon's position shown */
static bool show_pos = TRUE;
#else
static bool show_pos = FALSE;                  // debug: Simon's position and state on the top line
#endif
static u8 sprite_n;
static bool game_over = FALSE;
// the SNES port's options (its options screen at power-on): difficulty, starting on the second loop, holding a second
// sub-weapon, which button throws / swaps (R and X there, Z and C here) and the graphics
enum { DIFF_NORMAL, DIFF_HARD, DIFF_EASY };    // its order; easy is the Famicom version's, hard the VS. arcade game's
#ifndef START_DIFF                             /* -DSTART_DIFF=2 (easy) or 1 (hard), -DSTART_LOOP=1: testing aids */
#define START_DIFF DIFF_NORMAL
#endif
#ifndef START_LOOP
#define START_LOOP FALSE
#endif
static u8 difficulty = START_DIFF;
static bool second_loop = START_LOOP;
static u16 held_pad = 0;                       // the pad this frame (the NES game's $F7)
#define LOOP_VX (second_loop ? 0x20 : 0)        // the NES game's $7C, added by $EE48 to the enemies' speed across
// whole pixels the loop-2 speed adds this frame, from a 1/256 px remainder
// dir * v without the 68000's missing 32-bit multiply (gcc calls a slow library routine for it): dir is almost
// always -1, 0 or 1
static inline s16 dirmul(s8 dir, s16 v) { return dir == 1 ? v : dir == -1 ? -v : dir == 0 ? 0 : dir * v; }
static s16 loop_step(u8 *xf, s8 dir) { u16 f = *xf + LOOP_VX; *xf = f & 0xFF; return dirmul(dir, f >> 8); }
static bool weapon_swap = TRUE;
static bool z_throws = FALSE;
#ifndef START_NES_ART                          /* -DSTART_NES_ART=1: the original NES graphics (testing aid) */
#define START_NES_ART FALSE
#endif
static bool nes_art = START_NES_ART;            // GRAPHICS ORIGINAL: the NES game's tiles instead of the 16-bit ones
#define ART(data) (nes_art ? data##_nes : data)  // the tiles or palettes of the chosen graphics (same indices in both)
#ifndef START_NES_PALETTE                      /* -DSTART_NES_PALETTE=n: one of the 14 NES palettes (testing aid) */
#define START_NES_PALETTE 0
#endif
static u8 nes_palette = START_NES_PALETTE;      // PALETTE: which of the SNES port's 14 NES palettes colours the NES art
static u16 art_colors[64];
// the palette of the chosen graphics: the 16-bit one, or the NES one in the chosen NES palette (from each colour's
// NES index, as the SNES port's palette_lookup.asm does)
static const u16 *art_palette(const u16 *pal16, const u16 *pal_nes, const u8 *nesidx)
{
    if (!nes_art) return pal16;
    for (u8 i = 0; i < 64; i++) art_colors[i] = nesidx[i] < 64 ? nes_palettes[nes_palette][nesidx[i]] : pal_nes[i];
    return art_colors;
}
#define ART_PAL(name) art_palette(name##_palette, name##_palette_nes, name##_palette_nesidx)
#define BUTTON_THROW (z_throws ? BUTTON_Z : BUTTON_C)
#define BUTTON_SWAP  (z_throws ? BUTTON_C : BUTTON_Z)                 // Simon died with no life left: the main loop shows the game over screen

// ---------------------------------------------------------------- level streaming

// the block whose map, tiles and palettes are in use: its first world column and its data
static u8 loaded_block = 0xFF;
static s16 world_c0 = 0, world_cols = LEVEL_COLS;
static const u16 *world_map = level_map;
static const u32 *world_solid = level_solid, *world_wall = level_wall, *world_tiles = level_tiles;
static const u16 *world_palette = level_palette;
static const Stair *world_stairs = level_stairs;
static u8 world_nstairs = STAIRS;
static const WallCandle *world_wcandles = level_wcandles;
static u8 world_nwcandles = WCANDLES;
static const ObjGen *world_gens = NULL;                 // blocks 2 on: the object generators and the block's sprites
static u8 world_ngens = 0;
static const SimonPose *world_poses = block2_poses;
#define RISING_TILE    MAX2(MAX2(MAX2(MAX2(LEVEL_TILES, BLOCK4_TILES), MAX2(BLOCK2_TILES, BLOCK3_TILES)), BLOCK5_TILES), MAX2(BLOCK6_TILES, BLOCK7_TILES))   // after every block's tiles
#define DEBUG_FONT     (RISING_TILE + 4)        // the debug menu's font (96 tiles), see debug_font_load
#define MIKU_TILE      (CLIMB_TILE + 8)
#define CLIMB_TILE     (DEBUG_FONT + 96)        // Simon cut at the floor while he climbs into a stage (8 tiles)

// make the block of the current part of the world the loaded one; TRUE if its tiles had to be loaded (the caller
// turns the display off meanwhile)
static bool use_block(void)
{
    s16 c0 = sections[section].c0;
    u8 b = c0 >= BLOCK7_COL0 ? 7 : c0 >= BLOCK6_COL0 ? 6 : c0 >= BLOCK5_COL0 ? 5 : c0 >= BLOCK4_COL0 ? 4 : c0 >= BLOCK3_COL0 ? 3 : c0 >= BLOCK2_COL0 ? 2 : 1;
    if (b == loaded_block) return FALSE;
    loaded_block = b;
    if (b == 1)
    {
        world_c0 = 0; world_cols = LEVEL_COLS; world_map = level_map; world_solid = level_solid; world_wall = level_wall;
        world_tiles = ART(level_tiles); world_palette = ART_PAL(level); world_stairs = level_stairs; world_nstairs = STAIRS;
        world_wcandles = level_wcandles; world_nwcandles = WCANDLES;
    }
    else if (b == 2)
    {
        world_c0 = BLOCK2_COL0; world_cols = BLOCK2_COLS; world_map = ART(block2_map); world_solid = block2_solid;
        world_wall = block2_wall; world_tiles = ART(block2_tiles); world_palette = ART_PAL(block2);
        world_stairs = block2_stairs; world_nstairs = BLOCK2_STAIRS;
        world_wcandles = block2_wcandles; world_nwcandles = BLOCK2_WCANDLES;
        world_gens = block2_gens; world_ngens = BLOCK2_GENS; world_poses = block2_poses;
    }
    else if (b == 3)
    {
        world_c0 = BLOCK3_COL0; world_cols = BLOCK3_COLS; world_map = ART(block3_map); world_solid = block3_solid;
        world_wall = block3_wall; world_tiles = ART(block3_tiles); world_palette = ART_PAL(block3);
        world_stairs = block3_stairs; world_nstairs = BLOCK3_STAIRS;
        world_wcandles = block3_wcandles; world_nwcandles = BLOCK3_WCANDLES;
        world_gens = block3_gens; world_ngens = BLOCK3_GENS; world_poses = block3_poses;
    }
    else if (b == 4)
    {
        world_c0 = BLOCK4_COL0; world_cols = BLOCK4_COLS; world_map = ART(block4_map); world_solid = block4_solid;
        world_wall = block4_wall; world_tiles = ART(block4_tiles); world_palette = ART_PAL(block4);
        world_stairs = block4_stairs; world_nstairs = BLOCK4_STAIRS;
        world_wcandles = block4_wcandles; world_nwcandles = BLOCK4_WCANDLES;
        world_gens = block4_gens; world_ngens = BLOCK4_GENS; world_poses = block4_poses;
    }
    else if (b == 5)
    {
        world_c0 = BLOCK5_COL0; world_cols = BLOCK5_COLS; world_map = ART(block5_map); world_solid = block5_solid;
        world_wall = block5_wall; world_tiles = ART(block5_tiles); world_palette = ART_PAL(block5);
        world_stairs = block5_stairs; world_nstairs = BLOCK5_STAIRS;
        world_wcandles = block5_wcandles; world_nwcandles = BLOCK5_WCANDLES;
        world_gens = block5_gens; world_ngens = BLOCK5_GENS; world_poses = block5_poses;
    }
    else if (b == 6)
    {
        world_c0 = BLOCK6_COL0; world_cols = BLOCK6_COLS; world_map = ART(block6_map); world_solid = block6_solid;
        world_wall = block6_wall; world_tiles = ART(block6_tiles); world_palette = ART_PAL(block6);
        world_stairs = block6_stairs; world_nstairs = BLOCK6_STAIRS;
        world_wcandles = block6_wcandles; world_nwcandles = BLOCK6_WCANDLES;
        world_gens = block6_gens; world_ngens = BLOCK6_GENS; world_poses = block6_poses;
    }
    else
    {
        world_c0 = BLOCK7_COL0; world_cols = BLOCK7_COLS; world_map = ART(block7_map); world_solid = block7_solid;
        world_wall = block7_wall; world_tiles = ART(block7_tiles); world_palette = ART_PAL(block7);
        world_stairs = block7_stairs; world_nstairs = BLOCK7_STAIRS;
        world_wcandles = block7_wcandles; world_nwcandles = BLOCK7_WCANDLES;
        world_gens = block7_gens; world_ngens = BLOCK7_GENS; world_poses = block7_poses;
    }
    VDP_loadTileData(world_tiles, TILE_USER_INDEX,
                     b == 1 ? LEVEL_TILES : b == 2 ? BLOCK2_TILES : b == 3 ? BLOCK3_TILES : b == 4 ? BLOCK4_TILES : b == 5 ? BLOCK5_TILES
                     : b == 6 ? BLOCK6_TILES : BLOCK7_TILES, DMA);
    PAL_setColors(0, world_palette, 64, DMA);
    if (MIKU_enabled()) MIKU_set_palette(world_palette);
    return TRUE;
}

// A cached complete viewport is valid until the map or room is reloaded.
static void invalidate_columns(bool back)
{
    columns_ready = FALSE;
    for (u16 i = 0; i < PLANE_COLS; i++)
    {
        slot_col[i] = -9999;
        if (back) back_state[i] = 2;
    }
}

static void load_column(s16 col)
{
    u16 slot = col & (PLANE_COLS - 1);
    slot_col[slot] = col;
    // the screen is 64 px wider than the NES one: columns of the other parts stay blank (both sides of a door
    // show while Simon goes through it)
    const Section *sec = &sections[section];
    s16 c0 = state == ST_DOOR && sec->door < 0 ? sections[(u8)sec->next].c0 : sec->c0;
    s16 c1 = state == ST_DOOR && sec->door > 0 ? sections[(u8)sec->next].c1 : sec->c1;
    if (col < c0 || col >= c1)
        VDP_setTileMapDataColumnEx(BG_A, blank_col, map_base, slot, 0, 30, 1, CPU);
    else if (!in_hall && col >= GATE_COL0 && col < GATE_COL0 + GATE_COLS)
        VDP_setTileMapDataColumnEx(BG_A, gate_map + col - GATE_COL0, map_base, slot, 0, 30, GATE_COLS, CPU);
    else
        VDP_setTileMapDataColumnEx(BG_A, world_map + col - world_c0, map_base, slot, 0, 30, world_cols, CPU);
    if (statue_gone && col >= (BOSS_CAM >> 3) + STATUE_COL && col < (BOSS_CAM >> 3) + STATUE_COL + 4)
        for (u8 r = 0; r < 4; r++) VDP_setTileMapXY(BG_A, map_base, slot, STATUE_ROW + r);
    for (u8 i = 0; i < broken_block_count; i++)                  // only broken blocks need restoring
    {
        const Block *b = &blocks[broken_block_ids[i]];
        if (col == b->x >> 3 || col == (b->x >> 3) + 1)
        {
            VDP_setTileMapXY(BG_A, map_base, slot, b->y >> 3);
            VDP_setTileMapXY(BG_A, map_base, slot, (b->y >> 3) + 1);
        }
    }
}

// keep every column that can be on screen loaded (a few per frame at most)
static void stream_columns(u16 budget)
{
    s16 first = (cam_x - NES_X) >> 3;
    if (columns_ready && columns_first == first) return;
    s16 c = first - 1;
    for (; c <= first + 41 && budget; c++)
    {
        if (slot_col[c & (PLANE_COLS - 1)] != c) { load_column(c); budget--; }
    }
    columns_first = first;
    columns_ready = c > first + 41; // never cache a partial load
}

// The far plane B holds the courtyard's tree canopy as a 32-column strip that wraps. It scrolls at half the
// speed of the foreground (parallax) and is only shown between the left edge of the stage and the castle gate,
// because the hall's tiles have see-through pixels that would otherwise show the trees.
static void stream_back(u16 budget)
{
    s16 bx = cam_x >> 1;                       // plane B scroll
    s16 x0 = NES_X - cam_x;                    // screen x of world column 0
    s16 xh = x0 + (GATE_COL0 + GATE_BACK_COLS) * 8;   // screen x of the gate tower
    s16 first = bx >> 3;
    for (s16 i = -1; i <= 41 && budget; i++)
    {
        s16 c = first + i;
        s16 sx = c * 8 - bx;                   // where plane column c is drawn
        u8 want = (!in_hall && sx + 4 > x0 && sx + 4 < xh) ? 1 : 0;
        u16 slot = c & (PLANE_COLS - 1);
        if (back_state[slot] == want) continue;
        back_state[slot] = want;
        budget--;
        if (want) VDP_setTileMapDataColumnEx(BG_B, level_back + (c & 31), map_base, slot, BACK_ROW0, BACK_ROWS, 32, CPU);
        else      VDP_setTileMapDataColumnEx(BG_B, blank_col, map_base, slot, BACK_ROW0, BACK_ROWS, 1, CPU);
    }
}

// ---------------------------------------------------------------- collisions

// outside the current part of the world a column reads as the part's edge column: the courtyard (ending on the gate
// screen) and the hall overlap, and the parts lie side by side, so a zombie coming from off screen finds the floor of
// its own part
static s16 section_col(s16 c)
{
    const Section *sec = &sections[section];
    return c < sec->c0 ? sec->c0 : c >= sec->c1 ? sec->c1 - 1 : c;
}

static void mark_block_broken(u8 k)
{
    u32 bit = 1UL << k;
    if (!(blocks_broken & bit)) broken_block_ids[broken_block_count++] = k;
    blocks_broken |= bit;
}

static bool block_gone(s16 px, s16 py)
{
    // Called for every collision test. High-index blocks must not require
    // shifting through all preceding bits on the 68000.
    for (u8 i = 0; i < broken_block_count; i++)
    {
        const Block *b = &blocks[broken_block_ids[i]];
        if (px >= b->x && px < b->x + 16 && py >= b->y && py < b->y + 16) return TRUE;
    }
    return FALSE;
}

static bool solid_at(s16 px, s16 py)
{
    if (py >= 28 * 8) return FALSE;                             // below the map: a pit or the water
    if (py < 0 || block_gone(px, py)) return FALSE;
    s16 c = section_col(px >> 3);
    if (!in_hall && c >= GATE_COL0) return (gate_solid[c - GATE_COL0] >> (py >> 3)) & 1;
    return (world_solid[c - world_c0] >> (py >> 3)) & 1;
}

static bool wall_at(s16 px, s16 py)
{
    if (py < 0 || py >= 28 * 8 || block_gone(px, py)) return FALSE;
    s16 c = section_col(px >> 3);
    if (!in_hall && c >= GATE_COL0) return (gate_wall[c - GATE_COL0] >> (py >> 3)) & 1;
    return (world_wall[c - world_c0] >> (py >> 3)) & 1;
}

// Test the leading edge of the next one-pixel step, including the lower legs.
// During descent a low corner may be crossed from above: allow that step so
// the landing sweep can put Simon on its top. Approaches below it are blocked.
static bool wall_ahead_from(s8 dir, s16 from_y)
{
    // RAFT_CROUCH_COLLISION_V1
    // The crouched pose starts 8 px below the standing head. Keep the
    // existing 4 px inset, but omit the standing-only overhead probe.
    // This also applies while whipping on the ground from a crouch.
    bool crouched = state == ST_CROUCH
        || (state == ST_WHIP && whip_crouch && !air_whip);
    s16 x = dir > 0 ? simon_x + 16 : simon_x - 1;
    if ((!crouched && wall_at(x, simon_y + 4))
        || wall_at(x, simon_y + 12) || wall_at(x, simon_y + 20)) return TRUE;
    s16 shin = simon_y + 28;
    s16 bottom = simon_y + FEET - 1;
    return (wall_at(x, shin) && from_y + FEET > (shin & ~7))
        || (wall_at(x, bottom) && from_y + FEET > (bottom & ~7));
}

static bool wall_ahead(s8 dir)
{
    return wall_ahead_from(dir, simon_y);
}

// ---------------------------------------------------------------- moving platforms
// The NES game's object slots 0x17.. (table $D0D0, loaded with each room by $D052, moved by bank 6's $AAE2): a 32 px
// platform swinging around a centre. Offset v and speed u are 8.8 bytes stepped like a spring, v += u << n then
// u -= v << n, with the game's own byte arithmetic (exact for these small values, checked frame by frame in stage 4)
typedef struct { u8 sec, uf, u, vf, v; s16 cx; u8 y, shift; } PlatDef;   // cx: room x of the centre; y: top
typedef struct { u8 uf, u, vf, v; s16 x; } Plat;                         // x: world x of the centre
static const PlatDef plat_defs[] = {
    { SEC_ST4B, 0x80, 0, 0, 0x10, 0x040, 0x70, 2 },             // the way to the door at the end of stage 4
    { SEC_ST5B, 0x80, 0, 0, 0x18, 0x1B0, 0x70, 2 },
    { SEC_ST5B, 0x8A, 0, 0, 0x20, 0x130, 0x70, 1 },
    { SEC_ST10, 0x80, 0, 0, 0x30, 0x130, 0xB0, 1 },             // stage 10's ($D0EE)
    { SEC_ST10, 0x80, 0, 0, 0x30, 0x420, 0xB8, 1 },
    { SEC_ST10, 0x80, 0, 0, 0x40, 0x370, 0xB8, 1 },
    { SEC_ST10, 0x80, 0, 0, 0xD0, 0x4B0, 0xA0, 1 },
};
#define PLATS 4
static Plat plats[PLATS];
static const PlatDef *plat_def;                                 // first definition of the current section
static u8 plat_n, plat_sec = 0xFF;

// a += b << (shift + 1), as the game does it: the sign bit takes shift + 1 off, each later bit shifted out adds 1
static void plat_add(u8 *a, u8 *af, u8 b, u8 shift)
{
    if (b & 0x80) *a -= shift + 1;
    b <<= 1;
    for (u8 i = 0; i < shift; i++) { if (b & 0x80) (*a)++; b <<= 1; }
    u16 t = *af + b;
    *af = t; *a += t >> 8;
}

// is the platform under feet at y? Its test ($AC70): Simon's centre within 17 px to the left, 16 to the right of its
// centre, his feet from 1 px above its top to 8 below (here, exactly on it: the fall lands on the first pixel)
static s8 plat_under(s16 x, s16 feet)
{
    for (u8 i = 0; i < plat_n; i++)
    {
        s16 d = x + 8 - plats[i].x;
        if (feet == plat_def[i].y && d >= -17 && d <= 16) return i;
    }
    return -1;
}

static void plats_update(bool riding)
{
    if (plat_sec != section)                                    // a new room: its platforms start again
    {
        plat_sec = section; plat_n = 0;
        for (u8 i = 0; i < sizeof(plat_defs) / sizeof(plat_defs[0]); i++)
            if (plat_defs[i].sec == section)
            {
                const PlatDef *d = &plat_defs[i];
                if (!plat_n) plat_def = d;
                Plat *p = &plats[plat_n++];
                p->uf = d->uf; p->u = d->u; p->vf = d->vf; p->v = d->v;
                p->x = sections[section].c0 * 8 + d->cx + (s8)d->v;
            }
    }
    s8 ride = riding ? plat_under(simon_x, simon_y + FEET) : -1;
    for (u8 i = 0; i < plat_n; i++)
    {
        Plat *p = &plats[i];
        const PlatDef *d = &plat_def[i];
        plat_add(&p->v, &p->vf, p->u, d->shift);
        plat_add(&p->u, &p->uf, -p->v, d->shift);
        s16 x = sections[section].c0 * 8 + d->cx + (s8)p->v;
        if (i == ride)
        {
            // Carry him only as far as the room allows. The platform itself
            // keeps moving, so it may slide out from under him at a wall.
            s16 dx = x - p->x;
            s8 dir = dx > 0 ? 1 : -1;
            while (dx && !wall_ahead(dir)) { simon_x += dir; dx -= dir; }
        }
        p->x = x;
    }
}

static void draw_object(const SimonPose *pose, s16 wx, s16 y, bool mirror);

static void plats_draw(void)
{
    for (u8 i = 0; i < plat_n; i++) draw_object(&world_poses[B2_PLATFORM], plats[i].x - 16, plat_def[i].y, FALSE);
}

// is there a standable surface exactly under a box whose top is y and whose height is h? Brick blocks count too:
// the floor under stage 2's breakable blocks is made of them
static bool standable_at(s16 x, s16 y, s16 h)
{
    s16 feet = y + h;
    return (feet & 7) == 0 && (solid_at(x + 4, feet) || solid_at(x + 11, feet) || wall_at(x + 4, feet) || wall_at(x + 11, feet));
}

// Simon's feet: 4 px each side of his centre (the NES game steps off a ledge once both are past it: demo of stage 7)
static bool standable(s16 y)
{
    s16 feet = y + FEET;
    if ((feet & 7) == 0)
        for (s8 dx = 4; dx <= 12; dx += 8)
            if (solid_at(simon_x + dx, feet) || wall_at(simon_x + dx, feet)) return TRUE;
    return plat_under(simon_x, feet) >= 0;
}

// may Simon jump? The NES game ($9998) does not start a jump under a ceiling: 19 px above his centre, at his centre
// and 7 px to each side, there must be no solid tile (checked in stage 2 under its broken blocks)
static bool headroom(void)
{
    s16 cx = simon_x + 8, y = simon_y + 16 - 19;
    for (s8 dx = -7; dx <= 7; dx += 7)
        if (solid_at(cx + dx, y) || wall_at(cx + dx, y)) return FALSE;
    return TRUE;
}

// move from simon_y to new_y one pixel at a time while descending; returns TRUE if we landed
static bool move_down_to(s16 new_y)
{
    // Horizontal movement happens after descent. It may have brought the feet
    // onto a surface at the current height since the previous vertical test.
    // Check that height before advancing, or the next test is 8 px too low.
    if (new_y >= simon_y && standable(simon_y)) return TRUE;
    while (simon_y < new_y)
    {
        simon_y++;
        if (standable(simon_y)) return TRUE;
    }
    return FALSE;
}

static bool overlap(s16 ax, s16 ay, s16 aw, s16 ah, s16 bx, s16 by, s16 bw, s16 bh)
{
    return ax < bx + bw && bx < ax + aw && ay < by + bh && by < ay + ah;
}

// ---------------------------------------------------------------- HUD

static void hud_number(u16 col, u16 row, u32 value, u8 digits, const u16 *table)
{
    for (s8 i = digits - 1; i >= 0; i--)
    {
        VDP_setTileMapXY(WINDOW, map_base + table[value % 10], NES_X / 8 + col + i, row);
        value /= 10;
    }
}

// the bars show their own value, which the NES game moves 1 hit point towards the real one every other frame ($A0E0
// for Simon, $A206 for the boss); 8 tiles of 8 hit points, the last one full from 5 left, half from 1 ($A23B)
static u8 shown_hp = PLAYER_HP, shown_boss = BOSS_HP >> 8;

static void hud_bars(void)
{
    for (u8 i = 0; i < 8; i++)
    {
        u8 r = shown_hp > i * 8 ? shown_hp - i * 8 : 0, rb = shown_boss > i * 8 ? shown_boss - i * 8 : 0;
        VDP_setTileMapXY(WINDOW, map_base + hud_bar[r >= 5 ? 0 : r ? 2 : 1], NES_X / 8 + 7 + i, 2);
        VDP_setTileMapXY(WINDOW, map_base + hud_ebar[rb >= 5 ? 0 : rb ? 2 : 1], NES_X / 8 + 7 + i, 3);
    }
}

static void hud_bars_update(void)
{
    if (frame_count & 1) return;
    u8 hp = player_hp, boss = boss_hp > 0 ? boss_hp >> 8 : 0;
    if (shown_hp == hp && shown_boss == boss) return;
    if (shown_hp != hp) shown_hp += shown_hp < hp ? 1 : -1;
    if (shown_boss != boss) shown_boss += shown_boss < boss ? 1 : -1;
    hud_bars();
}

static void hud_update(void)
{
    hud_number(23, 2, hearts, 2, hud_digit);
    hud_number(6, 1, score, 6, hud_digit);
    hud_number(23, 3, lives, 2, hud_digit_lives);
    hud_number(18, 1, time_left, 4, hud_digit);
    hud_number(29, 1, sections[section].stage, 2, hud_digit);
    hud_bars();
}

// ---------------------------------------------------------------- sprites

// draw a pose with its anchor at screen x sx and OAM y sy (head of the standing Simon = STAND_Y)
// (straight into SGDK's sprite table, as VDP_setSpriteFull would: called for every sprite, the call cost showed)
static void draw_pose(const SimonPose *pose, s16 sx, s16 sy, bool mirror)
{
    u8 n = pose->count;
    if (n > MAX_SPRITES - sprite_n) n = MAX_SPRITES - sprite_n;
    const SimonSprite *s = pose->sprites;
    VDPSprite *v = &vdpSpriteCache[sprite_n];
    u16 keep = pal_force ? ~0x6000 : 0xFFFF, flip = mirror ? 0x800 : 0;   // mirror around the 16 px wide body
    sx += 0x80; sy += 0x80 + 1 - 8;
    for (; n; n--, s++, v++)
    {
        sprite_n++;
        v->y = sy + s->dy;
        v->size_link = (SPRITE_SIZE(1, 2) << 8) | sprite_n;
        v->attribut = (((s->attr & keep) | pal_force) ^ flip) + TILE_USER_INDEX + s->tile;
        v->x = sx + (mirror ? 8 - s->dx : s->dx);
    }
}

static void draw_object(const SimonPose *pose, s16 wx, s16 y, bool mirror)
{
    s16 sx = NES_X + wx - cam_x;
    if (sx > -16 && sx < 320) draw_pose(pose, sx, y, mirror);
}

// Simon climbing into a stage: the NES game hides what is below line 192 with sprites behind the background ($FE
// tiles at OAM y 192, 208, 224 around him); here his rows below it are cut from copies of his tiles
#define CLIMB_LINE 192
static u8 miku_pose_index(void)
{
    if (whip_freeze) return 0;
    if (state == ST_GATE && gate_phase >= 2) return 16;
    if (air_whip || stair_whip || state == ST_WHIP)
    {
        if (throwing) return 11;
        bool stairs = state == ST_STAIRS;
        bool low = whip_crouch && !air_whip && !stairs;
        if (stairs) return whip_phase >= 2 ? 15 : 14;
        if (low) return whip_phase >= 2 ? 13 : 12;
        return whip_phase == 0 ? 8 : whip_phase == 1 ? 9 : 10;
    }
    if (state == ST_HURT || state == ST_DEAD) return 7;
    if (state == ST_CROUCH || (state == ST_JUMP && simon_jump_curled[state_t < JUMP_FRAMES ? state_t : JUMP_FRAMES - 1])) return 3;
    if (state == ST_STAIRS || state == ST_CLIMB || state == ST_EXIT_CLIMB)
        return state == ST_STAIRS && stair_dir < 0 ? 6 : ((state == ST_STAIRS ? stair_anim : state_t) >> 3) & 1 ? 4 : 5;
    if (state == ST_WALK || state == ST_MOUNT || (state == ST_GATE && gate_phase < 2) || (state == ST_DOOR && door_phase == 2))
        return ((anim / 7) & 3) == 1 ? 1 : ((anim / 7) & 3) == 3 ? 2 : 0;
    return 0;
}
static void draw_miku_frame(u8 pose, const SimonPose *original, s16 sx, s16 sy, bool mirror, bool climbing)
{
    u8 rows = 32;
    if (climbing)
    {
        s16 visible = CLIMB_LINE + 1 - (sy + 1);
        rows = visible < 0 ? 0 : visible > 32 ? 32 : visible;
    }
    if (MIKU_render(pose, rows)) VDP_loadTileData(MIKU_tile_data(), TILE_USER_INDEX + MIKU_TILE, 16, DMA_QUEUE);
    for (u8 k = 0; k < 8 && sprite_n < MAX_SPRITES; k++)
    {
        VDPSprite *v = &vdpSpriteCache[sprite_n++];
        s16 dx = (k / 2) * 8 - 8;
        v->y = sy + 0x80 + 1 - 8 + (k & 1) * 16;
        v->x = sx + 0x80 + (mirror ? 8 - dx : dx);
        v->size_link = (SPRITE_SIZE(1, 2) << 8) | sprite_n;
        v->attribut = (MIKU_sprite_palette(k) << 13) | (mirror ? 0x800 : 0);
        v->attribut += TILE_USER_INDEX + MIKU_TILE + k*2;
    }
    if (!climbing && original)
        for (u8 k = 0; k < original->count; k++)
            if ((original->sprites[k].attr & 0x6000) != 0x4000)
            {
                SimonPose weapon = { 1, &original->sprites[k] };
                draw_pose(&weapon, sx, sy, mirror);
            }
}


static void draw_miku(const SimonPose *original, s16 sx, s16 sy, bool mirror, bool climbing)
{
    MIKU_set_flash((whip_freeze & 3) != 0);
    draw_miku_frame(miku_pose_index(), original, sx, sy, mirror, climbing);
}

static u32 climb_tiles[64];
static const SimonPose *simon_pose(void);
static void draw_climbing(void)
{
    const SimonPose *pose = simon_pose();
    u8 n = pose->count > 4 ? 4 : pose->count;
    for (u8 k = 0; k < n; k++)
    {
        const u32 *src = &world_tiles[pose->sprites[k].tile * 8];
        s16 rows = CLIMB_LINE + 1 - (simon_y + 1 + pose->sprites[k].dy);      // its rows on lines up to 192
        for (u8 r = 0; r < 16; r++) climb_tiles[k * 16 + r] = r < rows ? src[r] : 0;
    }
    VDP_loadTileData(climb_tiles, TILE_USER_INDEX + CLIMB_TILE, n * 2, DMA_QUEUE);
    s16 sx = NES_X + simon_x - cam_x + 0x80, sy = simon_y + 0x80 + 1 - 8;
    for (u8 k = 0; k < n && sprite_n < MAX_SPRITES; k++)
    {
        const SimonSprite *s_ = &pose->sprites[k];
        VDPSprite *v = &vdpSpriteCache[sprite_n++];
        v->y = sy + s_->dy;
        v->size_link = (SPRITE_SIZE(1, 2) << 8) | sprite_n;
        v->attribut = (s_->attr & 0xF800) + TILE_USER_INDEX + CLIMB_TILE + k * 2;
        v->x = sx + s_->dx;
    }
}

// ---------------------------------------------------------------- whip

// The NES hit effect ($DF79, fixed slot 3, type $30): tile $70 in sprite
// palette 3, held for 16 frames. The existing sparkle pose contains that art.
// Keep it independent of enemy slots, including a boss's final damaging hit.
static struct { s16 x, y; u8 frames, section; } hit_effect;

static void impact_spawn(s16 cx, s16 cy, s16 hw, s16 hh, s16 hit_x, s16 hit_y)
{
    s16 x = hit_x - (cx - hw), y = hit_y - (cy - hh);
    if (x < 0) x = 0; else if (x >= hw * 2) x = hw * 2 - 1;
    if (y < 0) y = 0; else if (y >= hh * 2) y = hh * 2 - 1;
    hit_effect.x = cx - hw + (x & ~7);
    hit_effect.y = cy - hh + (y & ~7);
    hit_effect.frames = 16; hit_effect.section = section;
}

static void whip_impact(s16 cx, s16 cy, s16 hw, s16 hh)
{
    static const u8 reach[3] = { 24, 26, 34 };
    impact_spawn(cx, cy, hw, hh,
                 simon_x + 8 + (facing_left ? -reach[whip_level] : reach[whip_level]),
                 simon_y + 16 + ((whip_crouch && !air_whip) ? 7 : -2));
}

static void impact_draw(void)
{
    if (hit_effect.frames && hit_effect.section == section)
        draw_object(&obj_poses[OBJ_SPARKLE], hit_effect.x, hit_effect.y - 8, FALSE);
}

static const SimonPhase *whip_table(void)
{
    if (throwing) return state == ST_STAIRS ? simon_sthrow : simon_throw;
    u8 c = frame_count & 3;   // level 3: the NES cycles the whip's sprite palette every frame
    if (state == ST_STAIRS) return whip_level > 1 ? simon_swhip3[c] : whip_level ? simon_swhip2 : simon_swhip;
    if (whip_crouch) return whip_level > 1 ? simon_cwhip3[c] : whip_level ? simon_cwhip2 : simon_cwhip;
    return whip_level > 1 ? simon_whip3[c] : whip_level ? simon_whip2 : simon_whip;
}

static bool whip_active(void)                  // the whip is fully extended and can hit things
{
    return (state == ST_WHIP || air_whip || stair_whip) && whip_phase == 2 && !throwing;
}

// does the whip strike the box of centre (cx, cy) and half sizes (hw, hh)? The NES game tests it on one frame of the
// swing only, the 18th (Simon's $568 = 17, $E406), with a box centred 24 px ahead of his centre (26 and 34 px for the
// chains, $E45D), 16 px across on each side and 6 px up and down (18x8, 26x8, $E464), 2 px above his centre or
// 7 px below it crouched ($E460, his y being 4 px lower then). All measured.
#define WHIP_HIT_FRAME 17
static bool whip_strikes(s16 cx, s16 cy, s16 hw, s16 hh)
{
    static const u8 reach[3] = { 24, 26, 34 }, bw[3] = { 16, 18, 26 }, bh[3] = { 6, 8, 8 };
    if (!whip_active() || whip_count != WHIP_HIT_FRAME) return FALSE;
    s16 x = simon_x + 8 + (facing_left ? -reach[whip_level] : reach[whip_level]);
    s16 y = simon_y + 16 + ((whip_crouch && !air_whip) ? 7 : -2);
    bool hit = abs(cx - x) < hw + bw[whip_level] && abs(cy - y) < hh + bh[whip_level];
    if (hit) sfx_play(SFX_14);                                  // a hit ($E4CC)
    return hit;
}

// ---------------------------------------------------------------- sub-weapons

static void start_whip(bool crouch);
static const SimonPose *item_pose(u8 item);

static u8 shots_active(void)
{
    u8 n = 0;
    for (u8 i = 0; i < MAX_SHOTS; i++) if (shots[i].state != W_FREE) n++;
    return n;
}

// A whips. C, or UP + A, throws the sub-weapon instead when Simon has one, a heart to spend and a free shot;
// the swing is then the whip's without the whip. Returns FALSE when nothing starts.
static bool start_attack(u16 pad, u16 pressed, bool crouch)
{
    bool want = (pressed & BUTTON_THROW) || ((pressed & BUTTON_A) && (pad & BUTTON_UP));
    if (subweapon == SUB_WATCH)                                 // used at once, the swing only shows it
    {
        throwing = want && !crouch && hearts >= WATCH_HEARTS && !watch_t;
        if (throwing) { hearts -= WATCH_HEARTS; watch_t = WATCH_FRAMES; hud_update(); sfx_play(SFX_1A); }
    }
    else
    {
        throwing = want && !crouch && subweapon && hearts && shots_active() <= shot_level;
        if (throwing) { hearts--; hud_update(); }
    }
    if (!throwing && !(pressed & BUTTON_A)) return FALSE;
    start_whip(crouch);
    return TRUE;
}

// does a sub-weapon touch the box of centre (cx, cy) and half sizes (hw, hh)? Box sizes come from the NES game's
// tables ($E5DF for the weapons, $E46A for the targets). Each hit counts towards the multiple-shot crystal ($79),
// and a dagger stops on what it hits.
static bool shot_strikes(s16 cx, s16 cy, s16 hw, s16 hh)
{
    for (u8 i = 0; i < MAX_SHOTS; i++)
    {
        Shot *s = &shots[i];
        if (s->state == W_FREE) continue;
        s16 dx = (s16)(s->x >> 8) - cx, dy = (s16)(s->y >> 8) - cy;
        if (abs(dx) < 8 + hw && abs(dy) < (s->kind == SUB_DAGGER ? 6 : 8) + hh)
        {
            if (hit_counter < 255) hit_counter++;
            if (s->kind == SUB_DAGGER) s->state = W_FREE;
            s->last = 0xFF;
            sfx_play(SFX_14);
            return TRUE;
        }
    }
    return FALSE;
}

static void shots_update(void)
{
    for (u8 i = 0; i < MAX_SHOTS; i++)
    {
        Shot *s = &shots[i];
        switch (s->state)
        {
        case W_FLY:
            s->t++;
            // the cross and the axe whir: their sound, 4 frames running, every 12 (16) frames from the 7th
            if (s->kind == SUB_CROSS && s->t >= 7 && modu(s->t - 7, 12) < 4) sfx_play(SFX_07);
            if (s->kind == SUB_AXE && s->t >= 7 && (s->t - 7) % 16 < 4) sfx_play(SFX_09);
            if (s->kind == SUB_DAGGER) s->x += dirmul(s->dir, DAGGER_VX);
            else if (s->kind == SUB_AXE)                           // a parabola through everything, off the bottom
            {
                s->x += dirmul(s->dir, AXE_VX);
                s->vy -= ((s->t - 1) & 15) < 4 ? 0x40 : 0x41;      // the NES game's gravity follows this pattern
                s->y -= s->vy;
                if ((s->y >> 8) > 255) s->state = W_FREE;
            }
            else if (s->kind == SUB_CROSS)                         // out, brake, back the other way
            {
                if (s->t > CROSS_OUT && !s->vy)
                {
                    if (s->vx > CROSS_BRAKE) s->vx -= CROSS_BRAKE;
                    else { s->vx = 0; s->vy = 1; s->dir = -s->dir; }   // vy = 1: on its way back
                }
                else if (s->vy && s->vx < CROSS_VX) { s->vx += CROSS_BACK; if (s->vx > CROSS_VX) s->vx = CROSS_VX; }
                s->x += dirmul(s->dir, s->vx);
                if (s->vy && abs((s16)(s->x >> 8) - (simon_x + 8)) < 8) s->state = W_FREE;   // caught by Simon
            }
            else                                                   // holy water: a parabola until it hits the floor
            {
                s->x += dirmul(s->dir, HOLY_VX);
                s->vy -= HOLY_GRAVITY;
                s->y -= s->vy;
                s16 bottom = (s->y >> 8) + 8;
                if (solid_at(s->x >> 8, bottom)) { s->y = (s32)((bottom & ~7) - 8) << 8; s->state = W_BURN; s->t = 0; sfx_play(SFX_1E); }
                else if (bottom > 248) s->state = W_FREE;
            }
            {
                s16 sx = (s->x >> 8) - cam_x;
                if (sx < -8 || sx > 264) s->state = W_FREE;
            }
            break;
        case W_BURN:
            if (++s->t >= FLAME_FRAMES) s->state = W_FREE;
            break;
        }
    }
    if (throwing && subweapon != SUB_WATCH && whip_phase == 2 && whip_left == THROW_AT && (state == ST_WHIP || air_whip || stair_whip))
    {
        for (u8 i = 0; i < MAX_SHOTS; i++)
        {
            Shot *s = &shots[i];
            if (s->state != W_FREE) continue;
            s->kind = subweapon; s->dir = facing_left ? -1 : 1;
            s->x = (s32)(simon_x + 8) << 8; s->y = (s32)(simon_y + 8) << 8;
            s->vx = s->kind == SUB_CROSS ? CROSS_VX : 0;
            s->vy = s->kind == SUB_AXE ? AXE_VY : s->kind == SUB_CROSS ? 0 : HOLY_VY;
            s->state = W_FLY; s->t = 0; s->last = 0; s->hit_boss = FALSE;
            break;
        }
    }
}

static void shots_draw(void)
{
    for (u8 i = 0; i < MAX_SHOTS; i++)
    {
        Shot *s = &shots[i];
        s16 x = s->x >> 8, y = s->y >> 8;
        if (s->state == W_FLY && s->kind == SUB_DAGGER) draw_object(item_pose(ITEM_DAGGER), x - 8, y - 8, s->dir < 0);
        else if (s->state == W_FLY && s->kind == SUB_AXE)
            draw_object(&obj_poses[OBJ_AXE0 + ((s->t >> 2) & 3)], x - 8, y - 8, s->dir < 0);
        else if (s->state == W_FLY && s->kind == SUB_CROSS)
            draw_object(&obj_poses[OBJ_CROSS0 + modu(s->t >> 2, 3)], x - 8, y - 8, FALSE);
        else if (s->state == W_FLY) draw_object(&obj_poses[OBJ_BOTTLE], s->dir < 0 ? x - 12 : x - 4, y - 4, s->dir < 0);
        else if (s->state == W_BURN)
        {
            u8 k = modu(s->t / 9, 5);                                 // 3 flame frames, then 2 blank ones (9 frames each)
            if (k < 3) draw_object(&obj_poses[OBJ_FLAME0 + k], x - 4, y - 8, FALSE);
        }
    }
}

// the rosary: the background flashes and every enemy on screen dies, again each frame while it lasts
static void rosary_update(void)
{
    if (!rosary_t) return;
    rosary_t--;
    PAL_setColor(0, (rosary_t && (frame_count & 2)) ? 0x0AAA : world_palette[0]);
    for (u8 i = 0; i < MAX_ENEMIES; i++)
        if (enemies[i].state == E_WALK) { enemies[i].state = E_DYING; enemies[i].t = 0; }
    for (u8 i = 0; i < MAX_MONSTERS; i++)
        if (monsters[i].kind == M_BAT || monsters[i].kind == M_FISH || monsters[i].kind == M_FIRE)
        { monsters[i].kind = M_DYING; monsters[i].t = 0; }
    for (u8 i = 0; i < PANTHERS; i++)
    {
        Panther *p = &panthers[i];
        if (p->state < P_DYING && p->x + 32 > cam_x && p->x < cam_x + 256) { p->state = P_DYING; p->t = 0; }
    }
}

// ---------------------------------------------------------------- candles and items

#define ITEM_LIFE 192                          // frames an item stays on the floor (measured on the NES game)

static const SimonPose *item_pose(u8 item)
{
    switch (item)
    {
    case ITEM_LARGE:       return &obj_poses[OBJ_ITEM0];
    case ITEM_WHIP:        return &obj_poses[OBJ_ITEM0 + 1];
    case ITEM_DAGGER:      return &obj_poses[OBJ_ITEM0 + 2];
    case ITEM_SMALL:       return &obj_poses[OBJ_SMALLHEART];
    case ITEM_MONEY_RED:   return &obj_poses[OBJ_MONEY0];
    case ITEM_MONEY_BLUE:  return &obj_poses[OBJ_MONEY0 + 1];
    case ITEM_MONEY_WHITE: return &obj_poses[OBJ_MONEY0 + 2];
    case ITEM_ROSARY:      return &obj_poses[OBJ_ROSARY];
    case ITEM_HOLY:        return &obj_poses[OBJ_HOLY];
    case ITEM_AXE:         return &obj_poses[OBJ_AXE0];
    case ITEM_CROSS:       return &obj_poses[OBJ_CROSS0 + 1];
    case ITEM_POTION:      return &obj_poses[OBJ_POTION];
    case ITEM_WATCH:       return &obj_poses[OBJ_WATCH];
    case ITEM_ROAST:       return &obj_poses[OBJ_ROAST];
    default:               return &obj_poses[OBJ_DOUBLE];
    }
}
static s16 item_w(u8 item) { return item == ITEM_SMALL ? 8 : 16; }

static const SimonPose *subweapon_pose(void)
{
    switch (subweapon)
    {
    case SUB_HOLY:  return item_pose(ITEM_HOLY);
    case SUB_AXE:   return item_pose(ITEM_AXE);
    case SUB_CROSS: return item_pose(ITEM_CROSS);
    case SUB_WATCH: return item_pose(ITEM_WATCH);
    default:        return item_pose(ITEM_DAGGER);
    }
}

static s16 obj_w(u8 i) { return i < CANDLES ? 16 : 8; }
static s16 obj_h(u8 i) { return i < CANDLES ? 32 : 16; }

// braziers belong to the courtyard; a wall candle to the part of the world it stands in (the MD screen is wider than
// the NES one, so the next part's candles would show at its edge), and to the next part while the door scrolls to it
static bool obj_here(u8 i)
{
    if (i >= DROP0) return TRUE;
    if (i < CANDLES) return !in_hall;
    if (!in_hall) return FALSE;
    s16 c = objs[i].x >> 3;
    const Section *sec = &sections[section];
    if (c >= sec->c0 && c < sec->c1) return TRUE;
    return state == ST_DOOR && c >= sections[(u8)sec->next].c0 && c < sections[(u8)sec->next].c1;
}

static void treasures_reset(void);
static void drops_clear(void) { for (u8 i = DROP0; i < NOBJS; i++) objs[i].state = O_GONE; }

static void objects_init(void)
{
    hit_effect.frames = 0;
    blocks_broken = 0; broken_block_count = 0;
    treasures_reset();
    drops_clear();
    for (u8 i = 0; i < 4; i++) debris[i].vx = 0;
    for (u8 i = CANDLES + WCANDLES_MAX; i < DROP0; i++) { objs[i].state = O_GONE; objs[i].x = blocks[i - CANDLES - WCANDLES_MAX].x; }
    for (u8 i = 0; i < CANDLES + WCANDLES_MAX; i++)
    {
        Obj *o = &objs[i];
        if (i < CANDLES)
        {
            o->x = level_candles[i].x;
            o->y = STAND_Y;
            while (!standable_at(o->x, o->y, 32) && o->y < 200) o->y++;   // stand on the real floor
            o->code = level_candles[i].code;
        }
        else
        {
            if (i - CANDLES >= world_nwcandles) { o->state = O_GONE; o->x = -999; continue; }   // not in this block
            o->x = world_wcandles[i - CANDLES].x;
            o->y = world_wcandles[i - CANDLES].y;
            o->code = world_wcandles[i - CANDLES].code;
#ifdef FORCE_CODE                               /* make EXTRA_FLAGS=-DFORCE_CODE=14: testing aid, every wall candle drops this */
            o->code = FORCE_CODE;
#endif
        }
        o->state = O_CANDLE;
        o->t = 0;
        o->power = FALSE;
    }
}

// What a broken candle drops, following the NES game's routine: a candle has an item code; code 0 means "decide now"
// from the number of hearts, the whip level and a coin flip; codes with a low nibble of 1 are money bags (the high
// nibble is the colour); the others are fixed items, but only one power-up may lie around, and a sub-weapon the
// player already has turns into a small heart or a white money bag.
static u8 random_filler(void) { return (random() & 1) ? ITEM_MONEY_WHITE : ITEM_SMALL; }

static u8 choose_item(u8 code, bool *power)
{
    u8 low = code & 15;
    *power = FALSE;

    if (code == 0)
    {
        if (hit_counter >= 10)                                        // every 10th hit: a multiple-shot crystal
        {
            hit_counter = 0;
            if (shot_level < 2) return ITEM_DOUBLE;
        }
        if (!power_flag && ((hearts >= 8 && whip_level < 2) || (hearts >= 4 && hearts < 8 && whip_level < 1)))
        {
            power_flag = TRUE; *power = TRUE;
            return ITEM_WHIP;
        }
        return random_filler();
    }
    if (low == 1) return (code >> 4) == 1 ? ITEM_MONEY_RED : (code >> 4) == 2 ? ITEM_MONEY_BLUE : ITEM_MONEY_WHITE;

    if (power_flag || low == subweapon) return random_filler();
    power_flag = TRUE; *power = TRUE;
    switch (low)
    {
    case 2: case 3: return ITEM_WHIP;
    case 4:         return ITEM_LARGE;
    case 8:         return ITEM_DAGGER;
    case 9:         return ITEM_CROSS;
    case 10:        return ITEM_ROSARY;
    case 11:        return ITEM_HOLY;
    case 12:        return ITEM_DOUBLE;
    case 13:        return ITEM_AXE;
    case 14:        return ITEM_POTION;
    case 15:        return ITEM_WATCH;
    default:        power_flag = FALSE; *power = FALSE; return ITEM_SMALL;   // item types not in this stage yet
    }
}

// a new sub-weapon: like the SNES port, the one in hand (with its multiple-shot level) goes to the reserve slot
static void take_subweapon(u8 sub)
{
    if (subweapon && weapon_swap) { other_sub = subweapon; other_level = shot_level; }
    subweapon = sub;
    if (difficulty != DIFF_EASY) { hit_counter = 0; shot_level = 0; }   // easy keeps the multiple shot
}

// Z (six-button pad; R on the SNES port) swaps the sub-weapon in hand with the reserve one
static void swap_subweapon(void)
{
    if (!other_sub) return;
    u8 t = subweapon; subweapon = other_sub; other_sub = t;
    t = shot_level; shot_level = other_level; other_level = t;
}

static void pick_up(Obj *o)
{
    switch (o->item)
    {
    case ITEM_LARGE:       hearts = hearts + 5 > 99 ? 99 : hearts + 5; break;
    case ITEM_SMALL:       hearts = hearts + 1 > 99 ? 99 : hearts + 1; break;
    case ITEM_WHIP:        if (whip_level < 2) whip_level++; whip_freeze = 24; break;
    case ITEM_MONEY_RED:   score += 400; break;     // the purple bag (measured on the NES game)
    case ITEM_MONEY_BLUE:  score += 700; break;
    case ITEM_MONEY_WHITE: score += 100; break;     // the white bag, also the random filler
    case ITEM_DAGGER:      take_subweapon(SUB_DAGGER); break;
    case ITEM_ROSARY:      rosary_t = ROSARY_FRAMES; break;
    case ITEM_HOLY:        take_subweapon(SUB_HOLY); break;
    case ITEM_AXE:         take_subweapon(SUB_AXE); break;
    case ITEM_CROSS:       take_subweapon(SUB_CROSS); break;
    case ITEM_WATCH:       take_subweapon(SUB_WATCH); break;
    case ITEM_POTION:      potion_t = POTION_FRAMES; break;
    case ITEM_ROAST:       player_hp = player_hp + ROAST_HP > PLAYER_HP ? PLAYER_HP : player_hp + ROAST_HP; break;
    case ITEM_DOUBLE:     // only useful with a sub-weapon that can be multiplied (not the stopwatch), otherwise 700 points
        if (subweapon && subweapon != SUB_WATCH) { if (shot_level < 2) shot_level++; }
        else score += 700;                          // turned into item code $21, the 700 bag
        break;
    }
    if (o->power) power_flag = FALSE;
    hud_update();
    // the NES game's sounds ($E762): hearts, money, the rest
    u8 snd = SFX_18;
    if (o->item == ITEM_LARGE || o->item == ITEM_SMALL) snd = SFX_16;
    else if (o->item == ITEM_MONEY_RED || o->item == ITEM_MONEY_BLUE || o->item == ITEM_MONEY_WHITE
             || (o->item == ITEM_DOUBLE && (!subweapon || subweapon == SUB_WATCH))) snd = SFX_17;
    else if (o->item == ITEM_ROSARY) snd = SFX_24;
    else if (o->item == ITEM_POTION) snd = SFX_1B;
    sfx_play(snd);
}

static void objects_update(void)
{
    // the candles only need testing on the whip's hit frame or with a sub-weapon in the air
    bool strikes = whip_active() && whip_count == WHIP_HIT_FRAME && !whip_hit_done;
    for (u8 k = 0; k < MAX_SHOTS && !strikes; k++) strikes = shots[k].state != W_FREE;
    for (u8 i = 0; i < NOBJS; i++)
    {
        Obj *o = &objs[i];
        if (o->state == O_GONE || (o->state == O_CANDLE && !strikes) || !obj_here(i)) continue;
        switch (o->state)
        {
        case O_CANDLE:
            if (!whip_hit_done && whip_strikes(o->x + obj_w(i) / 2, o->y + obj_h(i) / 2, obj_w(i) / 2, obj_h(i) / 2))
            {
                o->state = O_SPARK; o->t = 0;
                whip_hit_done = TRUE;
            }
            else if (shot_strikes(i < CANDLES ? o->x + 8 : o->x + 4, i < CANDLES ? o->y + 16 : o->y + 8, 6, 6))
            { o->state = O_SPARK; o->t = 0; }
            break;
        case O_SPARK:
            if (++o->t >= (i >= DROP0 ? DROP_FLAME : SPARK_FRAMES))
            {
                if (o->code == NO_ITEM) { o->state = O_GONE; break; }
                o->state = O_ITEM; o->t = 0;
                o->item = choose_item(o->code, &o->power);                    // decided when the item appears
                if (i < CANDLES) o->y += 8; else if (item_w(o->item) == 16) o->x -= 4;   // items are 16 px wide, candles 8
            }
            break;
        case O_ITEM:
            for (u8 k = 0; k < 2 && !standable_at(o->x, o->y, 16); k++) o->y++;               // 2 px per frame
            // the NES game's test ($E6EC): centres closer than the item's box (6) + 4 across and + 12 up and down,
            // + 10 crouched ($5F); across, its subtraction without SEC ($EF84) takes one more off: -10 < d <= 10
            s16 d = simon_x + 8 - (o->x + item_w(o->item) / 2);
            if (state != ST_DEAD && d > -10 && d <= 10
                && abs(o->y + 8 - (simon_y + 16)) < (state == ST_CROUCH || (state == ST_WHIP && whip_crouch) ? 16 : 18))
            {
                pick_up(o);
                o->state = O_GONE;
            }
            else if (++o->t >= ITEM_LIFE)                                     // nobody took it
            {
                if (o->power) power_flag = FALSE;
                o->state = O_GONE;
            }
            break;
        }
    }
}

static void objects_draw(void)
{
    for (u8 i = 0; i < NOBJS; i++)
    {
        Obj *o = &objs[i];
        s16 sx = o->x - cam_x;
        if (o->state == O_GONE || sx < -48 || sx >= 320 || !obj_here(i)) continue;     // off the screen: the cheap test first
        switch (o->state)
        {
        case O_CANDLE:
            if (i < CANDLES) draw_object(&obj_poses[OBJ_BRAZIER0 + ((frame_count >> 3) & 1)], o->x, o->y, FALSE);
            else             draw_object(&obj_poses[OBJ_WCANDLE0 + ((frame_count >> 3) & 1)], o->x, o->y, FALSE);
            break;
        case O_SPARK:
        {
            s16 fx = i < CANDLES ? o->x + 4 : o->x, fy = i < CANDLES ? o->y + 8 : o->y;     // flame position
            draw_object(&obj_poses[OBJ_FLAME0 + (o->t < 9 ? 0 : o->t < 18 ? 1 : 2)], fx, fy, FALSE);
            if (o->t < 16) draw_object(&obj_poses[OBJ_SPARKLE], i < CANDLES ? o->x : o->x - 4, i < CANDLES ? o->y : o->y - 8 + 8, FALSE);
            break;
        }
        case O_ITEM:   draw_object(item_pose(o->item), o->x, o->y, FALSE); break;
        }
    }
}

// An enemy killed by the whip or a sub-weapon turns into a flame, which may leave an item (the NES game's routine at
// $E097): on frames with ($1A & 15) == 2 one of four items from the table at $E138, in turn (the counter $7B, skipping
// the sub-weapon in hand; never for the fireballs); otherwise on one frame in 8 the candles' item code 0, or a large
// heart for a fishman. type: the NES game's object type (1 zombie, 2 bat, 3 fishman, 0x11 panther, 0x25 fireball).
static u8 drop_turn;                           // $7B, never reset

static void drop_spawn(s16 cx, s16 cy, u8 type)
{
    static const u8 specials[6][4] = { { 0x0A, 0x0F, 0x0B, 0x00 },     // per block ($E12C): rosary, stopwatch, holy water
                                       { 0x0B, 0x0A, 0x00, 0x09 },     // holy water, rosary, cross
                                       { 0x0A, 0x0A, 0x0E, 0x00 },     // rosary, rosary, axe
                                       { 0x0A, 0x0E, 0x0D, 0x00 },
                                       { 0x00, 0x0F, 0x0E, 0x08 },
                                       { 0x09, 0x0F, 0x0A, 0x00 } };
    const u8 *special = specials[(loaded_block < 6 ? loaded_block : 6) - 1];   // stage 18 is the NES game's block 6
    u8 code = NO_ITEM;
    if ((type < 0x20 || type >= 0x28) && (frame_count & 15) == 2)
    {
        do code = special[++drop_turn & 3]; while (code == subweapon);
    }
    else if (!(frame_count & 7))                // the NES game's types 3, 8, 0x0C, 0x0E and 0x12 leave the code 4 ($E0B9)
        code = type == 3 || type == 8 || type == 0x0C || type == 0x0E || type == 0x12 ? 4 : 0;
    for (u8 i = DROP0; i < NOBJS; i++)
        if (objs[i].state == O_GONE)
        {
            Obj *o = &objs[i];
            o->x = cx - 4; o->y = cy - 8; o->code = code;
            o->state = O_SPARK; o->t = 0; o->power = FALSE;
            return;
        }
}

// ---------------------------------------------------------------- breakable blocks

static bool block_whipped;                     // one block at most per swing

// a block's item comes out at once, whatever the power-up flag says (checked on the NES game), except a large heart
// (code 4, stage 12), which goes through the flag like a candle's ($EB6A)
static u8 block_item(u8 code, bool *power)
{
    *power = FALSE;
    if (code == 5) return ITEM_ROAST;
    if ((code & 15) == 1) return (code >> 4) == 1 ? ITEM_MONEY_RED : (code >> 4) == 2 ? ITEM_MONEY_BLUE : ITEM_MONEY_WHITE;
    if (code == 4) return choose_item(code, power);
    return ITEM_DOUBLE;
}

static void block_break(u8 k)
{
    const Block *b = &blocks[k];
    mark_block_broken(k);
    for (s16 c = b->x >> 3; c <= (b->x >> 3) + 1; c++)
        if (slot_col[c & (PLANE_COLS - 1)] == c) load_column(c);
    // four pieces (the NES game's table at $AAC9, whichever way Simon faces): 8 px above and at the block's top, at
    // its left and 8 px further, each rounded down to 16 px on the screen
    static const s8 dx[4] = { 0, 8, 0, 8 }, dy[4] = { -8, -8, 0, 0 };
    static const s16 vx[4] = { 0xC0, 0xE0, -0x80, 0x50 }, vy[4] = { -0x180, -0x1C0, -0x1E0, -0x1D0 };
    for (u8 i = 0; i < 4; i++)
    {
        debris[i].x = (s32)(cam_x + ((b->x + dx[i] - cam_x) & ~15)) << 8;
        debris[i].y = (s32)((b->y + dy[i]) & ~15) << 8;
        debris[i].vx = vx[i]; debris[i].vy = vy[i];
    }
    if (!b->code) return;
    Obj *o = &objs[CANDLES + WCANDLES_MAX + k];
    o->item = block_item(b->code, &o->power);
    o->x = b->x + 8 - item_w(o->item) / 2; o->y = b->y;                 // then it falls to the floor
    o->state = O_ITEM; o->t = 0;
}

// the whip's tip is a box centred 0x18 px ahead of Simon's centre (0x28 for the long chain), 0x10 (0x18) px wide on
// each side and 8 px high on each side of his centre ($3F, $A8D2)
static void blocks_update(void)
{
    if (!whip_active()) block_whipped = FALSE;
    else if (!block_whipped)
    {
        block_whipped = TRUE;
        s16 reach = whip_level == 2 ? 0x28 : 0x18, hw = whip_level == 2 ? 0x18 : 0x10;
        s16 cx = simon_x + 8 + (facing_left ? -reach : reach), cy = simon_y + 16 + ((whip_crouch && !air_whip) ? 4 : 0);   // $3F: 4 px lower when crouched
        for (u8 k = 0; k < BLOCKS; k++)
        {
            const Block *b = &blocks[k];
            if (b->sec != section || ((blocks_broken >> k) & 1) || (b->loop2 && !second_loop)) continue;
            if (abs(b->x + 8 - cx) < hw + 8 && abs(b->y + 8 - cy) < 16) { block_break(k); sfx_play(SFX_15); break; }
        }
    }
    for (u8 i = 0; i < 4; i++)
    {
        Debris *d = &debris[i];
        if (!d->vx) continue;
        d->x += d->vx; d->vy += DEBRIS_GRAVITY; d->y += d->vy;
        if ((d->y >> 8) >= 208) d->vx = 0;
    }
}

static void debris_draw(void)
{
    for (u8 i = 0; i < 4; i++)
        if (debris[i].vx) draw_object(&obj_poses[OBJ_DEBRIS], debris[i].x >> 8, debris[i].y >> 8, FALSE);
}

// ---------------------------------------------------------------- hidden treasures

// The NES game's table at $FC38 (its routine at $A63A of bank 6), positions as Simon's centre: with his centre within
// 14 px across and 22 px up or down of the point, TR_ENTER shows the treasure at once, TR_CROUCH while DOWN is held,
// TR_STILL after 128 frames without any button, TR_PUSH after 128 frames walking against a wall. Some only exist on
// the second loop. The treasure rises out of the floor (1 px every 4 frames, 15 px; the NES game hides what is still
// under the floor with sprites behind the background), stays 256 frames and is taken like an item, with the same box
// around its centre, rising or not. What then stays 48 frames, 16 px further right, is its points ($A7B8: '1000' for
// the bag), palettes still cycling.
// (4 bytes each, FF at the end: y & F0 | loop2 << 3 | how << 1 | floor, x & F8 | screen, the treasure's offset from
// the point: dy = (high nibble) + 8, dx = 16 * (low nibble), both signed, then the item; $A69E)
enum { TR_STILL, TR_CROUCH, TR_PUSH, TR_ENTER };
enum { TR_BAG, TR_1UP, TR_CROWN, TR_CHEST, TR_4000 };   // the NES game's item codes (1000 points, 1UP, 2000, 2000, 4000)
enum { TS_GONE, TS_NEW, TS_RISE, TS_WAIT, TS_TAKEN };
typedef struct { u8 sec, how, item; bool loop2; s16 x, y, ix, iy; } Treasure;
static const Treasure treasures[] = {
    { SEC_COURT, TR_ENTER,  TR_BAG,   FALSE, 728,                    176, 632,                    200 },   // over the gate
    { SEC_COURT, TR_CROUCH, TR_BAG,   TRUE,  304,                    176, 208,                    200 },
    { SEC_HALL,  TR_STILL,  TR_BAG,   TRUE,  832 + 512,              96,  768 + 512,              120 },
    { SEC_UNDER, TR_CROUCH, TR_BAG,   FALSE, UNDER_COL0 * 8 + 464,   176, UNDER_COL0 * 8 + 352,   136 },
    { SEC_ST2,   TR_PUSH,   TR_1UP,   TRUE,  ST2_COL0 * 8 + 128,     128, ST2_COL0 * 8 + 32,      120 },
    { SEC_ST4,   TR_ENTER,  TR_CROWN, FALSE, ROOM(4, 0) * 8 + 232,   144, ROOM(4, 0) * 8 + 136,   216 },
    { SEC_ST5,   TR_STILL,  TR_CHEST, FALSE, ROOM(5, 0) * 8 + 304,   80,  ROOM(5, 0) * 8 + 400,   120 },
    { SEC_ST5B,  TR_ENTER,  TR_4000,  TRUE,  ROOM(5, 1) * 8 + 448,   64,  ROOM(5, 1) * 8 + 464,   184 },
    { SEC_ST6B,  TR_STILL,  TR_BAG,   FALSE, ROOM(6, 1) * 8 + 496,   144, ROOM(6, 1) * 8 + 432,   168 },
    { SEC_ST6,   TR_STILL,  TR_1UP,   TRUE,  ROOM(6, 0) * 8 + 464,   160, ROOM(6, 0) * 8 + 368,   184 },
    { SEC_ST7B,  TR_CROUCH, TR_BAG,   FALSE, ROOM3(7, 1) * 8 + 536,  208, ROOM3(7, 1) * 8 + 424,  168 },
    { SEC_ST7B,  TR_CROUCH, TR_4000,  TRUE,  ROOM3(7, 1) * 8 + 152,  112, ROOM3(7, 1) * 8 + 40,   200 },
    { SEC_ST8B,  TR_CROUCH, TR_BAG,   FALSE, ROOM3(8, 1) * 8 + 656,  160, ROOM3(8, 1) * 8 + 528,  168 },
    { SEC_ST8,   TR_ENTER,  TR_4000,  TRUE,  ROOM3(8, 0) * 8 + 728,  144, ROOM3(8, 0) * 8 + 680,  168 },
    { SEC_ST9,   TR_PUSH,   TR_BAG,   FALSE, ROOM3(9, 0) * 8 + 1320, 144, ROOM3(9, 0) * 8 + 1208, 184 },
    { SEC_ST13B, TR_PUSH,   TR_1UP,   FALSE, ROOM5(13, 1) * 8 + 408, 80,  ROOM5(13, 1) * 8 + 360, 200 },
    { SEC_ST14B, TR_CROUCH, TR_BAG,   FALSE, ROOM5(14, 1) * 8 + 560, 112, ROOM5(14, 1) * 8 + 560, 200 },
    { SEC_ST14B, TR_STILL,  TR_BAG,   FALSE, ROOM5(14, 1) * 8 + 992, 192, ROOM5(14, 1) * 8 + 896, 200 },
    { SEC_ST14B, TR_STILL,  TR_BAG,   FALSE, ROOM5(14, 1) * 8 + 296, 192, ROOM5(14, 1) * 8 + 392, 200 },
    { SEC_ST17,  TR_CROUCH, TR_BAG,   FALSE, ROOM6(17, 0) * 8 + 368, 128, ROOM6(17, 0) * 8 + 272, 104 },   // the only one of block 6
};
#define TREASURES (sizeof(treasures) / sizeof(treasures[0]))
static u32 treasures_found = 0;                // one bit per treasure (the NES game's $144), until the stage restarts
static u8 treasure_wait = 0;                   // TR_STILL and TR_PUSH count to 64 every other frame ($145)
static struct { s16 x, y; u8 k, state; u16 t; } shown_treasure;
static u32 rising_tiles[32];                   // the rising treasure's 4 tiles, cut at the floor

static void treasures_reset(void) { treasures_found = 0; treasure_wait = 0; shown_treasure.state = TS_GONE; }

static bool simon_near(s16 x, s16 y)
{
    s16 dx = simon_x + 8 - x, dy = simon_y + 16 - y;
    return dx >= -14 && dx < 14 && dy >= -22 && dy < 22;
}

static void treasures_update(u16 pad)
{
    if (state == ST_DEAD || state == ST_GATE || state == ST_DOOR || state == ST_CLIMB || state == ST_EXIT_CLIMB || hall_load) return;
    for (u8 k = 0; k < TREASURES && shown_treasure.state == TS_GONE; k++)
    {
        const Treasure *t = &treasures[k];
        if (t->sec != section || ((treasures_found >> k) & 1UL) || (t->loop2 && !second_loop) || !simon_near(t->x, t->y))
            continue;
        bool found = t->how == TR_ENTER || (t->how == TR_CROUCH && (pad & BUTTON_DOWN));
        if (t->how == TR_STILL || t->how == TR_PUSH)
        {
            bool ok = t->how == TR_STILL ? !(pad & BUTTON_ALL)
                                         : (pad & (BUTTON_LEFT | BUTTON_RIGHT)) && wall_ahead(facing_left ? -1 : 1);
            if (!ok) treasure_wait = 0;
            else if (!(frame_count & 1) && ++treasure_wait == 0x40) { treasure_wait = 0; found = TRUE; }
        }
        if (!found) continue;
        treasures_found |= 1UL << k;
        shown_treasure.k = k; shown_treasure.x = t->ix; shown_treasure.y = t->iy; shown_treasure.state = TS_NEW;
        sfx_play(SFX_23);
    }
    switch (shown_treasure.state)
    {
    case TS_GONE: return;
    case TS_NEW: shown_treasure.state = TS_RISE; shown_treasure.t = 16; return;
    case TS_RISE:
        if (!(frame_count & 3))
        {
            if (!--shown_treasure.t) { shown_treasure.state = TS_WAIT; shown_treasure.t = 256; }
            else shown_treasure.y--;
        }
        break;
    case TS_WAIT:
        if (!--shown_treasure.t) { shown_treasure.state = TS_GONE; return; }
        break;
    case TS_TAKEN:
        if (!--shown_treasure.t) shown_treasure.state = TS_GONE;
        return;
    }
    if (!simon_near(shown_treasure.x, shown_treasure.y)) return;
    // $A7BD: sound 0x25 for the 1UP, else 0x17 and the points
    u8 item = treasures[shown_treasure.k].item;
    if (item == TR_1UP)
    { lives++; shown_treasure.state = TS_GONE; sfx_play(SFX_25); }
    else
    {
        score += item == TR_4000 ? 4000 : item == TR_BAG ? 1000 : 2000; sfx_play(SFX_17);
        shown_treasure.state = TS_TAKEN; shown_treasure.t = 48; shown_treasure.x += 16;
    }
    hud_update();
}

static void treasure_draw(void)
{
    if (shown_treasure.state < TS_RISE) return;
    u8 item = treasures[shown_treasure.k].item, pal = (frame_count >> 1) & 3;
    const SimonPose *pose;
    if (shown_treasure.state == TS_TAKEN)
        pose = loaded_block == 1 ? &obj_poses[OBJ_TREASURE0 + 8 + pal]
             : &world_poses[(item == TR_BAG ? B2_PTS1000_0 : item == TR_4000 ? B2_PTS4000_0 : B2_PTS2000_0) + pal];
    else if (item == TR_CROWN) pose = &world_poses[B2_TR2_0 + pal];
    else if (item == TR_CHEST) pose = &world_poses[B2_TR3_0 + pal];
    else if (item == TR_4000)  pose = &world_poses[B2_TR4_00 + ((frame_count >> 3) & 3) * 4 + pal];
    else pose = &obj_poses[OBJ_TREASURE0 + item * 4 + pal];
    s16 sx = NES_X + shown_treasure.x - 8 - cam_x, sy = shown_treasure.y - 8;
    if (shown_treasure.state != TS_RISE) { draw_object(pose, shown_treasure.x - 8, sy, FALSE); return; }
    // rising: only the rows above the floor line, from copies of its tiles (two 8x16 sprites)
    u8 rows = treasures[shown_treasure.k].iy - shown_treasure.y;
    for (u8 k = 0; k < pose->count; k++)
    {
        const u32 *src = &world_tiles[pose->sprites[k].tile * 8];
        for (u8 r = 0; r < 16; r++) rising_tiles[k * 16 + r] = r < rows ? src[r] : 0;
    }
    VDP_loadTileData(rising_tiles, TILE_USER_INDEX + RISING_TILE, 4, DMA_QUEUE);
    for (u8 k = 0; k < pose->count && sprite_n < MAX_SPRITES; k++, sprite_n++)
    {
        const SimonSprite *s_ = &pose->sprites[k];
        VDP_setSpriteFull(sprite_n, sx + s_->dx, sy + 1 - 8 + s_->dy, SPRITE_SIZE(1, 2),
                          (s_->attr & 0xF800) + TILE_USER_INDEX + RISING_TILE + k * 2, sprite_n + 1);
    }
}

// ---------------------------------------------------------------- zombies

static void monsters_init(void);
static void boss_init(void);

static void enemies_init(void)
{
    for (u8 i = 0; i < MAX_ENEMIES; i++) enemies[i].state = E_FREE;
    monsters_init();
    boss_init();
}

static void simon_hurt(s16 from_x)
{
    if (invuln || potion_t || state == ST_DEAD || state == ST_EXIT_CLIMB) return;
    if (god) return;
    u8 st = sections[section].stage;                            // the NES game's $E740, whatever hits: 8 in stages 1 to
    u16 damage = second_loop || st >= 12 ? 16 : st >= 7 ? 12 : 8;   // 6, 12 in 7 to 11, 16 from 12 on and on the second loop
    if (difficulty == DIFF_EASY) damage >>= 1;                  // the SNES port: half on easy, double on hard
    if (difficulty == DIFF_HARD) damage <<= 1;
    hurt_play();                                                // $E734: the DMC sample, on every hit
    player_hp = player_hp > damage ? player_hp - damage : 0;
    invuln = INVULN_FRAMES;
    if (state == ST_STAIRS || difficulty == DIFF_EASY)          // no knockback on the stairs, nor at all on easy
    {
        if (!player_hp) { state = ST_DEAD; state_t = 0; stair_whip = FALSE; }
        hud_update();
        return;
    }
    air_whip = FALSE;
    state_t = 0; jump_base_y = simon_y;
    jump_vx = from_x > simon_x ? -1 : 1;                        // thrown away from the enemy
    facing_left = (jump_vx > 0);
    state = player_hp ? ST_HURT : ST_DEAD;
    hud_update();
}

static void enemies_update(void)
{

    for (u8 i = 0; i < MAX_ENEMIES; i++)
    {
        Enemy *e = &enemies[i];
        if (e->state == E_FREE) continue;
        if (e->state == E_DYING)
        {
            if (++e->t >= DEATH_FRAMES) e->state = E_FREE;
            continue;
        }
        if (!watch_t)                                           // the stopwatch holds them where they are
        {
            e->t++;
            if (e->vy || !solid_at(e->x + 8, e->y + 32))        // off a ledge: straight down, then walks on
            {
                u16 d = e->fy + (e->vy += GRAVITY);
                e->y += d >> 8; e->fy = d & 0xFF;
                if (solid_at(e->x + 8, e->y + 32)) { e->y = ((e->y + 32) & ~7) - 32; e->vy = 0; e->fy = 0; }
                if (e->y > 240) { e->state = E_FREE; continue; }
            }
            else
            {
                if ((frame_count & 7) != 7) e->x += e->dir;     // 7 px every 8 frames, like the NES zombie
                e->x += loop_step(&e->xf, e->dir);
            }
        }
        if (e->x < cam_x - NES_X - 48 || e->x > cam_x + 256 + NES_X + 48) { e->state = E_FREE; continue; }

        if (whip_strikes(e->x + 8, e->y + 16, 6, 14) || shot_strikes(e->x + 8, e->y + 16, 6, 14))
        {
            e->state = E_FREE;                                  // one hit kills a zombie
            drop_spawn(e->x + 8, e->y + 16, 0x01);
            score += ZOMBIE_SCORE;
            hud_update();
            continue;
        }
        if (overlap(simon_x + 2, simon_y, 12, FEET, e->x + 2, e->y, 12, 30))
            simon_hurt(e->x);
    }
}

static void enemies_draw(void)
{
    for (u8 i = 0; i < MAX_ENEMIES; i++)
    {
        Enemy *e = &enemies[i];
        if (e->state == E_WALK)
            draw_object(&obj_poses[OBJ_ZOMBIE0 + ((e->t / 17) & 1)], e->x, e->y, e->dir > 0);
        else if (e->state == E_DYING)
            draw_object(&obj_poses[OBJ_SPARKLE], e->x + 4, e->y + 8, FALSE);
    }
}

// ---------------------------------------------------------------- black panthers

// the NES game's panther (object 0x11, its AI in bank 5 at $824D): a single probe 8 px below its centre ($EF98)
static bool panther_floor(const Panther *p) { return solid_at(p->x + 16, p->y + 16); }

static void panthers_init(void)
{
    for (u8 i = 0; i < PANTHERS; i++)
    {
        panthers[i].x = level_panthers[i].x;
        panthers[i].y = level_panthers[i].y;
        panthers[i].dir = -1;
        panthers[i].state = P_SIT;
        panthers[i].t = 0;
        panthers[i].xf = 0;
    }
}

static void panthers_update(void)
{

    for (u8 i = 0; i < PANTHERS; i++)
    {
        Panther *p = &panthers[i];
        if (p->state == P_GONE) continue;
        if (p->state == P_DYING)
        {
            if (++p->t >= DEATH_FRAMES) p->state = P_GONE;
            continue;
        }
        s16 dx = (simon_x + 8) - (p->x + 16);
        switch (watch_t ? P_GONE : p->state)                   // the stopwatch holds them where they are
        {
        case P_SIT:                                            // waits until Simon is within 64 px across, at any height
            if (dx > -64 && dx < 64) { p->dir = dx < 0 ? -1 : 1; p->state = P_RUN; p->t = 0; }
            break;
        case P_RUN:                                            // straight on at 2 px/frame, without turning back
            p->x += dirmul(p->dir, 2) + loop_step(&p->xf, p->dir);
            p->t++;
            if (!panther_floor(p)) { p->state = P_LEAP; p->vy = 0x180; p->yf = 0; }   // off the ledge: a hop
            break;
        case P_LEAP:                                           // 1.5 px/frame up, 0x20/256 gravity, 2 px/frame across
        {
            p->x += dirmul(p->dir, 2) + loop_step(&p->xf, p->dir);
            p->vy -= 0x20;
            s32 y = ((s32)p->y << 8 | p->yf) - p->vy;
            p->y = y >> 8; p->yf = y & 0xFF;
            if (p->vy < 0 && panther_floor(p))                // landed: centre snapped to 8 px, runs at Simon again
            {
                p->y = ((p->y + 8) & ~7) - 8; p->yf = 0;
                p->dir = dx < 0 ? -1 : 1;
                p->state = P_RUN; p->t = 0;
            }
            break;
        }
        }
        if (p->state != P_SIT && (p->x + 16 - cam_x < 8 || p->x + 16 - cam_x > 248)) { p->state = P_GONE; continue; }   // off the screen

        if (whip_strikes(p->x + 16, p->y + 8, 10, 6)
            || shot_strikes(p->x + 16, p->y + 8, 10, 6))
        {
            p->state = P_GONE;                                 // one hit kills a panther
            drop_spawn(p->x + 16, p->y + 8, 0x11);
            score += PANTHER_SCORE;
            hud_update();
            continue;
        }
        if (overlap(simon_x + 2, simon_y, 12, FEET, p->x + 2, p->y, 28, 14))
            simon_hurt(p->x + 16);
    }
}

static void panthers_draw(void)
{
    static const u8 run_seq[3] = { 2, 1, 3 };                   // run1, stretched, run2, 7 frames each
    for (u8 i = 0; i < PANTHERS; i++)
    {
        Panther *p = &panthers[i];
        u8 pose = OBJ_PANTHER0 + (p->dir > 0 ? 4 : 0);
        if (p->state == P_SIT) pose += 0;
        else if (p->state == P_LEAP) pose += 1;
        else if (p->state == P_RUN) pose += run_seq[modu(p->t / 7, 3)];
        else if (p->state == P_DYING) { draw_object(&obj_poses[OBJ_SPARKLE], p->x + 12, p->y, FALSE); continue; }
        else continue;
        draw_object(&obj_poses[pose], p->x, p->y, FALSE);
    }
}

// ---------------------------------------------------------------- Simon

// ---------------------------------------------------------------- stages 2 and 3: generators, bats, fishmen

// The NES game keeps up to 6 enemy generators per screen ($0160-$018F): each one works while it is on the screen
// (x 8 to 248) and has its own wait, counted down every other frame. Positions read from those records while
// playing (generators drift by a pixel with the scroll in the NES game itself); y is a centre. G_BAT2 (the NES game's
// type 4, $80E3) is the bat generator of the second loop only: the same code as G_BAT once past its loop test.
enum { G_ZOMBIE, G_BAT, G_FISH, G_BAT2 };
typedef struct { s16 x; u8 y, kind; } Gen;
static const Gen gens[] = {
    { ST2_COL0 * 8 + 108, 80, G_BAT }, { ST2_COL0 * 8 + 364, 80, G_BAT },
    { UNDER_COL0 * 8 + 32, 184, G_FISH }, { UNDER_COL0 * 8 + 96, 184, G_FISH }, { UNDER_COL0 * 8 + 160, 184, G_FISH },
    { UNDER_COL0 * 8 + 224, 184, G_FISH }, { UNDER_COL0 * 8 + 288, 184, G_FISH }, { UNDER_COL0 * 8 + 352, 184, G_FISH },
    { UNDER_COL0 * 8 + 416, 184, G_FISH },
    // zombies: the hall's and the upper room of stage 2's (NES room x + 512 / + the room's start), only while their
    // place is on the screen, so none come while Simon stands still away from them (checked in the NES game)
    { 32 + 512, 192, G_ZOMBIE }, { 288 + 512, 192, G_ZOMBIE }, { 1248 + 512, 192, G_ZOMBIE }, { 1376 + 512, 192, G_ZOMBIE },
    { ST2_COL0 * 8 + 672, 192, G_ZOMBIE }, { ST2_COL0 * 8 + 800, 128, G_ZOMBIE }, { ST2_COL0 * 8 + 928, 192, G_ZOMBIE },
    { ST3_COL0 * 8 + 32, 192, G_ZOMBIE }, { ST3_COL0 * 8 + 160, 128, G_ZOMBIE }, { ST3_COL0 * 8 + 288, 192, G_ZOMBIE },
    { 224 + 512, 128, G_BAT2 }, { 480 + 512, 128, G_BAT2 }, { 735 + 512, 128, G_BAT2 }, { 863 + 512, 128, G_BAT2 },
    { 991 + 512, 128, G_BAT2 }, { 1119 + 512, 128, G_BAT2 }, { 1247 + 512, 128, G_BAT2 }, { 1375 + 512, 128, G_BAT2 },
    { 1503 + 512, 128, G_BAT2 },                                                            // the hall
    { ST2_COL0 * 8 + 224, 128, G_BAT2 }, { ST2_COL0 * 8 + 480, 128, G_BAT2 },
    { ST3_COL0 * 8 + 96, 128, G_BAT2 }, { ST3_COL0 * 8 + 351, 128, G_BAT2 },
};
#define GENS (sizeof(gens) / sizeof(gens[0]))
static u8 gen_wait[GENS];
static bool gen_on[GENS];                      // on the screen since the previous frame
static u8 zombie_train = 0;                    // the NES game's $63

static Monster *monster_new(u8 kind, u8 limit)
{
    u8 n = 0;
    Monster *free_m = NULL;
    for (u8 i = 0; i < MAX_MONSTERS; i++)
    {
        if (monsters[i].kind == kind) n++;
        else if (monsters[i].kind == M_FREE && !free_m) free_m = &monsters[i];
    }
    if (n >= limit || !free_m) return NULL;
    free_m->kind = kind; free_m->state = 0; free_m->t = 0; free_m->timer = 0; free_m->vx = free_m->vy = 0;
    return free_m;
}

static void monsters_init(void)
{
    for (u8 i = 0; i < MAX_MONSTERS; i++) monsters[i].kind = M_FREE;
    for (u8 i = 0; i < GENS; i++) { gen_wait[i] = 0; gen_on[i] = FALSE; }
    for (u8 i = 0; i < OGENS_MAX; i++) { og_on[i] = FALSE; og_wait[i] = 0; og_count[i] = 0; }
    zombie_train = 0;
}

// three drops when a fishman leaves or falls back into the water (velocities: table at $8088 of the NES game)
static void splash(s32 x, s32 y, u8 sound)
{
    // NES $F095: $0E on leaving the water; $F15A: $0F on returning.
    // Play even when there are no free slots for the splash's drops.
    sfx_play(sound);
    static const s16 vx[3] = { 0x30, 0x60, -0x60 }, vy[3] = { 0x280, 0x140, 0x140 };
    for (u8 k = 0; k < 3; k++)
    {
        Monster *d = monster_new(M_DROP, 6);
        if (!d) return;
        d->x = x; d->y = y; d->vx = vx[k]; d->vy = vy[k];
    }
}

// the NES game's zombie generator: one side of the screen at random, the other one if that is within 64 px of
// Simon, on the generator's floor; trains of three, 32 frames apart, then 288 frames
static bool gen_zombie(const Gen *g)
{
    u8 n = 0;
    Enemy *e = NULL;
    for (u8 i = 0; i < MAX_ENEMIES; i++)
    {
        if (enemies[i].state != E_FREE) n++;
        else if (!e) e = &enemies[i];
    }
    if (!e || n >= 3) return FALSE;
    s16 simon_sx = simon_x + 8 - cam_x;
    u8 side = random() & 1;
    if (abs((side ? 8 : 248) - simon_sx) < 64) side ^= 1;
    s16 cx = cam_x + (side ? 8 : 248);
    if (!solid_at(cx, g->y + 20)) return FALSE;
    e->x = cx - 8; e->y = g->y - 16; e->dir = side ? 1 : -1;
    e->vy = 0; e->fy = 0; e->xf = 0; e->state = E_WALK; e->t = 0;
    return TRUE;
}

// a bat from the side Simon faces (the other one if that is within 64 px of him), at about his height
static bool spawn_bat(void)
{
    static const s8 dy[4] = { -20, -12, -4, 0 };
    Monster *b = monster_new(M_BAT, 3);
    if (!b) return FALSE;
    s16 simon_sx = simon_x + 8 - cam_x;
    bool left = facing_left;
    if (abs((left ? 8 : 248) - simon_sx) < 64) left = !left;
    b->x = (s32)(cam_x + (left ? 8 : 248)) << 8;
    b->dir = left ? 1 : -1;
    s16 y = simon_y + 16 + dy[frame_count & 3] + 1;             // the NES game adds a carry here
    b->y = (s32)y << 8; b->cy = y + 8;
    return TRUE;
}

// a fishman leaping out of the water at (x, y), unless Simon is within 40 px of it ($81A6: not on loop 2)
static bool spawn_fish(s16 x, u8 y)
{
    if (!second_loop && abs(simon_x + 8 - x) < 0x28) return FALSE;
    Monster *f = monster_new(M_FISH, 2);
    if (!f) return FALSE;
    f->x = (s32)x << 8; f->y = (s32)y << 8;
    f->dir = simon_x + 8 >= x ? 1 : -1;
    f->vy = FISH_VY; f->state = F_JUMP;
    splash(f->x, f->y, SFX_0E);
    return TRUE;
}

static void gens_update(void)
{
    if (state == ST_DEAD || state == ST_DOOR || state == ST_CLIMB || state == ST_EXIT_CLIMB || hall_load) return;
    const Section *sec = &sections[section];
    for (u8 i = 0; i < GENS; i++)
    {
        const Gen *g = &gens[i];
        s16 sx = g->x - cam_x;
        if (g->x < sec->c0 * 8 || g->x >= sec->c1 * 8 || sx < 8 || sx >= 0xF9) { gen_on[i] = FALSE; continue; }
        bool first = !gen_on[i];
        gen_on[i] = TRUE;
        if (watch_t) continue;                                  // the stopwatch holds the generators too
        if (gen_wait[i] && (frame_count & 1)) gen_wait[i]--;
        switch (g->kind)
        {
        case G_ZOMBIE:
            if (gen_wait[i] || !gen_zombie(g)) break;
            if (zombie_train >= 3) { zombie_train = 0; gen_wait[i] = 0x90; } else gen_wait[i] = 0x10;
            zombie_train++;
            break;
        case G_BAT2:
            if (!second_loop) break;
            // fall through
        case G_BAT:                                             // from the side Simon faces, at about his height
            if (gen_wait[i] || (state == ST_STAIRS && stair_dir > 0) || !spawn_bat()) break;
            gen_wait[i] = 0xC0;
            break;
        case G_FISH:                                            // waits 168 frames each time it comes on screen
            if (first) { gen_wait[i] = 0x54; break; }
            if (gen_wait[i] || !spawn_fish(g->x, g->y)) break;
            gen_wait[i] = 0xFF;
            break;
        }
    }
}

static s16 monster_hw(const Monster *m) { return m->kind == M_FIRE || m->kind == M_BANDAGE ? 2 : m->kind == M_BONE || m->kind == M_KAXE ? 4 : m->kind == M_EAGLE ? 14 : 6; }     // NES table at $E46A
static s16 monster_hh(const Monster *m)
{
    return m->kind == M_FIRE ? 2 : m->kind == M_FISH || m->kind == M_SKEL || m->kind == M_EAGLE ? 14 : m->kind == M_SNAKE ? 3
           : m->kind == M_BONE || m->kind == M_BANDAGE || m->kind == M_KAXE ? 4 : 6;
}

static void monster_kill(Monster *m, u16 points)
{
    m->kind = M_DYING; m->t = 0;
    if (points) { score += points; hud_update(); }
}

// ---------------------------------------------------------------- block 2's enemies

static s8 face_simon(s16 cx) { return simon_x + 8 >= cx ? 1 : -1; }

static void knight_update(Monster *m)
{
    if (m->immune) { m->immune--; return; }                    // stands still after a hit
    s16 cx = m->x >> 8, cy = m->y >> 8;
    bool level = abs(simon_y + 16 - cy) < 4;
    switch (m->state)
    {
    case K_PATROL:
        if (level) { m->dir = face_simon(cx); m->state = K_CHASE; m->timer = KNIGHT_TURN; return; }
        if (!--m->timer) { m->dir = -m->dir; m->timer = KNIGHT_TURN; }
        break;
    case K_CHASE:
        if (!level) { m->state = K_PATROL; m->timer = KNIGHT_TURN; return; }
        if (!--m->timer) { m->dir = face_simon(cx); m->timer = KNIGHT_TURN; }
        break;
    case K_FALL:                                                // off a ledge, onto the next floor
        m->vy += GRAVITY; m->y += m->vy;
        cy = m->y >> 8;
        if (solid_at(cx, cy + 16)) { m->y = (s32)(((cy + 16) & ~15) - 16) << 8; m->state = K_PATROL; m->timer = KNIGHT_TURN; }
        return;
    }
    m->x += dirmul(m->dir, KNIGHT_VX);
    m->t++;
    cx = m->x >> 8;
    if (!solid_at(cx, cy + 16)) { m->state = K_FALL; m->vy = 0; return; }
    if (wall_at(cx + dirmul(m->dir, 16), cy) || !(solid_at(cx + dirmul(m->dir, 4), cy + 20) || wall_at(cx + dirmul(m->dir, 4), cy + 20)))
        m->dir = -m->dir;
}

// ---------------------------------------------------------------- block 3's enemies

// does the NES game's collision map have a solid tile at this point? (its objects test any solid tile, $F9A0)
static bool map_solid(s16 x, s16 y)
{
    if (y < 0 || y >= 28 * 8 || block_gone(x, y)) return FALSE;
    s16 c = section_col(x >> 3);
    u32 occupied = !in_hall && c >= GATE_COL0
        ? gate_wall[c - GATE_COL0] | gate_solid[c - GATE_COL0]
        : world_wall[c - world_c0] | world_solid[c - world_c0];
    return (occupied >> (y >> 3)) & 1;
}


// Move a grounded/hopping enemy sideways without crossing a wall. Test the
// leading edge over its full sprite height, in steps of at most one pixel:
// the jump routines used to move x directly, so every hop could cross a wall.
// Floor-only surfaces must not become lateral obstacles.
static bool hopper_move_x(Monster *m, s16 dx, s16 hw, s16 hh)
{
    s16 cy = m->y >> 8;
    s16 checked_col = -32768;
    while (dx)
    {
        s16 step = dx > 0x100 ? 0x100 : dx < -0x100 ? -0x100 : dx;
        s32 nx = m->x + step;
        s16 edge = (nx >> 8) + (step > 0 ? hw - 1 : -hw);
        s16 col = edge >> 3;
        // Walls and broken blocks are aligned to tiles. While y stays fixed,
        // all substeps in the same column have exactly the same result.
        if (col != checked_col)
        {
            s16 bottom = cy + hh - 1;
            for (s16 y = cy - hh; y <= bottom; y = (y & ~7) + 8)
                if (wall_at(edge, y)) return FALSE;
            checked_col = col;
        }
        m->x = nx;
        dx -= step;
    }
    return TRUE;
}

static void flea_update(Monster *m)
{
    s16 cx = m->x >> 8;
    m->t++;
    switch (m->state)
    {
    case FL_HIDDEN:
        if (!--m->timer) { m->state = FL_FALL; m->vy = 0; }
        return;
    case FL_CARRIED:                                            // pad[0]: its eagle's slot
    {
        const Monster *e = &monsters[m->pad[0]];
        if (e->kind == M_EAGLE && ((frame_count & 7) || abs(simon_x + 8 - cx) >= FLEA_NEAR)) { m->x = e->x; return; }
        m->state = FL_FALL; m->vy = 0;
        return;
    }
    case FL_WAIT:
        if (--m->timer) return;
        {
            m->dir = face_simon(cx);
            bool high = abs(simon_x + 8 - cx) < FLEA_NEAR && facing_left == (m->dir > 0);     // Simon faces it
            m->vy = high ? FLEA_HIGH_VY : FLEA_LOW_VY;
            m->vx = high ? FLEA_HIGH_VX : FLEA_LOW_VX;
            m->state = FL_JUMP;
        }
        return;
    case FL_JUMP:
        if (!hopper_move_x(m, dirmul(m->dir, m->vx + LOOP_VX), 8, 8)) m->dir = -m->dir;
        // fall through
    case FL_FALL:                                               // lands on whatever is 8 px under its centre
    {
        m->vy -= B3_GRAVITY; m->y -= m->vy;
        s16 cy = m->y >> 8;
        if (map_solid(m->x >> 8, cy + 8))
        { m->y = (s32)(cy & ~7) << 8 | (m->y & 0xFF); m->state = FL_WAIT; m->timer = FLEA_HOP_WAIT; }
        return;
    }
    }
}

// Igor (stage 12, $893F): carried on Frankenstein's head, then hops about the boss screen at 1.5 px/frame across,
// with a fireball at Simon at the top of each hop; a hit only holds it, blinking, for IGOR_STUN frames ($E395)
enum { IG_CARRIED, IG_RISE, IG_FALL, IG_WAIT };
static void fire_at(s32 x, s32 y);

static void igor_bounds(Monster *m)                             // $8998: inside the screen, below y 0x30
{
    s16 sx = (m->x >> 8) - BOSS_CAM;
    if (sx < 9 || sx >= 0xF7)
    { m->x = (s32)(BOSS_CAM + (sx < 9 ? 9 : 0xF7)) << 8 | (m->x & 0xFF); m->dir = -m->dir; }
    if ((m->y >> 8) < 0x30) { m->y = (s32)0x30 << 8 | (m->y & 0xFF); m->vy = 0; }
}

static void igor_update(Monster *m)
{
    static const s16 hop_vy[4] = { 3 << 8, 5 << 8, 4 << 8, 6 << 8 };
    if (m->immune) { m->immune--; return; }
    m->t++;
    switch (m->state)
    {
    case IG_CARRIED:                                            // Frankenstein moves it ($8A1E)
        m->dir = face_simon(m->x >> 8); m->vx = IGOR_V; m->vy = 0;
        return;
    case IG_WAIT:
        if (--m->timer) { igor_bounds(m); return; }
        m->state = IG_RISE; m->vy = hop_vy[random() & 3];
        return;
    }
    m->x += dirmul(m->dir, m->vx + LOOP_VX);                    // $F06D, then $F002 as the fleaman's fall
    m->vy -= B3_GRAVITY; m->y -= m->vy;
    s16 cy = m->y >> 8;
    if (map_solid(m->x >> 8, cy + 8))
    { m->y = (s32)(cy & ~7) << 8 | (m->y & 0xFF); m->timer = IGOR_LAND_WAIT; m->state++; }
    igor_bounds(m);
    if (m->state == IG_RISE && m->vy < 0) { fire_at(m->x, m->y); m->state = IG_FALL; }
}

static void igor_hits(Monster *m)
{
    s16 cx = m->x >> 8, cy = m->y >> 8;
    if (m->immune) return;                                      // harmless while it blinks
    if (whip_strikes(cx, cy, 6, 6) || shot_strikes(cx, cy, 6, 6)) { m->immune = IGOR_STUN; return; }
    if (overlap(simon_x + 2, simon_y, 12, FEET, cx - 6, cy - 6, 12, 12)) simon_hurt(cx);
}

// the raven's travel: cy = its direction across, hp = 1 when it goes up
static void raven_dive(Monster *m)
{
    static const s16 dive_vy[4] = { 0x1C0, 0x280, 0x140, 0x200 };
    s16 cx = m->x >> 8, cy = m->y >> 8;
    m->hp = simon_y + 16 < cy;
    m->vy = dive_vy[random() & 3];
    m->cy = face_simon(cx);
    m->vx = RAVEN_VX;
    m->state = RV_DIVE;
}

static void raven_update(Monster *m)
{
    static const u8 hover[4] = { 0x18, 0x3F, 0x25, 0x79 };
    s16 cx = m->x >> 8, cy = m->y >> 8;
    m->dir = face_simon(cx);
    m->t++;
    switch (m->state)
    {
    case RV_PERCH:
        if (!--m->timer) raven_dive(m);
        return;
    case RV_DIVE:
        m->vy -= RAVEN_BRAKE;
        if (m->vy < 0) { m->timer = hover[random() & 3]; m->state = RV_HOVER; return; }
        m->y += m->hp ? -m->vy : m->vy;
        break;
    case RV_HOVER:
        if (--m->timer) return;
        if (abs(simon_y + 16 - cy) >= RAVEN_NEAR) { raven_dive(m); return; }
        m->cy = face_simon(cx); m->vx = RAVEN_CHARGE; m->timer = RAVEN_CHARGE_T; m->state = RV_CHARGE;
        return;
    case RV_CHARGE:
    {
        if (!--m->timer) { raven_dive(m); return; }
        m->vx += RAVEN_ACCEL;
        m->x += dirmul(m->cy, m->vx + LOOP_VX);
        cx = m->x >> 8;
        s16 sc = simon_x + 8;
        if (m->cy > 0 ? cx > sc + 8 : cx <= sc - 8)                // 8 px past him: back
        { m->hp = simon_y + 16 < cy; m->vx = RAVEN_BACK; m->timer = RAVEN_BACK_T; m->state = RV_BACK; }
        return;
    }
    case RV_BACK:
        if (!--m->timer) { raven_dive(m); return; }
        m->y += m->hp ? -m->vy : m->vy;
        m->vx -= RAVEN_ACCEL;
        break;
    }
    m->x += dirmul(m->cy, m->vx + LOOP_VX);
}

// the skeleton's walk: cy = its direction, hp = the walks left before it throws
static void skel_update(Monster *m)
{
    static const u8 walks[4] = { 4, 2, 3, 1 };
    s16 cx = m->x >> 8, cy = m->y >> 8;
    m->dir = face_simon(cx);
    m->t++;
    switch (m->state)
    {
    case SK_START:
        m->hp = walks[random() & 3]; m->vx = SKEL_VX; m->timer = SKEL_STEP; m->state = SK_STEP;
        break;
    case SK_STEP:
        if (--m->timer) break;
        if (!--m->hp) { m->timer = SKEL_STEP; m->state = SK_THROW; break; }
        m->cy = abs(simon_x + 8 - cx) >= SKEL_FAR ? m->dir : -m->dir;
        m->timer = SKEL_WALK; m->state = SK_WALK;
        break;
    case SK_WALK:
    {
        if (!--m->timer) { m->timer = SKEL_STEP; m->state = SK_STEP; break; }
        bool moved = hopper_move_x(m, dirmul(m->cy, m->vx), 8, 16);
        cx = m->x >> 8;
        if (!moved || map_solid(cx + dirmul(m->cy, 12), cy)) m->cy = -m->cy;
        else if (!map_solid(cx, cy + 16)) { m->vx = SKEL_JUMP_VX; m->vy = SKEL_JUMP_VY; m->state = SK_JUMP; }
        break;
    }
    case SK_THROW:
        if (--m->timer) break;
        {
            Monster *b = monster_new(M_BONE, 10);
            if (b) { b->x = m->x; b->y = m->y; b->dir = m->dir; b->vx = BONE_VX; b->vy = frame_count & 1 ? 0x380 : 0x480; }
        }
        m->timer = SKEL_THROWN; m->state = SK_THROWN;
        break;
    case SK_THROWN:
        if (!--m->timer) m->state = SK_START;
        break;
    case SK_JUMP:                                               // lands on the 16 px row its feet reach
        if (!hopper_move_x(m, dirmul(m->cy, m->vx), 8, 16)) m->cy = -m->cy;
        m->vy -= B3_GRAVITY; m->y -= m->vy;
        cy = m->y >> 8;
        if (map_solid(m->x >> 8, cy + 16)) { m->y = (s32)(cy & ~15) << 8 | (m->y & 0xFF); m->state = SK_START; }
        break;
    }
}

// ---------------------------------------------------------------- block 5's enemies

// the red skeleton: hp = the walks left before it turns to Simon, t = its walk's animation (still while it stands)
static void rskel_update(Monster *m)
{
    static const u8 walks[4] = { 4, 3, 5, 4 };
    s16 cx = m->x >> 8, cy = m->y >> 8;
    switch (m->state)
    {
    case RS_HIDDEN:
        if (--m->timer) return;
        m->hp = 1;
        // fall through
    case RS_LIE:
        if (m->state == RS_LIE && --m->timer) return;
        m->state = RS_RISE; m->timer = RSKEL_RISE;
        return;
    case RS_RISE:
        if (--m->timer) return;
        // fall through
    case RS_STAND:
        if (m->state == RS_STAND && --m->timer) return;
        if (!--m->hp) { m->dir = face_simon(cx); m->hp = walks[random() & 3]; }
        m->state = RS_WALK; m->timer = RSKEL_WALK;
        return;
    case RS_DROP:
        if (!--m->timer) { m->state = RS_LIE; m->timer = RSKEL_LIE; }
        return;
    case RS_FALL:
        m->vy += GRAVITY; m->y += m->vy;
        cy = m->y >> 8;
        if (map_solid(cx, cy + 16)) { m->y = (s32)(((cy + 16) & ~15) - 16) << 8; m->state = RS_WALK; }
        return;
    case RS_WALK:
        if (!--m->timer) { m->state = RS_STAND; m->timer = RSKEL_STAND; return; }
        m->t++;
        if (!hopper_move_x(m, dirmul(m->dir, RSKEL_VX + LOOP_VX), 8, 16))
            m->dir = -m->dir;
        cx = m->x >> 8;
        if (!map_solid(cx, cy + 16)) { m->state = RS_FALL; m->vy = 0; }
        return;
    }
}

// its hits: only while it walks, stands or falls
static void rskel_hits(Monster *m)
{
    if (m->state == RS_HIDDEN || m->state == RS_RISE || m->state == RS_DROP || m->state == RS_LIE) return;
    s16 cx = m->x >> 8, cy = m->y >> 8;
    if (whip_strikes(cx, cy, 6, 14) || shot_strikes(cx, cy, 6, 14))
    {
        m->state = RS_DROP; m->timer = RSKEL_DROP;
        score += RSKEL_SCORE; hud_update();
        return;
    }
    if (overlap(simon_x + 2, simon_y, 12, FEET, cx - 6, cy - 14, 12, 28)) simon_hurt(cx);
}

// the axe knight: dir = its facing (to Simon), cy = its walking direction, pad[1] = the walks left before it throws,
// pad[0] = its guard (0xFF: broken), hp = its damage, immune = the frames it stays stunned
static void axek_walk(Monster *m, s16 cx)
{
    m->cy = abs(simon_x + 8 - cx) < AXEK_FAR ? -m->dir : m->dir;
    m->state = AK_WALK; m->timer = AXEK_WALK;
}

// Move the axe knight's full 24x32 body, including when it backs away from
// Simon. A turn must not make an unchecked step into the opposite wall.
static bool axek_move_x(Monster *m, s16 dx)
{
    s16 cy = m->y >> 8;
    while (dx)
    {
        s16 step = dx > 0x100 ? 0x100 : dx < -0x100 ? -0x100 : dx;
        s16 nx = (m->x + step) >> 8;
        if (nx - 12 < sections[section].c0 * 8 || nx + 12 > sections[section].c1 * 8) return FALSE;
        // Keep the leading edge on the platform too: the old centre +/- 4
        // probe let the 24 px sprite back several pixels beyond a ledge.
        if (!map_solid(nx + (step > 0 ? 11 : -12), cy + 16)) return FALSE;
        if (!hopper_move_x(m, step, 12, 16)) return FALSE;
        dx -= step;
    }
    return TRUE;
}

static void axek_update(Monster *m)
{
    static const u8 walks[4] = { 9, 11, 10, 12 };
    if (m->immune) { m->immune--; return; }
    s16 cx = m->x >> 8;
    m->dir = face_simon(cx);
    m->t++;
    switch (m->state)
    {
    case AK_START:
        m->pad[1] = walks[random() & 3];
        axek_walk(m, cx);
        break;
    case AK_WALK:
        if ((u16)(cx - cam_x) >= 256) { m->state = AK_STAND; m->timer = AXEK_STAND; break; }   // off the screen: stops
        if (!--m->timer)
        {
            if (--m->pad[1]) { m->state = AK_STAND; m->timer = AXEK_STAND; }
            else { m->state = AK_AIM; m->timer = AXEK_AIM; }
            break;
        }
        if (!axek_move_x(m, dirmul(m->cy, AXEK_VX + LOOP_VX))) m->cy = -m->cy;
        break;
    case AK_STAND:
        if (!--m->timer) axek_walk(m, cx);
        break;
    case AK_AIM:
        if (--m->timer) break;
        {
            Monster *a = monster_new(M_KAXE, MAX_MONSTERS);
            if (a)
            {
                a->x = m->x; a->y = m->y + ((s32)(random() & 1 ? 8 : -12) << 8); a->dir = a->pad[1] = m->dir;
                a->vx = KAXE_V; a->timer = KAXE_OUT; a->pad[0] = m - monsters;
            }
        }
        m->state = AK_START;
        break;
    }
}

static void kaxe_update(Monster *a)
{
    a->t++;
    switch (a->state)
    {
    case KA_OUT:
        if (!--a->timer) a->state = KA_BRAKE;
        a->x += dirmul(a->dir, a->vx + LOOP_VX);
        return;
    case KA_BRAKE:
        a->vx -= KAXE_BRAKE;
        if (a->vx < 0) { a->vx = 0; a->dir = -a->dir; a->state = KA_BACK; }
        break;
    case KA_BACK:
        a->vx += KAXE_BRAKE;
        if (a->vx >= KAXE_V) { a->vx = KAXE_V; a->state = KA_HOME; }
        break;
    case KA_HOME:
    {
        const Monster *k = &monsters[a->pad[0]];
        if (k->kind == M_AXEK && abs((s16)(k->x >> 8) - (s16)(a->x >> 8)) < KAXE_HOME) { a->kind = M_FREE; return; }
        break;
    }
    }
    a->x += dirmul(a->dir, a->vx);
}

// the axe knight's hits (see above); the sub-weapons' own fates on its guard (stopped, bounced) are not reproduced
static void axek_hits(Monster *m)
{
    u8 idx = m - monsters + 1;
    s16 cx = m->x >> 8, cy = m->y >> 8;
    u8 dmg = whip_level ? 32 : 24;
    bool hit = FALSE, behind = FALSE, shot = FALSE;
    if (!m->immune && whip_strikes(cx, cy, 6, 14)) { hit = TRUE; behind = facing_left == (m->dir < 0); }
    for (u8 i = 0; i < MAX_SHOTS && !hit && !m->immune; i++)
    {
        Shot *s = &shots[i];
        if (s->state == W_FREE || s->last == idx) continue;
        s16 sx = s->x >> 8, dx = sx - cx, dy = (s16)(s->y >> 8) - cy;
        if (abs(dx) >= 8 + 6 || abs(dy) >= (s->kind == SUB_DAGGER ? 6 : 8) + 14) continue;
        if (hit_counter < 255) hit_counter++;
        if (s->kind == SUB_DAGGER) s->state = W_FREE; else s->last = idx;
        sfx_play(SFX_14);
        hit = shot = TRUE; behind = m->dir > 0 ? sx <= cx : sx > cx;
    }
    if (hit)
    {
        if (m->pad[0] != 0xFF && !behind)
        {
            m->pad[0] = m->pad[0] + dmg >= AXEK_GUARD ? 0xFF : m->pad[0] + dmg;
            if (shot) m->immune = AXEK_SUB_STUN;
        }
        else if (m->hp + dmg >= AXEK_HP)
        {
            drop_spawn(cx, cy, 0x0A);
            m->kind = M_FREE;
            score += AXEK_SCORE; hud_update();
            return;
        }
        else { m->hp += dmg; m->immune = AXEK_STUN; }
    }
    if (overlap(simon_x + 2, simon_y, 12, FEET, cx - 6, cy - 14, 12, 28)) simon_hurt(cx);
}

// the hits of the knight, the ghost and the bone pillar (see KNIGHT_HP, PILLAR_HP); FALSE when it died
static bool tough_hits(Monster *m)
{
    u8 idx = m - monsters + 1;
    bool knight = m->kind == M_KNIGHT, pillar = m->kind == M_PILLAR, dragon = m->kind == M_DRAGON, gbat = m->kind == M_GBAT;
    s16 cx = m->x >> 8, cy = m->y >> 8, hw = gbat ? GBAT_HW : 6, hh = gbat ? GBAT_HH : m->kind == M_GHOST || dragon ? 6 : 14;   // its box ($E46A)
    u8 dmg = 0;
    bool immune = m->immune && !watch_t;                        // the stopwatch holds its count, not the hits: on
    if (!immune && whip_strikes(cx, cy, hw, hh))                // the NES game every whip hits a stopped giant bat
        dmg = whip_level ? 32 : 24;                             // (measured: 24, 48, 72, 96)
    for (u8 i = 0; i < MAX_SHOTS; i++)
    {
        Shot *s = &shots[i];
        if (s->state == W_FREE) continue;
        s16 dx = (s16)(s->x >> 8) - cx, dy = (s16)(s->y >> 8) - cy;
        if (abs(dx) >= 8 + hw || abs(dy) >= (s->kind == SUB_DAGGER ? 6 : 8) + hh) continue;
        if (s->kind == SUB_HOLY) { dmg++; continue; }            // burns a little every frame, immune or not
        if (immune || s->last == idx) continue;
        if (hit_counter < 255) hit_counter++;
        if (s->kind == SUB_DAGGER) { s->state = W_FREE; dmg += 24; } else { s->last = idx; dmg += 32; }
    }
    if (dmg)
    {
        if (!pillar) m->immune = KNIGHT_IMMUNE;
        if (m->hp + dmg >= (pillar ? PILLAR_HP : dragon ? DRAGON_HP : gbat ? GBAT_HP : KNIGHT_HP))
        {
            drop_spawn(cx, cy, knight ? 0x08 : pillar ? 0x0E : dragon ? 0x14 : gbat ? 0x1E : 0x0D);
            m->kind = M_FREE;
            if (dragon) for (u8 k = 2; k <= 7; k++) monster_kill(&monsters[m->pad[k]], 0);   // all of it burns
            score += knight ? KNIGHT_SCORE : pillar ? PILLAR_SCORE : dragon ? DRAGON_SCORE : gbat ? GBAT_SCORE : GHOST_SCORE; hud_update();
            return FALSE;
        }
        m->hp += dmg;
    }
    if (overlap(simon_x + 2, simon_y, 12, FEET, cx - hw, cy - hh, 2 * hw, 2 * hh)) simon_hurt(cx);
    return TRUE;
}

// the generators of blocks 2 on that put a NES object at a place (kind $40 + type): it comes when the place comes on the screen
// and nothing from it is still there

static void objgens_update(void)
{
    if (loaded_block < 2 || state == ST_DEAD || state == ST_DOOR || state == ST_CLIMB || state == ST_EXIT_CLIMB || hall_load) return;
    const Section *sec = &sections[section];
    for (u8 i = 0; i < world_ngens; i++)
    {
        const ObjGen *g = &world_gens[i];
        s16 sx = g->x - cam_x;
        if (g->kind >= 2 && g->kind <= 4)                       // block 4's bats and fishmen: $87A6 / $87E2 of bank 6
        {
            if (g->x < sec->c0 * 8 || g->x >= sec->c1 * 8 || sx < 8 || sx >= 0xF9) { og_on[i] = FALSE; continue; }
            bool first = !og_on[i];
            og_on[i] = TRUE;
            if (watch_t || (g->kind == 4 && !second_loop)) continue;
            if (og_wait[i] && (frame_count & 1)) og_wait[i]--;
            if (g->kind == 3)
            {
                if (first) og_wait[i] = 0x54;
                else if (!og_wait[i] && spawn_fish(g->x, g->y)) og_wait[i] = 0xFF;
            }
            else if (!og_wait[i] && simon_y + 16 < 0xD8 && !(state == ST_STAIRS && stair_dir > 0) && spawn_bat())
                og_wait[i] = 0xA0;                              // not 0xC0 as in block 1, nor with Simon low down
            continue;
        }
        if (g->kind == 0x54)
        {
            bool on = g->x >= sec->c0 * 8 && g->x < sec->c1 * 8 && sx >= 8 && sx < 0xF9, was = og_on[i];
            og_on[i] = on;
            if (!on || was) continue;
            bool alive = FALSE;
            for (u8 k = 0; k < MAX_MONSTERS; k++) if (monsters[k].kind == M_DRAGON && monsters[k].gen == i) alive = TRUE;
            if (alive) continue;
            Monster *part[7];
            u8 n = 0;
            for (u8 k = 0; k < MAX_MONSTERS && n < 7; k++) if (monsters[k].kind == M_FREE) part[n++] = &monsters[k];
            if (n < 7) continue;
            for (u8 k = 0; k < 7; k++)
            {
                Monster *p = part[k];
                p->kind = k ? M_VERT : M_DRAGON; p->state = DR_WAIT; p->t = 0; p->timer = 8;
                p->x = (s32)g->x << 8; p->y = (s32)g->y << 8; p->cy = 0; p->vx = p->vy = 0; p->dir = -1;
                p->hp = 0; p->immune = 0; p->gen = i; p->pad[0] = part[0] - monsters; p->pad[1] = 0;
                if (k) part[0]->pad[1 + k] = p - monsters;
            }
            part[0]->cy = 12; part[0]->x -= 12 << 8; part[0]->pad[1] = 0; part[0]->pad[8] = 0;
            continue;
        }
        if (g->kind == 0x12)
        {
            if (g->x < sec->c0 * 8 || g->x >= sec->c1 * 8 || sx < 8 || sx >= 0xF9) { og_on[i] = FALSE; continue; }
            og_on[i] = TRUE;
            if (watch_t) continue;
            if (og_wait[i] && (frame_count & 1)) og_wait[i]--;
            if (og_wait[i]) continue;
            static const u8 dy[4] = { 0, 0x20, 0x10, 0x30 };
            Monster *e = monster_new(M_EAGLE, 3), *f = e ? monster_new(M_FLEA, MAX_MONSTERS) : NULL;
            if (!f) { if (e) e->kind = M_FREE; continue; }
            bool left = random() & 1;
            e->x = (s32)(cam_x + (left ? 0x12 : 0xEE)) << 8; e->dir = left ? 1 : -1;
            e->y = (s32)(g->y + dy[++og_count[i] & 3]) << 8;
            e->state = EG_FLY; e->timer = EAGLE_FLY;
            f->x = e->x; f->y = e->y + (16 << 8); f->dir = -e->dir;
            f->state = FL_CARRIED; f->pad[0] = e - monsters; f->hp = 0; f->immune = 0; f->gen = 0xFF;
            og_wait[i] = EAGLE_WAIT;
            continue;
        }
        if (g->kind == 5 || g->kind == 6)
        {
            if (g->x < sec->c0 * 8 || g->x >= sec->c1 * 8 || sx < 8 || sx >= 0xF9) { og_on[i] = FALSE; continue; }
            bool first = !og_on[i];
            og_on[i] = TRUE;
            if (watch_t || (g->kind == 5 && !second_loop)) continue;
            if (og_wait[i] && (frame_count & 1)) og_wait[i]--;
            if (first) { og_wait[i] = MEDUSA_FIRST; continue; }
            if (og_wait[i] || (state == ST_STAIRS && stair_dir > 0)) continue;
            Monster *m = monster_new(M_MEDUSA, 3);
            if (!m) continue;
            m->x = (s32)(cam_x + (facing_left ? 8 : 248)) << 8;
            m->dir = facing_left ? 1 : -1;
            m->cy = simon_y + 16;
            m->y = (s32)(m->cy - 33) << 8;
            og_wait[i] = MEDUSA_WAIT;
            continue;
        }
        if ((g->kind & 0x7F) == 0x0D)
        {
            if (g->x < sec->c0 * 8 || g->x >= sec->c1 * 8 || sx < 8 || sx >= 0xF9) { og_on[i] = FALSE; continue; }
            if (og_on[i] || ((g->kind & 0x80) ? sx < 0xE0 : sx >= 0x20) || abs(simon_y + 16 - g->y) >= 0x30) continue;
            Monster *m = monster_new(M_GHOST, 2);
            if (!m) continue;
            og_on[i] = TRUE;                                    // once while its place stays on the screen
            m->x = (s32)g->x << 8; m->y = (s32)g->y << 8; m->dir = face_simon(g->x);
            m->timer = 1; m->hp = 0; m->immune = 0; m->gen = i;
            continue;
        }
        bool on = g->x >= sec->c0 * 8 && g->x < sec->c1 * 8 && sx >= 0 && sx < 256;
        bool was = og_on[i];
        og_on[i] = on;
        u8 kind = g->kind == 0x48 ? M_KNIGHT : g->kind == 0x47 ? M_RBAT : g->kind == 0x4E ? M_PILLAR : g->kind == 0x4C ? M_FLEA
                  : g->kind == 0x4F ? M_RAVEN : g->kind == 0x50 ? M_SKEL : g->kind == 0x5A ? M_MUMMY
                  : g->kind == 0x53 && loaded_block == 5 ? M_RSKEL : g->kind == 0x4A && loaded_block == 5 ? M_AXEK
                  : g->kind == 0x5E && loaded_block == 6 ? M_GBAT : M_FREE;
        if (!on || was || kind == M_FREE) continue;
        bool alive = FALSE;
        for (u8 k = 0; k < MAX_MONSTERS; k++) if (monsters[k].kind == kind && monsters[k].gen == i) alive = TRUE;
        if (alive) continue;
        Monster *m = monster_new(kind, MAX_MONSTERS);
        if (!m) continue;
        m->x = (s32)g->x << 8; m->y = (s32)g->y << 8; m->dir = face_simon(g->x);
        m->state = kind == M_KNIGHT ? K_PATROL : kind == M_PILLAR ? PL_WAIT : kind == M_FLEA ? FL_HIDDEN : kind == M_RAVEN ? RV_PERCH
                   : kind == M_SKEL ? SK_START : kind == M_MUMMY ? MU_WAIT : kind == M_RSKEL ? RS_HIDDEN : kind == M_AXEK ? AK_START
                   : kind == M_GBAT ? GB_WAIT : RB_SLEEP;
        m->timer = kind == M_PILLAR ? PILLAR_FIRST : kind == M_FLEA || kind == M_RAVEN ? B3_WAIT : kind == M_RSKEL ? RSKEL_HIDDEN
                   : kind == M_GBAT ? GBAT_WAIT : KNIGHT_TURN;
        m->pad[0] = 0;
        m->hp = 0; m->immune = 0; m->gen = i; m->cy = kind == M_MUMMY ? MUMMY_HP : 0;
#ifdef BOSS_TEST_HP                                /* the testing aid of boss_init: weak mummies too */
        if (kind == M_MUMMY) m->cy = BOSS_TEST_HP << 7;
#endif
    }
}

static bool boss_aim(s16 x, s16 y, s16 tx, s16 ty, bool *left, bool *up, u16 *ratio);
static void mummy_update(Monster *m);
static bool mummy_hits(Monster *m);

// a bone dragon part's vertical motion ($8A85): n, the next part towards the base
static void dragon_wave(Monster *p, Monster *n)
{
    u8 mode = p->pad[1];
    if (mode)
    {
        s16 dy = mode == 2 ? p->vy + p->vx : p->vy - p->vx;
        if (dy >= DRAGON_DY << 8 || dy < -((DRAGON_DY - 1) << 8))
        {                                                       // at its limit: the next part takes over the motion
            dy = (dy < 0 ? -DRAGON_DY << 8 : DRAGON_DY << 8) | (dy & 0xFF);
            n->pad[1] = mode; n->vx = DRAGON_V;
        }
        p->vy = dy;
    }
    p->y = (n->y & ~0xFF) + ((s32)(p->vy >> 8) << 8);
}

// the whole bone dragon, from its head (pad[2..7]: the slots of its vertebrae and base; pad[8]: mouth open)
static void dragon_update(Monster *h)
{
    static const u8 reach[5] = { 40, 32, 24, 16, 8 }, turn[4] = { 52, 36, 60, 28 };
    Monster *base = &monsters[h->pad[7]];
    if ((s16)(base->x >> 8) - cam_x >= 0x170)                    // Simon went back: gone ($8C7E)
    {
        h->kind = M_FREE;
        for (u8 k = 2; k <= 7; k++) monsters[h->pad[k]].kind = M_FREE;
        return;
    }
    if (base->state == DR_WAIT && !--base->timer)
    {
        h->state = DR_REACH;
        for (u8 k = 2; k <= 7; k++) monsters[h->pad[k]].state = DR_REACH;
    }
    if (h->immune) h->immune--;                                 // stands still after a hit
    else
    {
        bool weave = TRUE;
        switch (h->state)
        {
        case DR_REACH:
            if (++h->cy >= DRAGON_REACH) { h->cy = DRAGON_REACH; h->state = DR_READY; h->timer = 8; }
            weave = FALSE;
            break;
        case DR_READY:
            if (!--h->timer) { h->pad[1] = 2; h->vx = DRAGON_V; h->timer = 0x38; h->state = DR_WEAVE; }
            weave = FALSE;
            break;
        case DR_WEAVE:
        case DR_OPEN:
        case DR_SHUT:
            if (!--h->timer)
            {
                if (h->state == DR_OPEN)
                {
                    s16 cx = h->x >> 8, cy = h->y >> 8;
                    if (simon_x + 8 < cx && abs(simon_y + 16 - cy) < 0x28)
                    {
                        Monster *f = monster_new(M_FIRE, 2);
                        if (f)
                        {
                            bool left, up;
                            u16 ratio;
                            bool major_y = boss_aim(cx, cy, simon_x + 8, simon_y + 16, &left, &up, &ratio);
                            u16 minor = ratio + (ratio >> 1);
                            f->x = h->x; f->y = h->y; f->dir = -1;
                            f->vx = -(s16)(major_y ? minor : DRAGON_FIRE_V);
                            f->vy = major_y ? DRAGON_FIRE_V : minor;
                            if (!up) f->vy = -f->vy;
                        }
                    }
                    h->state = DR_SHUT; h->timer = 0x10;
                }
                else
                {
                    if (h->state == DR_SHUT) { h->pad[8] = 0; h->state = DR_WEAVE; }
                    h->timer = turn[random() & 3];
                    h->pad[1] ^= 3;
                    break;
                }
            }
            if ((frame_count & 31) == 0)
            {
                if (h->state == DR_WEAVE && (random() & 1) == 0) { h->pad[8] = 1; h->timer = 0x10; h->state = DR_OPEN; }
            }
            else if ((frame_count & 31) == 8)
                h->pad[1] = simon_y + 16 >= (s16)(h->y >> 8) ? 2 : 1;
            break;
        }
        if (weave) dragon_wave(h, &monsters[h->pad[2]]);
        h->x = base->x - ((s32)h->cy << 8);
    }
    for (u8 k = 0; k < 5; k++)
    {
        Monster *v = &monsters[h->pad[2 + k]], *n = &monsters[h->pad[3 + k]];
        if (v->state == DR_REACH && ++v->cy >= reach[k]) { v->cy = reach[k]; v->state = DR_READY; }
        else if (v->state == DR_READY)
        {
            if (v->pad[1] && (v->vx -= DRAGON_SLOW) < 0) v->pad[1] = 0;
            dragon_wave(v, n);
        }
        v->x = base->x - ((s32)v->cy << 8);
    }
}

// a sickle of Death's ($8FFD): at Simon, 0.875 px a frame along the larger distance; cy = 1 when it goes up
static void sickle_aim(Monster *sk)
{
    bool left, up;
    u16 ratio;
    bool major_y = boss_aim(sk->x >> 8, sk->y >> 8, simon_x + 8, simon_y + 16, &left, &up, &ratio);
    sk->vx = major_y ? ratio : SICKLE_V; sk->vy = major_y ? SICKLE_V : ratio;
    sk->dir = left ? -1 : 1; sk->cy = up;
    sk->state = SC_FLY; sk->timer = SICKLE_FLY;
}

static void sickle_update(Monster *sk)
{
    sk->t++;
    switch (sk->state)
    {
    case SC_APPEAR: if (!--sk->timer) sk->state = SC_AIM; return;
    case SC_AIM:    sickle_aim(sk); return;
    case SC_STOP:   if (!--sk->timer) sickle_aim(sk); return;
    case SC_FLY:
        if (!--sk->timer) { sk->state = SC_STOP; sk->timer = SICKLE_STOP; return; }
        sk->x += dirmul(sk->dir, sk->vx + LOOP_VX);
        sk->y += sk->cy ? -sk->vy : sk->vy;
        return;
    }
}

static const u8 gbat_fly[4] = { 0x3D, 0x25, 0x20, 0x45 };      // NES tables at $93D2, $93EE, $946F
static const u8 gbat_hover[4] = { 0x7B, 0x20, 0x3D, 0xC7 };
static const u8 gbat_swoop[4] = { 0x4D, 0x20, 0x28, 0x3F };

// $9377: towards 0x30 px right of Simon (8-bit screen x) and 0x11 above him (SBC #$10 with the carry clear: the
// speeds measured match this)
static void gbat_target(Monster *m)
{
    bool left, up;
    u16 r;
    bool major_y = boss_aim((m->x >> 8) - cam_x, m->y >> 8, (u8)(simon_x + 8 - cam_x + 0x30), simon_y + 16 - 0x11, &left, &up, &r);
    u16 r15 = r + (r >> 1);
    if (major_y) { m->vx = r15 & 0xFF00; m->vy = 0xC0; }
    else { m->vx = 0xC0; m->vy = (r15 & 0xFF00) | ((r15 + (r15 >> 8)) & 0xFF); }   // the NES game adds the whole part in
    m->dir = left ? -1 : 1; m->pad[1] = up;
    m->state = GB_FLY; m->timer = gbat_fly[random() & 3]; m->t = 0;
}

// $93F2: a swoop under Simon, or a fireball
static void gbat_decide(Monster *m)
{
    s16 cx = m->x >> 8, cy = m->y >> 8, sx = cx - cam_x;
    if (sx < 0 || sx > 255)                                     // off the screen: on across
    { m->vy = 0; m->vx = 0xC0; m->state = GB_FLY; m->timer = gbat_fly[random() & 3]; m->t = 0; return; }
    s16 dy = simon_y + 16 - cy;
    if (dy < 0 || dy >= 0x38 || abs(simon_x + 8 - cx) >= 0x48) { fire_at(m->x, m->y); m->state = GB_WAIT; m->timer = 0x10; return; }
    bool left, up;
    u16 r;
    bool major_y = boss_aim(cx, cy, simon_x + 8, simon_y + 16 + 0x18, &left, &up, &r);
    if (major_y) { m->vy = 0x200; m->vx = r * 3; }
    else { m->vx = 0x1C0; m->vy = r * 2; }
    m->dir = left ? -1 : 1;
    m->state = GB_SWOOP; m->timer = gbat_swoop[random() & 3];
}

static void gbat_update(Monster *m)
{
    m->t++;
    if (m->immune) { m->immune--; return; }                    // still after a hit ($EEA7)
    switch (m->state)
    {
    case GB_WAIT:
        if (!--m->timer) gbat_target(m);
        break;
    case GB_FLY:
        if (!--m->timer) { m->state = GB_HOVER; m->timer = gbat_hover[random() & 3]; break; }
        m->x += dirmul(m->dir, m->vx);
        m->y += m->pad[1] ? -m->vy : m->vy;
        break;
    case GB_HOVER:
        if (!--m->timer) { gbat_decide(m); break; }
        if ((frame_count & 7) && (held_pad & BUTTON_A) && abs(simon_y + 16 - (s16)(m->y >> 8)) < 0x14
            && abs(simon_x + 8 - (s16)(m->x >> 8)) < 0x58)
        { m->vy = 0x280; m->state = GB_DODGE; m->timer = 8; }
        break;
    case GB_DODGE:
        if (!--m->timer) gbat_decide(m);
        else m->y -= m->vy;
        break;
    case GB_SWOOP:
        if (!--m->timer) { gbat_target(m); break; }
        m->vy -= 6;
        m->y += m->vy;
        m->x += dirmul(m->dir, m->vx);
        break;
    }
}

static void monsters_update(void)
{
    static const u8 walk_time[4] = { 79, 121, 93, 144 };       // NES table at $F119, picked at random
    // Projectiles and fleamen share this path. Skip attack-box scans when
    // Simon has neither an active whip hit nor any sub-weapon in flight.
    bool attacks = whip_active() && whip_count == WHIP_HIT_FRAME;
    for (u8 k = 0; k < MAX_SHOTS && !attacks; k++) attacks = shots[k].state != W_FREE;

    for (u8 i = 0; i < MAX_MONSTERS; i++)
    {
        Monster *m = &monsters[i];
        if (m->kind == M_FREE) continue;
        if (m->kind == M_DYING) { if (++m->t >= DEATH_FRAMES) m->kind = M_FREE; continue; }
        if (!watch_t) switch (m->kind)
        {
        case M_KNIGHT:
            knight_update(m);
            break;
        case M_RBAT:
        {
            s16 dy = simon_y + 16 - (s16)(m->y >> 8), dx = simon_x + 8 - (s16)(m->x >> 8);
            if (m->state == RB_SLEEP)
            {
                if (dy >= 0 && dy < 56 && abs(dx) < 96)
                { m->state = RB_SWOOP; m->dir = dx >= 0 ? 1 : -1; m->vy = RBAT_VY; m->t = 0; }
                break;
            }
            if (m->state == RB_SWOOP)
            {
                m->vy -= RBAT_BRAKE;
                if (m->vy < 0) m->state = RB_FLY; else m->y += m->vy;
            }
            m->x += dirmul(m->dir, RBAT_VX + LOOP_VX);
            m->t++;
            break;
        }
        case M_GHOST:
            if (m->immune) { m->immune--; break; }             // still after a hit
            if (!--m->timer)
            {
                bool left, up;
                u16 ratio;
                bool major_y = boss_aim(m->x >> 8, m->y >> 8, simon_x + 8, simon_y + 16, &left, &up, &ratio);
                u16 minor = ratio - (ratio >> 2);
                m->timer = GHOST_AIM;
                m->dir = left ? -1 : 1;
                m->vx = major_y ? minor : GHOST_V;
                m->vy = major_y ? GHOST_V : minor;
                if (up) m->vy = -m->vy;
            }
            m->x += dirmul(m->dir, m->vx + LOOP_VX);
            m->y += m->vy;
            m->t++;
            break;
        case M_FLEA:  flea_update(m); break;
        case M_IGOR:  igor_update(m); break;
        case M_DRAGON: dragon_update(m); break;
        case M_EAGLE:
            m->t++;
            if (m->state == EG_FLY) { if (--m->timer) m->x += dirmul(m->dir, EAGLE_VX); else { m->state = EG_STOP; m->timer = EAGLE_STOP; } }
            else if (!--m->timer) { m->state = EG_FLY; m->timer = EAGLE_FLY; }
            break;
        case M_RAVEN: raven_update(m); break;
        case M_SKEL:  skel_update(m); break;
        case M_RSKEL: rskel_update(m); break;
        case M_AXEK:  axek_update(m); break;
        case M_KAXE:  kaxe_update(m); break;
        case M_SICKLE: sickle_update(m); break;
        case M_GBAT:   gbat_update(m); break;
        case M_MUMMY: mummy_update(m); break;
        case M_BANDAGE:
        {
            u16 d = (u16)((s16)(m->y >> 8) - m->cy);               // the Medusa head's spring ($EF13)
            bool carry = (u16)m->vy >= d;
            m->vy -= d;
            m->y += m->vy + carry;
            m->x += dirmul(m->dir, m->vx + LOOP_VX);
            break;
        }
        case M_BONE:
            m->x += dirmul(m->dir, m->vx + LOOP_VX);
            m->vy -= B3_GRAVITY; m->y -= m->vy;
            m->t++;
            break;
        case M_SNAKE:
        {
            s16 cx = m->x >> 8;
            m->t++;
            switch (m->state)
            {
            case SN_FALL:
                m->vy -= GRAVITY; m->y -= m->vy;
                if (solid_at(cx, (m->y >> 8) + 8))
                { m->y = (s32)((m->y >> 8) & ~7) << 8; m->state = SN_CRAWL; m->timer = SNAKE_CRAWL; }
                break;
            case SN_CRAWL:
                if (!--m->timer) { m->state = SN_STOP; m->timer = 1; break; }
                m->x += dirmul(m->dir, SNAKE_VX + LOOP_VX);
                if (!solid_at(m->x >> 8, (m->y >> 8) + 8)) { m->vy = 0; m->state = SN_FALL; }
                break;
            default:
                if (!--m->timer) { m->state = SN_CRAWL; m->timer = SNAKE_CRAWL; }
                break;
            }
            break;
        }
        case M_PILLAR:
            m->dir = face_simon(m->x >> 8);
            if (m->state == PL_SHOOT || !--m->timer)
            {
                if (m->state != PL_WAIT && m->state != PL_FLASH)
                {
                    Monster *f = monster_new(M_FIRE, 3);
                    if (f) { f->x = m->x; f->y = m->y; f->dir = m->dir; f->vx = dirmul(m->dir, PILLAR_FIRE_VX + LOOP_VX); }
                }
                static const u8 rest[4] = { 240, 60, 120, 180 };
                switch (m->state)
                {
                case PL_WAIT:  m->state = PL_FLASH; m->timer = PILLAR_FLASH; break;
                case PL_FLASH: m->state = PL_SHOOT; break;
                case PL_SHOOT: m->state = PL_AGAIN; m->timer = PILLAR_SECOND; break;
                default:       m->state = PL_WAIT; m->timer = rest[random() & 3]; break;
                }
            }
            break;
        case M_MEDUSA:
        {
            u16 d = (u16)((s16)(m->y >> 8) - m->cy);
            bool carry = (u16)m->vy >= d;                       // the carry of $EF13's subtraction
            m->vy -= d;
            m->y += m->vy + carry;
            m->x += dirmul(m->dir, MEDUSA_VX + LOOP_VX);
            m->t++;
            break;
        }
        case M_BAT:                                             // a spring around cy: vy grows by the distance in px
            m->x += dirmul(m->dir, BAT_VX + LOOP_VX);
            m->vy += m->cy - (s16)(m->y >> 8);
            m->y += m->vy;
            m->t++;
            break;
        case M_FIRE:
        case M_DBIT:
            m->x += m->vx; m->y -= m->vy;
            break;
        case M_DROP:
            m->x += m->vx; m->vy -= GRAVITY; m->y -= m->vy;
            if ((m->y >> 8) > 248) { m->kind = M_FREE; continue; }
            break;
        case M_FISH:
        {
            s16 cx = m->x >> 8;
            switch (m->state)
            {
            case F_JUMP:                                        // up through everything, then down onto a floor
                m->vy -= GRAVITY; m->y -= m->vy;
                if (m->vy < 0)
                {
                    s16 cy = m->y >> 8;
                    if (cy >= WATER_Y) { splash(m->x, m->y, SFX_0F); m->kind = M_FREE; continue; }
                    if (solid_at(cx, cy + 16)) { m->y = (s32)(cy & ~15) << 8; m->state = F_LAND; m->timer = 8; }
                }
                break;
            case F_LAND:
                if (!--m->timer) { m->state = F_WALK; m->timer = walk_time[random() & 3]; m->t = 0; }
                break;
            case F_WALK:
                if (!--m->timer) { m->state = F_AIM; m->timer = 16; break; }
                m->x += dirmul(m->dir, FISH_VX + LOOP_VX); m->t++;
                if (!solid_at(m->x >> 8, (m->y >> 8) + 16)) { m->vy = 0; m->state = F_JUMP; }
                break;
            case F_AIM:
                if (!--m->timer)
                {
                    Monster *f = monster_new(M_FIRE, 2);
                    if (f) { f->x = m->x; f->y = m->y - (8 << 8); f->dir = m->dir; f->vx = dirmul(m->dir, FIRE_VX + LOOP_VX); }
                    m->state = F_SHOT; m->timer = 16;
                }
                break;
            case F_SHOT:                                        // then turns to Simon and walks again
                if (!--m->timer)
                {
                    m->dir = simon_x + 8 >= cx ? 1 : -1;
                    m->state = F_WALK; m->timer = walk_time[random() & 3]; m->t = 0;
                }
                break;
            }
            break;
        }
        }
        s16 cx = m->x >> 8, cy = m->y >> 8, sx = cx - cam_x;
        if (m->kind == M_DRAGON) { tough_hits(m); continue; }
        if (m->kind == M_IGOR) { igor_hits(m); continue; }
        if (m->kind == M_VERT)                                  // can't be hit ($E46A: 1 x 2 px)
        {
            if (overlap(simon_x + 2, simon_y, 12, FEET, cx - 1, cy - 2, 2, 4)) simon_hurt(cx);
            continue;
        }
        // Red skeletons remain visible in the MD's side margins. Keep their
        // slot until the complete 16 px body leaves the physical viewport.
        s16 margin = m->kind == M_RSKEL ? NES_X + 8 : 0;
        if (sx < -margin || sx > 256 + margin || cy < -8 || cy > 248 || ((m->kind == M_BAT || m->kind == M_MEDUSA) && ((m->dir < 0 && sx < 8) || (m->dir > 0 && sx > 248))))
        { m->kind = M_FREE; continue; }
        if (m->kind == M_DROP || m->kind == M_DBIT) continue;     // Dracula's pieces don't hurt (checked)
        if (m->kind == M_KNIGHT || m->kind == M_GHOST || m->kind == M_PILLAR || m->kind == M_GBAT) { tough_hits(m); continue; }
        if (m->kind == M_FLEA && m->state == FL_HIDDEN) continue;
        if (m->kind == M_MUMMY) { mummy_hits(m); continue; }
        if (m->kind == M_RSKEL) { rskel_hits(m); continue; }
        if (m->kind == M_AXEK) { axek_hits(m); continue; }

        s16 hw = monster_hw(m), hh = monster_hh(m);

        if (attacks && (whip_strikes(cx, cy, hw, hh) || shot_strikes(cx, cy, hw, hh)))
        {
            u16 points = m->kind == M_BAT ? BAT_SCORE : m->kind == M_FISH ? FISH_SCORE : m->kind == M_RBAT ? RBAT_SCORE
                         : m->kind == M_MEDUSA ? MEDUSA_SCORE : m->kind == M_SNAKE ? SNAKE_SCORE : m->kind == M_FLEA ? FLEA_SCORE
                         : m->kind == M_RAVEN ? RAVEN_SCORE : m->kind == M_SKEL ? SKEL_SCORE : m->kind == M_BONE ? BONE_SCORE
                         : m->kind == M_BANDAGE ? BANDAGE_SCORE : m->kind == M_EAGLE ? EAGLE_SCORE : m->kind == M_KAXE ? KAXE_SCORE : m->kind == M_SICKLE ? SICKLE_SCORE : FIRE_SCORE;
            drop_spawn(cx, cy, m->kind == M_BAT ? 0x02 : m->kind == M_FISH ? 0x03 : m->kind == M_RBAT ? 0x07
                       : m->kind == M_MEDUSA ? 0x06 : m->kind == M_SNAKE ? 0x09 : m->kind == M_FLEA ? 0x0C : m->kind == M_RAVEN ? 0x0F
                       : m->kind == M_SKEL ? 0x10 : m->kind == M_BONE ? 0x24 : m->kind == M_BANDAGE ? 0x22 : m->kind == M_EAGLE ? 0x12 : m->kind == M_KAXE ? 0x27 : m->kind == M_SICKLE ? 0x0B : 0x25);
            m->kind = M_FREE;
            score += points; hud_update();
            continue;
        }
        if (overlap(simon_x + 2, simon_y, 12, FEET, cx - hw, cy - hh, 2 * hw, 2 * hh))
        {
            bool hurt = !invuln && !potion_t && state != ST_DEAD;
            simon_hurt(cx);
            if (hurt && (m->kind == M_BAT || m->kind == M_RBAT)) monster_kill(m, 0);   // a bat dies on Simon, without points
        }
    }
}

static void monsters_draw(void)
{
    static const u8 bat_seq[4] = { 0, 1, 2, 1 };
    // Exact original (u8 t / BONE_ANIM) % 3, including t's wrap at 256.
    // Avoid division and modulo for every visible bone on every frame.
    static const u8 bone_pose[256] = {
        0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1,
    };
    for (u8 i = 0; i < MAX_MONSTERS; i++)
    {
        Monster *m = &monsters[i];
        s16 x = m->x >> 8, y = m->y >> 8;
        switch (m->kind)
        {
        case M_BAT:   draw_object(&obj_poses[OBJ_BAT0 + bat_seq[(m->t / 9) & 3]], x - 8, y - 8, m->dir > 0); break;
        case M_FIRE:  draw_object(&obj_poses[OBJ_FIRE + (m->dir < 0)], x - 4, y - 8, FALSE); break;
        case M_DROP:  draw_object(&obj_poses[OBJ_DROP], x - 4, y - 8, FALSE); break;
        case M_DBIT:  draw_object(&world_poses[B7_DRAC_BIT], x - 8, y, m->dir > 0); break;
        case M_DYING: draw_object(&obj_poses[OBJ_SPARKLE], x - 4, y - 8, FALSE); break;
        case M_RBAT:
        {
            static const u8 rbat_seq[4] = { 0, 1, 2, 1 };
            u8 pose = m->state == RB_SLEEP ? B2_RBAT_SLEEP : B2_RBAT0 + rbat_seq[(m->t / 9) & 3];
            draw_object(&world_poses[pose], x - 8, y - 8, m->dir > 0);
            break;
        }
        case M_SNAKE:  draw_object(&world_poses[B2_SNAKE0 + ((m->t / SNAKE_ANIM) & 1)], x - 8, y - 10, m->dir > 0); break;
        case M_GHOST:  draw_object(&world_poses[B2_GHOST0 + ((m->t / GHOST_ANIM) & 1)], x - 8, y - 8, m->dir > 0); break;
        case M_PILLAR:
            draw_object(&world_poses[m->state == PL_FLASH && (frame_count & 1) ? B2_PILLAR_FLASH : B2_PILLAR], x - 8, y - 16, m->dir > 0);
            break;
        case M_MEDUSA: draw_object(&world_poses[B2_MEDUSA0 + ((m->t / MEDUSA_ANIM) & 1)], x - 8, y - 8, m->dir > 0); break;
        case M_FLEA:
            if (m->state == FL_CARRIED)
                draw_object(&world_poses[(m->t / 9) & 1 ? B3_FLEA_JUMP : B3_FLEA_STAND], x - 8, y - 8, m->dir > 0);
            else if (m->state != FL_HIDDEN)
                draw_object(&world_poses[m->state == FL_WAIT ? B3_FLEA_STAND : B3_FLEA_JUMP], x - 8, y - 8, m->dir > 0);
            break;
        case M_DRAGON: draw_object(&world_poses[B4_DRAGON0 + m->pad[8]], x - 8, y - 8, FALSE); break;
        case M_VERT:   draw_object(&world_poses[B4_VERT], x - 8, y - 8, FALSE); break;
        case M_EAGLE:  draw_object(&world_poses[B4_EAGLE0 + ((m->t / EAGLE_ANIM) & 1)], x - 8, y - 16, m->dir > 0); break;
        case M_RAVEN:
        {
            static const u8 raven_seq[4] = { 0, 1, 2, 1 };
            u8 pose = m->state == RV_PERCH ? B3_RAVEN_PERCH : B3_RAVEN0 + raven_seq[(m->t / RAVEN_ANIM) & 3];
            draw_object(&world_poses[pose], x - 8, y - 8, m->dir > 0);
            break;
        }
        case M_SKEL:   draw_object(&world_poses[B3_SKEL0 + ((m->t / SKEL_ANIM) & 1)], x - 8, y - 16, m->dir > 0); break;
        case M_BONE:   draw_object(&world_poses[B3_BONE0 + bone_pose[m->t]], x - 8, y - 8, m->dir < 0); break;
        case M_MUMMY:
        {
            static const u8 mummy_seq[4] = { 0, 1, 2, 1 };
            u8 pose = (m->state == MU_AIM && (frame_count & 2) ? B3_MUMMYF0 : B3_MUMMY0) + mummy_seq[(m->t / MUMMY_ANIM) & 3];
            draw_object(&world_poses[pose], x - 8, y - 24, m->dir > 0);
            break;
        }
        case M_BANDAGE: draw_object(&world_poses[B3_BANDAGE], x - 8, y - 8, m->dir > 0); break;
        case M_GBAT:   draw_object(&world_poses[B6_GBAT0 + ((m->t / GBAT_ANIM) & 1)], x - 8, y - 8, FALSE); break;
        case M_IGOR:
        {
            if (m->immune & 1) break;                           // blinks after a hit
            u8 pose = m->state == IG_CARRIED ? ((m->t / 9) & 1 ? B3_FLEA_JUMP : B3_FLEA_STAND)
                      : m->state == IG_RISE ? B3_FLEA_JUMP : m->state == IG_FALL ? B4_IGOR_FALL : B3_FLEA_STAND;
            draw_object(&world_poses[pose], x - 8, y - 8, m->dir > 0);
            break;
        }
        case M_RSKEL:
        {
            s16 n = m->state == RS_DROP ? RSKEL_DROP - m->timer : m->state == RS_RISE ? RSKEL_RISE - m->timer : 0;
            u8 pose = m->state == RS_HIDDEN ? 0 : m->state == RS_LIE || (m->state == RS_RISE && n < RSKEL_RISE_LOW) ? B5_RSK_DOWN
                      : m->state == RS_RISE ? B5_RSK_FALL1 : m->state == RS_DROP ? (n < 16 ? (m->dir > 0 ? B5_RSK_FALL0R : B5_RSK_FALL0)
                      : n < 25 ? B5_RSK_FALL1 : B5_RSK_DOWN) : B5_RSK0 + ((m->t / RSKEL_ANIM) & 1);
            if (pose) draw_object(&world_poses[pose], x - 8, y - 16, m->dir > 0 && pose != B5_RSK_FALL0R);
            break;
        }
        case M_AXEK:   draw_object(&world_poses[B5_AXEK0 + ((m->t / AXEK_ANIM) & 1)], x - 8, y - 16, m->dir > 0); break;
        case M_SICKLE:
            if (m->state != SC_APPEAR || (frame_count & 1))     // blinks while it appears
                draw_object(&world_poses[B5_SICKLE0 + ((m->t / SICKLE_ANIM) & 3)], x - 8, y - 8, m->dir < 0);
            break;
        case M_KAXE:   draw_object(&world_poses[B5_KAXE0 + ((m->t / KAXE_ANIM) & 3)], x - 8, y - 8, (s8)m->pad[1] > 0); break;
        case M_KNIGHT: draw_object(&world_poses[B2_KNIGHT0 + ((m->t / KNIGHT_ANIM) & 3)], x - 8, y - 16, m->dir > 0); break;
        case M_FISH:
        {
            u8 pose = m->state >= F_AIM ? 2 : m->state == F_WALK ? (m->t / 25) & 1 : 0;
            draw_object(&obj_poses[OBJ_FISH0 + pose], x - 8, y - 16, m->dir > 0);
            break;
        }
        }
    }
}

// ---------------------------------------------------------------- stage 3: the boss, its orb and the end of the block

// The phantom bat sleeps at the end of stage 3. It wakes when the screen reaches the end of the stage, which then
// stays there, and works in that screen's coordinates (x 0 to 255, centre in 8.8 fixed point), like the NES game.
// Speeds are magnitudes, left / up give the directions, except the swoop's vy which goes from down to up.
enum { B_SLEEP, B_WAKE, B_GLIDE, B_HOVER, B_DODGE, B_SWOOP, B_REST, B_RISE, B_FLOAT, B_PAUSE, B_DFALL, B_DREST, B_DJUMP,
       B_FLAMES, B_ORB, B_TALLY };
// Death's states follow B_WAKE: B_DFALL, B_DREST, B_DJUMP
// Medusa's states follow B_WAKE: B_RISE, B_FLOAT, B_PAUSE
typedef struct { s32 x, y; s16 vx, vy, cy; bool left, up, spawned, medusa, mummies, frank, death, walk_left; u8 state, tx, immune, anim, turn; u16 timer;
                 bool dracula, head_fly; u8 ds, pose; s32 hx, hy; s16 hvx, hvy; } Boss;    // ds: Dracula's state, h: his flying head
static Boss boss;
static u8 tally_phase;
// Dracula's states (the NES game's 0 to 14, then the monster's 0 to 10)
enum { DC_WAIT, DC_HEAD, DC_RISE, DC_STAND, DC_SHOW, DC_POSE, DC_OPEN, DC_FIRED, DC_FADE, DC_GONE, DC_BACK, DC_HEADLESS,
       DC_BREAK, DC_HIDDEN, DC_MSTAND, DC_MWAIT, DC_CROUCH, DC_JUMP, DC_LAND, DC_MRISE, DC_AIM, DC_SPIT, DC_SPAT };
static void drac_behead(void);


static void restart_level(void);
static void ending_scene(void);
static void castle_map_scene(u8 next_stage);
static void game_setup(void);

static bool boss_tally(void) { return boss.state == B_TALLY; }

static void boss_init(void)
{
    boss.state = B_SLEEP; boss.spawned = FALSE; boss.immune = 0; boss.anim = 0; boss.left = FALSE;
    boss.medusa = loaded_block == 2; boss.mummies = loaded_block == 3; boss.frank = loaded_block == 4; boss.death = loaded_block == 5;
    boss.dracula = loaded_block == 7; boss.head_fly = FALSE;
    boss_sec = boss.medusa ? SEC_ST6B : boss.mummies ? SEC_ST9 : boss.frank ? SEC_ST12 : boss.death ? SEC_ST15B : boss.dracula ? SEC_ST18B : SEC_ST3;
    boss_cam = boss.medusa || boss.death || boss.dracula ? sections[boss_sec].cam0 : sections[boss_sec].cam1;
    statue_gone = FALSE;
    if (boss.medusa) { boss.x = (s32)MEDUSA_BX << 8; boss.y = (s32)MEDUSA_BY << 8; }
    else if (boss.frank) { boss.x = (s32)FRANK_X << 8; boss.y = (s32)FRANK_Y << 8; }
    else if (boss.death) { boss.x = (s32)DEATH_X << 8; boss.y = (s32)DEATH_Y << 8; }
    else if (boss.dracula) { boss.x = (s32)DRAC_X << 8; boss.y = (s32)DRAC_Y0 << 8; }
    else { boss.x = (s32)(BOSS_X - 512) << 8; boss.y = (s32)BOSS_Y << 8; }
    boss_hp = BOSS_HP; shown_boss = BOSS_HP >> 8; screen_locked = FALSE;
#ifdef BOSS_TEST_HP                                /* make EXTRA_FLAGS=-DBOSS_TEST_HP=6: testing aid, a weak boss */
    boss_hp = BOSS_TEST_HP << 8;
#endif
}

// the NES game's $EEBB: the directions from (x, y) to (tx, ty) and the ratio of the smaller distance to the larger
// one in 8.8 ($CA41); returns TRUE when the vertical distance is the larger
static bool boss_aim(s16 x, s16 y, s16 tx, s16 ty, bool *left, bool *up, u16 *ratio)
{
    s16 dx = tx - x, dy = ty - y;
    *left = dx < 0; *up = dy < 0;
    dx = abs(dx); dy = abs(dy);
    if (!dx) dx = 1;
    if (!dy) dy = 1;
    if (dx >= dy) { *ratio = ((u16)dy << 8) / (u16)dx; return FALSE; }
    *ratio = ((u16)dx << 8) / (u16)dy; return TRUE;
}

static s16 simon_sx(void) { return simon_x + 8 - BOSS_CAM; }

// $80FD: glide at 0.75 px/frame to 0x48 px beside Simon (a side at random, the other one near the screen's edges),
// 0x28 px above him
static void boss_target(void)
{
    u8 side = frame_count & 1, tx = 0;
    for (u8 k = 0; k < 2; k++, side ^= 1)                       // 8-bit sums, like the NES game's
    {
        tx = side ? (u8)(simon_sx() - 0x49) : (u8)(simon_sx() + 0x48);
        if (tx >= 0x10 && tx < 0xF0) break;
    }
    boss.tx = tx;
    u16 ratio;
    bool major_y = boss_aim(boss.x >> 8, boss.y >> 8, tx, (u8)(simon_y + 16 - 0x28), &boss.left, &boss.up, &ratio);
    u16 minor = ratio - (ratio >> 2);
    boss.vx = major_y ? minor : 0xC0;
    boss.vy = major_y ? 0xC0 : minor;
    boss.state = B_GLIDE;
}

// $EC88: a fireball at Simon from (x, y) in the world (8.8), 1.5 px/frame along the larger distance
static void fire_at(s32 x, s32 y)
{
    Monster *f = monster_new(M_FIRE, 2);
    if (!f) return;
    bool left, up;
    u16 ratio;
    bool major_y = boss_aim(x >> 8, y >> 8, simon_x + 8, simon_y + 16, &left, &up, &ratio);
    s16 minor = ratio + (ratio >> 1);
    s16 vx = major_y ? minor : 0x180, vy = major_y ? 0x180 : minor;
    f->x = x; f->y = y;
    f->vx = left ? -vx : vx; f->vy = up ? vy : -vy; f->dir = left ? -1 : 1;
}

static void boss_fire(void) { fire_at(((s32)BOSS_CAM << 8) + boss.x, boss.y); }

// $81DE: swoop at 0x18 px below Simon (2 px/frame across or 1.5 px/frame down along the larger distance), or a
// fireball when he is higher than the bat
static void boss_swoop(void)
{
    s16 scy = simon_y + 16;
    if (scy < (boss.y >> 8)) { boss_fire(); boss.state = B_REST; boss.timer = 0x18; return; }
    u16 ratio;
    bool major_y = boss_aim(boss.x >> 8, boss.y >> 8, simon_sx(), scy + 0x18, &boss.left, &boss.up, &ratio);
    ratio <<= 1;
    boss.vx = major_y ? ratio : 0x200;
    boss.vy = major_y ? 0x180 : ratio;
    boss.state = B_SWOOP;
}

static void boss_damage(s16 d)
{
    if (boss.medusa || boss.frank || boss.death) d >>= 1;       // Medusa, Frankenstein and Death take half ($E271)
    else if (boss.dracula) d >>= boss.ds >= DC_BREAK ? 2 : 1;   // Dracula half, the monster a quarter ($E33F)
    if (difficulty == DIFF_EASY) d += d & 0xFF00;               // the SNES port doubles the whole pixels on easy
    boss_hp -= d;
    if (boss_hp <= 0)
    {
        boss_hp = 0;
        if (boss.dracula && boss.ds < DC_BREAK) { drac_behead(); hud_update(); return; }
        if (boss.dracula) boss.y += 8 << 8;                     // $E37B
        boss.state = B_FLAMES; boss.timer = 0;
        score += boss.frank ? FRANK_SCORE : boss.death ? DEATH_SCORE : boss.dracula ? DRAC_SCORE : BOSS_SCORE;
        if (boss.death)                                         // sickles belong to this boss: vanish on the fatal hit
            for (u8 i = 0; i < MAX_MONSTERS; i++)
                if (monsters[i].kind == M_SICKLE) monsters[i].kind = M_FREE;
        if (boss.frank)                                         // Igor goes up in flames with it
            for (u8 i = 0; i < MAX_MONSTERS; i++) if (monsters[i].kind == M_IGOR) monster_kill(&monsters[i], 0);
    }
    hud_update();
}

// whip and sub-weapons: a hit, then BOSS_IMMUNE frames without; each thrown weapon hits once, holy water burns
static void boss_hits_at(s16 cx, s16 cy, s16 hw, s16 hh, bool touch);
static void boss_hits(void)
{
    s16 hw = boss.medusa ? MEDUSA_HW : boss.frank ? FRANK_HW : boss.death ? DEATH_HW : BOSS_HW;
    s16 hh = boss.medusa ? MEDUSA_HH : boss.frank ? FRANK_HH : boss.death ? DEATH_HH : BOSS_HH;
    if (boss.death && boss.state < B_DFALL) return;             // out of sight and out of reach until it sinks
    if (boss.immune) boss.immune--;
    boss_hits_at(BOSS_CAM + (boss.x >> 8), boss.y >> 8, hw, hh, TRUE);
}

// the hits on a box centred on (cx, cy) in the world; touch: it hurts Simon
static void boss_hits_at(s16 cx, s16 cy, s16 hw, s16 hh, bool touch)
{
    if (!boss.immune && whip_strikes(cx, cy, hw, hh))
    { whip_impact(cx, cy, hw, hh); boss.immune = BOSS_IMMUNE; boss_damage((whip_level ? 8 : 6) << 8); }
    for (u8 i = 0; i < MAX_SHOTS && boss.state < B_FLAMES; i++)
    {
        Shot *s = &shots[i];
        if (s->state == W_FREE) continue;
        s16 dx = (s16)(s->x >> 8) - cx, dy = (s16)(s->y >> 8) - cy;
        if (abs(dx) >= 8 + hw || abs(dy) >= (s->kind == SUB_DAGGER ? 6 : 8) + hh) continue;
        if (s->state == W_BURN) { if (!(frame_count & 3)) boss_damage(BOSS_HOLY); continue; }
        if (s->kind == SUB_HOLY || s->hit_boss || boss.immune) continue;
        impact_spawn(cx, cy, hw, hh, s->x >> 8, s->y >> 8);
        s->hit_boss = TRUE; boss.immune = BOSS_IMMUNE;
        if (hit_counter < 255) hit_counter++;
        if (s->kind == SUB_DAGGER) s->state = W_FREE;
        sfx_play(SFX_14);
        boss_damage((s->kind == SUB_DAGGER ? 6 : 8) << 8);
    }
    if (touch && boss.state < B_FLAMES
        && overlap(simon_x + 2, simon_y, 12, FEET, cx - hw, cy - hh, 2 * hw, 2 * hh))
        simon_hurt(cx);
}

// ---------------------------------------------------------------- stage 9: the mummies

static void mummy_walk(Monster *m)
{
    static const u8 walk_time[4] = { 0x7B, 0x41, 0xB4, 0x20 };
    m->dir = face_simon(m->x >> 8);
    m->timer = walk_time[++m->hp & 3];                          // hp: its turn in the table
    m->state = MU_WALK;
}

static void mummy_update(Monster *m)
{
    if (m->immune) { m->immune--; return; }                    // still after a hit
    s16 cx = m->x >> 8;
    switch (m->state)
    {
    case MU_WAIT:
        if (boss.state == B_SLEEP) return;
        m->hp = (m - monsters + frame_count) & 3; m->timer = MUMMY_WAKE; m->state = MU_STAND;
        return;
    case MU_STAND:
    case MU_THROWN:
        if (!--m->timer) mummy_walk(m);
        break;
    case MU_WALK:
        if (!--m->timer) { m->dir = face_simon(cx); m->timer = MUMMY_AIM; m->state = MU_AIM; break; }
        if (!(frame_count & 0x1F))
        {
            m->dir = face_simon(cx);
            if (facing_left == (m->dir > 0) && abs(simon_x + 8 - cx) < MUMMY_NEAR) m->dir = -m->dir;
        }
        m->x += dirmul(m->dir, MUMMY_VX + LOOP_VX);
        {
            s16 sx = (m->x >> 8) - BOSS_CAM;
            if (m->dir < 0 && sx < 9) m->x = (s32)(BOSS_CAM + 8) << 8 | (m->x & 0xFF);
            else if (m->dir > 0 && sx >= 0xF8) m->x = (s32)(BOSS_CAM + 0xF8) << 8 | (m->x & 0xFF);
        }
        break;
    case MU_AIM:
        if (--m->timer) break;
        {
            Monster *b = monster_new(M_BANDAGE, 5);
            if (b)
            {
                b->x = m->x; b->y = m->y + ((frame_count & 1) ? -(8 << 8) : 8 << 8); b->cy = b->y >> 8;
                b->vx = BANDAGE_V; b->vy = BANDAGE_V; b->dir = m->dir;
                sfx_play(SFX_13);
            }
        }
        m->timer = MUMMY_THROWN; m->state = MU_THROWN;
        break;
    }
    m->t++;
}

// the hits of a mummy; FALSE when it died
static bool mummy_hits(Monster *m)
{
    u8 idx = m - monsters + 1;
    s16 cx = m->x >> 8, cy = m->y >> 8, hw = 8, hh = 22;        // its box ($E46A)
    s16 dmg = 0;
    if (!m->immune && whip_strikes(cx, cy, hw, hh))
    { whip_impact(cx, cy, hw, hh); dmg = (whip_level ? 8 : 6) << 8; }
    for (u8 i = 0; i < MAX_SHOTS; i++)
    {
        Shot *s = &shots[i];
        if (s->state == W_FREE) continue;
        s16 dx = (s16)(s->x >> 8) - cx, dy = (s16)(s->y >> 8) - cy;
        if (abs(dx) >= 8 + hw || abs(dy) >= (s->kind == SUB_DAGGER ? 6 : 8) + hh) continue;
        if (s->state == W_BURN) { if (!(frame_count & 3)) dmg += BOSS_HOLY; continue; }
        if (s->kind == SUB_HOLY || m->immune || s->last == idx) continue;
        impact_spawn(cx, cy, hw, hh, s->x >> 8, s->y >> 8);
        if (hit_counter < 255) hit_counter++;
        sfx_play(SFX_14);
        if (s->kind == SUB_DAGGER) { s->state = W_FREE; dmg += 6 << 8; } else { s->last = idx; dmg += 8 << 8; }
    }
    if (dmg)
    {
        dmg >>= 2;
        if (difficulty == DIFF_EASY) dmg += dmg & 0xFF00;       // as boss_damage
        m->cy -= dmg;
        m->immune = BOSS_IMMUNE;
        s16 sum = 0;
        bool other = FALSE;
        for (u8 k = 0; k < MAX_MONSTERS; k++)
            if (monsters[k].kind == M_MUMMY)
            {
                if (monsters[k].cy > 0) sum += monsters[k].cy;
                if (&monsters[k] != m) other = TRUE;
            }
        boss_hp = sum;
        if (m->cy <= 0)
        {
            score += BOSS_SCORE;
            if (other) { m->kind = M_DYING; m->t = 0; }
            else
            {
                boss.x = (s32)(cx - BOSS_CAM) << 8; boss.y = (s32)cy << 8;
                boss.state = B_FLAMES; boss.timer = 0;
                m->kind = M_FREE;
            }
            hud_update();
            return FALSE;
        }
        hud_update();
    }
    if (overlap(simon_x + 2, simon_y, 12, FEET, cx - hw, cy - hh, 2 * hw, 2 * hh)) simon_hurt(cx);
    return TRUE;
}

// End of the block (NES state $18 = 12): 225 frames, then TIME goes into the score (10 points a unit, one unit a
// frame), 58 frames, the hearts (100 points each, one every 8 frames), 120 frames, then the next block
static void tally_update(void)
{
    if (boss.timer) { boss.timer--; return; }
    switch (tally_phase)
    {
    case 0: tally_phase = 1; break;
    case 1:
        if (time_left) { time_left--; score += 10; hud_update(); if (!(frame_count & 7)) sfx_play(SFX_03); break; }
        tally_phase = 2; boss.timer = 57;
        break;
    case 2:
        if (hearts) { hearts--; score += 100; hud_update(); boss.timer = 7; sfx_play(SFX_04); break; }
        tally_phase = 3; boss.timer = 119;
        break;
    case 3:                                                     // the next block: full health, 5 hearts, the sub-weapon
                                                                // kept
    {
        u8 sub = subweapon, sub2 = other_sub, lv = shot_level, lv2 = other_level;
        section = loaded_block == 1 ? SEC_ST4 : loaded_block == 2 ? SEC_ST7 : loaded_block == 3 ? SEC_ST10
                : loaded_block == 4 ? SEC_ST13 : loaded_block == 7 ? SEC_COURT : SEC_ST16;
        if (loaded_block == 7)                                  // after Dracula: the ending, then the second loop
        {
            second_loop = TRUE;
            ending_scene();
            game_setup();
        }
        else
        {
            castle_map_scene(sections[section].stage);
            game_setup();                                    // restore gameplay tiles, window, palette and camera
        }
        subweapon = sub; other_sub = sub2; shot_level = lv; other_level = lv2;
        hud_update();
        break;
    }
    }
}

// $FAB4: the statue's tiles go blank when Medusa wakes
static void statue_erase(void)
{
    statue_gone = TRUE;
    for (u8 c = 0; c < 4; c++)
    {
        s16 col = (BOSS_CAM >> 3) + STATUE_COL + c;
        u16 slot = col & (PLANE_COLS - 1);
        if (slot_col[slot] != col) continue;
        for (u8 r = 0; r < 4; r++) VDP_setTileMapXY(BG_A, map_base, slot, STATUE_ROW + r);
    }
}

// $89E2: Frankenstein walks to and fro at 0.75 px/frame for a random time, away from Simon when he is near, else
// towards him; it faces him all the time (boss.left) and stands still while a hit stuns it
static void frank_walk(void)
{
    static const u8 walk_time[4] = { 60, 36, 84, 24 };
    boss.walk_left = abs(simon_sx() - (s16)(boss.x >> 8)) < FRANK_NEAR ? !boss.left : boss.left;
    boss.timer = walk_time[random() & 3];
    boss.state = B_HOVER;
}

static void frank_update(void)
{
    if (boss.immune) return;
    boss.left = simon_sx() < (boss.x >> 8);                     // $EF7C
    switch (boss.state)
    {
    case B_WAKE:
        if (!--boss.timer) { boss.state = B_GLIDE; boss.timer = FRANK_CARRY; }
        break;
    case B_GLIDE:                                               // Igor on its head
    {
        Monster *ig = NULL;
        for (u8 i = 0; i < MAX_MONSTERS; i++) if (monsters[i].kind == M_IGOR) ig = &monsters[i];
        if (!--boss.timer) { if (ig && ig->state == IG_CARRIED) ig->state = IG_RISE; frank_walk(); break; }
        if (ig && ig->state == IG_CARRIED) ig->x = ((s32)BOSS_CAM << 8) + boss.x;
        boss.x += boss.left ? -(FRANK_V + LOOP_VX) : FRANK_V + LOOP_VX;
        break;
    }
    case B_HOVER:
        if (!--boss.timer) { frank_walk(); break; }
        boss.x += boss.walk_left ? -(FRANK_V + LOOP_VX) : FRANK_V + LOOP_VX;
        if ((boss.x >> 8) < 0x10 || (boss.x >> 8) >= 0xF0) boss.walk_left = !boss.walk_left;
        break;
    }
}

// ---------------------------------------------------------------- stage 15: Death and its sickles

static u8 death_rest(void) { static const u8 rest[4] = { 0x90, 0x5F, 0xB9, 0x54 }; return rest[random() & 3]; }

// $905B: the sickles, in the NES game's slots 13 down to 10 (pad[0] 3 to 0); FALSE when its slip leaves Death in its
// state: if the slots run out after one or more sickles, the last one gets Death's rest instead (it waits, then aims)
static bool death_sickles(void)
{
    static const u8 sdx[4] = { 0x04, 0x30, 0xA0, 0x20 }, sdy[4] = { 0xD0, 0x18, 0xB0, 0xE0 };
    u8 n = second_loop ? 4 : 3;
    Monster *last = NULL;
    for (s8 slot = 3; slot >= 0; slot--)
    {
        bool used = FALSE;
        for (u8 i = 0; i < MAX_MONSTERS; i++) if (monsters[i].kind == M_SICKLE && monsters[i].pad[0] == slot) used = TRUE;
        if (used) continue;
        Monster *sk = monster_new(M_SICKLE, MAX_MONSTERS);
        if (!sk) break;
        u16 x = (u8)simon_sx() + sdx[n - 1] + (slot != 3);     // the carry of the NES game's slot test, then of x
        u16 y = (u8)(simon_y + 16) + sdy[n - 1] + (x >> 8);
        sk->x = (s32)(BOSS_CAM + (x & 0xFF)) << 8; sk->y = (s32)(y & 0xFF) << 8;
        sk->pad[0] = slot; sk->state = SC_APPEAR; sk->timer = 256; sk->dir = 1; sk->gen = 0xFF;
        if (last) last->timer = SICKLE_APPEAR;                  // set while placing the next one
        last = sk;
        if (!--n) return TRUE;
    }
    if (last) { last->state = SC_STOP; last->timer = death_rest(); return FALSE; }
    return TRUE;
}

static void death_land(void)                                    // $EFAF: on a multiple of 8
{
    boss.y = (s32)((boss.y >> 8) & ~7) << 8 | (boss.y & 0xFF);
    if (death_sickles()) { boss.state = B_DREST; boss.timer = death_rest(); }
}

static void death_update(void)
{
    if (boss.immune) return;
    boss.left = simon_sx() < (boss.x >> 8);                     // $EF7C
    switch (boss.state)
    {
    case B_WAKE:
        if (!--boss.timer) { boss.state = B_DFALL; boss.vy = DEATH_FALL_V; }
        return;
    case B_DFALL:                                               // $8EF1
        boss.vy -= DEATH_FALL_SLOW; boss.y += boss.vy;
        break;
    case B_DREST:                                               // $8F23
        if (!(frame_count & 31) && abs(simon_sx() - (s16)(boss.x >> 8)) < DEATH_NEAR)
        { boss.walk_left = boss.left; boss.vx = DEATH_LEAP_VX; boss.vy = DEATH_LEAP_VY; boss.state = B_DJUMP; }
        else if (!--boss.timer)
        { boss.vy = random() & 1 ? 0x200 : 0x100; boss.walk_left = frame_count & 1; boss.vx = DEATH_HOP_VX; boss.state = B_DJUMP; }
        return;
    case B_DJUMP:                                               // $8F80
        boss.x += boss.walk_left ? -boss.vx : boss.vx;
        if ((boss.x >> 8) >= 0xF0 || (boss.x >> 8) < 0x10)
        { boss.x = (s32)((boss.x >> 8) >= 0xF0 ? 0xF0 : 0x10) << 8 | (boss.x & 0xFF); boss.walk_left = !boss.walk_left; }
        boss.vy -= DEATH_GRAVITY; boss.y -= boss.vy;
        if ((boss.y >> 8) < 0x20) { boss.y = (s32)0x21 << 8 | (boss.y & 0xFF); boss.vy = 0; return; }
        break;
    }
    if (map_solid(BOSS_CAM + (boss.x >> 8), (boss.y >> 8) + DEATH_FEET)) death_land();
}

// ---------------------------------------------------------------- stage 18: Dracula

static u8 drac_rest(void) { static const u8 rest[4] = { 0x24, 0x10, 0x32, 0x18 }; return rest[random() & 3]; }   // $9624

// $99C3: 3 fireballs from (x, y) on the boss screen at Simon's centre 16 px lower, level and 16 px higher ($9A35),
// 2 px a frame along the larger distance
static void drac_fire(s16 x, s16 y)
{
    static const s8 dy[3] = { 0x10, 0, -0x10 };
    for (u8 k = 0; k < 3; k++)
    {
        Monster *f = monster_new(M_FIRE, 6);
        if (!f) return;
        bool left, up;
        u16 ratio;
        bool major_y = boss_aim(x, y, simon_sx(), simon_y + 16 + dy[k], &left, &up, &ratio);
        s16 vx = major_y ? ratio << 1 : 0x200, vy = major_y ? 0x200 : ratio << 1;
        f->x = (s32)(BOSS_CAM + x) << 8; f->y = (s32)y << 8;
        f->vx = left ? -vx : vx; f->vy = up ? vy : -vy; f->dir = left ? -1 : 1;
    }
}

// his head (object type 4): 5 px left of his centre facing left, 6 right facing right, 26 above; the monster's head
// box: 8 px to the side it faces, 32 above ($97A1)
static s16 drac_head_x(void) { return (boss.x >> 8) + (boss.ds >= DC_BREAK ? (boss.left ? -8 : 8) : boss.left ? -5 : 6); }
static s16 drac_head_y(void) { return (boss.y >> 8) - (boss.ds >= DC_BREAK ? 0x20 : 26); }

// $96EA: the head flies off the other way (2 px a frame across, 5 up slowing by 0x21/256 a frame; type 0x35), the
// body stands 120 frames
static void drac_behead(void)
{
    boss.hx = (s32)drac_head_x() << 8; boss.hy = (s32)drac_head_y() << 8;
    boss.hvx = boss.left ? 0x200 : -0x200; boss.hvy = 0x500; boss.head_fly = TRUE;
    boss.pose = B7_DRAC_OPEN; boss.ds = DC_HEADLESS; boss.timer = 0x78;
}

static void drac_crouch(void) { boss.pose = B7_MON_CROUCH; boss.timer = 16; boss.ds = DC_CROUCH; }
static void drac_mwait(void) { boss.timer = frame_count & 1 ? 0x7B : 0x55; boss.ds = DC_MWAIT; }      // $97C7
static void drac_mstand(void) { boss.pose = B7_MON; boss.y = (s32)DRAC_Y << 8; boss.timer = 0x21; boss.ds = DC_MSTAND; }

static void drac_update(void)
{
    if (boss.head_fly)
    {
        boss.hx += boss.hvx; boss.hvy -= 0x21; boss.hy -= boss.hvy;
        if ((boss.hx >> 8) >= 250 || (boss.hx >> 8) < 6) boss.head_fly = FALSE;
    }
    if (boss.ds != DC_HEADLESS) boss.left = simon_sx() < (boss.x >> 8);       // $EF7C
    if (boss.immune) return;                                    // stunned by a hit ($EEA7)
    switch (boss.ds)
    {
    case DC_WAIT:  if (!--boss.timer) { boss.ds = DC_HEAD; boss.timer = 0x3C; } break;
    case DC_HEAD:  if (!--boss.timer) boss.ds = DC_RISE; break;
    case DC_RISE:
        boss.y -= DRAC_RISE;
        if ((boss.y >> 8) < DRAC_Y) { boss.y = (s32)DRAC_Y << 8; boss.ds = DC_STAND; boss.timer = 0x3C; }
        break;
    case DC_STAND: if (!--boss.timer) { boss.ds = DC_SHOW; boss.timer = 0x45; boss.pose = B7_DRAC; } break;
    case DC_SHOW:
    case DC_BACK:  if (!--boss.timer) { boss.ds = DC_POSE; boss.timer = drac_rest(); boss.pose = B7_DRAC; } break;
    case DC_POSE:  if (!--boss.timer) { boss.ds = DC_OPEN; boss.timer = 16; boss.pose = B7_DRAC_OPEN; } break;
    case DC_OPEN:  if (!--boss.timer) { drac_fire(boss.x >> 8, boss.y >> 8); boss.ds = DC_FIRED; boss.timer = 0x20; } break;
    case DC_FIRED: if (!--boss.timer) { boss.ds = DC_FADE; boss.timer = 0x20; } break;
    case DC_FADE:  if (!--boss.timer) { boss.ds = DC_GONE; boss.timer = 0x4F; boss.pose = B7_DRAC; } break;
    case DC_GONE:                                               // $969D: back beside Simon, on the screen
        if (--boss.timer) break;
        {
            static const u8 dx[8] = { 0x10, 0xF8, 0x80, 0x60, 0x30, 0xD8, 0x60, 0xA8 };
            u8 k = frame_count, x;
            while ((x = (u8)(simon_sx() + dx[k & 7])) < 0x14 || x >= 0xEC) k++;
            boss.x = (s32)x << 8;
        }
        boss.ds = DC_BACK; boss.timer = 0x20;
        break;
    case DC_HEADLESS: if (!--boss.timer) { boss.ds = DC_BREAK; boss.timer = 0x20; } break;
    case DC_BREAK:                                              // $973F: the body bursts ($9945, table $999A)
        if (--boss.timer) break;
        music_play(MUS_BLACK_NIGHT);
        {
            static const s16 vx[6] = { 0x2D0, 0x400, 0x2D0, -0x2D0, -0x400, -0x2D0 }, vy[6] = { -0x2D0, 0, 0x2D0, -0x2D0, 0, 0x2D0 };
            for (u8 k = 0; k < 6; k++)
            {
                Monster *b = monster_new(M_DBIT, 6);
                if (!b) break;
                b->x = ((s32)BOSS_CAM << 8) + boss.x; b->y = boss.y;
                b->vx = vx[k]; b->vy = vy[k]; b->dir = vx[k] > 0 ? 1 : -1;
            }
        }
        boss.ds = DC_HIDDEN; boss.timer = 16;
        break;
    case DC_HIDDEN:
        if (--boss.timer) break;
        boss_hp = BOSS_HP;
#ifdef BOSS_TEST_HP
        boss_hp = BOSS_TEST_HP << 8;
#endif
        hud_update();
        drac_mstand();
        break;
    case DC_MSTAND: if (!--boss.timer) drac_mwait(); break;
    case DC_MWAIT:                                              // $97DB: every 16 frames, jumps if Simon faces it holding the whip button
        if (!(frame_count & 15) && facing_left != boss.left && (held_pad & BUTTON_A)) drac_crouch();
        else if (!--boss.timer) drac_crouch();
        break;
    case DC_CROUCH:
        if (--boss.timer) break;
        boss.pose = B7_MON_JUMP; boss.walk_left = boss.left;
        boss.vy = frame_count & 1 ? 0x600 : 0x480; boss.vx = 0xC0; boss.ds = DC_JUMP;
        break;
    case DC_JUMP:                                               // $9845, $991C
        boss.vy -= DRAC_GRAVITY; boss.y -= boss.vy;
        if ((boss.y >> 8) < 0x20) boss.vy = 0;
        boss.pose = (boss.y >> 8) >= 0x60 ? B7_MON_JUMP : B7_MON_HIGH;
        boss.x += boss.walk_left ? -(boss.vx + LOOP_VX) : boss.vx + LOOP_VX;
        if (boss.walk_left ? (boss.x >> 8) < 0x18 : (boss.x >> 8) >= 0xE8) boss.walk_left = !boss.walk_left;
        if (map_solid(BOSS_CAM + (boss.x >> 8), (boss.y >> 8) + 8))
        {
            boss.y = (s32)((boss.y >> 8) & ~7) << 8 | (boss.y & 0xFF);   // $EFAF
            boss.pose = B7_MON_LAND; boss.timer = 0x18; boss.ds = DC_LAND;
            sfx_play(SFX_1D);
        }
        break;
    case DC_LAND:
        if (--boss.timer) break;
        boss.pose = B7_MON; boss.y -= 16 << 8; boss.timer = 16; boss.ds = DC_MRISE;
        break;
    case DC_MRISE:                                              // $98B3: spits unless Simon is near
        if (--boss.timer) break;
        {
            u8 d = abs(simon_sx() - (s16)(boss.x >> 8));
            if (d < 0x30 || !(d & 3)) { drac_mwait(); break; }
        }
        boss.timer = frame_count & 1 ? 0x28 : 0x10; boss.ds = DC_AIM;
        break;
    case DC_AIM:   if (!--boss.timer) { boss.pose = B7_MON_SPIT; boss.timer = 16; boss.ds = DC_SPIT; } break;
    case DC_SPIT:
        if (--boss.timer) break;
        sfx_play(SFX_12);
        drac_fire(drac_head_x(), drac_head_y());
        boss.timer = 16; boss.ds = DC_SPAT;
        break;
    case DC_SPAT:  if (!--boss.timer) drac_mstand(); break;
    }
}

static bool drac_shown(void)
{
    switch (boss.ds)
    {
    case DC_SHOW: case DC_FADE: case DC_BACK: case DC_BREAK: return frame_count & 1;    // blinking
    case DC_POSE: case DC_OPEN: case DC_FIRED: case DC_HEADLESS: return TRUE;
    default: return boss.ds >= DC_MSTAND;
    }
}

// only the head takes hits ($E46A: 8 x 8), while he stands still ($E33F); his body (16 x 24, the monster's 24 x 24)
// hurts Simon
static void drac_hits(void)
{
    if (boss.immune) boss.immune--;
    bool p2 = boss.ds >= DC_BREAK;
    if (boss.ds == DC_POSE || boss.ds == DC_OPEN || boss.ds == DC_FIRED || boss.ds >= DC_MWAIT)
        boss_hits_at(BOSS_CAM + drac_head_x(), drac_head_y(), 8, 8, FALSE);
    s16 cx = BOSS_CAM + (boss.x >> 8), cy = boss.y >> 8, hw = p2 ? 24 : 16;
    if (boss.ds >= DC_MWAIT && boss.state < B_FLAMES && !(frame_count & 3))   // $E31B: burning holy water on the monster's
        for (u8 i = 0; i < MAX_SHOTS; i++)                                    // body, an eighth of the damage
        {
            Shot *s = &shots[i];
            if (s->state == W_BURN && abs((s16)(s->x >> 8) - cx) < 8 + 24 && abs((s16)(s->y >> 8) - cy) < 8 + 24)
            { boss_damage(BOSS_HOLY >> 1); break; }
        }
    if (boss.state < B_FLAMES && drac_shown() && overlap(simon_x + 2, simon_y, 12, FEET, cx - hw, cy - 24, 2 * hw, 48))
        simon_hurt(cx);
}

static void drac_draw(void)
{
    s16 x = BOSS_CAM + (boss.x >> 8), y = boss.y >> 8;
    if (boss.head_fly)
    {
        s16 hx = BOSS_CAM + (boss.hx >> 8), hy = boss.hy >> 8;
        if (boss.hvx > 0) draw_object(&world_poses[B7_DRAC_HEAD], hx - 16, hy + 31, TRUE);
        else draw_object(&world_poses[B7_DRAC_HEAD], hx, hy + 31, FALSE);
    }
    if (boss.ds >= DC_HEAD && boss.ds <= DC_BACK && (boss.ds <= DC_STAND || drac_shown()))
        draw_object(&world_poses[B7_DRAC_HEAD], x - 8, y, !boss.left);
    if (drac_shown()) draw_object(&world_poses[boss.pose], x - 8, y, !boss.left);
}

static void boss_update(void)
{
    if (section != boss_sec) return;
    if (boss.state == B_TALLY) { tally_update(); return; }
    if (boss.mummies && boss.state <= B_WAKE)                   // the mummies are objects of their own (mummy_update)
    {
        if (boss.state == B_SLEEP && cam_x >= BOSS_CAM)
        {
            boss.state = B_WAKE; boss.spawned = TRUE; screen_locked = TRUE; music_play(MUS_POISON_MIND);
            for (u8 i = 0; i < MAX_ENEMIES; i++) enemies[i].state = E_FREE;
            for (u8 i = 0; i < MAX_MONSTERS; i++) if (monsters[i].kind != M_MUMMY) monsters[i].kind = M_FREE;
        }
        return;
    }
    s16 bsx = BOSS_CAM + (boss.x >> 8) - cam_x;
    if (!boss.spawned && bsx >= 0 && bsx < 0xF9)               // on screen: the other enemies go ($F48D)
    {
        boss.spawned = TRUE;
        for (u8 i = 0; i < MAX_ENEMIES; i++) enemies[i].state = E_FREE;
        monsters_init();
        Monster *ig = boss.frank ? monster_new(M_IGOR, 1) : NULL;
        if (ig) { ig->x = ((s32)BOSS_CAM << 8) + boss.x; ig->y = boss.y - ((s32)IGOR_DY << 8); ig->immune = 0; ig->dir = -1; }
    }
    if (boss.state == B_SLEEP)
    {
        if (boss.frank && boss.spawned) { boss.anim++; boss.left = simon_sx() < (boss.x >> 8); }
        // leftwards, the screen stops at the boss's place; the camera may still be that of the room left by a stairway
        // (further left in the world), hence the equality
        if (boss.medusa || boss.death || boss.dracula ? cam_x == BOSS_CAM : cam_x >= BOSS_CAM)
        {
            boss.state = B_WAKE; boss.timer = boss.medusa ? MEDUSA_WAKE : 120; screen_locked = TRUE;
            if (boss.dracula) boss.ds = DC_WAIT;                // the stage's music goes on (checked)
            else music_play(MUS_POISON_MIND);
        }
        return;
    }
    if (boss.state == B_FLAMES) { if (++boss.timer >= (boss.dracula ? DRAC_FLAMES : 60)) { boss.state = B_ORB; boss.timer = 0; boss.x = 128 << 8; boss.y = 128 << 8; boss.vy = 0; } return; }
    if (boss.state == B_ORB)                                    // hidden 61 frames, blinks 32, then falls
    {
        if (boss.timer < 93) { boss.timer++; return; }
        if (!solid_at(BOSS_CAM + 128, (boss.y >> 8) + 8))
        {
            boss.vy += ORB_GRAVITY; boss.y += boss.vy;
            s16 bottom = (boss.y >> 8) + 8;
            if (solid_at(BOSS_CAM + 128, bottom)) boss.y = (s32)((bottom & ~7) - 8) << 8;
        }
        boss.anim++;
        if (state != ST_DEAD && overlap(simon_x + 2, simon_y, 12, FEET, BOSS_CAM + 120, (boss.y >> 8) - 8, 16, 16))
        {
            boss.state = B_TALLY; tally_phase = 0; boss.timer = 224;
            music_play(boss.dracula ? MUS_ALL_CLEAR : MUS_STAGE_CLEAR);
            player_hp = PLAYER_HP; hud_update();
        }
        return;
    }
    if (boss.dracula) { if (!watch_t) drac_update(); drac_hits(); return; }
    if (watch_t) { boss_hits(); return; }                       // the stopwatch holds it too
    // All these NES boss AIs begin with $EEA7: while the hit timer is nonzero,
    // it decrements that timer and skips movement, animation and AI timers.
    // Bat and Medusa previously only ignored new hits, but kept moving.
    if (boss.immune) { boss_hits(); return; }
    boss.anim++;
    if (boss.frank) { frank_update(); boss_hits(); return; }
    if (boss.death) { death_update(); boss_hits(); return; }
    switch (boss.state)
    {
    case B_WAKE:
        if (--boss.timer) break;
        if (!boss.medusa) { boss_target(); break; }
        statue_erase();
        boss.turn = frame_count & 3; boss.vy = MEDUSA_RISE; boss.state = B_RISE; boss.anim = 0;
        // fall through
    case B_RISE:                                                // $8304
    {
        boss.y -= boss.vy;
        if ((boss.y >> 8) >= MEDUSA_TOP) break;
        Monster *sn = monster_new(M_SNAKE, 6);                  // with the way she faced
        if (sn)
        {
            sn->x = ((s32)BOSS_CAM << 8) + boss.x; sn->y = boss.y; sn->dir = boss.left ? -1 : 1;
            sn->state = SN_FALL; sn->vy = 0;
        }
        static const u8 float_time[4] = { 16, 128, 64, 160 };
        boss.cy = (boss.y >> 8) + 4;
        boss.left = simon_sx() < (boss.x >> 8);
        boss.vx = MEDUSA_BVX;
        boss.timer = float_time[++boss.turn & 3];
        boss.state = B_FLOAT;
        break;
    }
    case B_FLOAT:                                               // $8356
    {
        if (!--boss.timer) { boss.state = B_PAUSE; boss.timer = MEDUSA_PAUSE; break; }
        u16 d = (u16)((s16)(boss.y >> 8) - boss.cy);
        bool carry = (u16)boss.vy >= d;
        boss.vy -= d;
        boss.y += boss.vy + carry;
        boss.x += boss.left ? -(boss.vx + LOOP_VX) : boss.vx + LOOP_VX;
        if (boss.left ? (boss.x >> 8) < 0x10 : (boss.x >> 8) >= 0xF0) boss.left = !boss.left;
        break;
    }
    case B_PAUSE:
        if (!--boss.timer) { boss.vy = MEDUSA_RISE; boss.state = B_RISE; }
        break;
    case B_GLIDE:
        boss.y += boss.up ? -boss.vy : boss.vy;
        boss.x += boss.left ? -(boss.vx + LOOP_VX) : boss.vx + LOOP_VX;
        if (abs(boss.tx - (s16)(boss.x >> 8)) < 4)
        {
            static const u8 wait[4] = { 0x7B, 0x20, 0x3D, 0xC7 };   // NES table at $8176
            boss.state = B_HOVER; boss.timer = wait[frame_count & 3];
        }
        break;
    case B_HOVER:                                               // every 16 frames: up out of the way of a Simon facing it
        if (!--boss.timer) { boss_swoop(); break; }
        if (!(frame_count & 15) && abs(simon_y + 16 - (s16)(boss.y >> 8)) < 0x14 && abs(simon_sx() - (s16)(boss.x >> 8)) < 0x58
            && (simon_sx() < (boss.x >> 8)) != facing_left)
        { boss.vy = 0x280; boss.state = B_DODGE; boss.timer = 8; }
        break;
    case B_DODGE:
        if (!--boss.timer) boss_swoop();
        else boss.y -= boss.vy;
        break;
    case B_SWOOP:                                               // down, slowing by 6/256 a frame, then up again
        boss.vy -= 6;
        if (boss.vy < 0 && (boss.y >> 8) < 0x70) { boss_target(); break; }
        boss.y += boss.vy;
        boss.x += boss.left ? -(boss.vx + LOOP_VX) : boss.vx + LOOP_VX;
        if ((boss.x >> 8) < 0x10) { boss.x = (0x10 << 8) | (boss.x & 0xFF); boss.left = !boss.left; }
        else if ((boss.x >> 8) >= 0xF0) { boss.x = (0xF0 << 8) | (boss.x & 0xFF); boss.left = !boss.left; }
        break;
    case B_REST:
        if (!--boss.timer) boss_target();
        break;
    }
    boss_hits();
}

static void boss_draw(void)
{
    if (section != boss_sec) return;
    s16 x = BOSS_CAM + (boss.x >> 8), y = boss.y >> 8;
    if (boss.medusa && boss.state >= B_RISE && boss.state <= B_PAUSE)
    { draw_object(&world_poses[B2_MBOSS0 + ((boss.anim / 9) & 1)], x - 16, y - 16, FALSE); return; }
    if (boss.medusa && boss.state < B_RISE) return;             // still the statue of the background
    if (boss.mummies && boss.state < B_FLAMES) return;
    if (boss.dracula && boss.state < B_FLAMES) { if (boss.state != B_SLEEP) drac_draw(); return; }
    if (boss.dracula && boss.state == B_FLAMES)                 // 3 rows of flames
    {
        for (s16 dy = -32; dy <= 0; dy += 16)
            draw_object(&obj_poses[OBJ_BFLAME0 + modu(boss.timer / 9, 3)], x - 12, y + dy, FALSE);
        return;
    }
    if (boss.death && boss.state < B_FLAMES)
    {
        if (boss.state >= B_DFALL) draw_object(&world_poses[B5_DEATH], x - 8, y - 24, !boss.left);
        return;
    }
    if (boss.frank && boss.state < B_FLAMES)
    {
        static const u8 frank_seq[4] = { 2, 0, 1, 0 };
        if (boss.spawned)
            draw_object(&world_poses[B4_FRANK0 + frank_seq[(boss.anim / FRANK_ANIM) & 3]], x - 8, y - 24, !boss.left);
        return;
    }
    switch (boss.state)
    {
    case B_SLEEP:
    case B_WAKE:   draw_object(&obj_poses[OBJ_BOSS0], x - 24, y - 8, FALSE); break;
    case B_FLAMES: draw_object(&obj_poses[OBJ_BFLAME0 + modu(boss.timer / 9, 3)], x - 12, y - 8, FALSE); break;
    case B_ORB:
        if (boss.timer < 61 || (boss.timer < 93 && !(boss.timer & 1))) break;
        draw_object(&obj_poses[OBJ_ORB0 + ((boss.anim >> 1) & 1)], x - 8, y - 8, FALSE);
        break;
    case B_TALLY:  break;
    default:       draw_object(&obj_poses[OBJ_BOSS0 + 1 + ((boss.anim >> 3) & 1)], x - 24, y - 8, FALSE); break;
    }
}

static void start_whip(bool crouch)
{
    whip_crouch = crouch;
    whip_phase = 0; whip_count = 0; whip_hit_done = FALSE;
    whip_left = whip_table()[0].frames;
}

// advance the whip timeline by one frame; returns TRUE when the swing is over
static bool whip_tick(void)
{
    // the swing's sound on its 11th frame ($568): the whip's, the dagger's when one is thrown, none for the others
    if (++whip_count == 11 && (!throwing || subweapon == SUB_WATCH || subweapon == SUB_DAGGER))
        sfx_play(throwing && subweapon == SUB_DAGGER ? SFX_08 : SFX_0A);
    if (--whip_left) return FALSE;
    if (++whip_phase >= WHIP_PHASES) return TRUE;
    whip_left = whip_table()[whip_phase].frames;
    return FALSE;
}

// the stage's music: the NES game's table at $FB4F, by stage ($28); a door to a stage with the same music lets it
// play on, a restart starts it again
static void stage_music(bool restart)
{
    static const u8 by_stage[19] = { MUS_VAMPIRE_KILLER, MUS_VAMPIRE_KILLER, MUS_VAMPIRE_KILLER, MUS_VAMPIRE_KILLER,
                                     MUS_STALKER, MUS_STALKER, MUS_STALKER, MUS_WICKED_CHILD, MUS_WICKED_CHILD,
                                     MUS_WICKED_CHILD, MUS_WALKING_THE_EDGE, MUS_STALKER, MUS_STALKER,     // $FB4F
                                     MUS_HEART_OF_FIRE, MUS_HEART_OF_FIRE, MUS_HEART_OF_FIRE, MUS_OUT_OF_TIME,
                                     MUS_OUT_OF_TIME, MUS_NOTHING_TO_LOSE };
    static u8 playing = 0xFF;
    u8 m = by_stage[sections[section].stage];
    if (restart || m != playing || !music_playing()) music_play(m);
    playing = m;
}

static void restart_level(void)
{
    if (section == SEC_UNDER) section = SEC_ST2;                // the stage starts again in its first room
    if (section == SEC_ST4B || section == SEC_ST5B || section == SEC_ST6B || section == SEC_ST7B || section == SEC_ST8B
        || section == SEC_ST13B || section == SEC_ST14B || section == SEC_ST15B || section == SEC_ST17B || section == SEC_ST18B)
        section--;
    bool loading = use_block();
    if (loading) VDP_setEnable(FALSE);
    const Section *sec = &sections[section];
    simon_x = sec->start_x; simon_y = sec->start_y; cam_x = sec->cam0;
    s16 start_cam = sec->start_x + 8 - 128;                    // the NES game faces left from a start on the
    if (start_cam > sec->cam1) start_cam = sec->cam1;          // right half of the screen (x bit 7, table $CA0C)
    if (start_cam < sec->cam0) start_cam = sec->cam0;
    facing_left = sec->start_x + 8 - start_cam >= 128; state = ST_STAND; air_whip = FALSE; stair_whip = FALSE; lost = FALSE;
    static const u8 start_hearts[3] = { 5, 0, 30 };            // normal, hard, easy (the SNES port's table)
    player_hp = shown_hp = PLAYER_HP; invuln = 0; hearts = start_hearts[difficulty]; power_flag = FALSE;
    throwing = FALSE; rosary_t = 0; watch_t = 0; potion_t = 0; whip_freeze = 0;
    time_left = section == SEC_COURT || section == SEC_HALL ? START_TIME : sec->time * 100; time_tick = 0;
    if (difficulty == DIFF_HARD) time_left = 170;               // the VS. arcade game's TIME for stages 1 to 3
    if (difficulty != DIFF_EASY)                                // dying loses the sub-weapons (not on easy)
    { subweapon = other_sub = SUB_NONE; shot_level = other_level = 0; }
    PAL_setColor(0, world_palette[0]);
    for (u8 i = 0; i < MAX_SHOTS; i++) shots[i].state = W_FREE;
    objects_init();
    enemies_init();
    panthers_init();
    invalidate_columns(TRUE);
    stream_columns(PLANE_COLS);
    stream_back(PLANE_COLS);
    hud_update();
    stage_music(TRUE);
    if (loading) VDP_setEnable(TRUE);
}

// end of the gate cutscene: the NES game turns the display off, loads the hall (block 1) and puts Simon at its start
static void enter_hall(void)
{
    section = SEC_HALL;
    simon_x = HALL_X; simon_y = HALL_Y; facing_left = FALSE; state = ST_STAND; anim = 0;
    drops_clear();
    for (u8 i = 0; i < MAX_SHOTS; i++) shots[i].state = W_FREE;
    invalidate_columns(TRUE);
    hall_load = HALL_LOAD;
    time_tick = 0;                                              // TIME goes on (not reset) 64 frames after the load
    VDP_setEnable(FALSE);
}

// stage 16's archway and stage 17's exit: the NES game turns the display off and starts the next stage (TIME,
// health, hearts and sub-weapon go on), Simon at its start
static void enter_stage(u8 sec_id)
{
    section = sec_id;
    VDP_setEnable(FALSE);
    use_block();
    const Section *sec = &sections[section];
    simon_x = sec->start_x; simon_y = sec->start_y; cam_x = sec->cam0;
    s16 start_cam = sec->start_x + 8 - 128;                    // facing as restart_level
    if (start_cam > sec->cam1) start_cam = sec->cam1;
    if (start_cam < sec->cam0) start_cam = sec->cam0;
    facing_left = sec->start_x + 8 - start_cam >= 128; state = ST_STAND; anim = 0; air_whip = FALSE; stair_whip = FALSE;
    drops_clear();
    for (u8 i = 0; i < MAX_SHOTS; i++) shots[i].state = W_FREE;
    objects_init();
    enemies_init();
    panthers_init();
    PAL_setColor(0, world_palette[0]);
    invalidate_columns(TRUE);
    stream_columns(PLANE_COLS);
    stream_back(PLANE_COLS);
    hud_update();
    stage_music(FALSE);
    VDP_setEnable(TRUE);
}

// Simon can step onto a flight from its foot (UP) or from its top (DOWN) when he is on that floor and close to it
// (from either side: in stage 2 the flights to the underground start in the middle of the floor; in the NES game
// Simon went from 7 px past the top back to it)
static bool try_mount(bool up)
{
    for (u8 i = 0; i < world_nstairs; i++)
    {
        const Stair *st = &world_stairs[i];
        s16 topx = st->x + st->dir * st->steps * 8, topy = st->y - st->steps * 8;
        s16 d = simon_x - (up ? st->x : topx);
        if (up && simon_y == st->y && d >= -24 && d <= 24)
        { stair_id = i; mount_x = st->x; mount_k = st->dir > 0 ? 0 : -2; mount_up = TRUE; state = ST_MOUNT; return TRUE; }
        if (!up && simon_y == topy && d >= -24 && d <= 24)
        { stair_id = i; mount_x = topx; mount_k = st->dir > 0 ? -3 : 1; mount_up = FALSE; state = ST_MOUNT; return TRUE; }
    }
    return FALSE;
}

// Simon went past the end of a flight that goes on in another room (stage 2's upper room and underground): the
// NES game turns the display off while it loads the room, and keeps the scroll and Simon's place on the screen
static void change_room(s8 flight, bool at_top)
{
    stair_id = flight;
    stair_pos = at_top ? world_stairs[(u8)flight].steps * 16 : 0;
    s16 c = world_stairs[(u8)flight].x >> 3;
    for (u8 i = 0; i < SECTIONS; i++)
        if (i != SEC_COURT && c >= sections[i].c0 && c < sections[i].c1) section = i;
    for (u8 i = 0; i < MAX_SHOTS; i++) shots[i].state = W_FREE;
    invalidate_columns(FALSE);
    enemies_init();                                             // the new room starts empty
    drops_clear();
    hall_load = HALL_LOAD;
    VDP_setEnable(FALSE);
}

// the closed door is a background column of the part (see Section); while it is open the game clears it and draws
// the door with sprites
static s16 door_tile_column(const Section *sec)
{
    if (sec->door > 0) return sec->c1 - 1 - sec->door_in;
    // Stage 14's left door occupies room column 2; the other left doors use 1.
    // Use this coordinate for both background removal/restoration and sprite animation.
    return sec->c0 + (sec->stage == 14 ? 2 : 1);
}

static void door_column(bool closed)
{
    const Section *sec = &sections[section];
    s16 col = door_tile_column(sec);
    u16 row0 = (sec->door_y - 16) >> 3;
    for (u16 r = row0; r < row0 + DOOR_ROWS; r++)
        VDP_setTileMapXY(BG_A, closed ? map_base + world_map[r * world_cols + col - world_c0] : map_base, col & (PLANE_COLS - 1), r);
}

// The stage 10 exit is an automatic flight, absent from block4_stairs.
// Finish it in the old room before loading the stage 11 entrance.
static bool exit_climb_tick(void)
{
    if (++state_t & 1) simon_y--; else simon_x++;
    return state_t >= 96; // 48 px up and right, behind the top HUD
}

static void enter_climbing_stage(void)
{
    section = sections[section].next;
    state = ST_CLIMB; state_t = 0; anim = 0; treasures_reset();
    for (u8 i = 0; i < MAX_SHOTS; i++) shots[i].state = W_FREE;
    enemies_init();
    for (u8 i = 0; i < PANTHERS; i++) panthers[i].state = P_GONE;
    // Start below the floor, already clipped, throughout the entrance wait.
    simon_x = sections[section].c0 * 8 + 12; simon_y = 208;
    cam_x = sections[section].cam0;
    stage_music(FALSE);
    invalidate_columns(FALSE);
    stream_columns(PLANE_COLS);
    hud_update();
}

static void simon_update(u16 pad, u16 pressed)
{
    bool left = pad & BUTTON_LEFT, right = pad & BUTTON_RIGHT;
    s16 previous_x = simon_x, previous_y = simon_y;
    u8 previous_state = state;

    switch (state)
    {
    case ST_STAND:
    case ST_WALK:
        if (!standable(simon_y))                        // walked off a ledge: the NES game finds it on the next frame,
        {                                               // and he drops, still going forwards
            jump_vx = state == ST_WALK ? (facing_left ? -1 : 1) : 0;
            state = ST_FALL; state_t = 0; drop = TRUE;
            break;
        }
        if ((pad & BUTTON_UP) && try_mount(TRUE)) break;
        if ((pad & BUTTON_DOWN) && try_mount(FALSE)) break;
        if ((pressed & BUTTON_B) && headroom())        // jump, direction is locked
        {
            // the NES game still takes this frame's step, and rises on the second frame after the press: its
            // recorded curve's first frames are skipped (the demos' inputs show it)
            state = ST_JUMP; state_t = JUMP_SKIP; jump_base_y = simon_y;
            jump_vx = right ? 1 : left ? -1 : 0;
            if (jump_vx) { facing_left = (jump_vx < 0); if (!wall_ahead(jump_vx)) simon_x += jump_vx; }
        }
        else if (start_attack(pad, pressed, FALSE))
        {
            state = ST_WHIP;
            if (left || right)                          // the NES game still takes this frame's step (measured)
            {
                facing_left = left;
                if (!wall_ahead(left ? -1 : 1)) simon_x += left ? -1 : 1;
            }
        }
        else if (pad & BUTTON_DOWN)
        {
            state = ST_CROUCH;
            if (left || right)                          // still this frame's step, as the whip's (demo of stage 12)
            {
                facing_left = left;
                if (!wall_ahead(left ? -1 : 1)) simon_x += left ? -1 : 1;
            }
        }
        else if (left || right)
        {
            if (state != ST_WALK) { state = ST_WALK; anim = 0; }
            facing_left = left;
            if (!wall_ahead(left ? -1 : 1)) simon_x += left ? -1 : 1;
            anim++;
        }
        else state = ST_STAND;
        break;
    case ST_CROUCH:
        if (!standable(simon_y))
        { state = ST_FALL; state_t = 0; jump_vx = 0; drop = TRUE; break; }
        if (!(pad & BUTTON_DOWN)) state = ST_STAND;
        else if (start_attack(pad, pressed, TRUE)) state = ST_WHIP;
        break;
    case ST_JUMP:
    {
        // one frame past the recorded curve: back to the height he left from (the NES game's last step, +5)
        s16 ny = jump_base_y + (state_t < JUMP_FRAMES ? simon_jump_dy[state_t] : 0);
        bool landed = FALSE;
        if (ny > simon_y) landed = move_down_to(ny); else simon_y = ny;
        // after y, like the NES game; on the frame he lands, and on that last step, he already stands: a step only
        // if the pad says so (demos of stages 7, 8 and 12)
        if (landed || state_t >= JUMP_FRAMES)
        {
            if (left || right) { facing_left = left; if (!wall_ahead(left ? -1 : 1)) simon_x += left ? -1 : 1; }
        }
        else if (jump_vx && !wall_ahead_from(jump_vx, previous_y)) simon_x += jump_vx;
        if (landed) state = ST_STAND;
        else if (++state_t > JUMP_FRAMES) { state = ST_FALL; state_t = 0; drop = FALSE; }
        break;
    }
    case ST_FALL:
    {
        s16 vy = 2 + (state_t >> 2);
        if (vy > 6) vy = 6;
        if (drop) vy = state_t ? FALL_VY : 0;           // NES game: one frame still, then 8 px/frame
        state_t++;
        bool landed = move_down_to(simon_y + vy);
        if (jump_vx && !(drop && landed) && !wall_ahead_from(jump_vx, previous_y)) simon_x += jump_vx;   // a drop lands without
        if (landed) state = ST_STAND;                                                   // a step (stage 7 demo)
        break;
    }
    case ST_WHIP:
        if (!standable(simon_y))
        { state = ST_FALL; state_t = 0; jump_vx = 0; drop = TRUE; air_whip = TRUE; break; }
        if (whip_tick()) state = ST_STAND;
        break;
    case ST_HURT:                                       // knockback hop, no control
    {
        s16 ny = jump_base_y - (s16)(state_t * (HURT_FRAMES - state_t)) / 6;
        bool landed = FALSE;
        if (ny > simon_y) landed = move_down_to(ny); else simon_y = ny;
        if (jump_vx && !wall_ahead_from(jump_vx, previous_y)) simon_x += jump_vx;
        if (landed) state = ST_STAND;
        else if (++state_t >= HURT_FRAMES) { state = ST_FALL; state_t = 0; jump_vx = 0; drop = FALSE; }
        break;
    }
    case ST_MOUNT:                                      // walk to the foot (or the top) of the flight at 1 px/frame
    {
        // the NES game (bank 6, $9D4B) walks him until he is 1 or 2 px right of its target (its table $9D47 per
        // end of a flight: 0, -1, 5, 2 from the end's x), so he stops 1 px later coming from the left than from
        // the right, and steps onto the flight there, already a little way along it
        s16 e = simon_x - (mount_x + mount_k);
        if (e < 1 || e > 2) { simon_x += e < 1 ? 1 : -1; facing_left = e > 2; anim++; }
        else
        {
            const Stair *st = &world_stairs[stair_id];
            state = ST_STAIRS; stair_dir = 0; stair_anim = 0; stair_whip = FALSE;
            stair_pos = (mount_up ? 0 : st->steps * 16) + 2 * st->dir * (simon_x - mount_x);
        }
        break;
    }
    case ST_STAIRS:                                     // 0.5 px/frame along the diagonal
    {
        const Stair *st = &world_stairs[stair_id];
        u16 fwd = st->dir > 0 ? BUTTON_RIGHT : BUTTON_LEFT, back = st->dir > 0 ? BUTTON_LEFT : BUTTON_RIGHT;
        bool up = pad & (BUTTON_UP | fwd), dn = pad & (BUTTON_DOWN | back);
        if (stair_whip) { if (whip_tick()) stair_whip = FALSE; }
        else if (start_attack(pad, pressed, FALSE)) stair_whip = TRUE;
        else if ((pressed & BUTTON_B) && (pad & BUTTON_DOWN))        // jump off the stairs: down + jump
        { state = ST_FALL; state_t = 0; jump_vx = 0; stair_dir = 0; drop = FALSE; }
        else if (up != dn)
        {
            stair_dir = up ? 1 : -1;
            facing_left = (stair_dir * st->dir < 0);
            stair_pos += stair_dir;
            stair_anim++;
            if (stair_pos <= 0)                                                          // bottom of the flight
            {
                if (st->link_down >= 0) { change_room(st->link_down, TRUE); st = &world_stairs[stair_id]; }
                else { stair_pos = 0; state = ST_STAND; }
            }
            else if (stair_pos >= st->steps * 16)                                        // top
            {
                if (st->link_up >= 0) { change_room(st->link_up, FALSE); st = &world_stairs[stair_id]; }
                else { stair_pos = st->steps * 16; state = ST_STAND; }
            }
        }
        else stair_dir = 0;
        simon_x = st->x + st->dir * stair_pos / 2;
        simon_y = st->y - stair_pos / 2;
        break;
    }
    case ST_GATE:                                       // castle gate cutscene, no control (stage 16: leftwards)
    {
        bool arch = section == SEC_ST16;
        facing_left = arch;
        if (gate_phase < 2)
        {
            u16 f = gate_frac + GATE_SPEED;
            simon_x += arch ? -(s16)(f >> 8) : (s16)(f >> 8);
            gate_frac = f & 0xFF;
            anim++;
            if (arch ? simon_x <= ARCH_MASKED : simon_x >= GATE_MASKED) gate_phase = 1;
            if (arch ? simon_x <= ARCH_STOP : simon_x >= GATE_STOP) { gate_phase = 2; state_t = 0; }
        }
        else if (++state_t >= GATE_WAIT)
        {
            if (arch) enter_stage(SEC_ST17);
            else enter_hall();
        }
        break;
    }
    case ST_DOOR:                                       // door between stages, no control (timings of the NES game)
    {
        s8 dir = sections[section].door;
        facing_left = dir < 0;
        switch (door_phase)
        {
        case 0:                                         // the screen scrolls 128 px
        case 5:
            if (state_t < 128) cam_x += dir;
            if (++state_t < 129) break;
            state_t = 0;
            if (door_phase == 0) { door_phase = 1; break; }
            section = sections[section].next;           // the next stage starts here
            stage_music(FALSE);
            state = ST_STAND;
            invalidate_columns(FALSE);
            stream_columns(PLANE_COLS);
            hud_update();
            break;
        case 1:                                         // the door opens: half, then wide open
            if (++state_t == 16) { door_column(FALSE); sfx_play(SFX_1D); }   // first opening step ($C3E0)
            if (state_t >= 31) { door_phase = 2; state_t = 0; }
            break;
        case 2:                                         // Simon walks through at 1 px/frame (74 px to the left, measured
            if (state_t < (dir > 0 ? 68 : 74)) { simon_x += dir; anim++; }      // in stage 4)
            if (++state_t >= (dir > 0 ? 69 : 75)) { door_phase = 3; state_t = 0; }
            break;
        case 3:                                         // it closes
            if (++state_t >= (dir > 0 ? 10 : 12)) { door_phase = 4; state_t = 0; door_column(TRUE); sfx_play(SFX_1D); }
            break;
        case 4:
            if (++state_t >= 48) { door_phase = 5; state_t = 0; }
            break;
        }
        break;
    }
    case ST_EXIT_CLIMB:
        facing_left = FALSE;
        if (exit_climb_tick()) enter_climbing_stage();
        break;
    case ST_CLIMB:                                      // entrance: wait below the floor, then climb into the next stage
    {                                                   // centre (20, 224), y and x 1 px in turn, to (67, 176)
        facing_left = FALSE;
        state_t++;
        if (state_t > CLIMB_WAIT)
        {
            if ((state_t - CLIMB_WAIT) & 1) simon_y--; else simon_x++;
            if (state_t - CLIMB_WAIT >= CLIMB_STEPS) state = ST_STAND;
        }
        break;
    }
    case ST_DEAD:
        if (!lost && !standable(simon_y)) move_down_to(simon_y + 4);
        if (++state_t >= DEAD_FRAMES)
        {
            whip_level = 0;                                   // the NES game takes the chain back too
            if (lives == 0) game_over = TRUE;
            else { lives--; restart_level(); }
        }
        break;
    }

    // Descent is tested before the horizontal step. At a platform's corner,
    // that step can put the feet over a surface already crossed this frame.
    // Sweep the same descent at the new x too, rather than finding the next
    // tile row 8 px inside the floor. Only a strictly descending frame counts:
    // the jump's zero-height startup frame must not land again and cancel it.
    if ((previous_state == ST_JUMP || previous_state == ST_FALL || previous_state == ST_HURT)
        && simon_x != previous_x && simon_y > previous_y)
    {
        s16 target_y = simon_y;
        simon_y = previous_y;
        if (move_down_to(target_y)) state = ST_STAND;
    }

    if (state == ST_JUMP || state == ST_FALL)
    {
        if (!air_whip && start_attack(pad, pressed, FALSE)) air_whip = TRUE;
        else if (air_whip && whip_tick()) air_whip = FALSE;
    }
    else air_whip = FALSE;                                   // landed or hurt: the swing is cancelled
    if (state != ST_STAIRS) stair_whip = FALSE;

    if (!in_hall && simon_x >= GATE_TRIGGER && simon_x <= GATE_TRIGGER_END && (state == ST_STAND || state == ST_WALK))
    { sfx_play(SFX_19); state = ST_GATE; gate_phase = 0; gate_frac = 0; anim = 0; treasures_reset(); }
    if (section == SEC_ST16 && simon_x >= ARCH_TRIGGER && simon_x <= ARCH_TRIGGER_END && simon_y == 112 - 16
        && (state == ST_STAND || state == ST_WALK))
    { sfx_play(SFX_19); state = ST_GATE; gate_phase = 0; gate_frac = 0; anim = 0; treasures_reset(); }
    if (sections[section].next >= 0 && sections[section].door < 2 && (state == ST_STAND || state == ST_WALK)
        && simon_y == sections[section].door_y
        && (sections[section].door > 0 ? simon_x >= sections[section].cam1 + DOOR_AT - 8 * sections[section].door_in + sections[section].door_dx
                                       : simon_x <= sections[section].cam0 + DOOR_AT_LEFT + sections[section].door_dx))
    {
        state = ST_DOOR; door_phase = 0; state_t = 0; anim = 0; treasures_reset();
        for (u8 i = 0; i < MAX_SHOTS; i++) shots[i].state = W_FREE;
        enemies_init();                                         // the enemies are gone
        for (u8 i = 0; i < PANTHERS; i++) panthers[i].state = P_GONE;
        invalidate_columns(FALSE);   // the next part shows through the door
        stream_columns(PLANE_COLS);
    }
    if (sections[section].door == 2 && (state == ST_STAND || state == ST_WALK || state == ST_JUMP || state == ST_FALL)
        && (u32)(simon_x + 8 - (sections[section].cam1 + sections[section].door_in) + 4) < 8u
        && (u32)(simon_y + 16 - sections[section].door_y + 4) < 8u)
    {
        state = ST_EXIT_CLIMB; state_t = 0; anim = 0;
        air_whip = FALSE; stair_whip = FALSE; treasures_reset();
        for (u8 i = 0; i < MAX_SHOTS; i++) shots[i].state = W_FREE;
        enemies_init();
        for (u8 i = 0; i < PANTHERS; i++) panthers[i].state = P_GONE;
    }
    if (sections[section].door == 3 && (state == ST_STAND || state == ST_WALK || state == ST_JUMP || state == ST_FALL)
        && (u32)(simon_x + 8 - (sections[section].cam0 + sections[section].door_in) + 4) < 8u
        && (u32)(simon_y + 16 - sections[section].door_y + 4) < 8u)
        enter_stage(sections[section].next);
    if (simon_y >= PIT_Y && state != ST_DEAD && state != ST_CLIMB && state != ST_EXIT_CLIMB)  // into a pit or the water: the NES game's $966D
    {
        state = ST_DEAD; state_t = 0; lost = TRUE; air_whip = FALSE;
        fall_play(); // one Wilhelm scream per fatal fall, FM mode only
    }
    // the screen's edges at both ends of a part (NES: Simon's centre stops at x 9 and x 239 on the screen)
    const Section *sec = &sections[section];
    if (state != ST_DOOR && state != ST_EXIT_CLIMB)
    {
        s16 left = screen_locked ? BOSS_CAM : sec->cam0, right = screen_locked ? BOSS_CAM : sec->cam1;
        if (simon_x < left + (section == SEC_COURT ? 0 : 1)) simon_x = left + (section == SEC_COURT ? 0 : 1);
        if (simon_x > right + 231) simon_x = right + 231;
    }
}

static const SimonPose *simon_pose(void)
{
    static const u8 walk_seq[4] = { POSE_STAND, POSE_WALK1, POSE_WALK2, POSE_WALK1 };
    if (air_whip) return &whip_table()[whip_phase].pose;
    switch (state)
    {
    case ST_MOUNT:
    case ST_WALK:   return &simon_poses[walk_seq[(anim / 7) & 3]];
    case ST_CROUCH: return &simon_poses[POSE_CROUCH];
    case ST_JUMP:   return &simon_poses[simon_jump_curled[state_t < JUMP_FRAMES ? state_t : JUMP_FRAMES - 1] ? POSE_CROUCH : POSE_STAND];
    case ST_HURT:   return &simon_poses[POSE_CROUCH];
    case ST_DEAD:   return &simon_poses[POSE_CROUCH];
    case ST_GATE:   return &simon_poses[gate_phase < 2 ? walk_seq[(anim / 7) & 3] : POSE_WALK1];
    case ST_DOOR:   return &simon_poses[door_phase == 2 ? walk_seq[(anim / 7) & 3] : POSE_STAND];
    case ST_EXIT_CLIMB:
        return &simon_poses[(state_t >> 3) & 1 ? POSE_STAIR_UP_A : POSE_STAIR_UP_B];
    case ST_CLIMB:                                       // NES poses $0E (4 frames), then $02 and $0E, 8 frames each
        if (state_t <= CLIMB_WAIT) return &simon_poses[POSE_STAND];
        return &simon_poses[((state_t - CLIMB_WAIT + 3) >> 3) & 1 ? POSE_STAIR_UP_A : POSE_STAIR_UP_B];
    case ST_WHIP:   return &whip_table()[whip_phase].pose;
    case ST_STAIRS:
        if (stair_whip) return &whip_table()[whip_phase].pose;
        if (stair_dir == 0) return &simon_poses[POSE_STAIR_UP_B];
        if ((stair_anim >> 3) & 1) return &simon_poses[stair_dir > 0 ? POSE_STAIR_UP_B : POSE_STAIR_DOWN_B];
        return &simon_poses[POSE_STAIR_UP_A];
    default:        return &simon_poses[POSE_STAND];
    }
}

// ---------------------------------------------------------------- pause and debug menu

// During the pause, up up down down left right left right B A gives 99 lives, 99 hearts and full health, and opens
// the debug menu on the top line: LEFT / RIGHT pick a stage, A goes to its start, B switches invincibility,
// C switches the position display. START resumes the game.
#define WARPS 19
// the NES game names no stage: these short names only describe the place
static const u8 warp_secs[WARPS] = { SEC_COURT, SEC_HALL, SEC_ST2, SEC_ST3, SEC_ST4, SEC_ST5, SEC_ST6, SEC_ST7, SEC_ST8,
                                     SEC_ST9, SEC_ST10, SEC_ST11, SEC_ST12, SEC_ST13, SEC_ST14, SEC_ST15,
                                     SEC_ST16, SEC_ST17, SEC_ST18 };
static const char *const warp_names[WARPS] = { "1 COURTYARD", "1 HALL", "2 CELLAR", "3 BAT TOWER", "4 CAVERN", "5 ARMORY",
                                               "6 MEDUSA", "7 GALLERY", "8 RUINS", "9 TOMB", "10 AQUEDUCT",
                                               "11 LAB", "12 MONSTER", "13 PRISON", "14 STONE HALL",
                                               "15 DEATH", "16 BRIDGE", "17 KEEP", "18 DRACULA" };

// SGDK's font draws in colour 15 of its palette, which is black in some blocks and with the NES art: the menu uses a
// copy of the font in the brightest colour of the HUD's palette (1), loaded after the rising treasure's tiles
extern const TileSet font_default;               // in SGDK's library, not declared by its headers

static void debug_font_load(void)
{
    u8 best = 1;
    for (u8 i = 2; i < 16; i++)
    {
        u16 c = world_palette[16 + i], b = world_palette[16 + best];
        if ((c & 14) + ((c >> 4) & 14) + ((c >> 8) & 14) > (b & 14) + ((b >> 4) & 14) + ((b >> 8) & 14)) best = i;
    }
    TileSet *font = unpackTileSet(&font_default, NULL);
    u32 *t = font->tiles;
    for (u16 i = 0; i < font->numTile * 8; i++)
    {
        u32 v = 0;
        for (u8 n = 0; n < 32; n += 4)
            if (((t[i] >> n) & 15) == 15) v |= (u32)best << n;
        t[i] = v;
    }
    VDP_loadTileData(t, TILE_USER_INDEX + DEBUG_FONT, font->numTile, CPU);
    MEM_free(font);
}

static void debug_draw(void)
{
    char b[41];
    u8 k = 0;
    while (warp_secs[k] != debug_sec) k++;
    sprintf(b, "<%-11s> A:GO B:GOD %s C:POS", warp_names[k], god ? "ON " : "OFF");
    for (u8 i = 0; b[i]; i++)
        VDP_setTileMapXY(WINDOW, TILE_ATTR_FULL(PAL1, 1, 0, 0, TILE_USER_INDEX + DEBUG_FONT + b[i] - 32), NES_X / 8 + i, 0);
}

static void top_line_clear(void)
{
    VDP_clearTextLineBG(WINDOW, 0);
}

static void konami_check(u16 pressed)
{
    static const u16 code[10] = { BUTTON_UP, BUTTON_UP, BUTTON_DOWN, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT,
                                  BUTTON_LEFT, BUTTON_RIGHT, BUTTON_B, BUTTON_A };
    if (!(pressed & (BUTTON_UP | BUTTON_DOWN | BUTTON_LEFT | BUTTON_RIGHT | BUTTON_A | BUTTON_B | BUTTON_C))) return;
    if (pressed & code[konami_idx]) konami_idx++;
    else konami_idx = (pressed & code[0]) ? 1 : 0;
    if (konami_idx == 10)
    {
        konami_idx = 0;
        lives = MAX_LIVES; player_hp = PLAYER_HP; hearts = 99;
        hud_update();
        debug_menu = TRUE;
        debug_font_load();
        debug_draw();
    }
}

// one frame of the pause; returns TRUE when the game goes on
static bool pause_update(u16 pressed)
{
    if (pressed & BUTTON_START) { paused = FALSE; music_hold(FALSE); debug_menu = FALSE; konami_idx = 0; top_line_clear(); return TRUE; }
    if (!debug_menu) { konami_check(pressed); return FALSE; }
    u8 k = 0;
    while (warp_secs[k] != debug_sec) k++;
    if (pressed & BUTTON_LEFT)  k = (k + WARPS - 1) % WARPS;
    if (pressed & BUTTON_RIGHT) k = (k + 1) % WARPS;
    debug_sec = warp_secs[k];
    if (pressed & BUTTON_B) god = !god;
    if (pressed & BUTTON_C) show_pos = !show_pos;
    if (pressed & BUTTON_A)                                     // warp: the stage starts again there
    {
        u16 h = hearts;
        section = debug_sec;
        music_hold(FALSE);                                      // the pause held it
        restart_level();
        hearts = h; hud_update();                               // keep the hearts of the code
        paused = FALSE; debug_menu = FALSE; top_line_clear();
        return TRUE;
    }
    debug_draw();
    return FALSE;
}

// ---------------------------------------------------------------- title screen, introduction, game over

static void sprites_end(void)
{
    if (!sprite_n) VDP_setSpriteFull(sprite_n++, -32, -32, SPRITE_SIZE(1, 1), 0, 0);   // nothing to show
    VDP_setSpriteLink(sprite_n - 1, 0);
    VDP_updateSprites(sprite_n, DMA_QUEUE);
}

// a whole NES picture on plane A, placed like the level (32 px to the right, its first row hidden), no HUD window
static void screen_load(const u32 *tiles, u16 count, const u16 *palette, const u16 *map)
{
    VDP_setEnable(FALSE);
    VDP_setWindowOff();
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_loadTileData(tiles, TILE_USER_INDEX, count, DMA);
    PAL_setColors(0, palette, 64, DMA);
    VDP_setTileMapDataRectEx(BG_A, map, TILE_USER_INDEX, NES_X / 8, 0, 32, 30, 32, CPU);
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 0);
    VDP_setVerticalScroll(BG_A, 8);
    VDP_setEnable(TRUE);
}

// one frame of the sprites the NES game drew on that screen
static void screen_sprites(const ScreenSprite *spr, const ScreenList *list)
{
    sprite_n = 0;
    for (u8 i = 0; i < list->count && sprite_n < MAX_SPRITES; i++, sprite_n++)
    {
        const ScreenSprite *sp = &spr[list->first + i];
        VDP_setSpriteFull(sprite_n, sp->x, sp->y, SPRITE_SIZE(1, 2), sp->attr + TILE_USER_INDEX, sprite_n + 1);
    }
    sprites_end();
}

static void black_frames(u16 n)
{
    sprite_n = 0; sprites_end();
    PAL_setColors(0, palette_black, 64, DMA);
    while (n--) SYS_doVBlankProcess();
}

static void castle_map_number(u16 col, u16 row, u32 value, u8 digits, const u16 *table)
{
    for (s8 i = digits - 1; i >= 0; i--)
    {
        VDP_setTileMapXY(WINDOW, TILE_USER_INDEX + table[value % 10], col + i, row);
        value /= 10;
    }
}

// Post-boss castle map (SNES bank7.asm $C698-$C7E2, palette 09): recorded
// scroll, Simon and blinking markers. Use native 256-pixel mode for this NES
// picture so the scrolling panorama cannot leak into the 320-pixel side bars.
static void castle_map_scene(u8 next_stage)
{
    const CastleMapScene *scene = NULL;
    for (u8 i = 0; i < CASTLE_MAP_SCENES; i++)
        if (castle_map_scenes[i].stage == next_stage) { scene = &castle_map_scenes[i]; break; }
    if (!scene) return;
    music_stop();
    black_frames(15);
    VDP_setEnable(FALSE);
    VDP_setScreenWidth256();
    VDP_setWindowOff();
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_loadTileData(ART(castle_map_tiles), TILE_USER_INDEX, CASTLE_MAP_TILES, DMA);
    PAL_setColors(0, ART_PAL(castle_map), 64, DMA);
    // The NES/SNES split keeps the HUD fixed while only the map scrolls.
    VDP_clearPlane(WINDOW, TRUE);
    VDP_setTileMapDataRectEx(WINDOW, castle_map_hud, TILE_USER_INDEX, 0, 0, 32, HUD_ROWS, 32, CPU);
    VDP_setWindowVPos(FALSE, HUD_ROWS);
    castle_map_number(23, 2, hearts, 2, castle_map_hud_digit);
    castle_map_number(6, 1, score, 6, castle_map_hud_digit);
    castle_map_number(23, 3, lives, 2, castle_map_hud_digit_lives);
    castle_map_number(18, 1, time_left, 4, castle_map_hud_digit);
    castle_map_number(29, 1, next_stage, 2, castle_map_hud_digit);
    for (u8 i = 0; i < 8; i++)
    {
        u8 hp = player_hp > i * 8 ? player_hp - i * 8 : 0;
        VDP_setTileMapXY(WINDOW, TILE_USER_INDEX + castle_map_hud_bar[hp >= 5 ? 0 : hp ? 2 : 1], 7 + i, 2);
        VDP_setTileMapXY(WINDOW, TILE_USER_INDEX + castle_map_hud_ebar[1], 7 + i, 3);
    }
    VDP_setVerticalScroll(BG_A, 8);
    VDP_setVerticalScroll(BG_B, 8);
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 0);
    u16 loaded = scene->columns < PLANE_COLS ? scene->columns : PLANE_COLS;
    for (u16 c = 0; c < loaded; c++)
        VDP_setTileMapDataColumnEx(BG_A, castle_map_columns[scene->column + c], TILE_USER_INDEX,
                                  c, 0, 30, 1, CPU);
    VDP_setEnable(TRUE);
    for (u16 f = 0; f < scene->frames; f++)
    {
        const CastleMapFrame *frame = &castle_map_frames[scene->frame + f];
        u16 last = (frame->scroll + 255) >> 3;
        while (loaded <= last && loaded < scene->columns)
        {
            VDP_setTileMapDataColumnEx(BG_A, castle_map_columns[scene->column + loaded], TILE_USER_INDEX,
                                      loaded & (PLANE_COLS - 1), 0, 30, 1, CPU);
            loaded++;
        }
        if (frame->footstep) sfx_play(SFX_06);
        const ScreenList *list = &castle_map_lists[frame->sprites];
        sprite_n = 0;
        for (u8 i = 0; i < list->count && sprite_n < MAX_SPRITES; i++, sprite_n++)
        {
            const ScreenSprite *sp = &castle_map_sprites[list->first + i];
            VDP_setSpriteFull(sprite_n, sp->x - NES_X, sp->y, SPRITE_SIZE(1, 2),
                              sp->attr + TILE_USER_INDEX, sprite_n + 1);
        }
        if (subweapon)
        {
            u8 icon = subweapon == SUB_HOLY ? 1 : subweapon == SUB_AXE ? 2 : subweapon == SUB_CROSS ? 3 : subweapon == SUB_WATCH ? 4 : 0;
            for (u8 i = 0; i < 2 && sprite_n < MAX_SPRITES; i++, sprite_n++)
            {
                const ScreenSprite *sp = &castle_map_weapons[icon][i];
                VDP_setSpriteFull(sprite_n, 136 + sp->x, 19 + sp->y, SPRITE_SIZE(1, 2),
                                  sp->attr + TILE_USER_INDEX, sprite_n + 1);
            }
        }
        sprites_end();
        VDP_setHorizontalScrollVSync(BG_A, -(s16)frame->scroll);
        SYS_doVBlankProcess();
    }
    VDP_setEnable(FALSE);
    VDP_clearPlane(WINDOW, TRUE);
    VDP_setScreenWidth320();
}

// text in the HUD's font on plane A at NES column col, row row (A-Z, 0-9, '-'; anything else is blank)
static void __attribute__((unused)) draw_text(u16 col, u16 row, const char *t)
{
    for (; *t; t++, col++)
    {
        char c = *t;
        s16 i = c >= 'A' && c <= 'Z' ? c - 'A' : c >= '0' && c <= '9' ? 26 + c - '0' : c == '-' ? 36 : -1;
        VDP_setTileMapXY(BG_A, map_base + (i < 0 ? 0 : font_map[i]), NES_X / 8 + col, row);
    }
}

// Credits are an OPTIONS submenu; palette 1 is reserved for readable text,
// while the supplied Rumbleminze logo uses the other three tile palettes.
#ifndef START_SECTION
#include "credits_logo_data.inc"
#define CREDITS_LOGO_BASE (TILE_USER_INDEX + LEVEL_TILES)
#define CREDITS_FRAME_BASE (CREDITS_LOGO_BASE + CREDITS_LOGO_TILES)

#define CREDITS_TEXT_BASE (CREDITS_FRAME_BASE + 8)
static u16 credits_text_tile;

// Render text at a pixel-centered position, including the half-tile offset
// needed for odd-length labels. Use CPU transfers while the display is off.
static void credits_center_text(u16 center_x, u16 row, const char *text)
{
    u16 length = 0;
    while (text[length]) length++;
    if (!length || length > 30) return;
    const u16 left = center_x - length * 4;
    const u16 shift = left & 7;
    const u16 count = length + (shift ? 1 : 0);
    u32 tiles[31 * 8] = { 0 };
    for (u16 i = 0; i < length; i++)
    {
        char c = text[i];
        s16 glyph = c >= 'A' && c <= 'Z' ? c - 'A' : c >= '0' && c <= '9' ? 26 + c - '0' : c == '-' ? 36 : -1;
        for (u16 y = 0; y < 8; y++)
        {
            u32 pixels = c == '/' ? credits_frame_tiles[7 * 8 + y]
                         : glyph < 0 ? 0 : level_tiles[(font_map[glyph] & 0x7FF) * 8 + y];
            if (shift)
            {
                tiles[i * 8 + y] |= pixels >> (shift * 4);
                tiles[(i + 1) * 8 + y] |= pixels << ((8 - shift) * 4);
            }
            else tiles[i * 8 + y] = pixels;
        }
    }
    VDP_loadTileData(tiles, credits_text_tile, count, CPU);
    for (u16 i = 0; i < count; i++)
        VDP_setTileMapXY(BG_A, TILE_ATTR_FULL(PAL1, 0, 0, 0, credits_text_tile + i), left / 8 + i, row);
    credits_text_tile += count;
}

static void credits_frame_tile(u16 x, u16 y, u16 tile)
{
    VDP_setTileMapXY(BG_A, TILE_ATTR_FULL(PAL1, 0, 0, 0, CREDITS_FRAME_BASE + tile), x, y);
}

static void credits_screen(void)
{
    VDP_setEnable(FALSE);
    VDP_setWindowOff();
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_loadTileData(level_tiles, TILE_USER_INDEX, LEVEL_TILES, DMA);
    VDP_loadTileData(credits_logo_tiles, CREDITS_LOGO_BASE, CREDITS_LOGO_TILES, DMA);
    VDP_loadTileData(credits_frame_tiles, CREDITS_FRAME_BASE, 8, DMA);
    PAL_setColors(0, credits_logo_palette, 64, DMA);
    VDP_setBackgroundColor(0);
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 0);
    VDP_setVerticalScroll(BG_A, 0);
    VDP_setVerticalScroll(BG_B, 0);
    sprite_n = 0; sprites_end();

    for (u16 x = 3; x < 37; x++)
    {
        credits_frame_tile(x, 1, 1);
        credits_frame_tile(x, 26, 1);
    }
    for (u16 y = 2; y < 26; y++)
    {
        credits_frame_tile(2, y, 2);
        credits_frame_tile(37, y, 2);
    }
    credits_frame_tile(2, 1, 3); credits_frame_tile(37, 1, 4);
    credits_frame_tile(2, 26, 5); credits_frame_tile(37, 26, 6);

    credits_text_tile = CREDITS_TEXT_BASE;
    credits_center_text(160, 3, "CASTLEVANIA MD");
    credits_center_text(160, 5, "CREDITS");
    // Combined body: logo x=48..159, 16px gap, text x=176..271.
    // The full 224px-wide body is centered on the 320px screen.
    VDP_setTileMapDataRectEx(BG_A, credits_logo_map, CREDITS_LOGO_BASE, 6, 7, 14, 14, 14, CPU);
    credits_center_text(224, 9, "SNES PORT");
    credits_center_text(224, 11, "RUMBLEMINZE");
    credits_center_text(224, 13, "2025");
    credits_center_text(224, 17, "16-BIT TILES");
    credits_center_text(224, 19, "FIUKE BNUY");
    credits_center_text(160, 22, "MEGA DRIVE / GENESIS");
    credits_center_text(160, 23, "PORT BY 5 CUSTOMS");
    credits_center_text(160, 25, "START OR B - RETURN");
    VDP_setEnable(TRUE);

    u16 prev = JOY_readJoypad(JOY_1);
    while (TRUE)
    {
        u16 pad = JOY_readJoypad(JOY_1);
        if (pad & ~prev & (BUTTON_START | BUTTON_B)) break;
        prev = pad;
        SYS_doVBlankProcess();
    }
}
#endif

// Power-on options hub. Credits are a submenu; preferences survive the round trip.
#ifndef START_SECTION
#include "options_menu_data.inc"
#define OPTION_LINES 7
#define OPTION_SOUND_TEST OPTION_LINES
#define OPTION_CREDITS (OPTION_LINES + 1)
#define OPTION_MENU_LINES (OPTION_LINES + 2)
#define OPTION_MUSIC 6
#define OPTION_GRAPHICS 4
#define OPTION_PALETTE 5
#define OPTIONS_FIRST_ROW 15
#define OPTIONS_LOGO_BASE (TILE_USER_INDEX + LEVEL_TILES)
#define OPTIONS_BORDER_BASE (OPTIONS_LOGO_BASE + OPTIONS_LOGO_TILES)

// Physical screen columns: unlike draw_text(), there is no NES side offset here.
static void options_text(u16 col, u16 row, const char *text)
{
    draw_text(col - NES_X / 8, row, text);
}

static void options_border_tile(u16 x, u16 y, u16 tile)
{
    VDP_setTileMapXY(BG_A, TILE_ATTR_FULL(PAL3, 0, 0, 0, OPTIONS_BORDER_BASE + tile), x, y);
}

static void options_art(void)
{
    VDP_loadTileData(ART(level_tiles), TILE_USER_INDEX, LEVEL_TILES, DMA);
    PAL_setColors(0, ART_PAL(level), 64, DMA);
    VDP_loadTileData(options_logo_tiles, OPTIONS_LOGO_BASE, OPTIONS_LOGO_TILES, DMA);
    VDP_loadTileData(options_border_tiles, OPTIONS_BORDER_BASE, 8, DMA);
    PAL_setColors(32, options_logo_palette, 16, DMA);
    PAL_setColors(48, options_border_palette, 16, DMA);
}

static void options_frame(void);

// Screen off, planes cleared, the menu art, the logo and the border: shared by the game choice and OPTIONS.
static void options_frame_layout(void)
{
    VDP_setEnable(FALSE);
    VDP_setWindowOff();
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    options_art();
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 0);
    VDP_setVerticalScroll(BG_A, 0);
    VDP_setVerticalScroll(BG_B, 0);
    sprite_n = 0; sprites_end();
    VDP_setTileMapDataRectEx(BG_A, options_logo_map, OPTIONS_LOGO_BASE, 6, 0, 28, 12, 28, CPU);
    options_frame();
}

static void options_layout(void)
{
    options_frame_layout();
    options_text(16, 13, "OPTIONS");
    options_text(6, OPTIONS_FIRST_ROW + OPTION_SOUND_TEST, "SOUND TEST");
    options_text(20, OPTIONS_FIRST_ROW + OPTION_SOUND_TEST, "   A - LISTEN   ");
    options_text(6, OPTIONS_FIRST_ROW + OPTION_CREDITS, "CREDITS");
    options_text(20, OPTIONS_FIRST_ROW + OPTION_CREDITS, "   A - VIEW     ");
    options_text(10, 27, "START - CONTINUE");
}

// The border around the menu rows (rows 12 to 25).
static void options_frame(void)
{
    for (u16 x = 4; x < 36; x++)
    {
        options_border_tile(x, 12, 1);
        options_border_tile(x, 25, 1);
    }
    for (u16 y = 13; y < 25; y++)
    {
        options_border_tile(3, y, 2);
        options_border_tile(36, y, 2);
    }
    options_border_tile(3, 12, 3); options_border_tile(36, 12, 4);
    options_border_tile(3, 25, 5); options_border_tile(36, 25, 6);
}

// Listen using the uncommitted MUSIC choice, then return to the same options row.
static u8 sound_test_screen(u8 mode)
{
    static const char *const titles[15] = {
        "01 PROLOGUE", "02 VAMPIRE KILLER", "03 STALKER", "04 WICKED CHILD",
        "05 OUT OF TIME", "06 HEART OF FIRE", "07 WALKING ON THE EDGE",
        "08 NOTHING TO LOSE", "09 POISON MIND", "10 BLACK NIGHT", "11 VOYAGER",
        "12 STAGE CLEAR", "13 ALL CLEAR", "14 LOSE LIFE", "15 GAME OVER"
    };
    static const char *const modes[3] = { "ORIGINAL", "FM", "YM2612" };
    u8 saved_mode = sound_get_music_mode();
    sound_set_music_mode(mode);
    music_hold(FALSE);
    VDP_setEnable(FALSE);
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    options_art();
    sprite_n = 0; sprites_end();
    options_text(13, 1, "CASTLEVANIA MD");
    options_text(15, 3, "SOUND TEST");
    options_text(10, 5, "MUSIC"); options_text(21, 5, modes[mode]);
    for (u16 x = 4; x < 36; x++)
    { options_border_tile(x, 6, 1); options_border_tile(x, 24, 1); }
    for (u16 y = 7; y < 24; y++)
    { options_border_tile(3, y, 2); options_border_tile(36, y, 2); }
    options_border_tile(3, 6, 3); options_border_tile(36, 6, 4);
    options_border_tile(3, 24, 5); options_border_tile(36, 24, 6);
    for (u8 i = 0; i < 15; i++) options_text(7, 7 + i, titles[i]);
    options_text(11, 23, "STATUS - STOPPED");
    options_text(10, 25, "LEFT-RIGHT - MUSIC");
    options_text(5, 27, "A-START PLAY  C STOP  B RETURN");
    u8 selected = 0, current = 0;
    u16 prev = JOY_readJoypad(JOY_1);
    options_border_tile(4, 7, 7);
    VDP_setEnable(TRUE);
    while (TRUE)
    {
        u16 pad = JOY_readJoypad(JOY_1), pressed = pad & ~prev;
        prev = pad;
        if (pressed & BUTTON_B) break;
        if (pressed & (BUTTON_UP | BUTTON_DOWN))
        {
            options_border_tile(4, 7 + selected, 0);
            selected = (selected + ((pressed & BUTTON_DOWN) ? 1 : 14)) % 15;
            options_border_tile(4, 7 + selected, 7);
        }
        bool restart = FALSE;
        if (pressed & (BUTTON_LEFT | BUTTON_RIGHT))
        {
            restart = music_playing();
            mode = (mode + ((pressed & BUTTON_LEFT) ? 2 : 1)) % 3;
            sound_set_music_mode(mode);
            options_text(21, 5, "        ");
            options_text(21, 5, modes[mode]);
        }
        if (pressed & (BUTTON_A | BUTTON_START)) current = selected;
        if (restart || (pressed & (BUTTON_A | BUTTON_START)))
        {
            // The legacy banks have these two catalogue entries in reverse order.
            u8 id = current;
            if (mode != SOUND_MUSIC_YM2612 && (id == 4 || id == 6)) id = 10 - id;
            music_play(id);
        }
        if (pressed & BUTTON_C) music_stop();
        options_text(5, 23, "                              ");
        if (music_playing())
        { options_text(5, 23, "PLAY"); options_text(11, 23, titles[current]); }
        else options_text(11, 23, "STATUS - STOPPED");
        SYS_doVBlankProcess();
    }
    music_stop();
    sound_set_music_mode(saved_mode);
    return mode;
}

#ifdef VK_BASE
// Vampire Collection MD: the game choice after the boot logo. CASTLEVANIA goes on to its OPTIONS hub;
// VAMPIRE KILLER (MSX2) leaves this game for good (collection_launch_vk).
#define SELECT_ROW_CV 17
#define SELECT_ROW_VK 20
static void game_select_screen(void)
{
    static const u16 rows[2] = { SELECT_ROW_CV, SELECT_ROW_VK };
    music_play_menu();
    options_frame_layout();
    options_text(14, 13, "SELECT GAME");
    options_text(6, SELECT_ROW_CV, "CASTLEVANIA");
    options_text(28, SELECT_ROW_CV, "NES");
    options_text(6, SELECT_ROW_VK, "VAMPIRE KILLER");
    options_text(28, SELECT_ROW_VK, "MSX2");
    options_text(13, 27, "START - PLAY");

    u8 line = 0;
    options_border_tile(4, rows[0], 7);
    VDP_setEnable(TRUE);
    u16 prev = JOY_readJoypad(JOY_1);
    while (TRUE)
    {
        u16 pad = JOY_readJoypad(JOY_1), pressed = pad & ~prev;
        prev = pad;
        if (pressed & (BUTTON_START | BUTTON_A | BUTTON_C)) break;
        if (pressed & (BUTTON_UP | BUTTON_DOWN))
        {
            options_border_tile(4, rows[line], 0);
            line ^= 1;
            options_border_tile(4, rows[line], 7);
        }
        SYS_doVBlankProcess();
    }
    // Castlevania-only ROM: no Vampire Killer after VK_BASE, CASTLEVANIA goes on instead of a crash.
    if (line == 1 && collection_has_vk()) collection_launch_vk();
}
#endif

static void options_screen(void)
{
    static const char *const names[OPTION_LINES] = { "DIFFICULTY", "LOOP", "WEAPON SWAP", "CONTROLS", "GRAPHICS",
                                                     "PALETTE", "MUSIC" };
    static const char *const values[OPTION_LINES][14] = {
        { "     NORMAL     ", "    VS HARD     ", "      EASY      " },
        { "    1ST LOOP    ", "    2ND LOOP    " },
        { "       ON       ", "      OFF       " },
        { "  Z-SWAP C-USE  ", "  Z-USE C-SWAP  " },
        { "    ORIGINAL    ", "     16-BIT     " },
        { "      NES       ", "     FCEUX      ", "  KITRINX34 HS  ", "   KITRINX34    ", "NES CLASSIC FBX ",
          " NINTENDULATOR  ", " PLAYCHOICE 10  ", "      PVM       ", "      REAL      ", " SMOOTH Y2 FBX  ",
          " VS CASTLEVANIA ", "   GREYSCALE    ", "    APPLE II    ", "  VIRTUAL BOY   " },
        { "    ORIGINAL    ", "       FM       ", "     YM2612     " },
    };
    static const u8 counts[OPTION_LINES] = { 3, 2, 2, 2, 2, 14, 3 };
    u8 choice[OPTION_LINES] = { difficulty, second_loop, !weapon_swap, z_throws, !nes_art, nes_palette, sound_get_music_mode() };

    music_play_menu();
    options_layout();
    for (u8 i = 0; i < OPTION_LINES; i++)
    {
        options_text(6, OPTIONS_FIRST_ROW + i, names[i]);
        options_text(20, OPTIONS_FIRST_ROW + i, values[i][choice[i]]);
    }
    options_border_tile(4, OPTIONS_FIRST_ROW, 7);
    VDP_setEnable(TRUE);

    u8 line = 0;
    u16 prev = JOY_readJoypad(JOY_1);
    while (TRUE)
    {
        u16 pad = JOY_readJoypad(JOY_1), pressed = pad & ~prev;
        prev = pad;
        if ((line == OPTION_CREDITS || line == OPTION_SOUND_TEST) && (pressed & (BUTTON_A | BUTTON_C)))
        {
            if (line == OPTION_CREDITS) credits_screen();
            else { choice[OPTION_MUSIC] = sound_test_screen(choice[OPTION_MUSIC]); music_play_menu(); }
            options_layout();
            for (u8 i = 0; i < OPTION_LINES; i++)
            {
                options_text(6, OPTIONS_FIRST_ROW + i, names[i]);
                options_text(20, OPTIONS_FIRST_ROW + i, values[i][choice[i]]);
            }
            options_border_tile(4, OPTIONS_FIRST_ROW + line, 7);
            VDP_setEnable(TRUE);
            prev = JOY_readJoypad(JOY_1);  // consume the key that closed credits
            continue;
        }
        if (pressed & BUTTON_START) break;
        if (pressed & (BUTTON_UP | BUTTON_DOWN))
            line = (line + ((pressed & BUTTON_DOWN) ? 1 : OPTION_MENU_LINES - 1)) % OPTION_MENU_LINES;
        if (line < OPTION_LINES && (pressed & (BUTTON_LEFT | BUTTON_RIGHT | BUTTON_A)))
        {
            u8 n = counts[line];
            choice[line] = (choice[line] + ((pressed & BUTTON_LEFT) ? n - 1 : 1)) % n;
            options_text(20, OPTIONS_FIRST_ROW + line, values[line][choice[line]]);
            if (line == OPTION_GRAPHICS && choice[line] && choice[OPTION_PALETTE])
            { choice[OPTION_PALETTE] = 0; options_text(20, OPTIONS_FIRST_ROW + OPTION_PALETTE, values[OPTION_PALETTE][0]); }
            if (line == OPTION_PALETTE && choice[OPTION_GRAPHICS])
            { choice[OPTION_GRAPHICS] = 0; options_text(20, OPTIONS_FIRST_ROW + OPTION_GRAPHICS, values[OPTION_GRAPHICS][0]); }
            if (line == OPTION_GRAPHICS || line == OPTION_PALETTE)
            {
                nes_art = !choice[OPTION_GRAPHICS]; nes_palette = choice[OPTION_PALETTE];
                SYS_doVBlankProcess();                 // the new tiles go in while the screen is off
                VDP_setEnable(FALSE);
                options_art();
                VDP_setEnable(TRUE);
            }
        }
        for (u8 i = 0; i < OPTION_MENU_LINES; i++)
            options_border_tile(4, OPTIONS_FIRST_ROW + i, i == line ? 7 : 0);
        SYS_doVBlankProcess();
    }
    difficulty = choice[0]; second_loop = choice[1]; weapon_swap = !choice[2]; z_throws = choice[3];
    nes_art = !choice[OPTION_GRAPHICS]; nes_palette = choice[OPTION_PALETTE];
    music_stop();
    sound_set_music_mode(choice[OPTION_MUSIC]);
}
#endif

// The NES game's title (state 1): the small bat comes out of the tree, then the big one flaps in a loop. START is
// taken from the first frame: the sprites stay still and PUSH START KEY blinks, then the introduction comes. (The
// NES game plays a demo when nobody has pressed START for 652 frames: FALSE is returned then.)
#define TITLE_DEMO_AFTER 652
static bool title_screen(void)
{
    screen_load(ART(title_tiles), TITLE_TILES, ART_PAL(title), title_map);
    u16 f = 0, prev = BUTTON_START;                 // START still held from a game over screen does not count
    s16 start_t = -1;
    u16 waited = 0;
    while (start_t < TITLE_START_FRAMES)
    {
        u16 pad = JOY_readJoypad(JOY_1), pressed = pad & ~prev;
        prev = pad;
        if (start_t < 0 && ++waited > TITLE_DEMO_AFTER) return FALSE;
        if (start_t < 0 && (pressed & BUTTON_START)) start_t = 0;
        if (start_t < 0)
        {
            screen_sprites(title_sprites, &title_lists[title_frames[f]]);
            if (++f >= TITLE_FRAMES) f = TITLE_LOOP;
        }
        else
        {
            for (u8 i = 0; i < TITLE_START_CELLS; i++)
            {
                u16 c = title_start_cells[i];
                VDP_setTileMapXY(BG_A, TILE_USER_INDEX + (title_hidden[start_t] ? 0 : title_map[c]), NES_X / 8 + (c & 31), c >> 5);
            }
            start_t++;
        }
        SYS_doVBlankProcess();
    }
    return TRUE;
}

// The introduction (NES state 4): Simon walks to the castle gate, bats fly by; no control
static void intro_scene(void)
{
    black_frames(INTRO_BLACK);
    screen_load(ART(intro_tiles), INTRO_TILES, ART_PAL(intro), intro_map);
    if (MIKU_enabled()) MIKU_set_palette(ART_PAL(intro));
    music_play(MUS_PROLOGUE);
    for (u16 f = 0; f < INTRO_FRAMES; f++)
    {
        if (MIKU_enabled())
        {
            const ScreenList *list = &intro_lists[intro_frames[f]];
            sprite_n = 0;
            for (u8 i = 0; i < list->count && sprite_n < MAX_SPRITES; i++)
            {
                if (miku_intro[f].skip & (1UL << i)) continue;
                const ScreenSprite *sp = &intro_sprites[list->first + i];
                VDP_setSpriteFull(sprite_n, sp->x, sp->y, SPRITE_SIZE(1, 2), sp->attr + TILE_USER_INDEX, sprite_n + 1);
                sprite_n++;
            }
            if (miku_intro[f].skip) draw_miku_frame(miku_intro[f].pose, NULL, miku_intro[f].x, miku_intro[f].y, miku_intro[f].mirror, FALSE);
            sprites_end();
        }
        else screen_sprites(intro_sprites, &intro_lists[intro_frames[f]]);
        SYS_doVBlankProcess();
    }
}

// The ending (NES state 15), after Dracula's tally: the castle's towers sink (a rumble every 64 frames), then the
// credits are written page after page into the picture, faded in and out through their palette, to "Voyager"
static void ending_fade(u8 k)
{
    u16 c[3];
    for (u8 i = 0; i < 3; i++)
        c[i] = !nes_art ? ending_text[k][i] : ending_text_nesidx[k][i] < 64 ? nes_palettes[nes_palette][ending_text_nesidx[k][i]]
             : ending_text_nes[k][i];
    PAL_setColors(ENDING_TEXT_PAL * 16 + 1, c, 3, DMA);
}

static void ending_scene(void)
{
    music_stop();
    black_frames(ENDING_BLACK);
    screen_load(ART(ending_tiles), ENDING_TILES, ART_PAL(ending), ending_map);
    ending_fade(0);
    u16 w = 0, fd = 0, sd = 0;
    for (u16 f = 0; f < ENDING_FRAMES; f++)
    {
        for (; sd < ENDING_SOUNDS && ending_sounds[sd].frame <= f; sd++)
        {
            u8 v = ending_sounds[sd].value;
            if (v < SFX_01) music_play(v); else sfx_play(v);
        }
        for (; w < ENDING_WRITES && ending_writes[w].frame <= f; w++)
        {
            const ScreenWrite *e = &ending_writes[w];
            VDP_setTileMapXY(BG_A, e->word + TILE_USER_INDEX, NES_X / 8 + (e->cell & 31), e->cell >> 5);
        }
        for (; fd < ENDING_FADES && ending_fades[fd].frame <= f; fd++) ending_fade(ending_fades[fd].value);
        screen_sprites(ending_sprites, &ending_lists[ending_frames[f]]);
        SYS_doVBlankProcess();
    }
}

// the level's tiles, palettes and planes back, then the stage starts (after the title or a game over screen)
static void game_setup(void)
{
    VDP_setEnable(FALSE);
    loaded_block = 0xFF;                                        // the title and the options have used the tiles
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_setTileMapDataRectEx(WINDOW, level_hud, map_base, NES_X / 8, 0, 32, HUD_ROWS, 32, CPU);
    VDP_setWindowVPos(FALSE, HUD_ROWS);
    VDP_setVerticalScroll(BG_A, 8);
    VDP_setVerticalScroll(BG_B, 8);
    restart_level();
    VDP_setEnable(TRUE);
}

// ---------------------------------------------------------------- the title's demos
// The NES game's own inputs (tools/demo_to_md.py), replayed: one record frame per play frame, none while the game
// stands still for a whip upgrade (the NES game's reader $FEB3 is not called then). Its demos are in stages 12, 7 and
// 8 in turn. They are played on the normal difficulty of the first loop, then the player's choice comes back. START,
// the player's or the demo's last frame, ends one.
#define DEMOS 3
static const u8 *const demos[DEMOS] = { demo_stage12, demo_stage7, demo_stage8 };
static const u8 demo_secs[DEMOS] = { SEC_ST12, SEC_ST7, SEC_ST8 };
static u8 demo_turn = 0;
static const u8 *demo_p = NULL;                // the demo playing, NULL: a game
static u8 demo_left, demo_pressed, demo_held, player_difficulty;
static bool player_loop;

static u16 nes_buttons(u8 b)                   // NES A jumps (B here), NES B whips (A here)
{
    u16 p = 0;
    if (b & 0x80) p |= BUTTON_B;
    if (b & 0x40) p |= BUTTON_A;
    if (b & 0x10) p |= BUTTON_START;
    if (b & 0x08) p |= BUTTON_UP;
    if (b & 0x04) p |= BUTTON_DOWN;
    if (b & 0x02) p |= BUTTON_LEFT;
    if (b & 0x01) p |= BUTTON_RIGHT;
    return p;
}

// the demo's buttons for this frame; FALSE at its end or after the death animation
static bool demo_read(u16 *pad, u16 *pressed)
{
    // Recorded inputs no longer describe a valid run after a death. Let the
    // death animation finish without consuming them, then return to the title
    // before ST_DEAD would restart the level with a partly consumed record.
    if (state == ST_DEAD)
    {
        *pad = 0; *pressed = 0;
        return state_t < DEAD_FRAMES - 1;
    }
    if (!demo_left)
    {
        if (*demo_p == 0xFF) return FALSE;
        demo_left = demo_p[0]; demo_pressed = demo_p[1]; demo_held = demo_p[2];
        demo_p += 3;
        *pressed = nes_buttons(demo_pressed);
    }
    else *pressed = 0;
    demo_left--;
    *pad = nes_buttons(demo_held);
    return TRUE;
}

static void new_game(void);

// the title, then the introduction and a new game, or the next demo when nobody presses START
static void front_end(void)
{
    if (demo_p) { demo_p = NULL; difficulty = player_difficulty; second_loop = player_loop; }
    if (title_screen())
    {
        intro_scene();
        new_game();
        return;
    }
    player_difficulty = difficulty; player_loop = second_loop;
    difficulty = DIFF_NORMAL; second_loop = FALSE;
    new_game();
    section = demo_secs[demo_turn];
    demo_p = demos[demo_turn]; demo_left = 0;
    demo_turn = (demo_turn + 1) % DEMOS;
}

// a new game, and also CONTINUE: the NES game starts the block again (the courtyard for stages 1 to 3) with the
// score at 0 and 3 lives
static void new_game(void)
{
    score = 0; lives = difficulty == DIFF_EASY ? 9 : START_LIVES; whip_level = START_WHIP;
    subweapon = START_SUB; other_sub = SUB_NONE; shot_level = other_level = 0; hit_counter = 0;
    section = SEC_COURT;
    paused = FALSE; game_over = FALSE;
}

// The game over screen (NES state $0D): the HUD stays, GAME OVER, CONTINUE and END below it. The NES game moves the
// heart with SELECT; the pad has none, so UP and DOWN do it here. START on CONTINUE starts again, on END the title
// comes back. Returns TRUE for CONTINUE.
static bool game_over_screen(void)
{
    music_play(MUS_GAME_OVER);
    sprite_n = 0; sprites_end();
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 0);
    PAL_setColor(0, world_palette[0]);
    for (u16 n = GAMEOVER_AFTER - DEAD_FRAMES; n; n--) SYS_doVBlankProcess();
    VDP_setTileMapDataRectEx(BG_A, gameover_map, map_base, NES_X / 8, GAMEOVER_ROW0, 32, 30 - GAMEOVER_ROW0, 32, CPU);
    sprite_n = 0;
    draw_pose(&obj_poses[OBJ_HUDBOX], NES_X + 128, 22, FALSE);   // the HUD's sub-weapon frame
    sprites_end();
    bool end = FALSE;
    u16 prev = JOY_readJoypad(JOY_1);
    while (TRUE)
    {
        u16 pad = JOY_readJoypad(JOY_1), pressed = pad & ~prev;
        prev = pad;
        if (pressed & BUTTON_START) return !end;
        if (pressed & (BUTTON_UP | BUTTON_DOWN))
        {
            end = !end;
            sfx_play(SFX_04);
            VDP_setTileMapXY(BG_A, end ? map_base : map_base + GAMEOVER_HEART, NES_X / 8 + GAMEOVER_CURSOR_COL, GAMEOVER_ROW_CONTINUE);
            VDP_setTileMapXY(BG_A, end ? map_base + GAMEOVER_HEART : map_base, NES_X / 8 + GAMEOVER_CURSOR_COL, GAMEOVER_ROW_END);
        }
        SYS_doVBlankProcess();
    }
}

int main(bool hardReset)
{
    VDP_setScreenWidth320();
    VDP_setPlaneSize(PLANE_COLS, 32, TRUE);
    VDP_setScrollingMode(HSCROLL_PLANE, VSCROLL_PLANE);
    sound_init();

#ifndef START_SECTION                              /* the test builds go straight to the game */
    startup_logo_show();
#ifdef VK_BASE
    game_select_screen();
#endif
    options_screen();
    front_end();
#else
    new_game();
#endif
    game_setup();
#ifdef START_SECTION                               /* make EXTRA_FLAGS=-DSTART_SECTION=2: testing aid, start in a part */
    section = START_SECTION;
    restart_level();
    subweapon = START_SUB; hearts = 50; hud_update();
#ifdef START_X                                     /* with -DSTART_X=3585 -DSTART_Y=96: start at this anchor x / head y */
    section = START_SECTION; simon_x = START_X; simon_y = START_Y;
    cam_x = simon_x - SCROLL_AT;
    if (cam_x < sections[section].cam0) cam_x = sections[section].cam0;
    if (cam_x > sections[section].cam1) cam_x = sections[section].cam1;
    invalidate_columns(TRUE);
    stream_columns(PLANE_COLS);
#endif
#endif

    u16 prev = 0;
    bool was_dead = FALSE;
    while (TRUE)
    {
        u16 pad = JOY_readJoypad(JOY_1);
        u16 pressed = pad & ~prev;
        prev = pad;
        if (demo_p && ((pressed & BUTTON_START) || (!whip_freeze && !hall_load && !demo_read(&pad, &pressed))))
        {
            music_stop();                                       // START or the demo's end: the title again
            front_end();
            game_setup();
            prev = JOY_readJoypad(JOY_1);
            continue;
        }
        frame_count++;
        held_pad = pad;
        if (whip_freeze)
        {
            if (!(frame_count & 1)) whip_freeze--;
            goto draw;
        }
        if (invuln) invuln--;

        if (paused)
        {
            if (!pause_update(pressed)) { SYS_doVBlankProcess(); continue; }
        }
        else if ((pressed & BUTTON_START) && !hall_load && state != ST_DOOR && state != ST_CLIMB && state != ST_EXIT_CLIMB && state != ST_GATE && state != ST_DEAD)
        {
            paused = TRUE;
            music_hold(TRUE);
            sfx_play(SFX_54);
            SYS_doVBlankProcess();
            continue;
        }
        if (pressed & BUTTON_SWAP) swap_subweapon();
        if (hit_effect.frames) hit_effect.frames--;
        bool no_pad = state == ST_DEAD || state == ST_GATE || state == ST_DOOR || state == ST_CLIMB || state == ST_EXIT_CLIMB || hall_load || boss_tally();
        if (hall_load && !--hall_load) VDP_setEnable(TRUE);
        // the platforms move first and carry Simon if he stands on one
        plats_update(state == ST_STAND || state == ST_WALK || state == ST_CROUCH || state == ST_WHIP);
        if (!hall_load) simon_update(no_pad ? 0 : pad, no_pad ? 0 : pressed);
        if (game_over)
        {
            bool cont = game_over_screen();
            if (cont) new_game();
            else front_end();
            game_setup();
            prev = JOY_readJoypad(JOY_1);
            continue;
        }
        // TIME: one unit every 64 frames, stopped during the gate cutscene and the doors; at 0 Simon dies like at 0 health
        // (97 frames to the restart in both cases in the NES game)
        if (time_left && !watch_t && !boss_tally() && state != ST_GATE && state != ST_DOOR && state != ST_CLIMB && state != ST_EXIT_CLIMB && !hall_load && ++time_tick >= TIME_TICK)
        {
            time_tick = 0;
            hud_number(18, 1, --time_left, 4, hud_digit);
            if (!time_left && state != ST_DEAD) { state = ST_DEAD; state_t = 0; stair_whip = FALSE; air_whip = FALSE; }
        }
        if (state == ST_DEAD && !was_dead) music_play(MUS_LOSE_LIFE);   // the NES game's sound $4E
        was_dead = state == ST_DEAD;
        shots_update();
        objects_update();
        blocks_update();
        treasures_update(no_pad ? 0 : pad);
        rosary_update();
        if (watch_t) watch_t--;
        if (potion_t && !--potion_t) sfx_play(SFX_1C);         // it wears off ($FB12)
        enemies_update();
        panthers_update();
        gens_update();
        objgens_update();
        if (!boss_tally()) monsters_update();                  // Death's sickles stop for the tally, as on the NES
        boss_update();
        hud_bars_update();

        if (state != ST_DOOR)                       // the door scrolls the screen by itself
        {
            cam_x = simon_x - SCROLL_AT;
            if (cam_x < sections[section].cam0) cam_x = sections[section].cam0;
            if (cam_x > sections[section].cam1) cam_x = sections[section].cam1;
            if (screen_locked) cam_x = BOSS_CAM;
        }

    draw:
        sprite_n = 0;
        if (state == ST_GATE && gate_phase)                      // the archway's mask, in front of Simon
            draw_pose(&obj_poses[OBJ_MASK], NES_X + (section == SEC_ST16 ? ARCH_MASK_X : GATE_MASK_X) - cam_x,
                      section == SEC_ST16 ? ARCH_MASK_Y : GATE_MASK_Y, FALSE);
        bool door_open = state == ST_DOOR && (door_phase == 2 || (door_phase == 1 && state_t >= 16) || (door_phase == 3 && state_t < 3));
        bool door_half = state == ST_DOOR && ((door_phase == 1 && state_t < 16) || (door_phase == 3 && state_t >= 3));
        if (!(invuln && (frame_count & 2)) && !(potion_t && (frame_count & 1)) && !hall_load && !lost)   // blink while invincible
        {
            bool curled = state == ST_JUMP && !air_whip && simon_jump_curled[state_t < JUMP_FRAMES ? state_t : JUMP_FRAMES - 1];
            if (whip_freeze & 3) pal_force = PAL3 << 13;
            if (MIKU_enabled()) draw_miku(simon_pose(), NES_X + simon_x - cam_x, simon_y - (curled ? CURL_LIFT : 0), facing_left, state == ST_CLIMB);
            else if (state == ST_CLIMB) draw_climbing();
            else draw_pose(simon_pose(), NES_X + simon_x - cam_x, simon_y - (curled ? CURL_LIFT : 0), facing_left);
            pal_force = 0;
        }
        if (door_open || door_half)                              // behind Simon; it opens towards the next part
        {
            const Section *sec = &sections[section];
            s16 dy = sec->door_y - 16;
            if (sec->door > 0)
            {
                s16 dx = door_tile_column(sec) * 8;
                if (door_open) draw_object(&obj_poses[OBJ_DOOR_OPEN], dx, dy, FALSE);
                else           draw_object(&obj_poses[OBJ_DOOR_HALF], dx + 8, dy, FALSE);
            }
            else
            {
                s16 dx = door_tile_column(sec) * 8;
                if (door_open) draw_object(&obj_poses[OBJ_DOOR_OPEN], dx - 8, dy, TRUE);
                else           draw_object(&obj_poses[OBJ_DOOR_HALF], dx - 16, dy, TRUE);
            }
        }
        impact_draw();
        plats_draw();
        enemies_draw();
        panthers_draw();
        monsters_draw();
        boss_draw();
        objects_draw();
        treasure_draw();
        debris_draw();
        shots_draw();
        draw_pose(&obj_poses[OBJ_HUDBOX], NES_X + 128, 22, FALSE);   // the sub-weapon frame in the HUD
        if (subweapon) draw_pose(subweapon_pose(), NES_X + 136, 26, FALSE);   // OAM x 136, y 26 in the NES game
        if (sprite_n) VDP_setSpriteLink(sprite_n - 1, 0);

        if (show_pos)
        { char b[40]; sprintf(b, "x%4d y%3d st%-2d id%-2d p%-4d", simon_x, simon_y, state, stair_id, stair_pos); VDP_drawTextBG(WINDOW, b, 5, 0); }
        stream_columns(hall_load ? PLANE_COLS : 3);
        stream_back(hall_load ? PLANE_COLS : 4);
        VDP_setHorizontalScrollVSync(BG_A, NES_X - cam_x);    // at the vertical blank: written now, mid-screen,
        VDP_setHorizontalScrollVSync(BG_B, -(cam_x >> 1));    // the picture tore where the beam was
        VDP_updateSprites(sprite_n, DMA_QUEUE);
        SYS_doVBlankProcess();
    }
    return 0;
}

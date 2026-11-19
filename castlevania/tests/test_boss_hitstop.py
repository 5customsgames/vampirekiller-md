#!/usr/bin/env python3
"""Check the actual boss update: eight frozen frames, then normal movement."""
from pathlib import Path
import re, subprocess, tempfile, sys
root=Path(__file__).resolve().parents[1]
s=Path(sys.argv[1]).read_text() if len(sys.argv)>1 else (root/'src/main.c').read_text()
def fn(sig):
 start=s.index(sig+'\n{');return s[start:s.index('\n}',start)+2]
def block(start,end):
 a=s.index(start);return s[a:s.index(end,a)+len(end)]
defines='\n'.join(line for line in s.splitlines() if line.startswith('#define '))
enums=block('enum { B_SLEEP,','};')+block('enum { DC_WAIT,','};')
boss_type=block('typedef struct { s32 x, y; s16 vx, vy, cy; bool left, up, spawned, medusa,','} Boss;')
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;typedef int8_t s8;typedef uint16_t u16;typedef int16_t s16;typedef int32_t s32;
#define TRUE true
#define FALSE false
'''
stubs=r'''
#undef BOSS_CAM
#define BOSS_CAM 0
#undef LOOP_VX
#define LOOP_VX 0
static Boss boss;
static u8 section,boss_sec,watch_t,player_hp,tally_phase,state;
static bool screen_locked,facing_left;
static u16 frame_count;
static s16 cam_x,simon_x,simon_y;
enum {E_FREE,M_FREE,M_MUMMY,M_IGOR,M_SNAKE,ST_DEAD,MUS_POISON_MIND,MUS_ALL_CLEAR,MUS_STAGE_CLEAR,SN_FALL};
typedef struct {s32 x,y;s8 dir;s16 vy;u8 kind,state,immune;} Monster;
static Monster monsters[MAX_MONSTERS];
static struct {u8 state;} enemies[MAX_ENEMIES];
static int frank_calls,death_calls,hits,checks,failures;
static s16 simon_sx(void){return 200;}
static void tally_update(void){}
static void music_play(u8 id){(void)id;}
static void monsters_init(void){}
static Monster *monster_new(u8 kind,u8 limit){(void)kind;(void)limit;return NULL;}
static bool solid_at(s16 x,s16 y){(void)x;(void)y;return true;}
static bool overlap(s16 a,s16 b,s16 c,s16 d,s16 e,s16 f,s16 g,s16 h){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;(void)h;return false;}
static void hud_update(void){}
static void drac_update(void){}
static void drac_hits(void){}
static void frank_update(void){frank_calls++;boss.x+=256;}
static void death_update(void){death_calls++;boss.x+=256;}
static void statue_erase(void){}
static void boss_target(void){boss.state=B_GLIDE;}
static void boss_swoop(void){boss.state=B_SWOOP;}
static void boss_hits_at(s16 cx,s16 cy,s16 hw,s16 hh,bool touch){(void)cx;(void)cy;(void)hw;(void)hh;(void)touch;hits++;}
static void check(const char*n,bool ok){checks++;if(!ok){if(failures<12)printf("FAIL %s\n",n);failures++;}}
'''
main=r'''
int main(void){
 for(int type=0;type<4;type++){
  memset(&boss,0,sizeof(boss));boss.spawned=true;boss.medusa=type==1;boss.frank=type==2;boss.death=type==3;
  boss.state=type==0?B_GLIDE:type==1?B_FLOAT:type==2?B_HOVER:B_DJUMP;
  boss.x=100<<8;boss.y=100<<8;boss.vx=256;boss.vy=128;boss.cy=100;boss.tx=200;boss.timer=100;boss.anim=9;
  boss.immune=BOSS_IMMUNE;frank_calls=death_calls=hits=0;
  Boss before=boss;
  for(int f=0;f<8;f++){
   boss_update();
   check("stun freezes position",boss.x==before.x&&boss.y==before.y);
   check("stun freezes velocity and AI state",boss.vx==before.vx&&boss.vy==before.vy&&boss.state==before.state);
   check("stun freezes AI timer and animation",boss.timer==before.timer&&boss.anim==before.anim);
   check("stun decremented once per frame",boss.immune==7-f);
   check("special boss AI not called during stun",!frank_calls&&!death_calls);
  }
  boss_update();
  check("boss moves on ninth frame",boss.x!=before.x||boss.y!=before.y);
  check("animation resumes once",boss.anim==before.anim+1);
  if(type==0||type==1)check("AI timer resumes once",boss.timer==before.timer-1||type==0);
  if(type==2)check("Frankenstein resumes once",frank_calls==1);
  if(type==3)check("Death resumes once",death_calls==1);
 }
 memset(&boss,0,sizeof(boss));boss.spawned=true;boss.state=B_FLAMES;boss.immune=8;boss.timer=10;
 boss_update();check("lethal blow does not delay death flames",boss.timer==11);
 memset(&boss,0,sizeof(boss));boss.spawned=true;boss.state=B_GLIDE;boss.immune=8;boss.anim=10;watch_t=10;
 boss_update();check("stopwatch and hit stun do not double-decrement",boss.immune==7&&boss.anim==10);
 printf("%d boss hit-stop checks, %d failures\n",checks,failures);return failures?1:0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 c=Path(tmp)/'test.c';exe=Path(tmp)/'test'
 c.write_text(prefix+defines+'\n'+enums+boss_type+stubs+fn('static void boss_hits(void)')+fn('static void boss_update(void)')+main)
 subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)

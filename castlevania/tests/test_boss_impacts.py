#!/usr/bin/env python3
"""Exercise actual damage/effect paths for bosses, including projectile rejection."""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[1];s=(root/'src/main.c').read_text()
def fn(sig):
 start=re.search(re.escape(sig)+r'[^\n]*\n\{',s).start();return s[start:s.index('\n}',start)+2]
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;typedef int16_t s16;typedef uint16_t u16;typedef int32_t s32;
#define TRUE true
#define FALSE false
#define FEET 32
#define MAX_SHOTS 3
#define MAX_MONSTERS 4
#define BOSS_CAM 0
#define SFX_14 20
#define OBJ_SPARKLE 2
#define WHIP_HIT_FRAME 17
enum {ST_STAND,ST_WHIP};enum {W_FREE,W_FLY,W_BURN};
enum {SUB_DAGGER=8,SUB_CROSS=9,SUB_HOLY=11,SUB_AXE=13};
enum {B_REST,B_FLAMES};enum {DC_POSE,DC_BREAK};
enum {DIFF_NORMAL,DIFF_EASY};enum {M_FREE,M_MUMMY,M_DYING,M_IGOR};
static struct {bool medusa,frank,death,dracula;u8 state,immune,ds;u16 timer;s32 x,y;} boss;
typedef struct {s32 x,y;u8 state,kind,last;bool hit_boss;} Shot;
typedef struct {s32 x,y;s16 cy;u8 kind,immune,t;} Monster;
static Shot shots[MAX_SHOTS];static Monster monsters[MAX_MONSTERS];
static u8 section,whip_level,whip_count,whip_phase,state,difficulty,hit_counter;
static bool facing_left,whip_crouch,air_whip,stair_whip,throwing;
static s16 simon_x,simon_y,boss_hp;
static u16 frame_count;static unsigned score;
static int sounds,draws,draw_x,draw_y,checks,failures;
static int obj_poses[3];
static void sfx_play(u8 id){if(id!=SFX_14)abort();sounds++;}
static void hud_update(void){}
static void drac_behead(void){boss.ds=DC_BREAK;}
static void monster_kill(Monster*m,u16 points){(void)points;m->kind=M_DYING;}
static void simon_hurt(s16 x){(void)x;}
static void draw_object(const int*pose,s16 x,s16 y,bool mirror){if(pose!=&obj_poses[OBJ_SPARKLE]||mirror)abort();draws++;draw_x=x;draw_y=y;}
static void check(const char*n,bool ok){checks++;if(!ok){if(failures<10)printf("FAIL %s\n",n);failures++;}}
'''
names=['BOSS_IMMUNE','BOSS_HOLY','BOSS_SCORE','FRANK_SCORE','DEATH_SCORE','DRAC_SCORE']
defines='\n'.join(re.search(r'^#define '+n+r'\s+\S+',s,re.M)[0] for n in names)+'\n'
effect=re.search(r'static struct \{ s16 x, y; u8 frames, section; \} hit_effect;',s)[0]
main=r'''
static void reset(int type){
 memset(&boss,0,sizeof(boss));memset(shots,0,sizeof(shots));memset(monsters,0,sizeof(monsters));
 memset(&hit_effect,0,sizeof(hit_effect));boss_hp=64<<8;section=1;frame_count=0;difficulty=DIFF_NORMAL;
 boss.medusa=type==1;boss.frank=type==2;boss.death=type==3;boss.dracula=type>=4;boss.ds=type==5?DC_BREAK:DC_POSE;
 simon_x=58;simon_y=86;whip_level=2;whip_phase=2;whip_count=17;state=ST_WHIP;
 facing_left=whip_crouch=air_whip=stair_whip=throwing=false;hit_counter=0;sounds=draws=0;
}
int main(void){
 for(int b=0;b<6;b++)for(int dir=0;dir<2;dir++){
  reset(b);facing_left=dir;simon_x=dir?126:58;
  s16 before=boss_hp;boss_hits_at(100,100,24,8,false);
  check("accepted whip damages boss",boss_hp<before);
  check("accepted whip plays impact sound once",sounds==1);
  check("accepted whip creates sixteen-frame effect",hit_effect.frames==16);
  check("impact lies on boss rectangle",hit_effect.x>=76&&hit_effect.x<124&&hit_effect.y>=92&&hit_effect.y<108);
  for(int f=0;f<16;f++){impact_draw();hit_effect.frames--;}
  check("effect drawn for sixteen frames",draws==16);
  impact_draw();check("effect expires",draws==16);
  reset(b);boss.immune=1;before=boss_hp;boss_hits_at(100,100,24,8,false);
  check("immune boss produces no fake hit",boss_hp==before&&!hit_effect.frames&&!sounds);
  reset(b);whip_count=16;boss_hits_at(100,100,24,8,false);
  check("inactive whip frame has no feedback",!hit_effect.frames&&!sounds);
  for(int weapon=0;weapon<3;weapon++){
   reset(b);state=ST_STAND;Shot*q=&shots[0];q->state=W_FLY;q->kind=weapon==0?SUB_DAGGER:weapon==1?SUB_CROSS:SUB_AXE;
   q->x=100<<8;q->y=100<<8;before=boss_hp;boss_hits_at(100,100,24,8,false);
   check("accepted projectile has damage sound and effect",boss_hp<before&&sounds==1&&hit_effect.frames==16&&q->hit_boss);
   if(weapon==0)check("dagger consumed on impact",q->state==W_FREE);
   hit_effect.frames=0;sounds=0;boss.immune=0;before=boss_hp;boss_hits_at(100,100,24,8,false);
   check("same projectile cannot create repeated hits",boss_hp==before&&!sounds&&!hit_effect.frames);
  }
  reset(b);state=ST_STAND;shots[0]=(Shot){100<<8,100<<8,W_FLY,SUB_HOLY,0,false};
  boss_hits_at(100,100,24,8,false);check("holy water in flight has no direct impact",!sounds&&!hit_effect.frames);
  shots[0].state=W_BURN;before=boss_hp;boss_hits_at(100,100,24,8,false);
  check("burning holy water keeps damage without repeated impact spam",boss_hp<before&&!sounds&&!hit_effect.frames);
  reset(b);boss_hp=1;boss_hits_at(100,100,24,8,false);impact_draw();
  check("final blow keeps impact visible",boss_hp==0&&hit_effect.frames==16&&draws==1);
 }
 for(int weapon=0;weapon<4;weapon++){
  reset(0);Monster*m=&monsters[0];m->kind=M_MUMMY;m->x=100<<8;m->y=100<<8;m->cy=32<<8;
  if(weapon){state=ST_STAND;shots[0]=(Shot){100<<8,100<<8,W_FLY,weapon==1?SUB_DAGGER:weapon==2?SUB_CROSS:SUB_AXE,0,false};}
  check("mummy survives ordinary hit",mummy_hits(m));
  check("mummy hit has sound and effect",m->cy<(32<<8)&&sounds==1&&hit_effect.frames==16);
 }
 reset(0);impact_spawn(100,100,24,8,-1000,1000);impact_draw();
 check("impact clipped to target",draw_x==76&&draw_y==92);
 section++;impact_draw();check("effect hidden after room change",draws==1);
 printf("%d boss impact checks, %d failures\n",checks,failures);return failures?1:0;
}
'''
code=prefix+defines+effect+''.join(fn(sig) for sig in [
 'static bool overlap(s16 ax, s16 ay, s16 aw, s16 ah, s16 bx, s16 by, s16 bw, s16 bh)',
 'static void impact_spawn(s16 cx, s16 cy, s16 hw, s16 hh, s16 hit_x, s16 hit_y)',
 'static void whip_impact(s16 cx, s16 cy, s16 hw, s16 hh)', 'static void impact_draw(void)',
 'static bool whip_active(void)','static bool whip_strikes(s16 cx, s16 cy, s16 hw, s16 hh)',
 'static void boss_damage(s16 d)', 'static void boss_hits_at(s16 cx, s16 cy, s16 hw, s16 hh, bool touch)',
 'static bool mummy_hits(Monster *m)'])+main
with tempfile.TemporaryDirectory() as tmp:
 c=Path(tmp)/'test.c';exe=Path(tmp)/'test';c.write_text(code)
 subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)

from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1];source=(root/'src/main.c').read_text()
def fn(signature):
 start=source.index(signature+'\n{');return source[start:source.index('\n}',start)+2]
header='''#ifndef GENESIS_H
#define GENESIS_H
#include <stdint.h>
#include <stdbool.h>
typedef uint8_t u8;typedef int8_t s8;typedef uint16_t u16;typedef int16_t s16;typedef uint32_t u32;
#endif
'''
prefix=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maps.h"
#define TRUE true
#define FALSE false
#define TILE_USER_INDEX 16
#define PLANE_COLS 64
#define HUD_ROWS 5
#define NES_X 32
#define MAX_SPRITES 64
#define CPU 0
#define DMA 1
#define BG_A 0
#define BG_B 1
#define WINDOW 2
#define SPRITE_SIZE(w,h) 1
#define ART(name) (nes_art?name##_nes:name)
#define ART_PAL(name) (nes_art?name##_palette_nes:name##_palette)
enum {SUB_NONE=0,SUB_DAGGER=8,SUB_CROSS=9,SUB_HOLY=11,SUB_AXE=13,SUB_WATCH=15};
enum {SEC_COURT,SEC_ST4,SEC_ST7,SEC_ST10,SEC_ST13,SEC_ST16};
#define SFX_06 6
#define SFX_03 3
#define SFX_04 4
static struct {u8 stage;} sections[]={{1},{4},{7},{10},{13},{16}};
static struct {u16 timer;} boss;
static u8 section,loaded_block,tally_phase,subweapon,other_sub,shot_level,other_level;
static u8 hearts=0,lives=3,player_hp=64,sprite_n;
static u16 time_left=0,frame_count;static u32 score=123456;static bool nes_art,second_loop;
static u16 vram[64][30],window[32][5];
static const CastleMapScene *expected;static u16 frame_index;static int width=320,scroll;
static int checks,failures,steps,sprites,black,music_stops,setup_calls,ending_calls;
static void check(const char*n,bool ok){checks++;if(!ok){if(failures<8)fprintf(stderr,"FAIL %s\n",n);failures++;}}
static void music_stop(void){music_stops++;}
static void black_frames(u16 n){black+=n;}
static void VDP_setEnable(bool value){(void)value;}
static void VDP_setScreenWidth256(void){width=256;}
static void VDP_setScreenWidth320(void){width=320;}
static void VDP_setWindowOff(void){}
static void VDP_setWindowVPos(bool side,u16 rows){check("fixed HUD enabled",!side&&rows==5);}
static void VDP_clearPlane(int plane,bool wait){(void)wait;if(plane==BG_A)memset(vram,0,sizeof(vram));if(plane==WINDOW)memset(window,0,sizeof(window));}
static void VDP_loadTileData(const u32*tiles,u16 base,u16 count,int method){(void)method;check("selected art loaded",tiles==ART(castle_map_tiles)&&base==16&&count==CASTLE_MAP_TILES);}
static void PAL_setColors(int first,const u16*palette,int count,int method){(void)method;check("selected map palette loaded",!first&&count==64&&palette==ART_PAL(castle_map));}
static void VDP_setVerticalScroll(int plane,s16 y){(void)plane;check("NES vertical crop",y==8);}
static void VDP_setHorizontalScroll(int plane,s16 x){(void)plane;scroll=x;}
static void VDP_setHorizontalScrollVSync(int plane,s16 x){(void)plane;scroll=x;}
static void VDP_setTileMapDataColumnEx(int plane,const u16*data,u16 base,u16 column,u16 y,u16 h,u16 pitch,int method){
 (void)method;check("column layout",plane==BG_A&&column<64&&!y&&h==30&&pitch==1);
 for(int r=0;r<30;r++)vram[column][r]=data[r]+base;
}
static void VDP_setTileMapDataRectEx(int plane,const u16*data,u16 base,u16 x,u16 y,u16 w,u16 h,u16 pitch,int method){
 (void)method;check("HUD layout",plane==WINDOW&&!x&&!y&&w==32&&h==5&&pitch==32);
 for(int r=0;r<5;r++)for(int c=0;c<32;c++)window[c][r]=base+data[r*32+c];
}
static void VDP_setTileMapXY(int plane,u16 tile,u16 x,u16 y){check("HUD coordinates",plane==WINDOW&&x<32&&y<5);if(x<32&&y<5)window[x][y]=tile;}
static void VDP_setSpriteFull(u16 n,s16 x,s16 y,int size,u16 attr,u16 link){(void)x;(void)y;(void)size;check("sprite index and tile valid",n<64&&((attr&2047)>=16)&&((attr&2047)<16+CASTLE_MAP_TILES)&&link==n+1);sprites++;}
static void sprites_end(void){}
static void sfx_play(u8 id){check("map footstep identifier",id==6||id==3||id==4);if(id==6)steps++;}
static void SYS_doVBlankProcess(void){
 check("frame stays in map mode",width==256&&expected&&frame_index<expected->frames);
 const CastleMapFrame*f=&castle_map_frames[expected->frame+frame_index];
 check("recorded scroll reproduced",scroll==-(int)f->scroll);
 for(int c=f->scroll/8;c<=(f->scroll+255)/8;c++)for(int r=5;r<30;r++)
  check("visible panorama correctly streamed",vram[c&63][r]==16+castle_map_columns[expected->column+c][r]);
 check("live score digit",window[11][1]==16+castle_map_hud_digit[score%10]);
 check("live stage digit",window[30][1]==16+castle_map_hud_digit[expected->stage%10]);
 check("player health kept",window[7][2]==16+castle_map_hud_bar[0]);
 check("defeated boss bar empty",window[7][3]==16+castle_map_hud_ebar[1]);
 frame_index++;
}
static void game_setup(void){setup_calls++;subweapon=other_sub=shot_level=other_level=0;}
static void ending_scene(void){ending_calls++;}
static void hud_update(void){}
'''
code=prefix+fn('static void castle_map_number(u16 col, u16 row, u32 value, u8 digits, const u16 *table)')+fn('static void castle_map_scene(u8 next_stage)')+fn('static void tally_update(void)')
main=r'''
static void reset(const CastleMapScene*scene){expected=scene;frame_index=steps=sprites=black=music_stops=0;width=320;}
static void finished(void){
 int foot=0;for(int i=0;i<expected->frames;i++)foot+=castle_map_frames[expected->frame+i].footstep;
 check("full recorded scene played",frame_index==expected->frames);
 check("all footsteps played",steps==foot);
 check("black loading interval",black==15);
 check("music stopped once",music_stops==1);
 check("320 pixel gameplay restored",width==320);
 check("old map HUD cleared",window[0][0]==0&&window[31][4]==0);
}
int main(void){u8 weapons[]={SUB_NONE,SUB_DAGGER,SUB_HOLY,SUB_AXE,SUB_CROSS,SUB_WATCH};
 for(int scene=0;scene<CASTLE_MAP_SCENES;scene++)for(int art=0;art<2;art++)for(int w=0;w<6;w++){
  reset(&castle_map_scenes[scene]);nes_art=art;subweapon=weapons[w];
  castle_map_scene(expected->stage);finished();check("weapon choice not changed",subweapon==weapons[w]);
 }
 reset(NULL);castle_map_scene(1);castle_map_scene(18);check("no map before stage 1 or ending",frame_index==0&&black==0&&width==320);
 for(int block=1;block<=5;block++){
  reset(&castle_map_scenes[block-1]);loaded_block=block;tally_phase=3;boss.timer=0;
  subweapon=SUB_AXE;other_sub=SUB_CROSS;shot_level=2;other_level=1;
  int calls=setup_calls;tally_update();finished();
  check("map at correct post-boss transition",section==block&&setup_calls==calls+1);
  check("weapons and multiple shots survive gameplay reload",subweapon==SUB_AXE&&other_sub==SUB_CROSS&&shot_level==2&&other_level==1);
 }
 reset(NULL);loaded_block=7;tally_phase=3;boss.timer=0;tally_update();
 check("Dracula keeps ending and second loop",ending_calls==1&&second_loop&&black==0&&section==SEC_COURT);
 printf("%d runtime checks, %d failures; all scenes, both arts, five weapons and transition/ending paths\n",checks,failures);
 return failures?1:0;}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'genesis.h').write_text(header);(d/'test.c').write_text(code+main)
 subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-I'+str(d),'-I'+str(root/'inc'),str(d/'test.c'),str(root/'src/maps.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)

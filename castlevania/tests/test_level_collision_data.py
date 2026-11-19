#!/usr/bin/env python3
"""Validate actual collision helpers against every room's generated floor data."""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'src/main.c').read_text()
def fn(sig):
 start=s.index(sig+'\n{'); return s[start:s.index('\n}',start)+2]
defines='\n'.join(line for name in ['level']+[f'block{n}' for n in range(2,8)]
                  for line in (root/f'inc/{name}.h').read_text().splitlines() if line.startswith('#define '))
# Room constants and section initialisers are taken directly from the game.
constants='\n'.join(line for line in s.splitlines() if line.startswith('#define '))
start=s.index('enum { SEC_COURT,')
section_enum=s[start:s.index(';',start)+1]
start=s.index('typedef struct { s16 c0, c1, cam0,')
section_type=s[start:s.index('; } Section;',start)+12]
start=s.index('static const Section sections[SECTIONS] = {')
section_data=s[start:s.index('\n};',start)+3]
arrays=''
for name in ['level','gate']+[f'block{n}' for n in range(2,8)]:
 text=(root/f'src/{"level" if name=="gate" else name}.c').read_text()
 for kind in ['solid','wall']:
  match=re.search(r'const u32 '+name+'_'+kind+r'\[.*?\] = \{.*?\};',text,re.S)
  arrays+=match[0]+'\n'
prefix=r'''
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
typedef uint8_t u8; typedef int8_t s8; typedef uint16_t u16; typedef int16_t s16; typedef uint32_t u32;
#define TRUE true
#define FALSE false
'''
helpers=r'''
static u8 section;

static s16 simon_x, simon_y, world_c0;
static const u32 *world_solid,*world_wall;
static bool block_gone(s16 x,s16 y){(void)x;(void)y;return false;}
static s8 plat_under(s16 x,s16 y){(void)x;(void)y;return -1;}
static int checks,failures;
static void check(const char*label,bool ok){checks++;if(!ok){if(failures<12)printf("FAIL %s sec=%d x=%d y=%d\n",label,section,simon_x,simon_y);failures++;}}
static void select_room(u8 sec){
 section=sec;
 int block=sections[sec].stage<=3?1:(sections[sec].stage+2)/3;
 if(sections[sec].stage==18)block=7;
 const u32 *solids[]={level_solid,block2_solid,block3_solid,block4_solid,block5_solid,block6_solid,block7_solid};
 const u32 *walls[]={level_wall,block2_wall,block3_wall,block4_wall,block5_wall,block6_wall,block7_wall};
 const int origins[]={0,BLOCK2_COL0,BLOCK3_COL0,BLOCK4_COL0,BLOCK5_COL0,BLOCK6_COL0,BLOCK7_COL0};
 world_c0=origins[block-1];world_solid=solids[block-1];world_wall=walls[block-1];
}
'''
main=r'''
int main(void){
 for(int sec=0;sec<SECTIONS;sec++){
  select_room(sec);int surfaces=0;
  for(int c=sections[sec].c0;c<sections[sec].c1;c++)for(int r=6;r<28;r++){
   if(!(solid_at(c*8,r*8)||wall_at(c*8,r*8)))continue;
   if(solid_at(c*8,r*8-1)||wall_at(c*8,r*8-1))continue;
   simon_x=c*8-4;simon_y=r*8-FEET;
   check("surface supports Simon",standable(simon_y));
   simon_y--;check("descent stops on top",move_down_to(simon_y+9)&&simon_y==r*8-FEET);
   surfaces++;
  }
  check("room has testable surfaces",surfaces>0);
  // The underground start is deliberately reached through stairs, not spawned
  // at its Section.start_x; restart_level redirects it to SEC_ST2.
  bool restart_room = sec!=SEC_UNDER && sec!=SEC_ST4B && sec!=SEC_ST5B && sec!=SEC_ST6B
      && sec!=SEC_ST7B && sec!=SEC_ST8B && sec!=SEC_ST13B && sec!=SEC_ST14B
      && sec!=SEC_ST15B && sec!=SEC_ST17B && sec!=SEC_ST18B;
  if(restart_room){
   simon_x=sections[sec].start_x;simon_y=sections[sec].start_y;
   check("stage arrival has floor support",standable(simon_y));
  }
  printf("Room %d (stage %d): %d floor tops\n",sec,sections[sec].stage,surfaces);
 }
 printf("%d checks, %d failures\n",checks,failures);return failures?1:0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 c=Path(tmp)/'test.c';exe=Path(tmp)/'test'
 defines='\n'.join(line.split('/*')[0] for line in defines.splitlines())
 c.write_text(prefix+defines+'\n'+constants+'\n'+section_enum+section_type+section_data+arrays+helpers
              +fn('static s16 section_col(s16 c)')+fn('static bool solid_at(s16 px, s16 py)')
              +fn('static bool wall_at(s16 px, s16 py)')+fn('static bool standable(s16 y)')
              +fn('static bool move_down_to(s16 new_y)')+main)
 subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Wno-missing-field-initializers',str(c),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)

#!/usr/bin/env python3
"""Test the exact fatal-fall guard, FM-only PCM dispatch and unchanged death cue."""
from pathlib import Path
import argparse,json,hashlib,re,subprocess,tempfile,wave
p=argparse.ArgumentParser();p.add_argument('--project',type=Path);a=p.parse_args()
root=a.project or Path(__file__).resolve().parents[1]
main=(root/'src/main.c').read_text();sound=(root/'src/sound.c').read_text()
start=main.index('    if (simon_y >= PIT_Y && state != ST_DEAD && state != ST_CLIMB)')
brace=main.index('{',start);end=main.index('\n    }',brace)+6;guard=main[start:end]
sig='void fall_play(void)';start=sound.index(sig+'\n{');fall=sound[start:sound.index('\n}',start)+2]
info=json.loads((root/'res/audio/wilhelm.json').read_text());raw=(root/'res/audio/wilhelm.pcm').read_bytes()
assert len(raw)==35072 and len(raw)%256==0
assert hashlib.sha256(raw).hexdigest()==info['sha256']
assert raw[info['samples']:]==bytes(len(raw)-info['samples'])
assert len(raw)/info['rate']<97/60
assert '256 256 0 NONE FALSE' in (root/'res/wilhelm_audio.res').read_text()
with wave.open(str(root/'res/audio/wilhelm-preview.wav'),'rb') as w:
 assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,1,22050)
 assert bytes(x^128 for x in w.readframes(w.getnframes()))==raw
assert len(re.findall(r'\bfall_play\(\);',main))==1
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint8_t u8;typedef uint16_t u16;typedef int16_t s16;
#define TRUE true
#define FALSE false
#define PIT_Y 208
#define SOUND_PCM_RATE_22050 1
#define SOUND_PAN_CENTER 3
enum {ST_STAND,ST_FALL,ST_HURT,ST_DEAD,ST_CLIMB};
static bool use_fm_music,lost,air_whip;static s16 simon_y;static u8 state;static u16 state_t;
static const u8 wilhelm_pcm[35072] __attribute__((aligned(256)))={0};
static int starts,checks,failures;
static void SND_PCM_startPlay(const u8*p,unsigned size,int rate,int pan,bool loop){
 if(p!=wilhelm_pcm||size!=35072||rate!=1||pan!=3||loop)abort();
 starts++;
}
static void check(const char*n,bool b){checks++;if(!b){printf("FAIL %s\n",n);failures++;}}
'''
test=r'''
static void setup(bool fm,int pose,int y){use_fm_music=fm;state=pose;simon_y=y;lost=false;air_whip=true;state_t=23;starts=0;}
int main(void){
 for(int fm=0;fm<2;fm++)for(int pose=ST_STAND;pose<=ST_HURT;pose++)for(int y=207;y<=216;y++){
  setup(fm,pose,y);fatal_fall_check();
  check("existing fatal threshold preserved",(state==ST_DEAD)==(y>=208));
  check("cry only for fatal falls in FM",starts==((fm&&y>=208)?1:0));
  if(y>=208){
   check("death state and lost marker preserved",lost&&!air_whip&&state_t==0);
   for(int frame=0;frame<97;frame++)fatal_fall_check();
   check("one cry per death",starts==(fm?1:0));
  }
 }
 setup(true,ST_CLIMB,224);fatal_fall_check();check("scripted climb does not trigger",state==ST_CLIMB&&!starts);
 setup(true,ST_DEAD,224);fatal_fall_check();check("already dead from another cause does not trigger",!starts);
 setup(true,ST_FALL,208);fatal_fall_check();
 state=ST_STAND;simon_y=160;lost=false;fatal_fall_check();
 state=ST_FALL;simon_y=208;fatal_fall_check();
 check("a later fatal fall can scream again",starts==2);
 printf("%d fatal fall checks, %d failures\n",checks,failures);return failures?1:0;
}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d);c=d/'test.c';exe=d/'test';c.write_text(prefix+fall+'\nstatic void fatal_fall_check(void)\n{\n'+guard+'\n}\n'+test)
 subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PCM hash/format, SGDK alignment and duration before level restart verified.')

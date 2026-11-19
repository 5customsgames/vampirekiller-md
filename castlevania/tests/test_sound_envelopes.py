#!/usr/bin/env python3
"""Check actual APU envelopes/output and replay all recordings against a Python oracle."""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[1];s=(root/'src/sound.c').read_text();m=(root/'src/music.c').read_text()
def fn(sig):
 start=s.index(sig);return s[start:s.index('\n}',start)+2]
def array(name):return re.search(r'static const u\d+ '+name+r'\[\d+\] = \{.*?\};',s,re.S)[0]
structs='\n'.join(re.findall(r'typedef struct \{[^\n]+\} (?:Apu|Player);',s))
prefix='''#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;typedef uint16_t u16;typedef int16_t s16;
#define TRUE true
#define FALSE false
#define SOUNDS 53
#define HURT_PCM_SIZE 1536
typedef struct {const u8 *data;u16 size,loop;} Sound;
'''
stubs=r'''
static Apu music_apu,sfx_apu,silent_apu;static Player sfx;static bool held;
static u8 output[4];
static void psg_set(u8 ch,u16 period,u8 att){(void)period;output[ch]=att;}
static void fm_triangle(bool on,u16 period){(void)on;(void)period;}
static int checks,failures;
static void check(const char*n,bool ok){checks++;if(!ok){fprintf(stderr,"FAIL %s\n",n);failures++;}}
'''
main=r'''
int main(void){
 for(int ch=0;ch<4;ch++)if(ch!=2){
  Apu a={0};apu_write(&a,0x15,15);apu_write(&a,ch*4,2);apu_write(&a,ch*4+3,8);
  check("length write restarts envelope",a.env_start[ch]);
  envelope_clock(&a,ch);check("envelope starts at full level",apu_volume(&a,ch)==15);
  envelope_clock(&a,ch);envelope_clock(&a,ch);check("divider waits period plus one",a.env_level[ch]==15);
  envelope_clock(&a,ch);check("envelope decays",apu_volume(&a,ch)==14);
  apu_write(&a,ch*4,0x17);check("constant volume override",apu_volume(&a,ch)==7);
  for(int n=0;n<16;n++)envelope_clock(&a,ch);
  check("envelope still runs in constant mode",a.env_level[ch]<14&&apu_volume(&a,ch)==7);
  apu_write(&a,ch*4,0);apu_write(&a,ch*4+3,8);envelope_clock(&a,ch);
  for(int n=0;n<24;n++)envelope_clock(&a,ch);
  check("non-looping envelope stays silent",apu_volume(&a,ch)==0);
  apu_write(&a,ch*4,0x20);apu_write(&a,ch*4+3,8);envelope_clock(&a,ch);
  for(int n=0;n<16;n++)envelope_clock(&a,ch);
  check("looping envelope reloads",a.env_level[ch]==15);
  apu_write(&a,0x15,0);check("disabled channel remains silent",apu_volume(&a,ch)==0);
 }
 player_start(&sfx,&sfx_apu,34);player_step(&sfx,&sfx_apu);sound_out();
 check("impact uses noise channel",sfx_apu.owned==8);
 check("impact starts with audible envelope",apu_volume(&sfx_apu,3)==14&&output[3]==2);
 for(int f=0;f<128;f++)player_step(&sfx,&sfx_apu);
 sound_out();check("finished impact releases sound channel",!sfx.on&&output[3]==15);
 fprintf(stderr,"%d audio checks, %d failures\n",checks,failures);
 for(int id=0;id<SOUNDS;id++){
  Apu a;Player p;player_start(&p,&a,id);
  for(int f=0;f<128;f++){
   player_step(&p,&a);
   for(int ch=0;ch<4;ch++)if(ch!=2)
    printf("%d,%d,%d,%u,%u,%u,%u\n",id,f,ch,a.env_level[ch],a.env_div[ch],a.env_start[ch],apu_volume(&a,ch));
  }
 }
 return failures?1:0;
}
'''
code=prefix+m.replace('#include "music.h"','')+structs+'\n'+''.join(array(n) for n in ['length_table','noise_period','attenuation'])
code+=''.join(fn(n) for n in ['static void apu_write(','static s16 sweep_target(','static void sweep_clock(',
                           'static void envelope_clock(','static u8 apu_volume(','static void apu_clock(',
                           'static void player_start(','static bool player_step('])
code+=stubs+fn('static void sound_out(')+main
with tempfile.TemporaryDirectory() as tmp:
 c=Path(tmp)/'test.c';exe=Path(tmp)/'test';c.write_text(code)
 subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
 result=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
 print(result.stderr.strip())
# Independent quarter-clock reference; actual recordings supply register events.
arrays={name:list(map(int,re.findall(r'\b\d+\b',body))) for name,body in re.findall(r'static const u8 (\w+)\[\d+\] = \{(.*?)\};',m,re.S)}
sound_table=re.search(r'const Sound sounds\[.*?\] = \{(.*?)\};',m,re.S)[1]
entries=[(name,int(loop)) for name,_,loop in re.findall(r'\{\s*(\w+),\s*(\d+),\s*(\d+)\s*\}',sound_table)]
# Use the hardware's 32-entry length table, independent of C declaration.
lengths=[10,254,20,2,40,4,80,6,160,8,60,10,14,12,26,14,12,16,24,18,48,20,96,22,192,24,72,26,16,28,32,30]
expected=[]
for id,(name,loop) in enumerate(entries):
 data=arrays[name];regs=[0]*24;regs[21]=15;length=[0]*4;level=[0]*4;div=[0]*4;start=[False]*4
 pointer=wait=0;on=True
 for f in range(128):
  if on:
   if wait:wait-=1
   else:
    while True:
     if pointer>=len(data):
      if loop==65535:on=False;break
      pointer=loop
     reg=data[pointer];pointer+=1
     if reg==255:break
     if reg==254:wait=data[pointer]-1;pointer+=1;break
     value=data[pointer];pointer+=1;regs[reg]=value
     if reg==21:
      for ch in range(4):
       if not value&(1<<ch):length[ch]=0
     elif reg<16 and reg%4==3:
      ch=reg//4
      if ch!=2:start[ch]=True
      if regs[21]&(1<<ch):length[ch]=lengths[value>>3]
   if on:
    for _ in range(4):
     for ch in (0,1,3):
      control=regs[ch*4]
      if start[ch]:start[ch]=False;level[ch]=15;div[ch]=control&15
      elif div[ch]:div[ch]-=1
      else:
       div[ch]=control&15
       if level[ch]:level[ch]-=1
       elif control&32:level[ch]=15
    for _ in range(2):
     for ch in (0,1,3):
      if length[ch] and not regs[ch*4]&32:length[ch]-=1
  for ch in (0,1,3):
   vol=(regs[ch*4]&15 if regs[ch*4]&16 else level[ch]) if length[ch] else 0
   expected.append((id,f,ch,level[ch],div[ch],int(start[ch]),vol))
actual=[tuple(map(int,line.split(','))) for line in result.stdout.splitlines()]
assert len(actual)==len(expected),(len(actual),len(expected))
for a,e in zip(actual,expected):assert a==e,(a,e)
print(f'All {len(entries)} recordings match the independent envelope reference over 128 frames.')

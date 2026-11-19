#!/usr/bin/env python3
"""Validate all 15 tracks, loops, original/FM selection, pause and shared SFX channels."""
from pathlib import Path
import argparse,subprocess,tempfile,struct,json
p=argparse.ArgumentParser();p.add_argument('--project',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[1];project=a.project or root
header=r'''
#ifndef GENESIS_H
#define GENESIS_H
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
typedef uint8_t u8;typedef int8_t s8;typedef uint16_t u16;typedef int16_t s16;typedef uint32_t u32;
typedef volatile uint8_t vu8;typedef volatile int8_t vs8;
#define TRUE true
#define FALSE false
extern volatile s8 fake_ym[4];extern volatile u8 fake_psg;
#define YM2612_BASEPORT fake_ym
#define SOUND_PCM_RATE_32000 0
#define SOUND_PCM_RATE_22050 1
#define SOUND_PAN_CENTER 3
void YM2612_writeReg(u16 port,u16 reg,u8 value);
void Z80_requestBus(bool wait);void Z80_releaseBus(void);
void SYS_disableInts(void);void SYS_enableInts(void);void SYS_setVIntCallback(void (*callback)(void));
void SND_PCM_loadDriver(bool wait);void SND_PCM_stopPlay(void);
void SND_PCM_startPlay(const u8*data,u32 size,u16 rate,u16 pan,bool loop);
#endif
'''
stubs=r'''
#include <stdio.h>
#include <stdlib.h>
#include "genesis.h"
volatile s8 fake_ym[4];volatile u8 fake_psg;
const u8 wilhelm_pcm[35072] __attribute__((aligned(256)))={0};
static u8 regs[2][256];static int bus,interrupts,pcm_starts,pcm_stops,checks,failures;
static void (*vint)(void);

static void check(const char*n,bool ok){checks++;if(!ok){fprintf(stderr,"FAIL %s\n",n);failures++;}}
void YM2612_writeReg(u16 p,u16 r,u8 v){if(p>1||r>255)abort();regs[p][r]=v;}
void Z80_requestBus(bool w){(void)w;if(bus)abort();bus=1;}
void Z80_releaseBus(void){if(!bus)abort();bus=0;}
void SYS_disableInts(void){interrupts++;}
void SYS_enableInts(void){interrupts--;if(interrupts<0)abort();}
void SYS_setVIntCallback(void (*f)(void)){vint=f;}
void SND_PCM_loadDriver(bool w){(void)w;}
void SND_PCM_stopPlay(void){pcm_stops++;}
void SND_PCM_startPlay(const u8*d,u32 n,u16 r,u16 p,bool l){(void)d;(void)n;(void)r;(void)p;(void)l;pcm_starts++;}
'''
info=json.loads((root/'apercu/pistes.json').read_text())['tracks']
module=(root/'src/fm_music.c').read_text().replace('#define FM_PSG_DATA (*(vu8 *)0xC00011)','#define FM_PSG_DATA fake_psg')
sound=(root/'src/sound.c').read_text().replace('#define PSG_DATA (*(vu8 *)0xC00011)','#define PSG_DATA fake_psg')
# Both production C files normally have separate translation units. Rename the
# driver's private 'held' only so this single-unit test can inspect both states.
body='#define held fm_driver_held\n'+module+'\n#undef held\n'+sound
counts=','.join(str(t['frames']) for t in info)
loops=','.join(str(t['loop_frame']) for t in info)
main=r'''
static uint64_t register_hash(void){uint64_t h=1469598103934665603ULL;for(int p=0;p<2;p++)for(int r=0;r<256;r++){h^=regs[p][r];h*=1099511628211ULL;}return h;}
int main(void){
 for(int id=0;id<15;id++){
  memset(regs,0,sizeof(regs));FM_MUSIC_start(id);
  int count=frame_counts[id]+(loop_frames[id]>=0?2*(frame_counts[id]-loop_frames[id]):0);
  for(int f=0;f<count;f++){
   check("music frame active",FM_MUSIC_tick());
   printf("F,%d,%d,%llu,%u,%u,%u,%u,%u,%u,%u,%u\n",id,f,(unsigned long long)register_hash(),
     psg_period[0],psg_period[1],psg_period[2],psg_att[0],psg_att[1],psg_att[2],psg_att[3],psg_noise);
  }
  if(loop_frames[id]<0)check("one-shot ends",!FM_MUSIC_tick());
  else check("loop remains alive",FM_MUSIC_playing());
  FM_MUSIC_stop();
 }
 sound_init();check("original is default",!sound_fm_enabled());
 music_play(MUS_VAMPIRE_KILLER);vint();check("original uses old player",music.on&&!fm_music_mode);
 sound_set_fm(true);music_play(MUS_VAMPIRE_KILLER);vint();check("FM selected",fm_music_mode&&music_playing());
 const u8*before=position;music_hold(true);
 for(int f=0;f<20;f++)vint();
 check("pause freezes score",position==before&&fm_driver_held);
 check("pause silences music FM",regs[0][0x4D]==127&&regs[0][0x4E]==127&&regs[1][0x4C]==127&&regs[1][0x4D]==127);
 music_hold(false);vint();check("resume advances score",position!=before&&!fm_driver_held);
 // No music voice uses FM 0 (SFX triangle) or FM 5 (hurt DAC).
 check("original triangle patch retained",regs[0][0xB0]==7);
 sfx_play(SFX_14);vint();check("impact runs alongside FM",sfx.on&&sfx_apu.owned==8&&fm_music_mode);
 check("noise SFX owns noise clock",psg_applied_noise==255&&psg_applied_period[2]==65535);
 for(int f=0;f<100;f++)vint();
 check("PSG noise restored after SFX",!sfx.on&&psg_applied_noise==psg_noise&&psg_applied_att[3]==psg_att[3]);
 hurt_play();check("hurt sample retained",pcm_starts==1);
 int stops_before=pcm_stops;
 fall_play();check("FM fall scream starts on reserved DAC",pcm_starts==2);
 music_play(MUS_LOSE_LIFE);vint();
 check("death music does not cut scream",pcm_stops==stops_before&&pcm_starts==2&&fm_music_mode);
 music_stop();check("stop works in FM",!music_playing());
 check("choice survives stop",sound_fm_enabled());
 music_play(MUS_GAME_OVER);check("choice survives game over",fm_music_mode);
 sound_set_fm(false);music_play(MUS_POISON_MIND);vint();
 check("return to original works",!fm_music_mode&&music.on&&!sound_fm_enabled());
 int starts_before=pcm_starts;fall_play();check("original mode never uses scream",pcm_starts==starts_before);
 check("DAC still enabled for effects",regs[0][0x2B]==128);
 // All 38 original SFX retain the same APU register, envelope, length and
 // sweep evolution while FM music is active.
 for(int id=SFX_01;id<SOUNDS;id++){
  Apu reference[128];bool running[128];
  sound_set_fm(false);music_play(MUS_VAMPIRE_KILLER);sfx_play(id);
  for(int f=0;f<128;f++){vint();reference[f]=sfx_apu;running[f]=sfx.on;}
  sound_set_fm(true);music_play(MUS_VAMPIRE_KILLER);sfx_play(id);
  for(int f=0;f<128;f++){vint();check("SFX unchanged beside FM",memcmp(&reference[f],&sfx_apu,sizeof(Apu))==0&&running[f]==sfx.on);}
 }
 check("locks balanced",!bus&&!interrupts);
 fprintf(stderr,"%d soundtrack checks, %d failures\n",checks,failures);return failures?1:0;
}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'genesis.h').write_text(header);(d/'fm_music_data.inc').write_bytes((root/'src/fm_music_data.inc').read_bytes())
 c=d/'test.c';exe=d/'test';c.write_text(stubs+body+f'\nstatic const int frame_counts[15]={{{counts}}};\nstatic const int loop_frames[15]={{{loops}}};\n'+main)
 subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-I'+str(d),'-I'+str(root/'inc'),'-I'+str(project/'inc'),'-I'+str(root/'res'),str(c),str(project/'src/music.c'),'-o',str(exe)],check=True)
 result=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
 print(result.stderr.strip())
actual={id:[] for id in range(15)}
for line in result.stdout.splitlines():
 if line.startswith('F,'):
  values=list(map(int,line[2:].split(',')));actual[values[0]].append(values[2:])
def u32(b,n):return struct.unpack_from('<I',b,n)[0]
for t in info:
 b=(root/f'apercu/{t["id"]:02d}-{t["name"]}.vgm').read_bytes();start=0x34+u32(b,0x34)
 reg=[[0]*256 for _ in range(2)];period=[1]*3;att=[15]*4;noise=7;latch=0;i=start
 n=t['frames']+(2*(t['frames']-t['loop_frame']) if t['loop_frame']>=0 else 0)
 for frame in range(n):
  while True:
   command=b[i];i+=1
   if command==0x62:break
   if command==0x66:
    assert t['loop_frame']>=0;i=0x1C+u32(b,0x1C);continue
   if command in (0x52,0x53):
    r,v=b[i:i+2];i+=2;assert r not in (0x2A,0x2B)
    if r==0x28:assert (v&7) in (1,2,4,5)
    else:assert (r%4+(3 if command==0x53 else 0)) in (1,2,3,4)
    reg[command-0x52][r]=v
   elif command==0x50:
    v=b[i];i+=1
    if v&128:
     latch=(v>>4)&7;ch=latch>>1
     if latch&1:att[ch]=v&15
     elif ch==3:noise=v&7
     else:period[ch]=(period[ch]&0x3F0)|(v&15)
    elif not latch&1 and latch>>1<3:
     ch=latch>>1;period[ch]=(period[ch]&15)|((v&63)<<4)
   else:raise AssertionError(command)
  h=1469598103934665603
  for port in reg:
   for v in port:h=((h^v)*1099511628211)&((1<<64)-1)
  expected=[h]+period+att+[noise]
  assert actual[t['id']][frame]==expected,(t['id'],frame,actual[t['id']][frame],expected)
 print(t['name']+': frame trace matches, '+('two loop repetitions' if t['loop_frame']>=0 else 'one-shot ending'))
print('All YM and PSG states match the VGM streams; no DAC samples or SFX FM channels used by music.')

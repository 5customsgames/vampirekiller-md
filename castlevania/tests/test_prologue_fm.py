#!/usr/bin/env python3
"""Compile actual register player + sound engine, comparing events with the VGM preview."""
from pathlib import Path
import argparse,subprocess,tempfile,struct,re
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
static u8 regs[2][256];static int bus,interrupts,pcm_starts,pcm_stops,checks,failures;
static void (*vint)(void);
static bool record;
static void check(const char*n,bool ok){checks++;if(!ok){fprintf(stderr,"FAIL %s\n",n);failures++;}}
void YM2612_writeReg(u16 p,u16 r,u8 v){if(p>1||r>255)abort();regs[p][r]=v;if(record)printf("Y,%u,%u,%u\n",p,r,v);}
void Z80_requestBus(bool w){(void)w;if(bus)abort();bus=1;}
void Z80_releaseBus(void){if(!bus)abort();bus=0;}
void SYS_disableInts(void){interrupts++;}
void SYS_enableInts(void){interrupts--;if(interrupts<0)abort();}
void SYS_setVIntCallback(void (*f)(void)){vint=f;}
void SND_PCM_loadDriver(bool w){(void)w;}
void SND_PCM_stopPlay(void){pcm_stops++;}
void SND_PCM_startPlay(const u8*d,u32 n,u16 r,u16 p,bool l){(void)d;(void)n;(void)r;(void)p;(void)l;pcm_starts++;}
'''
module=(root/'src/prologue_fm.c').read_text().replace('#define PROLOGUE_PSG_DATA (*(vu8 *)0xC00011)','#define PROLOGUE_PSG_DATA fake_psg')
sound=(root/'src/sound.c').read_text().replace('#define PSG_DATA (*(vu8 *)0xC00011)','#define PSG_DATA fake_psg')
main=r'''
int main(void){
 record=true;PROLOGUE_FM_start();check("prologue starts",PROLOGUE_FM_playing());
 for(int f=0;f<458;f++)check("frame stream remains active",PROLOGUE_FM_tick());
 check("stream ends after 458 frames",!PROLOGUE_FM_tick()&&!PROLOGUE_FM_playing());
 record=false;
 PROLOGUE_FM_stop();check("stop is idempotent",!PROLOGUE_FM_playing());
 PROLOGUE_FM_start();PROLOGUE_FM_tick();PROLOGUE_FM_stop();
 check("manual interruption stops",!PROLOGUE_FM_playing());
 const u8 bad[]={0x52,0x2A,0x80};const u8*cursor=bad;
 check("DAC sample writes rejected",prologue_commands(&cursor,bad+3)<0);
 const u8 truncated[]={0x53,0xA0};cursor=truncated;
 check("truncated register command rejected",prologue_commands(&cursor,truncated+2)<0);
 const u8 invalid[]={0xFF};cursor=invalid;
 check("unsupported command rejected",prologue_commands(&cursor,invalid+1)<0);
 sound_init();music_play(MUS_PROLOGUE);check("FM route selected",fm_prologue_mode&&music_playing());
 for(int f=0;f<459;f++)vint();
 check("natural end visible through music API",!music_playing());
 check("no recorded sample used by prologue",!pcm_starts);
 music_play(MUS_VAMPIRE_KILLER);
 check("game track resumes",music_playing()&&!fm_prologue_mode);
 check("original triangle instrument restored",regs[0][0xB0]==7&&regs[0][0x4C]==16);
 check("DAC available for original hurt effect",regs[0][0x2B]==0x80);
 vint();sfx_play(SFX_14);vint();
 check("impact sound still runs",sfx.on&&sfx_apu.owned==8);
 hurt_play();check("hurt sample still available",pcm_starts==1);
 music_play(MUS_PROLOGUE);music_stop();check("music stop cancels FM prologue",!music_playing()&&!fm_prologue_mode);
 check("bus and interrupt locks balanced",bus==0&&interrupts==0);
 fprintf(stderr,"%d FM/PSG checks, %d failures\n",checks,failures);return failures?1:0;
}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'genesis.h').write_text(header)
 (d/'prologue_fm_data.inc').write_bytes((root/'src/prologue_fm_data.inc').read_bytes())
 c=d/'test.c';exe=d/'test';c.write_text(stubs+module+sound+main)
 subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-I'+str(d),'-I'+str(root/'inc'),'-I'+str(project/'inc'),str(c),str(project/'src/music.c'),'-o',str(exe)],check=True)
 r=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
 print(r.stderr.strip())
# Compare every YM register write with the exact preview stream.
vgm=(root/'apercu/Prologue-FM-PSG.vgm').read_bytes();i=0x34+struct.unpack_from('<I',vgm,0x34)[0];expected=[];waits=0;psg=0
while i<len(vgm):
 command=vgm[i];i+=1
 if command in (0x52,0x53):
  reg,value=vgm[i:i+2];i+=2;assert reg!=0x2A
  expected.append((command-0x52,reg,value))
 elif command==0x50:i+=1;psg+=1
 elif command==0x62:waits+=1
 elif command==0x66:break
 else:raise AssertionError(hex(command))
actual=[tuple(map(int,line[2:].split(','))) for line in r.stdout.splitlines() if line.startswith('Y,')]
assert actual==expected,(len(actual),len(expected))
assert waits==458 and psg>10
for port,reg,value in expected:
 if reg==0x28:assert (value&7) not in (3,7), 'Invalid or reserved sixth channel key-on'
assert len(expected)>100
print(f'{len(expected)} YM2612 writes match the preview; {psg} PSG writes, 458 frames, no DAC sample data.')

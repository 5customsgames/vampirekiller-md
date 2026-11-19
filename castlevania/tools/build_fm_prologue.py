#!/usr/bin/env python3
"""Revoice the original Prologue score as five YM2612 voices plus PSG accents.
Read the existing NES APU recording; no MSU audio samples are used in the ROM.
Requires Python 3 and a native C compiler for extracting the existing APU state.
"""
from pathlib import Path
import argparse,json,math,re,struct,subprocess,tempfile

FM_CLOCK=7670454
FRAMES=458
# Four serial FM operators, algorithm 0, register-slot order (1,3,2,4).
# Each row: multiplier, TL, attack, decay, sustain rate, sustain/release.
PATCHES=[
 ('cuivre',5,[(1,34,31,9,3,0x35),(1,42,31,8,3,0x46),(1,30,31,6,2,0x46),(1,2,28,7,2,0x38)]),
 ('orgue',3,[(2,43,31,4,0,0x27),(1,54,31,3,0,0x27),(1,38,31,4,0,0x27),(1,5,31,4,0,0x28)]),
 ('basse',4,[(1,38,31,12,3,0x45),(1,57,31,10,3,0x45),(1,29,31,10,3,0x45),(1,4,31,8,2,0x38)]),
 ('cloche',2,[(3,33,31,12,4,0x45),(2,46,31,12,4,0x45),(2,34,31,10,3,0x45),(1,13,31,10,2,0x38)]),
 ('nappe',2,[(1,54,22,5,1,0x36),(1,61,22,4,1,0x36),(1,43,22,4,1,0x36),(1,15,22,4,1,0x37)]),
]

def fn(s,name):
 a=s.index(name);return s[a:s.index('\n}',a)+2]

def trace(root):
 s=(root/'src/sound.c').read_text();music=(root/'src/music.c').read_text()
 structs='\n'.join(re.findall(r'typedef struct \{[^\n]+\} (?:Apu|Player);',s))
 arrays=''.join(re.search(r'static const u\d+ '+n+r'\[\d+\] = \{.*?\};',s,re.S)[0] for n in ['length_table'])
 funcs=['static void apu_write(','static s16 sweep_target(','static void sweep_clock(','static void envelope_clock(',
        'static u8 apu_volume(','static void apu_clock(','static void player_start(','static bool player_step(']
 prefix='''#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;typedef uint16_t u16;typedef int16_t s16;
#define TRUE true
#define FALSE false
#define SOUNDS 53
#define HURT_PCM_SIZE 1536
typedef struct {const u8*data;u16 size,loop;} Sound;
'''
 main='''int main(void){Apu a;Player p;player_start(&p,&a,0);
 for(int f=0;f<458;f++){player_step(&p,&a);printf("%d",f);
 for(int ch=0;ch<4;ch++){int t=a.r[ch*4+2]|((a.r[ch*4+3]&7)<<8);
 int vol=ch==2?(a.len[2]&&a.lin&&t>=2?15:0):apu_volume(&a,ch);
 if(ch<2 && (t<8||sweep_target(&a,ch)>2047))vol=0;
 printf(",%d,%d",t,vol);}printf("\\n");}return 0;}'''
 with tempfile.TemporaryDirectory() as d:
  c=Path(d)/'trace.c';exe=Path(d)/'trace'
  c.write_text(prefix+music.replace('#include "music.h"','')+structs+arrays+''.join(fn(s,n) for n in funcs)+main)
  subprocess.run(['cc','-std=c99','-O2',str(c),'-o',str(exe)],check=True)
  result=subprocess.check_output([str(exe)],text=True)
 return [list(map(int,line.split(',')))[1:] for line in result.splitlines()]

def fm(ch,reg,value):return [0x52 if ch<3 else 0x53,reg+ch%3,value]
def key(ch,on):return [0x52,0x28,(0xF0 if on else 0)|(ch if ch<3 else ch+1)]
def frequency(hz):
 # f = FNUM * clock / (144 * 2^20) * 2^(BLOCK-1).
 for block in range(8):
  fnum=round(hz*144*(2**20)/FM_CLOCK/(2**(block-1)))
  if fnum<2048:return (block<<11)|fnum
 return (7<<11)|2047

def generate(rows):
 init=[0x52,0x22,0,0x52,0x27,0]
 for ch,(_,feedback,ops) in enumerate(PATCHES):
  init+=key(ch,False)
  for op,values in enumerate(ops):
   for reg,value in zip((0x30,0x40,0x50,0x60,0x70,0x80),values):init+=fm(ch,reg+op*4,value)
   init+=fm(ch,0x90+op*4,0)
  init+=fm(ch,0xB0,feedback<<3) # algorithm 0
  init+=fm(ch,0xB4,[0xC0,0xC0,0xC0,0x80,0x40][ch])
 for ch in range(4):init += [0x50,0x9F|(ch<<5)]
 frames=[];last=[None]*5;last_tl=[None]*5;psg_last=None;notes=[]
 for f,row in enumerate(rows):
  cmds=[];tone=[]
  for src in range(3):
   period,vol=row[src*2:src*2+2]
   hz=1789773/((32 if src==2 else 16)*(period+1))
   tone.append((hz,vol))
  # Main lead, lower harmony, original bass; two quiet layers are deliberate
  # additions: octave bell and a sustained string-colour doubling of harmony.
  voices=[(tone[0][0],tone[0][1],5,0.75),
          (tone[1][0],tone[1][1],4,0.48),
          (tone[2][0],tone[2][1],15,0.47),
          (tone[0][0]*2,tone[0][1],5,0.15),
          (tone[1][0]*2,tone[1][1],4,0.17)]
  for ch,(hz,vol,reference,gain) in enumerate(voices):
   pitch=frequency(hz) if vol else None
   if pitch!=last[ch]:
    cmds+=key(ch,False)
    if pitch is not None:
     cmds+=fm(ch,0xA4,pitch>>8)+fm(ch,0xA0,pitch&255)
     # A real note attack, not repeated key-on at every envelope change.
     cmds+=key(ch,True)
     notes.append(dict(frame=f,channel=ch,midi=round(69+12*math.log2(hz/440))))
    last[ch]=pitch
   if vol:
    amplitude=max(.001,min(1,vol/reference)*gain)
    attenuation=round(-20*math.log10(amplitude)/.75)
    tl=min(127,PATCHES[ch][2][3][1]+attenuation)
    if tl!=last_tl[ch]:cmds+=fm(ch,0x4C,tl);last_tl[ch]=tl
  # A soft high PSG square adds a recognisable 16-bit/chiptune edge; the
  # principal voices are FM. Avoid DAC samples and noise-channel clock sharing.
  hz,vol=tone[0];period=max(1,min(1023,round(3579545/(32*hz*2))))
  att=15 if not vol else min(14,10+round(-20*math.log10(max(.01,vol/5))/2))
  current=(period,att)
  if current!=psg_last:
   cmds += [0x50,0x80|(period&15),0x50,(period>>4)&63,0x50,0x90|att]
   psg_last=current
  frames.append(cmds)
 stop=[]
 for ch in range(5):
  stop+=key(ch,False)
  for op in range(4):stop+=fm(ch,0x40+op*4,127)
 for ch in range(4):stop+=[0x50,0x9F|(ch<<5)]
 return init,frames,stop,notes

def carray(name,data):
 lines=['    '+', '.join(f'0x{x:02X}' for x in data[i:i+20])+',' for i in range(0,len(data),20)]
 return f'static const u8 {name}[{len(data)}] = {{\n'+'\n'.join(lines)+'\n};\n'

def write(root,out):
 rows=trace(root);init,frames,stop,notes=generate(rows)
 stream=sum((x+[0x62] for x in frames),[])+[0x66]
 out.mkdir(parents=True,exist_ok=True);(out/'src').mkdir(exist_ok=True);(out/'apercu').mkdir(exist_ok=True)
 data=carray('prologue_init',init)+carray('prologue_data',stream)+carray('prologue_stop',stop)
 (out/'src/prologue_fm_data.inc').write_text('// Generated by tools/build_fm_prologue.py; no PCM samples.\n'+data)
 vgm=bytearray(0x100);vgm[:4]=b'Vgm ';struct.pack_into('<I',vgm,8,0x171)
 struct.pack_into('<I',vgm,0x0C,3579545);struct.pack_into('<I',vgm,0x2C,FM_CLOCK)
 struct.pack_into('<I',vgm,0x18,FRAMES*735);struct.pack_into('<I',vgm,0x24,60)
 struct.pack_into('<I',vgm,0x34,0x100-0x34)
 struct.pack_into('<H',vgm,0x28,9);vgm[0x2A]=16
 vgm+=bytes(init+sum((x+[0x62] for x in frames),[])+stop+[0x66])
 struct.pack_into('<I',vgm,4,len(vgm)-4)
 (out/'apercu/Prologue-FM-PSG.vgm').write_bytes(vgm)
 info=dict(frames=FRAMES,seconds=FRAMES/60,voices=[p[0] for p in PATCHES],
           init_bytes=len(init),stream_bytes=len(stream),stop_bytes=len(stop),
           music_rom_bytes=len(init)+len(stream)+len(stop),pcm_bytes=0,note_events=len(notes),
           max_frame_bytes=max(map(len,frames)))
 (out/'apercu/partition.json').write_text(json.dumps(dict(info=info,notes=notes),indent=2)+'\n')
 print(json.dumps(info,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path)
 p.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();write(a.project,a.out)

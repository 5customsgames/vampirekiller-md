import sys; sys.argv=['x']
from nes_dump import Machine
from pathlib import Path
rom=Path("../../Castlevania (USA) (Rev 1).nes").read_bytes()
def score_of(m):
    base=(m.ctrl&1)*1024
    d=[m.nt[base+2*32+6+i]-208 for i in range(6)]
    return int("".join(str(x) for x in d)) if all(0<=x<=9 for x in d) else None
def run(code):
    m=Machine(rom); mpu=m.mpu; mpu.reset(); mpu.pc=m.mem[0xFFFC]|(m.mem[0xFFFD]<<8); ram=m.mem._subject
    st={"absx":0,"prev":None,"force":False}
    def frame(pad):
        m.pad=pad; ram[0x45]=0x40
        start=mpu.processorCycles; m.vblank,m.spr0=True,False
        if m.ctrl&0x80: mpu.nmi()
        for stage,limit in ((0,2273),(1,7000),(2,29780)):
            while mpu.processorCycles<start+limit:
                if mpu.pc==0xEB7E and st["force"]:
                    ram[0x584+mpu.x]=code
                mpu.step()
            if stage==0: m.vblank=False
            if stage==1: m.spr0=True
        tot=(m.ctrl&1)*256+m.scroll_x
        if st["prev"] is not None:
            d=(tot-st["prev"])%512; st["absx"]+=d if d<256 else d-512
        st["prev"]=tot
    for f in range(1100): frame(8 if 300<=f<304 else 0)
    st["prev"]=(m.ctrl&1)*256+m.scroll_x
    def sprites(): return [(st["absx"]+m.oam[i*4+3],m.oam[i*4],m.oam[i*4+1],m.oam[i*4+2]) for i in range(1,64) if m.oam[i*4]<0xEF]
    def anchor():
        c=[x for x,y,t,a in sprites() if t in (8,16,24,52,42)]
        return min(c) if c else None
    cx,cy=796,176
    alive=lambda: any(t in (0x40,0x50) and abs(x-cx)<=4 and abs(y-cy)<=2 for x,y,t,a in sprites())
    n=0
    while not alive() and n<4000: frame(0x80); n+=1
    n=0
    while n<600:
        a=anchor()
        if a is None: frame(0)
        elif a<cx-30: frame(0x80)
        elif a>cx+24: frame(0x40)
        else: break
        n+=1
    for _ in range(25): frame(0)
    before=score_of(m)
    st["force"]=True
    for i in range(70): frame(2 if i==0 else 0)
    st["force"]=False
    for i in range(120): frame(0x80)           # walk right over the item
    return before,score_of(m)
for code in (0x11,0x21,0x31,0x01):
    b,a=run(code)
    print(f"code {code:#04x}: score {b} -> {a}  (+{(a or 0)-(b or 0)})",flush=True)

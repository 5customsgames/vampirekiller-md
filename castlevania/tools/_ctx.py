import sys; sys.argv=['x']
from nes_dump import Machine
from pathlib import Path
rom=Path("../../Castlevania (USA) (Rev 1).nes").read_bytes()
def run(cx,cy,kind,force=None):
    m=Machine(rom); mpu=m.mpu; mpu.reset(); mpu.pc=m.mem[0xFFFC]|(m.mem[0xFFFD]<<8); ram=m.mem._subject
    st={"absx":0,"prev":None,"ctx":None,"types":[]}
    def frame(pad):
        m.pad=pad; ram[0x45]=0x40
        start=mpu.processorCycles; m.vblank,m.spr0=True,False
        if m.ctrl&0x80: mpu.nmi()
        for stage,limit in ((0,2273),(1,7000),(2,29780)):
            while mpu.processorCycles<start+limit:
                if mpu.pc==0xEB7E:
                    if st["ctx"] is None:
                        st["ctx"]={k:ram[a] for k,a in (("$64",0x64),("$70",0x70),("$71",0x71),("$72",0x72),("$79",0x79),("$15b",0x15b),("$6d",0x6d),("$28",0x28),("code",0x584+mpu.x))}
                    if force is not None:
                        ram[0x584+mpu.x]=force
                if mpu.pc==0xEF04: st["types"].append(mpu.a)
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
    if kind=="brazier":
        alive=lambda: any(t in (0x97,0x99) and abs(x-cx)<=1 for x,y,t,a in sprites())
    else:
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
    seen={}
    for i in range(120):
        frame(2 if i==0 else 0)
        for x,y,t,a in sprites():
            if abs(x-cx)<=24 and 100<y<214 and t in (0xBF,0xC1,0xC3,0xBB,0xBD,0x9F,0xA1,0xA3,0xAD,0xAF,0x60,0x62,0xA5,0xA7,0xB7,0xB9): seen[(hex(t),a)]=seen.get((hex(t),a),0)+1
    return st["ctx"],[hex(t) for t in sorted(set(st["types"]))],sorted(k for k,v in seen.items() if v>=15)
for name,cx,cy,kind in (("brazier 2 (courtyard)",216,176,"brazier"),("hall candle 796",796,176,"candle")):
    for force in (None,0,4):
        ctx,types,sp=run(cx,cy,kind,force)
        print(name,"force",force,"| state",ctx,"| types",types,"| sprites",sp)

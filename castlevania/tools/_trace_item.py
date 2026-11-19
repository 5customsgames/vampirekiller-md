import sys; sys.argv=['x']
from nes_dump import Machine
from pathlib import Path
from py65.disassembler import Disassembler
rom=Path("../../Castlevania (USA) (Rev 1).nes").read_bytes()

def scenario(trace_frame=None):
    m=Machine(rom); m.mpu.reset(); m.mpu.pc=m.mem[0xFFFC]|(m.mem[0xFFFD]<<8); ram=m.mem._subject
    st={"absx":0,"prev":None,"n":0}
    trace=[]
    def step(pad):
        m.pad=pad; ram[0x45]=0x40
        if trace_frame is not None and st["n"]==trace_frame:
            # run this frame by hand, logging every instruction
            mpu=m.mpu
            start=mpu.processorCycles
            m.vblank,m.spr0=True,False
            if m.ctrl&0x80: mpu.nmi()
            for stage,limit in ((0,2273),(1,7000),(2,29780)):
                while mpu.processorCycles<start+limit:
                    trace.append((mpu.pc,m.bank,mpu.a,mpu.x,mpu.y)); mpu.step()
                if stage==0: m.vblank=False
                if stage==1: m.spr0=True
        else:
            m.frame()
        st["n"]+=1
        tot=(m.ctrl&1)*256+m.scroll_x
        if st["prev"] is not None:
            d=(tot-st["prev"])%512; st["absx"]+=d if d<256 else d-512
        st["prev"]=tot
    for f in range(1100): step(8 if 300<=f<304 else 0)
    st["prev"]=(m.ctrl&1)*256+m.scroll_x
    def sprites(): return [(st["absx"]+m.oam[i*4+3],m.oam[i*4],m.oam[i*4+1],m.oam[i*4+2]) for i in range(1,64) if m.oam[i*4]<0xEF]
    def anchor():
        c=[x for x,y,t,a in sprites() if t in (8,16,24,52,42)]
        return min(c) if c else None
    cx,cy=796,176
    alive=lambda: any(t in (0x40,0x50) and abs(x-cx)<=4 and abs(y-cy)<=2 for x,y,t,a in sprites())
    n=0
    while not alive() and n<4000: step(0x80); n+=1
    n=0
    while n<600:
        a=anchor()
        if a is None: step(0)
        elif a<cx-30: step(0x80)
        elif a>cx+24: step(0x40)
        else: break
        n+=1
    for _ in range(25): step(0)
    events={}
    for i in range(70):
        step(2 if i==0 else 0)
        sp=sprites()
        if "destroyed" not in events and not alive(): events["destroyed"]=(i,st["n"])
        if "sparkle" not in events and any(t==0x70 for x,y,t,a in sp): events["sparkle"]=(i,st["n"])
        if "item" not in events and any(t==0xC1 for x,y,t,a in sp): events["item"]=(i,st["n"])
    return m,events,trace,st

m,events,_,_=scenario()
print("events (whip frame index, global frame):",events)
tf=events["item"][1]-1       # the global frame number before the item shows up = frame in which it is created
m2,ev2,trace,_=scenario(trace_frame=tf)
print("traced frame",tf,"instructions:",len(trace))
d=Disassembler(m2.mpu)
# print the distinct code ranges executed in the traced frame (excluding the idle loop and NMI scaffolding)
pcs=sorted(set(p for p,b,a,x,y in trace))
ranges=[];s=pcs[0];prev=pcs[0]
for p in pcs[1:]:
    if p-prev>12: ranges.append((s,prev)); s=p
    prev=p
ranges.append((s,prev))
print("executed code ranges:",[(hex(a),hex(b)) for a,b in ranges])
import pickle; pickle.dump(trace,open("trace_item.pkl","wb"))

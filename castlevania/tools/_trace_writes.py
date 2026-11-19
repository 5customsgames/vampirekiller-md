import sys; sys.argv=['x']
exec(open("_trace_item.py").read().split("m,events,_,_=scenario()")[0])
# re-run the scenario while logging RAM writes between whip hit and item appearance
m=Machine(rom); m.mpu.reset(); m.mpu.pc=m.mem[0xFFFC]|(m.mem[0xFFFD]<<8); ram=m.mem._subject
writes=[]; logging=[False]
orig=m.mem.__class__.__setitem__
def hook(self,address,value):
    if logging[0] and isinstance(address,int):
        a=address&0xffff
        if a<0x800 and not (0x200<=a<0x300) and not (0x100<=a<0x200) and not (a>=0x700):
            writes.append((m.mpu.pc,a,value))
    return orig(self,address,value)
m.mem.__class__.__setitem__=hook
st={"absx":0,"prev":None,"n":0}
def step(pad):
    m.pad=pad; ram[0x45]=0x40; m.frame(); st["n"]+=1
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
snap=bytes(ram[:0x800])
log={}
for i in range(60):
    logging[0]=True
    step(2 if i==0 else 0)
    logging[0]=False
    log[i]=list(writes); writes.clear()
# summarize: writes from frames 14..40 whose address is not written every frame (skip the noisy always-written addresses)
from collections import Counter
cnt=Counter()
for i in range(60):
    for pc,a,v in log[i]: cnt[a]+=1
rare=[a for a,c in cnt.items() if c<=6]
print("addresses written rarely (<=6 times in 60 frames):")
for i in range(12,45):
    ev=[(hex(pc),hex(a),hex(v)) for pc,a,v in log[i] if a in rare]
    if ev: print(i,ev[:14])

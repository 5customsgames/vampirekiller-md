#!/usr/bin/env python3
"""Execute the original 6502 boss hit gate, using the project's extracted PRG.
Requires py65, as do the existing NES recording tools.
"""
from pathlib import Path
from py65.devices.mpu6502 import MPU
root=Path(__file__).resolve().parents[1]
p=(root/'tools/extracted/prg.bin').read_bytes()
# A surviving ordinary boss hit loads 8 into that object's $0568 timer.
fixed=p[-16384:]
assert fixed[0xE2A9-0xC000:0xE2AE-0xC000]==bytes.fromhex('A9 08 9D 68 05')
entries={'Bat':0x80C7,'Medusa':0x82C5,'Mummies':0x8644,'Frankenstein':0x89E2,'Death':0x8EB8,
         'Dracula (first form)':0x94F4,'Dracula (second form)':0x9520}
for name,entry in entries.items():
 m=MPU();m.memory[0xC000:]=fixed;m.memory[0x8000:0xC000]=p[5*16384:6*16384]
 assert bytes(m.memory[entry:entry+3])==bytes.fromhex('20 A7 EE'),name
 slot=7;m.x=slot;m.memory[0x568+slot]=8;m.memory[0x488+slot]=0x80
 results=[]
 for frame in range(9):
  m.pc=entry;m.sp=0xFF;m.stPushWord(0x5FFF)
  for _ in range(64):
   if m.pc in (0x6000,entry+3):break
   m.step()
  else:raise AssertionError('gate did not return')
  frozen=m.pc==0x6000
  assert frozen==(frame<8),(name,frame,frozen)
  assert m.memory[0x568+slot]==max(0,7-frame)
  results.append('stop' if frozen else 'resume')
 print(name+': '+', '.join(results))
print('Original NES code: eight AI calls skipped, ninth call resumes.')

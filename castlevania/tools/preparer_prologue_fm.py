#!/usr/bin/env python3
"""Disable only the previous PCM-prologue resource after copying the FM files."""
from pathlib import Path
import argparse,re
p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',nargs='?',type=Path,default=Path('.'));a=p.parse_args()
root=a.project
if not (root/'src/prologue_fm.c').is_file() or 'fm_prologue_mode' not in (root/'src/sound.c').read_text():
 p.exit(1,'Copy the FM prologue files into the project first.\n')
old=root/'res/prologue_audio.res'
if not old.exists():print('No previous PCM prologue resource: nothing to disable.')
else:
 content=old.read_text();code=re.sub(r'//[^\n]*','',content).strip()
 if ' '.join(code.split())!='BIN prologue_pcm "audio/prologue.pcm" 256 256 0 NONE FALSE':
  p.exit(1,'The resource differs from the previous PCM prologue; no file changed.\n')
 backup=old.with_name('prologue_audio.res.desactive-FM')
 if backup.exists():p.exit(1,'Resource backup already exists; no file changed.\n')
 old.rename(backup)
 print('Previous 239 KiB PCM prologue resource disabled; original file kept as backup.')

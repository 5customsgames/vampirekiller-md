#!/usr/bin/env python3
"""Validate the checked-in hall collision map against room 1/0 artwork tiles."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from lz4w_pack import unpack
root = Path(__file__).resolve().parents[1] / 'sgdk/src/generated'
player = (root / 'player_assets.c').read_text()
rooms = (root / 'rooms.c').read_text()
match = re.search(r'vk_player_room\[768\]\s*=\s*\{([^}]*)\}', player, re.S)
assert match
hall = [int(v) for v in re.findall(r'\d+', match.group(1))]
# vk_maps_z: the rooms packed in LZ4W one after the other, room i at vk_maps_off[i]
z = bytes(int(v) for v in re.findall(r'\d+', re.search(r'vk_maps_z\[\d+\][^=]*=\s*\{(.*?)\};', re.sub(r'/\*.*?\*/', '', rooms), re.S).group(1)))
off = [int(v) for v in re.findall(r'\d+', re.search(r'vk_maps_off\[\d+\]\s*=\s*\{(.*?)\};', rooms, re.S).group(1))]
visible = list(unpack(z[off[0]:off[1]]))
assert len(hall) == 768 and len(visible) == 704
assert hall[64:] == visible, 'Hall collision tiles differ from rendered stage 1 room 0'
print('Hall collision map: 704/704 visible tiles match stage 1 room 0; top 64 preserved')

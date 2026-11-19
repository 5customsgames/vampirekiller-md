#!/bin/sh
# The 12-18 playthrough (tests/md_playthrough/playthrough_12_18.txt, recorded in PSG + MSX graphics) in the other modes: FM, 16-bit graphics, both.
# The stage start draws take one more VBlank in these modes, so tools/playthrough_12_18_md.py adds one idle frame after the start of the stages of
# MODE_SHIFTS (research/frame-timing.md section 6); same 55 checkpoints, 0 lost frame, 0 absorbed turn, and the project floor of 6 lines
# (MIN_SLACK=N to change it) on every ordinary turn.
set -eu
cd "$(dirname "$0")/.."
: "${VK_MD_CORE:?Set VK_MD_CORE}"
OUT="${VK_PLAYTHROUGH_OUT:-scratchpad/playthrough}"
for mode in "VK_SOUND_FM=1" "VK_GFX16=1" "VK_SOUND_FM=1 VK_GFX16=1"; do
    echo "== $mode"
    env $mode ${PYTHON:-python3} tools/playthrough_12_18_md.py --core "$VK_MD_CORE" --out "$OUT" --min-slack "${MIN_SLACK-6}"
done

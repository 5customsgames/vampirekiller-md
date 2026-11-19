#!/bin/sh
# Continuous playthrough of stages 12 to 18 on the MD build (controller inputs only after the RAM entry).
# VIDEO=path.mp4 also exports the run as a 60 fps H.264 video (x2 nearest neighbour, ffmpeg required).
# MIN_SLACK=N: fail when an ordinary turn ends less than N lines before the VBlank (default 6, the project floor; MIN_SLACK= to skip).
# RECORD=1 searches the inputs again (slow: minutes) and rewrites tests/md_playthrough/playthrough_12_18.txt.
set -eu
cd "$(dirname "$0")/.."
: "${VK_MD_CORE:?Set VK_MD_CORE}"
OUT="${VK_PLAYTHROUGH_OUT:-scratchpad/playthrough}"
set -- --core "$VK_MD_CORE" --out "$OUT"
[ -n "${VIDEO:-}" ] && set -- "$@" --video "$VIDEO"
[ -n "${RECORD:-}" ] && set -- "$@" --record
[ -n "${MIN_SLACK-6}" ] && [ -z "${RECORD:-}" ] && set -- "$@" --min-slack "${MIN_SLACK-6}"
exec ${PYTHON:-python3} tools/playthrough_12_18_md.py "$@"

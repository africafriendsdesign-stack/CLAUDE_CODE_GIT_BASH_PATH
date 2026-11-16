#!/usr/bin/env bash
# Assemble : plans + vignettage + calque motion design + grain + musique masterisée.
set -euo pipefail
W=${W:-./work}; OUT=${OUT:-./Demenagement_Express_Spot_9x16.mp4}
ls "$W"/clips/c*.mp4 | sed 's/^/file /' > "$W/clips/list.txt"
ffmpeg -v error -y -f concat -safe 0 -i "$W/clips/list.txt" \
  -vf "tpad=stop_mode=clone:stop_duration=6,trim=end_frame=975,setpts=PTS-STARTPTS" \
  -c:v libx264 -crf 14 -preset fast -pix_fmt yuv420p "$W/base.mp4"
ffmpeg -v error -y -i "$W/base.mp4" -framerate 30 -i "$W/ov/%04d.png" -i "$W/music.wav" \
  -filter_complex "[0:v]vignette=angle=PI/4.5:mode=forward[v];[v][1:v]overlay=format=auto[o];\
[o]noise=alls=5:allf=t,format=yuv420p[vout];\
[2:a]loudnorm=I=-14:TP=-1.0:LRA=9[aout]" \
  -map "[vout]" -map "[aout]" -c:v libx264 -preset slow -crf 19 -maxrate 16M -bufsize 32M -profile:v high -r 30 \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart -shortest "$OUT"
echo "OK -> $OUT"

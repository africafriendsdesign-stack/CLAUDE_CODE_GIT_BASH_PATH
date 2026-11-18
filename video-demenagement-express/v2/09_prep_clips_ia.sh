#!/usr/bin/env bash
# Normalise les clips Kling vers clips_ia/P01..P10.mp4 (1080x1920, 30 fps, filigrane retiré par recadrage).
set -euo pipefail
U=${U:-/root/.claude/uploads/a9c2a5bb-5ea8-5ac6-985d-9934e2f2cc71}
OUTD=$(cd "$(dirname "$0")" && pwd)/clips_ia; mkdir -p "$OUTD"
V="crop=680:1208:20:0"            # vertical 720x1280 : retire les ~70 px du bas (logo « KlingAI 4.0 »)
# id fichier début durée vitesse recadrage
LIST=(
 "P01 59865617-Pomt1      0.0  5.0 1.0  $V"
 "P02 dcb6d662-Prompt2    0.0  5.0 1.0  PAN"
 "P03 c5823c05-Promts3    0.0  2.05 0.82 $V"
 "P04 1e53a9d3-Prompt4    0.0  5.0 1.0  $V"
 "P05 0f9e40ea-Prompt5    0.5  5.5 1.0  $V"
 "P06 9a0bfa4d-Prompt6    1.0  4.0 1.0  $V"
 "P07 2a2c1663-Promt7     2.05 4.0 1.0  $V"
 "P08 f221d16f-Prompt8    0.5  4.5 1.0  $V"
 "P09 9cbb6230-Prompts9   0.3  5.2 1.0  $V"
 "P10 efcb357d-Prompts10  0.8  5.2 1.0  $V"
)
for l in "${LIST[@]}"; do
  read -r id f ss dur sp crop <<<"$l"
  if [[ $crop == PAN ]]; then   # 16:9 -> 9:16 : panoramique de la cliente (gauche) vers l'équipe (droite)
    crop="crop=371:660:'250+530*min(t/$dur,1)':0"
  fi
  ffmpeg -nostdin -v error -y -ss "$ss" -t "$dur" -i "$U/$f.mp4" -an \
    -vf "$crop,setpts=PTS/$sp,scale=1080:1920:flags=lanczos,setsar=1,framerate=fps=30,unsharp=5:5:0.4" \
    -c:v libx264 -crf 15 -preset fast -pix_fmt yuv420p "$OUTD/$id.mp4"
  echo "$id $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUTD/$id.mp4")"
done

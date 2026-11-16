#!/usr/bin/env bash
# Version 2 : clips IA (clips_ia/P01.mp4 … P10.mp4) + voix off + sous-titres + musique + carte de fin.
# Les plans manquants sont remplacés par des cartes de repère (animatic).
# Prérequis : 05_voix.py puis 06_timeline.py ont produit $W/v2/{vo.wav,timeline.json}.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(dirname "$HERE")
W=${W:-./work}; V2="$W/v2"; mkdir -p "$V2/plans"
OUT=${OUT:-$HERE/Demenagement_Express_V2_9x16.mp4}
TL="$V2/timeline.json"
python3 "$ROOT/03_music.py" "$V2/music.wav" "$TL" >/dev/null
GRADE="eq=contrast=1.05:saturation=1.08,colorbalance=rs=-0.03:bs=0.04:rh=0.04:bh=-0.03"
MISSING=()
: > "$V2/plans/list.txt"
while read -r id dur; do
  src="$HERE/clips_ia/$id.mp4"; n=$(python3 -c "print(round($dur*30))")
  if [[ -f "$src" ]]; then
    # recadrage 9:16 centré, 30 fps, étalonnage commun pour unifier les clips IA
    ffmpeg -nostdin -v error -y -i "$src" -an -vf "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1,fps=30,$GRADE,tpad=stop_mode=clone:stop_duration=$dur,trim=end_frame=$n,setpts=PTS-STARTPTS" \
      -c:v libx264 -crf 15 -preset fast -pix_fmt yuv420p "$V2/plans/$id.mp4"
  else
    [[ $id != END ]] && MISSING+=("$id")
    ffmpeg -nostdin -v error -y -f lavfi -i "color=c=0x1a1a1d:s=1080x1920:r=30:d=$dur" -c:v libx264 -crf 20 -pix_fmt yuv420p "$V2/plans/$id.mp4"
  fi
  echo "file '$V2/plans/$id.mp4'" >> "$V2/plans/list.txt"
done < <(python3 -c "import json;[print(p['id'],p['dur']) for p in json.load(open('$TL'))['plans']]")
echo "Clips manquants (cartes de repère) : ${MISSING[*]:-aucun}"
MODE=v2; [[ ${#MISSING[@]} -gt 0 ]] && MODE=v2-animatic
python3 - "$TL" "$V2/timeline_render.json" "${MISSING[@]}" <<'PY'
import json, sys
tl = json.load(open(sys.argv[1])); miss = set(sys.argv[3:])
tl['plans'] = [p for p in tl['plans'] if p['id'] in miss]
json.dump(tl, open(sys.argv[2], 'w'), ensure_ascii=False)
PY
rm -rf "$V2/ov"; T=$(python3 -c "import json;print(json.load(open('$TL'))['total'])")
q=$(python3 -c "print($T/4)")
for k in 0 1 2 3; do
  TIMELINE="$V2/timeline_render.json" MODE=$MODE node "$ROOT/02_render_overlay.js" "$V2/ov" $(python3 -c "print($k*$q, ($k+1)*$q)") &
done; wait
ffmpeg -v error -y -f concat -safe 0 -i "$V2/plans/list.txt" -framerate 30 -i "$V2/ov/%04d.png" -i "$V2/vo.wav" -i "$V2/music.wav" \
  -filter_complex "[0:v]vignette=angle=PI/5[v];[1:v]setpts=PTS-STARTPTS[o];[v][o]overlay=format=auto,noise=alls=4:allf=t,format=yuv420p[vout];\
[2:a]volume=1.0[vo];[3:a]volume=0.55[mu];[vo][mu]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.0:LRA=9[aout]" \
  -map "[vout]" -map "[aout]" -c:v libx264 -preset slow -crf 19 -maxrate 16M -bufsize 32M -r 30 \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart -t "$T" "$OUT"
echo "OK -> $OUT"

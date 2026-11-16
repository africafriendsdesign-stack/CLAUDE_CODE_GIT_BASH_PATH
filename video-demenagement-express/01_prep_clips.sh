#!/usr/bin/env bash
# Prépare chaque plan : coupe, stabilisation, upscale 1080x1920, étalonnage, push-in.
set -euo pipefail
U=${U:-/root/.claude/uploads/a9c2a5bb-5ea8-5ac6-985d-9934e2f2cc71}
W=${W:-./work}; mkdir -p "$W/clips"
A="$U/4d64f4ae-AllVideo_01794846144365.mp4"   # emballage canapés
B="$U/8cfce370-AllVideo_01794846255750.mp4"   # camion, escaliers, salon final
C="$U/4a95f0f1-AllVideo_01794846339770.mp4"   # colis filmés étiquetés
D="$U/c1cfe0b5-AllVideo_01794846413467.mp4"   # équipe escalier, filmage, chaises
E="$U/9590d71d-AllVideo_01794846459690.mp4"   # couloir de nuit
# id  source start durée(s du plan)  zoom_from zoom_to
CLIPS=(
 "c01 $B 0.0 3.0 1.00 1.10"
 "c02 $A 4.0 2.0 1.04 1.12"
 "c03 $D 11.3 2.5 1.10 1.02"
 "c04 $D 15.0 2.0 1.02 1.10"
 "c05 $C 13.0 2.0 1.10 1.02"
 "c06 $B 4.0 3.0 1.02 1.12"
 "c07 $D 1.0 2.0 1.06 1.14"
 "c08 $E 11.8 2.0 1.04 1.12"
 "c09 $B 14.0 2.0 1.10 1.02"
 "c10 $D 19.0 2.0 1.02 1.10"
 "c11 $B 8.0 2.0 1.04 1.12"
 "c12 $B 19.0 2.9 1.00 1.08"
)
GRADE="hqdn3d=2:2:4:4,eq=contrast=1.08:saturation=1.12:gamma=0.97,colorbalance=rs=-0.04:bs=0.05:rh=0.05:bh=-0.04:gh=0.01,unsharp=5:5:0.6"
# CLIPS_FILE : liste alternative « id A|B|C|D|E début durée zoom0 zoom1 » (une ligne par plan)
if [[ -n "${CLIPS_FILE:-}" ]]; then
  CLIPS=(); while read -r id L ss dur z0 z1; do [[ -z "$id" || "$id" == \#* ]] && continue; CLIPS+=("$id ${!L} $ss $dur $z0 $z1"); done < "$CLIPS_FILE"
fi
for line in "${CLIPS[@]}"; do
  read -r id src ss dur z0 z1 <<<"$line"
  [[ -n "${ONLY:-}" && "$ONLY" != *"$id"* ]] && continue
  n=$(python3 -c "print(round($dur*30))")
  ffmpeg -nostdin -v error -y -ss "$ss" -t "$dur" -i "$src" -an -vf "vidstabdetect=shakiness=6:accuracy=12:result=$W/clips/$id.trf" -f null -
  # push-in : zoom interpolé linéairement sur la durée du plan, recadrage centré
  ffmpeg -nostdin -v error -y -ss "$ss" -t "$dur" -i "$src" -an -vf "\
vidstabtransform=input=$W/clips/$id.trf:smoothing=18:optzoom=1:interpol=bicubic,\
scale=1080:1920:flags=lanczos,setsar=1,$GRADE,\
scale=w='trunc(1080*($z0+($z1-$z0)*t/$dur)/2)*2':h=-2:eval=frame:flags=bicubic,crop=1080:1920,\
fps=30,tpad=stop_mode=clone:stop_duration=1,trim=end_frame=$n,setpts=PTS-STARTPTS" \
    -c:v libx264 -preset medium -crf 14 -pix_fmt yuv420p "$W/clips/$id.mp4"
  echo "ok $id ($n frames)"
done

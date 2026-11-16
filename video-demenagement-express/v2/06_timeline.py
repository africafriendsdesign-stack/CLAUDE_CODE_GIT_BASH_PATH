#!/usr/bin/env python3
"""Calcule la timeline (plans + voix + sous-titres) et mixe la piste voix.
Usage : python3 06_timeline.py <dossier_voix_wav> <sortie_dossier>"""
import json, os, subprocess, sys, wave
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
vdir, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
sc = json.load(open(os.path.join(here, 'scenario.json')))

def load(p):
    with wave.open(p) as w:
        sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), '<i2') / 32768
    # retire les silences de bord
    nz = np.where(np.abs(a) > .01)[0]; a = a[max(0, nz[0] - 200): nz[-1] + 1200]
    return a, sr

t, prev_end, plans, cues, clips = 0.0, 0.0, [], [], []
items = [(p['id'], p['dur'], p['vo'], p['vo'], p['titre']) for p in sc['plans']] + [('END', sc['end_card'], sc['end_vo'], sc['end_sub'], 'Carte de fin')]
for pid, dur, vo, sub, titre in items:
    a, sr = load(os.path.join(vdir, pid + '.wav'))
    st = max(t + .25, prev_end + .2) if pid != 'END' else max(t + .9, prev_end + .2)
    L = len(a) / sr; clips.append((st, a)); prev_end = st + L
    plans.append({'id': pid, 'start': round(t, 3), 'dur': dur, 'titre': titre})
    # sous-titres : découpe en segments ≤ 34 caractères, durée ∝ longueur
    words, segs, cur = sub.split(), [], ''
    for w_ in words:
        if len(cur) + len(w_) + 1 > 34 and cur: segs.append(cur); cur = w_
        else: cur = (cur + ' ' + w_).strip()
    segs.append(cur); tot = sum(len(s) for s in segs); u = st
    for s in segs:
        d_ = L * len(s) / tot; cues.append({'t0': round(u, 3), 't1': round(u + d_, 3), 'txt': s}); u += d_
    t += dur
    if prev_end > t + (0 if pid == 'END' else .8):
        print(f'ATTENTION {pid}: la voix dépasse le plan de {prev_end - t:.2f}s')
total = round(t, 3)
mix = np.zeros(int(max(total, prev_end) * sr) + sr)
for st, a in clips:
    i = int(st * sr); mix[i:i + len(a)] += a
mix = mix[: int(total * sr)]
with wave.open(os.path.join(out, 'vo_raw.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
# traitement « voix radio » : passe-haut, présence, compression, un soupçon de réverb
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(out, 'vo_raw.wav'), '-af',
    'highpass=f=85,equalizer=f=220:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=3.5,equalizer=f=9000:t=h:w=1:g=2,'
    'acompressor=threshold=-20dB:ratio=3.5:attack=5:release=120:makeup=4,aecho=0.8:0.5:35|60:0.12|0.07,aresample=48000',
    '-ac', '2', os.path.join(out, 'vo.wav')], check=True)
tl = {'total': total, 'outro': plans[-1]['start'], 'plans': plans, 'cues': cues,
      'vo_spans': [[round(st, 3), round(st + len(a) / sr, 3)] for st, a in clips]}
json.dump(tl, open(os.path.join(out, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
for p in plans: print(p)
print('total', total)

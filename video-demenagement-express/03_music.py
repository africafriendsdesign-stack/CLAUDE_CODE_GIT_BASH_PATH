#!/usr/bin/env python3
"""Bande-son originale synthétisée (aucun sample externe, libre de droits).
120 BPM, calée sur le montage : volets à 3.0 / 11.5 / 20.5 / 27.5 s.
Usage : python3 03_music.py sortie.wav
"""
import sys, wave
import numpy as np

SR, DUR, BPM = 48000, 32.5, 120
BEAT = 60 / BPM
CUTS = [3.0, 11.5, 20.5, 27.5]
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i, v in enumerate(x):
        s = (1 - a) * v + a * s; y[i] = s
    return y


def lp_fft(x, fc, order=4):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** (2 * order)), len(x))


def hp_fft(x, fc, order=4):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order)), len(x))


def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR); j = min(N, i + len(sig))
    if j <= i: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt(0.5 * (1 - pan)) * 1.414
    R[i:j] += s * np.sqrt(0.5 * (1 + pan)) * 1.414


def note(n):  # numéro MIDI -> Hz
    return 440 * 2 ** ((n - 69) / 12)


def drums_on(x):  # batterie entre 3.0 et 27.5, coupée 0.5 s avant chaque volet (tension)
    if x < 3.0 or x >= 27.25: return False
    return not any(T - 0.5 <= x < T for T in CUTS[1:3])


# ---------- grosse caisse + sidechain ----------
kick_len = int(0.45 * SR); kt = np.arange(kick_len) / SR
freq = 45 + 110 * np.exp(-kt * 28)
kick = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-kt * 7.5)
kick[:200] += rng.standard_normal(200) * np.linspace(.6, 0, 200)
duck = np.ones(N)
b = 3.0
while b < DUR:
    if drums_on(b):
        add(kick, b, 0.95)
        i = int(b * SR); j = min(N, i + int(0.3 * SR))
        duck[i:j] = np.minimum(duck[i:j], 1 - 0.55 * np.exp(-np.arange(j - i) / SR * 12))
    b += BEAT

# ---------- clap / hats ----------
cl = int(.25 * SR); ct = np.arange(cl) / SR
clap = hp_fft(rng.standard_normal(cl), 900, 2) * (np.exp(-ct * 22) + .5 * np.exp(-((ct - .012) * 400) ** 2))
hl = int(.06 * SR); hat = hp_fft(rng.standard_normal(hl), 7000, 3) * np.exp(-np.arange(hl) / SR * 70)
b = 3.0
while b < DUR:
    if drums_on(b + BEAT) : add(clap, b + BEAT, .32, .1)
    for k in range(4):
        x = b + k * BEAT / 2 + BEAT / 4
        if drums_on(x) and x > 3.0 + 2 * BEAT: add(hat, x, .14 if k % 2 else .09, -.35 if k % 2 else .35)
    b += 2 * BEAT

# ---------- accords (pad) + basse ----------
PROG = [(57, [57, 60, 64, 69]), (53, [53, 57, 60, 65]), (48, [55, 60, 64, 67]), (55, [55, 59, 62, 67])]  # Am F C G
BAR = 4 * BEAT
pad = np.zeros(N); bass = np.zeros(N)
for bi in range(int(np.ceil(DUR / BAR))):
    root, chord = PROG[bi % 4]
    i0, i1 = int(bi * BAR * SR), min(N, int((bi + 1) * BAR * SR))
    tt = t[i0:i1]
    env = np.minimum(1, (tt - tt[0]) / .25) * np.minimum(1, (tt[-1] - tt) / .05 + .0)
    for n in chord:
        for det in (-.11, 0, .09):
            f = note(n + 12) * 2 ** (det / 12)
            pad[i0:i1] += (2 * ((tt * f) % 1) - 1) * env * .05
    fb = note(root - 12)
    gate = ((tt / (BEAT / 2)) % 1 < .7).astype(float)
    bass[i0:i1] += (2 * ((tt * fb) % 1) - 1) * gate * .5 + np.sin(2 * np.pi * fb * tt) * gate * .5
pad = lp_fft(pad, 1600, 2)
pad_env = np.interp(t, [0, 2.5, 3, 27.5, 28.5, 31.5, 32.5], [.45, 1, .75, .75, 1, .9, 0])
pad *= pad_env * duck
bass = lp_fft(bass, 320, 3) * np.interp(t, [0, 2.9, 3.0, 27.2, 27.5], [0, 0, 1, 1, 0]) * duck
# léger chorus stéréo sur le pad
dl = int(.013 * SR)
L += pad * .9 + bass * .55
R += np.concatenate([np.zeros(dl), pad[:-dl]]) * .9 + bass * .55

# ---------- arpège pluck (sections) ----------
pl = int(.22 * SR); pt = np.arange(pl) / SR
b = 3.0; step = 0
while b < 27.25:
    root, chord = PROG[int(b / BAR) % 4]
    n = chord[[0, 2, 1, 3, 2, 1, 3, 2][step % 8]] + 24
    s = np.sign(np.sin(2 * np.pi * note(n) * pt)) * .5 + np.sin(2 * np.pi * note(n) * pt)
    if drums_on(b): add(lp_fft(s, 3000, 2) * np.exp(-pt * 18) * .06, b, 1, .45 if step % 2 else -.45)
    b += BEAT / 2; step += 1

# ---------- whooshes sur les volets ----------
for T in CUTS:
    wl = int(1.3 * SR); wt = np.arange(wl) / SR - 0.9  # pic à T
    env = np.where(wt < 0, np.exp(wt * 5.5), np.exp(-wt * 9))
    nz = rng.standard_normal(wl)
    w = lp_fft(nz, 900, 2) * (1 - np.clip(wt + .9, 0, 1)) + hp_fft(nz, 1800, 2) * np.clip(wt + .9, 0, 1)
    w *= env
    pan = np.clip(wt * 1.5, -1, 1)
    i = int((T - .9) * SR); j = min(N, i + wl)
    L[i:j] += (w * np.sqrt(.5 * (1 - pan)))[: j - i] * .55
    R[i:j] += (w * np.sqrt(.5 * (1 + pan)))[: j - i] * .55

# ---------- impacts (titre d'ouverture + logo final) ----------
il = int(2.2 * SR); it = np.arange(il) / SR
imp = np.sin(2 * np.pi * (38 + 40 * np.exp(-it * 9)) * it) * np.exp(-it * 2.2)
imp += lp_fft(rng.standard_normal(il), 400, 2) * np.exp(-it * 6) * .8
add(imp, .42, .9); add(imp, 27.62, 1.0)
# riser vers le final
rl = int(2.4 * SR); rt = np.arange(rl) / SR
riser = hp_fft(rng.standard_normal(rl), 2500, 2) * (rt / rt[-1]) ** 3 * .25
riser += np.sin(2 * np.pi * np.cumsum(200 + 900 * (rt / rt[-1]) ** 2) / SR) * (rt / rt[-1]) ** 3 * .05
add(riser, 27.5 - 2.4, 1, 0)
# sonnerie discrète sur le téléphone (carte de fin)
for k in range(2):
    rgl = int(.09 * SR); rg = np.arange(rgl) / SR
    tone = (np.sin(2 * np.pi * 1320 * rg) + .5 * np.sin(2 * np.pi * 1760 * rg)) * np.exp(-rg * 25)
    add(tone, 27.5 + 1.8 + k * .14, .12, .2)

# ---------- master ----------
mix = np.stack([L, R], 1)
mix *= np.interp(t, [0, .05, DUR - .6, DUR], [0, 1, 1, 0])[:, None]
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix /= np.max(np.abs(mix)) / .89
with wave.open(sys.argv[1], 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((mix * 32767).astype('<i2').tobytes())
print('ok', sys.argv[1])

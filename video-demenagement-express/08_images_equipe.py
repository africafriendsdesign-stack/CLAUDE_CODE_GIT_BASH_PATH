#!/usr/bin/env python3
"""Extrait les images de référence de l'équipe (la plus nette de chaque fenêtre),
les améliore (×2, débruitage, netteté, étalonnage) et monte une planche 9:16.
Usage : python3 08_images_equipe.py <dossier_videos> <dossier_sortie> <dossier_tmp>"""
import glob, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
U, OUT, TMP = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
# nom, vidéo, début, fin, recadrage (x, y, w, h) sur 576x1024 ou None
REFS = [
    ('1_equipe_au_travail', '4d64f4ae', 1.4, 2.2, None),
    ('2_demenageur_camion', '4d64f4ae', 0.55, 1.2, (0, 130, 576, 764)),
    ('3_equipe_gilets_tshirts_rouges', 'c1cfe0b5', 7.3, 8.7, None),
    ('4_cheffe_gilet_orange', 'c1cfe0b5', 9.7, 10.4, None),
    ('5_demenageur_tshirt_rouge', '9590d71d', 11.7, 12.3, None),
    ('6_equipe_fauteuil', 'c1cfe0b5', 15.3, 16.9, (0, 128, 576, 768)),
    ('7_portage_exterieur', 'c1cfe0b5', 17.5, 18.9, (0, 128, 576, 768)),
]
def sharp(a):
    g = a.mean(2); return np.var(g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
font = lambda s, f='Black': ImageFont.truetype(f'/usr/share/fonts/opentype/inter/InterDisplay-{f}.otf', s)
outs = []
for name, vid, a, b, crop in REFS:
    src = glob.glob(f'{U}/{vid}*.mp4')[0]; d = f'{TMP}/{name}'; os.makedirs(d, exist_ok=True)
    for f_ in glob.glob(f'{d}/*.png'): os.remove(f_)
    # sélection exacte par horodatage (le seek rapide est imprécis sur ces vidéos de téléphone)
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', src, '-vf', f"select='between(t,{a},{b})'", '-fps_mode', 'vfr', f'{d}/%03d.png'], check=True)
    fr = sorted(glob.glob(f'{d}/*.png')); best = max(fr, key=lambda p: sharp(np.asarray(Image.open(p).convert('RGB'), float)))
    vf = 'hqdn3d=3:3:2:2'
    if crop: vf += ',crop=%d:%d:%d:%d' % (crop[2], crop[3], crop[0], crop[1])
    vf += ',scale=iw*2:ih*2:flags=lanczos,unsharp=7:7:1.0:5:5:0.0,eq=contrast=1.06:saturation=1.12:gamma=0.98,colorbalance=rh=0.03:bh=-0.02'
    o = f'{OUT}/{name}.jpg'
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', best, '-vf', vf, '-q:v', '2', o], check=True)
    outs.append((name, o)); print(name, os.path.basename(best), Image.open(o).size)
# planche 9:16
W, H = 1080, 1920; Y = (228, 255, 26); K = (11, 11, 12)
bd = Image.new('RGB', (W, H), K); dr = ImageDraw.Draw(bd)
dr.rectangle([60, 70, 76, 170], fill=Y)
dr.text((100, 62), "DÉMÉNAGEMENT", font=font(64), fill='white'); dr.text((100, 128), "EXPRESS · L'ÉQUIPE", font=font(52), fill=Y)
cells = [(60, 230, 470, 560), (550, 230, 470, 560), (60, 820, 470, 560), (550, 820, 470, 560), (60, 1410, 300, 440), (390, 1410, 300, 440), (720, 1410, 300, 440)]
labels = ["L'équipe au travail", "Devant le camion", "Gilets + t-shirts rouges", "Cheffe, gilet orange", "T-shirt rouge", "Filmage fauteuil", "Portage"]
for (name, o), (x, y, w, h), lab in zip(outs, cells, labels):
    im = Image.open(o).convert('RGB'); r = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 3; im = im.crop((l, t, l + w, t + h))
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w, h], 22, fill=255); bd.paste(im, (x, y), m)
    f = font(26 if w < 400 else 30, 'Bold'); tw = dr.textlength(lab, font=f)
    dr.rounded_rectangle([x + 14, y + h - 58, x + 34 + tw, y + h - 14], 12, fill=(11, 11, 12))
    dr.text((x + 24, y + h - 54), lab, font=f, fill=Y if 'orange' in lab else 'white')
bd.save(f'{OUT}/0_planche_equipe_9x16.jpg', quality=92); print('planche ok')

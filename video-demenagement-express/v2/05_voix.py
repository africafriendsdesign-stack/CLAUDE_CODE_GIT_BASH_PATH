#!/usr/bin/env python3
"""Génère la voix off phrase par phrase avec Piper (hors ligne).
Usage : python3 05_voix.py <modele.onnx> <dossier_sortie> [length_scale]
length_scale > 1 = débit plus lent."""
import json, os, subprocess, sys
model, out = sys.argv[1], sys.argv[2]; ls = sys.argv[3] if len(sys.argv) > 3 else '1.0'
os.makedirs(out, exist_ok=True)
sc = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenario.json')))
lines = [(p['id'], p['vo']) for p in sc['plans']] + [('END', sc['end_vo'])]
for pid, txt in lines:
    wav = os.path.join(out, pid + '.wav')
    subprocess.run([sys.executable, '-m', 'piper', '-m', model, '-f', wav, '--length-scale', ls,
                    '--noise-scale', '0.62', '--noise-w-scale', '0.8', '--', txt], check=True,
                   capture_output=True, cwd='/tmp')
    d = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', wav],
                       capture_output=True, text=True).stdout.strip()
    print(f'{pid}\t{float(d):.2f}s\t{txt}')

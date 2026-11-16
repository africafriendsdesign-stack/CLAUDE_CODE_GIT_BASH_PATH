// Rend overlay.html image par image en PNG transparents (30 fps).
// Usage : node 02_render_overlay.js <dossier_sortie> [t_debut t_fin | --stills t1,t2,...]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.resolve(__dirname, 'overlay.html'));
  await page.evaluate(() => window.ready);
  if (process.env.TIMELINE) {           // version 2 : timeline.json (+ MODE=v2 | v2-animatic)
    const tl = JSON.parse(fs.readFileSync(process.env.TIMELINE, 'utf8'));
    await page.evaluate(cfg => configure(cfg), { mode: process.env.MODE || 'v2', cues: tl.cues, plans: tl.plans, sections: tl.sections || [],
      end: tl.total, outro: tl.outro, bug0: 0.6, bug1: tl.outro - 0.4 });
  }
  let frames;
  if (process.argv[3] === '--stills') frames = process.argv[4].split(',').map(s => [Number(s), 's_' + s]);
  else { const a = Number(process.argv[3] || 0), b = Number(process.argv[4] || 32.5);
    frames = []; for (let f = Math.round(a * 30); f < Math.round(b * 30); f++) frames.push([f / 30, String(f).padStart(4, '0')]); }
  for (const [t, name] of frames) {
    const url = await page.evaluate(t => render(t), t);
    fs.writeFileSync(path.join(out, name + '.png'), Buffer.from(url.split(',')[1], 'base64'));
  }
  await browser.close(); console.log('rendered', frames.length);
})();

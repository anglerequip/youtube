// Headless 3D renderer: drives a three.js scene frame by frame and pipes JPEG frames into ffmpeg.
//
//   node renderer/render.mjs --scene <name> --plan plan.json --out visual.mp4
//   node renderer/render.mjs --scene <name> --plan plan.json --stills 0,2.5,10 --stills-dir dir/
//   node renderer/render.mjs --scene <name> --plan plan.json --inspect 0,2.5,10 --inspect-out report.json
//   add --from <frame> [--to <frame>] to render only part of the video (for patching one shot)
//
// GPU: by default Chromium uses SwiftShader (CPU) so it runs anywhere. On a machine with a GPU set
// RENDER_GPU=1 for much faster renders.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
// Resolve playwright however it is installed (local node_modules or global NODE_PATH).
const { chromium } = createRequire(import.meta.url)('playwright');

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]);
  return acc;
}, []));

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.ttf': 'font/ttf', '.png': 'image/png', '.jpg': 'image/jpeg' };

function serve() {
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      const p = path.normalize(path.join(ROOT, decodeURIComponent(req.url.split('?')[0])));
      if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
      fs.createReadStream(p).pipe(rsp);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

const plan = JSON.parse(fs.readFileSync(args.plan, 'utf8'));
const srv = await serve();
const port = srv.address().port;
const gpuArgs = process.env.RENDER_GPU ? ['--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=default']
  : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
const browser = await chromium.launch({ args: gpuArgs });
const page = await browser.newPage({ viewport: { width: 400, height: 400 } });
page.on('console', m => { if ((m.type() === 'error' || m.type() === 'warning') && !m.text().includes('GPU stall')) console.error('[page]', m.text()); });
page.on('pageerror', e => { console.error('[page error]', e.message); });
await page.goto(`http://127.0.0.1:${port}/renderer/index.html`);
await page.waitForFunction(() => window.__ready === true);
const info = await page.evaluate(async ({ scene, plan }) => window.__boot(scene, plan), { scene: args.scene, plan });

const t0 = Date.now();
if (args.inspect) {
  // scene-graph inspection (renderer/inspect.js) at the given times: each time and the frame after it
  const frames = [];
  for (const ts of String(args.inspect).split(',')) {
    const i = Math.min(info.frames - 2, Math.round(parseFloat(ts) * plan.fps));
    frames.push(await page.evaluate(i => window.inspectFrame(i), i));
    frames.push(await page.evaluate(i => window.inspectFrame(i), i + 1));
  }
  const report = { scene: args.scene, static: await page.evaluate(() => window.inspectStatic()), frames };
  fs.writeFileSync(args['inspect-out'], JSON.stringify(report));
  console.log(`inspected ${frames.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
} else if (args.stills) {
  fs.mkdirSync(args['stills-dir'], { recursive: true });
  for (const ts of String(args.stills).split(',')) {
    const i = Math.round(parseFloat(ts) * plan.fps);
    const url = await page.evaluate(i => window.renderFrame(i, 0.95), i);
    fs.writeFileSync(path.join(args['stills-dir'], `t${parseFloat(ts).toFixed(1).padStart(5, '0')}.jpg`), Buffer.from(url.split(',')[1], 'base64'));
  }
  console.log(`stills done in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
} else {
  const n = info.frames;
  const f0 = args.from ? parseInt(args.from) : 0, f1 = args.to ? Math.min(n, parseInt(args.to)) : n;
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(plan.fps), '-c:v', 'mjpeg',
    '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', args.out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = f0; i < f1; i++) {
    const url = await page.evaluate(i => window.renderFrame(i), i);
    if (!ff.stdin.write(Buffer.from(url.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 60 === 0) {
      const el = (Date.now() - t0) / 1000;
      console.log(`  frame ${i}/${n}  ${(el / Math.max(1, i)).toFixed(2)} s/frame`);
    }
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg ' + c))));
  console.log(`rendered ${f1 - f0} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  const meta = await page.evaluate(() => window.__meta);
  fs.writeFileSync(args.out.replace(/\.mp4$/, '') + '.meta.json', JSON.stringify(meta));
}
await browser.close();
srv.close();

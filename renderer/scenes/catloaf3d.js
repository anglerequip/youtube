// Why does my cat sit like a loaf? (content/episodes/cat-loaf/plan.py)
// A cosy living room on a winter afternoon: wooden floor, round rug, sofa, a radiator under a window with a low
// sun outside. The sun really shines through the window (walls and ceiling cast the shadow), so the plan slides
// the sun patch across the floor by moving the sun direction. One orange tabby (renderer/cat.js) lies on the rug;
// two more copies appear only for the side-by-side surface comparison. A colour-grade pass gives the cold-blue
// room, the heat-loss view and the desaturated "pain" look. This file only draws what the plan lists.
import * as THREE from 'three';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { man, woman } from '../characters.js';
import { cat } from '../cat.js';
import { MAT, woodTexture } from '../materials.js';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };
const box = (w, h, d, m, x, y, z, parent) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); o.position.set(x, y, z); parent.add(o); return o; };
const rbox = (w, h, d, r, m, x, y, z, parent) => { const o = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 4, r), m); o.position.set(x, y, z); parent.add(o); return o; };
const RUG_Y = 0.012;

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

function bookshelf(parent, x, z, rotY, seed) {
  let q = seed; const R = () => ((q = (q * 1664525 + 1013904223) >>> 0) / 4294967296);
  const g = new THREE.Group(), wood = MAT.wood('#7a5a3c');
  const W = 0.9, H = 1.85, D = 0.3;
  box(0.03, H, D, wood, -W / 2, H / 2, 0, g); box(0.03, H, D, wood, W / 2, H / 2, 0, g);
  box(W, 0.03, D, wood, 0, H, 0, g); box(W, 0.012, D, wood, 0, H / 2, -D / 2 + 0.006, g);
  const cols = ['#c97a5a', '#8fa6c8', '#d9c7a0', '#7d8c35', '#a99bc4', '#e2c45a', '#5e4630', '#b9bdc2', '#2e8f86'].map(c => std(c, { roughness: 0.8 }));
  for (let k = 0; k < 5; k++) {
    const y = 0.06 + k * 0.42; box(W, 0.025, D, wood, 0, y, 0, g);
    let bx = -W / 2 + 0.04;
    while (bx < W / 2 - 0.08) {
      const w = 0.025 + R() * 0.035, h = 0.2 + R() * 0.14;
      if (R() < 0.12) { bx += 0.06; continue; }
      const b = box(w, h, 0.2 + R() * 0.05, cols[Math.floor(R() * cols.length)], bx + w / 2, y + 0.0125 + h / 2, 0.01, g);
      b.rotation.z = R() < 0.1 ? 0.12 : 0; bx += w + 0.004;
    }
  }
  g.position.set(x, 0, z); g.rotation.y = rotY; parent.add(g); return g;
}

function room(S, L) {
  const R = L.room, Wn = L.window, g = new THREE.Group();
  // floor: warm oak planks
  const ft = woodTexture('#a98058', 4); ft.repeat.set(6, 1);
  const floorM = new THREE.MeshStandardMaterial({ map: ft, roughness: 0.6, envMapIntensity: 0.5 });
  const floor = new THREE.Mesh(new THREE.BoxGeometry(R.x1 - R.x0, 0.1, R.z1 - R.z0), floorM); floor.position.set(0, -0.05, 0); g.add(floor);
  // walls (warm off-white), a window hole in the back wall
  const wallM = std('#e4ddcf', { roughness: 0.95 }), t = 0.14, h = R.h;
  const bz = R.z0 - t / 2, wl = Wn.cx - Wn.w / 2, wr = Wn.cx + Wn.w / 2;
  box(wl - R.x0 + t, h, t, wallM, (R.x0 - t + wl) / 2, h / 2, bz, g);
  box(R.x1 + t - wr, h, t, wallM, (wr + R.x1 + t) / 2, h / 2, bz, g);
  box(Wn.w, Wn.y0, t, wallM, Wn.cx, Wn.y0 / 2, bz, g);
  box(Wn.w, h - Wn.y1, t, wallM, Wn.cx, (Wn.y1 + h) / 2, bz, g);
  box(t, h, R.z1 - R.z0 + 2 * t, wallM, R.x0 - t / 2, h / 2, 0, g);
  box(t, h, R.z1 - R.z0 + 2 * t, std('#ddd5c6', { roughness: 0.95 }), R.x1 + t / 2, h / 2, 0, g);
  box(R.x1 - R.x0 + 2 * t, h, t, wallM, 0, h / 2, R.z1 + t / 2, g);
  box(R.x1 - R.x0 + 2 * t, t, R.z1 - R.z0 + 2 * t, std('#efe9dd', { roughness: 1 }), 0, h + t / 2, 0, g);
  // skirting boards
  const skM = std('#f1ece2', { roughness: 0.6 });
  box(R.x1 - R.x0, 0.09, 0.02, skM, 0, 0.045, R.z0 + 0.01, g);
  box(0.02, 0.09, R.z1 - R.z0, skM, R.x0 + 0.01, 0.045, 0, g);
  box(0.02, 0.09, R.z1 - R.z0, skM, R.x1 - 0.01, 0.045, 0, g);
  // window: white frame, a cross of glazing bars (they print a cross into the sun patch), a sill
  const frM = std('#f3f0ea', { roughness: 0.5 });
  const fz = R.z0 - 0.07;
  box(Wn.w + 0.1, 0.06, 0.1, frM, Wn.cx, Wn.y0 - 0.0, fz, g);
  box(Wn.w + 0.1, 0.06, 0.1, frM, Wn.cx, Wn.y1, fz, g);
  box(0.06, Wn.y1 - Wn.y0, 0.1, frM, wl, (Wn.y0 + Wn.y1) / 2, fz, g);
  box(0.06, Wn.y1 - Wn.y0, 0.1, frM, wr, (Wn.y0 + Wn.y1) / 2, fz, g);
  box(0.035, Wn.y1 - Wn.y0, 0.05, frM, Wn.cx, (Wn.y0 + Wn.y1) / 2, fz, g);
  box(Wn.w, 0.035, 0.05, frM, Wn.cx, Wn.y0 + (Wn.y1 - Wn.y0) * 0.62, fz, g);
  rbox(Wn.w + 0.24, 0.04, 0.2, 0.01, frM, Wn.cx, Wn.y0 - 0.02, R.z0 + 0.06, g);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(Wn.w, Wn.y1 - Wn.y0),
    new THREE.MeshPhysicalMaterial({ color: '#dfe8ee', transparent: true, opacity: 0.12, roughness: 0.05, depthWrite: false }));
  glass.position.set(Wn.cx, (Wn.y0 + Wn.y1) / 2, fz); glass.castShadow = false; S.add(glass);
  // radiator under the window: rounded columns, pipes and a valve
  const radM = new THREE.MeshPhysicalMaterial({ color: '#eeebe4', roughness: 0.35, clearcoat: 0.4 });
  const rad = new THREE.Group(), cols = 22, rw = 1.16;
  for (let k = 0; k < cols; k++) rbox(0.042, 0.56, 0.08, 0.016, radM, -rw / 2 + (k + 0.5) * rw / cols, 0.44, 0, rad);
  for (const y of [0.2, 0.68]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, rw, 24), radM); p.rotation.z = Math.PI / 2; p.position.set(0, y, 0); rad.add(p); }
  const pipeM = std('#cfd2d4', { metalness: 0.7, roughness: 0.35 });
  for (const s of [-1, 1]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.16, 24), pipeM); p.position.set(s * (rw / 2 + 0.04), 0.08, 0); rad.add(p); }
  const valve = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.05, 24), std('#e9e6df')); valve.position.set(rw / 2 + 0.04, 0.2, 0); rad.add(valve);
  rad.position.set(Wn.cx, 0, R.z0 + 0.1); g.add(rad);
  // sofa against the left wall (muted sage), with two cushions and a throw
  const sofaM = std('#8c9a7c', { roughness: 0.95 }), sofa = new THREE.Group();
  rbox(0.9, 0.42, 1.9, 0.06, sofaM, 0, 0.21, 0, sofa);
  rbox(0.24, 0.5, 1.9, 0.07, sofaM, -0.33, 0.62, 0, sofa);
  for (const s of [-1, 1]) rbox(0.9, 0.58, 0.18, 0.07, sofaM, 0, 0.36, s * 0.95, sofa);
  for (const [z, c] of [[-0.45, '#d9c7a0'], [0.42, '#c97a5a']]) { const cu = rbox(0.14, 0.38, 0.4, 0.08, std(c, { roughness: 0.95 }), -0.15, 0.6, z, sofa); cu.rotation.z = 0.25; }
  rbox(0.5, 0.025, 0.7, 0.012, std('#a99bc4', { roughness: 1 }), 0.05, 0.43, 0.35, sofa);
  for (const [x, z] of [[0.36, 0.86], [0.36, -0.86], [-0.36, 0.86], [-0.36, -0.86]]) { const f = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.016, 0.06, 16), MAT.wood('#5e4630')); f.position.set(x, 0.03, z); sofa.add(f); }
  sofa.position.set(R.x0 + 0.5, 0, 0.0); g.add(sofa);
  // side table with a mug and a reading lamp, by the right wall
  const tbl = new THREE.Group(), woodM = MAT.wood('#8a6342');
  const top = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.26, 0.03, 48), woodM); top.position.y = 0.55; tbl.add(top);
  for (let k = 0; k < 3; k++) { const a = k * 2.094; const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.012, 0.55, 16), woodM); leg.position.set(Math.cos(a) * 0.17, 0.275, Math.sin(a) * 0.17); leg.rotation.set(Math.sin(a) * 0.1, 0, -Math.cos(a) * 0.1); tbl.add(leg); }
  const mug = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.036, 0.09, 32), MAT.ceramic('#c97a5a')); mug.position.set(0.06, 0.61, 0.05); tbl.add(mug);
  const handle = new THREE.Mesh(new THREE.TorusGeometry(0.025, 0.007, 12, 32), MAT.ceramic('#c97a5a')); handle.position.set(0.1, 0.61, 0.05); tbl.add(handle);
  const lb = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 0.03, 32), std('#3b3f45', { metalness: 0.5 })); lb.position.set(-0.08, 0.585, -0.06); tbl.add(lb);
  const ls = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.36, 16), std('#3b3f45', { metalness: 0.5 })); ls.position.set(-0.08, 0.77, -0.06); tbl.add(ls);
  const shade = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.13, 0.16, 40, 1, true), new THREE.MeshStandardMaterial({ color: '#efe2c4', emissive: '#ffd9a0', emissiveIntensity: 0.6, side: THREE.DoubleSide, roughness: 0.9 }));
  shade.position.set(-0.08, 0.98, -0.06); tbl.add(shade);
  tbl.position.set(R.x1 - 0.45, 0, -2.0); g.add(tbl);
  // a plant in the far right corner
  const plant = new THREE.Group();
  const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.13, 0.32, 40), MAT.ceramic('#d6cfc0')); pot.position.y = 0.16; plant.add(pot);
  const leafM = std('#6f7f3c', { roughness: 0.8, flatShading: true });
  for (let k = 0; k < 9; k++) {
    const a = k * 2.4, l = new THREE.Mesh(new THREE.IcosahedronGeometry(0.16, 2), leafM);
    l.scale.set(0.35, 1.0, 0.12); l.position.set(Math.cos(a) * 0.12, 0.62 + (k % 3) * 0.12, Math.sin(a) * 0.12); l.rotation.set(Math.sin(a) * 0.5, a, Math.cos(a) * 0.5); plant.add(l);
  }
  plant.position.set(R.x1 - 0.35, 0, R.z0 + 0.4); g.add(plant);
  // a framed picture on the right wall
  const pic = new THREE.Group();
  box(0.03, 0.5, 0.7, std('#5e4630'), 0, 0, 0, pic);
  const art = canvasTex(256, 192, (c, w, hh) => { c.fillStyle = '#d9cdb4'; c.fillRect(0, 0, w, hh); c.fillStyle = '#8fa6c8'; c.fillRect(0, 0, w, hh * 0.55); c.fillStyle = '#7d8c35'; c.beginPath(); c.moveTo(0, hh * 0.7); c.quadraticCurveTo(w * 0.4, hh * 0.35, w, hh * 0.62); c.lineTo(w, hh); c.lineTo(0, hh); c.fill(); c.fillStyle = '#e2c45a'; c.beginPath(); c.arc(w * 0.72, hh * 0.28, 16, 0, 7); c.fill(); });
  const canvas = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.42), new THREE.MeshStandardMaterial({ map: art, roughness: 0.9 })); canvas.position.set(-0.017, 0, 0); canvas.rotation.y = -Math.PI / 2; pic.add(canvas);
  pic.position.set(R.x1 - 0.02, 1.55, -0.5); g.add(pic);
  bookshelf(g, R.x0 + 0.17, 1.9, Math.PI / 2, 7);      // behind the wizard
  bookshelf(g, R.x1 - 0.17, 1.25, -Math.PI / 2, 11);   // behind the woman
  S.add(shadowed(g));
  // round rug: soft wool rings
  const rugTex = canvasTex(1024, 1024, (c, w) => {
    const cx = w / 2; c.fillStyle = '#b8735a'; c.fillRect(0, 0, w, w);
    for (const [r, col] of [[0.47, '#c98a6e'], [0.42, '#b8735a'], [0.33, '#e0c9a6'], [0.3, '#b8735a'], [0.16, '#c98a6e'], [0.12, '#a9634c']]) { c.fillStyle = col; c.beginPath(); c.arc(cx, cx, r * w, 0, 7); c.fill(); }
    for (let k = 0; k < 9000; k++) { c.fillStyle = `rgba(${k % 2 ? 255 : 60},${k % 2 ? 240 : 40},${k % 2 ? 220 : 30},0.05)`; const a = (k * 2.399) % 6.283, rr = ((k * 7919) % 1000) / 1000 * w / 2; c.fillRect(cx + Math.cos(a) * rr, cx + Math.sin(a) * rr, 2, 2); }
  });
  const rug = new THREE.Mesh(new THREE.CylinderGeometry(L.rug_r, L.rug_r, RUG_Y, 128), [std('#a9634c', { roughness: 1 }), new THREE.MeshStandardMaterial({ map: rugTex, roughness: 1 }), std('#a9634c')]);
  rug.position.set(L.rug[0], RUG_Y / 2, L.rug[2]); rug.receiveShadow = true; S.add(rug);
}

function outside(world, S, L) {
  const gnd = world.ground(400); gnd.position.y = -0.12;
  world.hills(10, 120);
  const trunkM = std('#5a4632', { flatShading: true });
  const crowns = ['#a7b84a', '#7d8c35', '#8a9a45'].map(c => std(c, { flatShading: true, roughness: 0.95 }));
  for (const [x, z, s] of [[-1.5, -7.5, 1.4], [2.8, -9.0, 1.8], [6.5, -12, 2.0], [-5.5, -11, 1.9], [0.6, -15, 2.2], [9, -8, 1.6], [-9, -14, 2.1]]) {
    const tr = new THREE.Group();
    const tk = new THREE.Mesh(new THREE.CylinderGeometry(0.07 * s, 0.1 * s, 0.9 * s, 16), trunkM); tk.position.y = 0.45 * s; tr.add(tk);
    const cr = new THREE.Mesh(new THREE.IcosahedronGeometry(0.75 * s, 2), crowns[Math.abs(Math.round(x * 3)) % 3]); cr.position.y = 1.35 * s; cr.rotation.set(x, z, 0); tr.add(cr);
    tr.position.set(x, -0.12, z); S.add(tr);
  }
  // a low hedge and fence posts beyond the window
  const hedgeM = std('#5d6a2c', { flatShading: true, roughness: 1 });
  for (let k = -6; k <= 6; k++) { const hb = new THREE.Mesh(new THREE.IcosahedronGeometry(0.55, 2), hedgeM); hb.scale.set(1.3, 0.8, 0.9); hb.position.set(k * 1.1, 0.25, -5.2); S.add(hb); }
}

function gradePass() {
  return new ShaderPass({
    uniforms: { tDiffuse: { value: null }, sat: { value: 1 }, cool: { value: 0 }, thermal: { value: 0 },
                center: { value: new THREE.Vector2(0.5, 0.5) }, halfSz: { value: new THREE.Vector2(0.15, 0.15) }, aspect: { value: 9 / 16 } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform sampler2D tDiffuse; uniform float sat, cool, thermal, aspect; uniform vec2 center, halfSz; varying vec2 vUv;
      void main(){
        vec4 c = texture2D(tDiffuse, vUv); vec3 col = c.rgb;
        float lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
        float r = length((vUv - center) / halfSz);   // 1.0 = the edge of the cat's on-screen box
        float mC = smoothstep(0.8, 1.25, r);               // cold blue everywhere except a warm pocket around the cat
        col = mix(col, vec3(0.1, 0.2, 0.42) * 0.35 + col * vec3(0.42, 0.62, 1.15), cool * mC);
        float mT = smoothstep(0.9, 1.15, r);               // heat-loss view: the room drops to a cold navy
        vec3 cold = vec3(0.025, 0.04, 0.11) + lum * vec3(0.08, 0.16, 0.42);
        col = mix(col, cold, thermal * mT);
        col = mix(col, vec3(0.04, 0.06, 0.16) + col * 0.55, thermal * (1.0 - mT) * 0.35);
        col = mix(vec3(lum), col, sat);
        gl_FragColor = vec4(col, c.a);
      }`,
  });
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  outside(world, S, L);
  room(S, L);

  const wiz = man(); wiz.position.set(...L.wiz); wiz.rotation.y = L.face_w; S.add(wiz);
  const wom = woman(); wom.position.set(...L.woman); wom.rotation.y = L.face_m; S.add(wom);
  // pure black never appears in the house style: lift near-black fabric and hair to a deep charcoal
  const lift = new THREE.Color('#4a4550').convertSRGBToLinear();   // a shade lighter than cat-stare: the room is darker
  for (const p of [wiz, wom]) p.traverse(o => {
    if (!o.isMesh) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || !m.color || m.isMeshBasicMaterial) continue;
      if (Math.max(m.color.r, m.color.g, m.color.b) < lift.r) {
        m.color.r = Math.max(m.color.r, lift.r); m.color.g = Math.max(m.color.g, lift.g); m.color.b = Math.max(m.color.b, lift.b);
        // in this darker interior the lifted fabric still fell below the QA black level in shade: a faint floor of self-light
        if (m.emissive) { m.emissive.set('#26222c'); m.emissiveIntensity = 1; }
      }
      else if (m.emissive && Math.max(m.color.r, m.color.g, m.color.b) < 0.17) { m.emissive.set('#1e1a20'); m.emissiveIntensity = 1; }   // dark hair: shadowed strand gaps
    }
  });

  const tom = cat(); S.add(tom);
  // the comparison pair: the same cat stretched out (front) and loafed (behind), each with a bar of exposed surface
  const T = L.twin;
  const twinS = cat(); twinS.position.set(T[0] - 0.22, 0, T[2]); S.add(twinS);
  const twinL = cat(); twinL.position.set(T[0] + 0.22, 0, T[2]); S.add(twinL);
  const barM = new THREE.MeshStandardMaterial({ color: '#c92a2e', emissive: '#c92a2e', emissiveIntensity: 0.35, roughness: 0.5 });
  const baseM = std('#e5e2d6', { roughness: 0.6 });
  // one bar behind each cat, both at the same distance from the camera so their heights compare fairly
  const bars = [[T[0] - 0.22, L.bar_h[0]], [T[0] + 0.22, L.bar_h[1]]].map(([bx, h]) => {
    const g = new THREE.Group(); g.position.set(bx, 0, T[2] - 0.66);
    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.075, 0.015, 40), baseM); base.position.y = 0.0075; g.add(base);
    const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1, 40), barM); g.add(bar);
    S.add(shadowed(g)); return { g, bar, h };
  });
  const twins = [twinS, twinL, ...bars.map(b => b.g)];

  // thin white ring on the floor around the cat (house style ground highlight)
  const ringM = new THREE.MeshStandardMaterial({ color: '#f4f1ea', emissive: '#f4f1ea', emissiveIntensity: 0.9, transparent: true, opacity: 0 });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.0045, 12, 96), ringM); ring.rotation.x = Math.PI / 2; S.add(ring);

  // heat-loss view: every mesh except the cat swaps to a cold navy material (shapes still read), restored after
  const coldM = new THREE.MeshBasicMaterial({ color: '#1f2c58' });   // flat cold field: no seams, the warm cat is the only shaded thing
  const inCat = o => { for (let p = o; p; p = p.parent) if (p === tom) return true; return false; };
  const swaps = [];
  S.traverse(o => { if (o.isMesh && !inCat(o) && o !== ring && o !== world.skyDome) swaps.push([o, o.material]); });
  let coldOn = false;
  const setCold = on => { if (on === coldOn) return; coldOn = on; for (const [o, m] of swaps) o.material = on ? coldM : m; };
  // soft fill from the camera side for presenter close-ups (keeps the woman's black outfit from crushing to pure black)
  const fill = new THREE.DirectionalLight('#fff4e6', 0); S.add(fill); S.add(fill.target);
  const grade = gradePass();
  world.composer.insertPass(grade, world.composer.passes.length - 1);
  grade.uniforms.aspect.value = plan.W / plan.H;

  const v = new THREE.Vector3(), win = new THREE.Vector3(L.window.cx, (L.window.y0 + L.window.y1) / 2, L.window.z);
  const headLook = (person, target, maxYaw = 0.9) => {
    v.set(...target).sub(person.position);
    const yaw = Math.atan2(v.x, v.z) - person.rotation.y;
    const w = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    const pitch = -Math.atan2(target[1] - person.position.y - 1.55, Math.hypot(v.x, v.z));
    return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, w)), headPitch: Math.max(-0.3, Math.min(0.45, pitch)) };
  };
  const wizHead = [L.wiz[0], 1.62, L.wiz[2]], womHead = [L.woman[0], 1.52, L.woman[2]];
  const onRug = (x, z) => Math.hypot(x - L.rug[0], z - L.rug[2]) < L.rug_r;
  const P = new THREE.Vector3(), dir = new THREE.Vector3(), box3 = new THREE.Box3();
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  return {
    lightCenter: new THREE.Vector3(0, 0, -1),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      const catHead = [F.cat_x[k], 0.2, F.cat_z[k]];
      const lw = F.look_w[k] === 'cat' ? headLook(wiz, catHead) : headLook(wiz, womHead);
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, ...lw, headTilt: 0.04 * Math.sin(t * 0.7) });
      const camNow = shot.pos ? shot.pos[Math.min(Math.max(0, i - shot.i0), shot.pos.length - 1)] : world.camera.position.toArray();
      const lm = F.look_m[k] === 'camera' ? headLook(wom, camNow) : headLook(wom, wizHead);
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, ...lm, headTilt: 0.05 * Math.sin(t * 0.9 + 1) });
      // the cat
      const x = F.cat_x[k], z = F.cat_z[k], mode = F.cat_mode[k];
      tom.position.set(x, onRug(x, z) ? RUG_Y : 0, z); tom.rotation.y = F.cat_face[k];
      tom.pose({ mode, t, fold: F.fold[k], hunch: F.hunch[k], ears: F.ears[k], blink: F.cat_blink[k], pitch: F.cat_pitch[k],
                 yaw: F.cat_yaw[k], walk: mode === 'stand' ? F.walk[k] : undefined, heat: F.heat[k], heatBody: F.heat_body[k],
                 pupil: 1.0, tail: 0.0 });
      // comparison pair
      const tv = F.twin[k] > 0;
      for (const o of twins) o.visible = tv;
      if (tv) {
        twinS.pose({ mode: 'lie', fold: 0, t, pitch: 0.05, blink: (t % 3.9) < 0.12 ? 1 : 0 });
        twinL.pose({ mode: 'lie', fold: 1, t, pitch: -0.05, blink: ((t + 1.7) % 3.9) < 0.12 ? 1 : 0 });
        for (const b of bars) { const hh = Math.max(0.002, b.h * F.bars[k]); b.bar.scale.y = hh; b.bar.position.y = 0.015 + hh / 2; }
      }
      // ring
      const rv = F.ring[k];
      ring.visible = rv > 0; ring.position.set(x, RUG_Y + 0.004, z); ringM.opacity = 0.9 * rv; ring.scale.setScalar(0.85 + 0.15 * rv);
      // grade
      grade.uniforms.sat.value = F.sat[k]; grade.uniforms.cool.value = F.cool[k]; grade.uniforms.thermal.value = 0.0; setCold(F.thermal[k] > 0);
      // the sun: aim it through the window so the patch centre lands where the plan says
      const u = F.sun_u[k];
      P.set(L.patch_a[0] + (L.patch_b[0] - L.patch_a[0]) * u, 0, L.patch_a[2] + (L.patch_b[2] - L.patch_a[2]) * u);
      dir.copy(win).sub(P).normalize();
      world.sun.position.copy(P).addScaledVector(dir, 14); world.sun.target.position.copy(P); world.sun.target.updateMatrixWorld();
      const sc = world.sun.shadow.camera; sc.left = -7.5; sc.right = 7.5; sc.top = 7.5; sc.bottom = -7.5; sc.near = 1; sc.far = 32; sc.updateProjectionMatrix();
      world.sun.shadow.bias = -0.0003; world.sun.shadow.normalBias = 0.015;
      if (shot.lighting === 'golden') { world.sun.color.set('#ffd6a8'); world.sun.intensity = 3.4; }
      else { world.sun.color.set('#fff0dc'); world.sun.intensity = 3.0; }
      world.hemi.intensity = shot.lighting === 'golden' ? 1.05 : 1.1;
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.05, Math.max(0.005, d * 0.02)); world.camera.far = 500; world.camera.updateProjectionMatrix();
      tom.updateMatrixWorld(true); world.camera.updateMatrixWorld(true);
      const fpi = focalPt(i); fill.intensity = fpi[1] > 1.2 ? 1.1 : 0;
      fill.position.copy(world.camera.position).add(new THREE.Vector3(0.3, 0.4, 0)); fill.target.position.set(...fpi); fill.target.updateMatrixWorld();
      // the cat's on-screen box: the grade keeps her warm inside it
      box3.setFromObject(tom, true);
      let x0 = 1, x1 = 0, y0 = 1, y1 = 0;
      for (let q = 0; q < 8; q++) {
        v.set(q & 1 ? box3.max.x : box3.min.x, q & 2 ? box3.max.y : box3.min.y, q & 4 ? box3.max.z : box3.min.z).project(world.camera);
        const sx = (v.x + 1) / 2, sy = (v.y + 1) / 2; x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy);
      }
      grade.uniforms.center.value.set((x0 + x1) / 2, (y0 + y1) / 2);
      grade.uniforms.halfSz.value.set(Math.max(0.03, (x1 - x0) / 2 * 0.95), Math.max(0.03, (y1 - y0) / 2 * 0.95));
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const fp = focalPt(i);
      const near = (q, r) => Math.hypot(fp[0] - q[0], fp[2] - q[2]) < r;
      const entity = near(T, 0.8) ? 'twin' : fp[1] > 1.2 ? (near(L.wiz, 0.5) ? 'wizard' : 'woman') : 'cat';
      return [{ entity, part: 'subject', kind: 'thickness', p: fp, size: 0.25 }];
    },
    vars() { return {}; },
  };
}

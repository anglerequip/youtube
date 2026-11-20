// Reusable set (CLAUDE.md "Autopilot efficiency": the street/traffic set). A straight two-lane road along Z with
// sandy kerb strips, verges, fence posts and low-poly trees, plus higher-poly traffic props at the section 11
// budget: boxy 1990s cars (24-segment wheels, rounded bodies), traffic cones, road signs and a small digger.
//
//   import { road, hcar, hcone, sign, digger } from '../sets/street.js';
//   const R = road(world, { x: 0, z0: -160, z1: 220, closure: { z0: -40, z1: 0, taper: 14 } });
//   const c = hcar('#d9c7a0', 'hatch'); c.position.set(R.lane(0), 0, 20); scene.add(c); c.setBrake(1);
import * as THREE from 'three';
import { PALETTE } from '../world.js';

const flat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0, flatShading: true, ...extra });
const shadow = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };
export const LANE_W = 3.6;

// rounded box: a subdivided box pulled toward a superellipsoid (car bodies, sign backs)
function roundBox(w, h, d, r = 0.12, seg = 8) {
  const g = new THREE.BoxGeometry(w, h, d, seg, seg, seg), P = g.attributes.position, v = new THREE.Vector3();
  const hx = w / 2 - r, hy = h / 2 - r, hz = d / 2 - r;
  for (let i = 0; i < P.count; i++) {
    v.fromBufferAttribute(P, i);
    const c = new THREE.Vector3(Math.max(-hx, Math.min(hx, v.x)), Math.max(-hy, Math.min(hy, v.y)), Math.max(-hz, Math.min(hz, v.z)));
    const n = v.clone().sub(c); if (n.lengthSq() > 1e-9) n.setLength(r); v.copy(c).add(n);
    P.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals(); return g;
}

let _radial;
function radialTexture() {
  if (_radial) return _radial;
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128); _radial = new THREE.CanvasTexture(c); return _radial;
}

// Boxy 1990s car, ~4.1 m long, facing -Z, at the higher poly budget. .setBrake(0..1) lights the tail lights and a
// red glow on the road behind it.
export function hcar(color, kind = 'hatch', roofRack = false) {
  const g = new THREE.Group();
  const body = new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0.05 });
  const glass = new THREE.MeshStandardMaterial({ color: '#2b3038', roughness: 0.2, metalness: 0.3 });
  const L = kind === 'estate' ? 4.4 : 4.1, Wd = 1.75;
  const lower = new THREE.Mesh(roundBox(Wd, 0.64, L, 0.14), body); lower.position.y = 0.56; g.add(lower);
  const cabinL = kind === 'sedan' ? L * 0.48 : kind === 'estate' ? L * 0.66 : L * 0.56;
  const cabinZ = kind === 'sedan' ? 0.05 : 0.35;
  const cab = new THREE.Mesh(roundBox(Wd * 0.88, 0.56, cabinL, 0.1), body); cab.position.set(0, 1.12, cabinZ); g.add(cab);
  const win = new THREE.Mesh(roundBox(Wd * 0.9, 0.32, cabinL * 0.92, 0.08), glass); win.position.set(0, 1.14, cabinZ); g.add(win);
  const tyre = new THREE.MeshStandardMaterial({ color: '#1d1d20', roughness: 0.9 }), hub = new THREE.MeshStandardMaterial({ color: '#b9bdc2', roughness: 0.4, metalness: 0.6 });
  const wg = new THREE.CylinderGeometry(0.33, 0.33, 0.24, 24); wg.rotateZ(Math.PI / 2);
  const hg = new THREE.CylinderGeometry(0.17, 0.17, 0.25, 24); hg.rotateZ(Math.PI / 2);
  for (const [x, z] of [[-0.8, -1.3], [0.8, -1.3], [-0.8, 1.3], [0.8, 1.3]]) {
    const w = new THREE.Mesh(wg, tyre); w.position.set(x, 0.33, z * L / 4.1); g.add(w);
    const h = new THREE.Mesh(hg, hub); h.position.set(x * 1.01, 0.33, z * L / 4.1); g.add(h);
  }
  const tailMat = new THREE.MeshStandardMaterial({ color: '#7a1416', emissive: PALETTE.red, emissiveIntensity: 0.15, roughness: 0.4 });
  for (const x of [-0.62, 0.62]) { const tl = new THREE.Mesh(roundBox(0.34, 0.16, 0.05, 0.02, 4), tailMat); tl.position.set(x, 0.7, L / 2 + 0.005); g.add(tl); }
  const headMat = new THREE.MeshStandardMaterial({ color: '#f4efe2', emissive: '#fff3d6', emissiveIntensity: 0.25, roughness: 0.3 });
  for (const x of [-0.6, 0.6]) { const hl = new THREE.Mesh(roundBox(0.36, 0.15, 0.05, 0.02, 4), headMat); hl.position.set(x, 0.7, -L / 2 - 0.005); g.add(hl); }
  const plate = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.12, 0.03), flat('#e8e6df')); plate.position.set(0, 0.5, L / 2 + 0.01); g.add(plate);
  const glowMat = new THREE.MeshBasicMaterial({ color: '#ff2a1f', transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, map: radialTexture() });
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(2.0, 1.3), glowMat); glow.rotation.x = -Math.PI / 2; glow.position.set(0, 0.04, L / 2 + 0.55); g.add(glow);
  if (roofRack) for (const x of [-0.6, 0.6]) { const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, cabinL * 0.9, 16), flat('#2a2a2c')); bar.rotation.x = Math.PI / 2; bar.position.set(x, 1.43, cabinZ); g.add(bar); }
  g.setBrake = b => { tailMat.emissiveIntensity = 0.15 + 2.4 * b; glowMat.opacity = 0.42 * b; };
  shadow(g); glow.castShadow = false; glow.receiveShadow = false;
  return g;
}

export function hcone(scene, x, z) {
  const g = new THREE.Group();
  const c = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.62, 32), new THREE.MeshStandardMaterial({ color: '#e8762c', roughness: 0.6 })); c.position.y = 0.33;
  const band = new THREE.Mesh(new THREE.CylinderGeometry(0.115, 0.15, 0.1, 32), new THREE.MeshStandardMaterial({ color: '#f2f0ea', roughness: 0.5 })); band.position.y = 0.36;
  const base = new THREE.Mesh(roundBox(0.46, 0.05, 0.46, 0.02, 4), new THREE.MeshStandardMaterial({ color: '#d0652a', roughness: 0.7 })); base.position.y = 0.025;
  g.add(c, band, base); g.position.set(x, 0.05, z); scene.add(shadow(g)); return g;
}

// a road sign on two posts; lines of text (and an optional merge arrow) drawn on a canvas
export function sign(scene, x, z, lines, opt = {}) {
  const g = new THREE.Group();
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 384; const c = cv.getContext('2d');
  c.fillStyle = opt.bg ?? '#e8762c'; c.fillRect(0, 0, 512, 384);
  c.strokeStyle = '#1c1c1c'; c.lineWidth = 14; c.strokeRect(14, 14, 484, 356);
  c.fillStyle = '#1c1c1c'; c.textAlign = 'center'; c.font = '800 64px Poppins, sans-serif';
  lines.forEach((l, k) => c.fillText(l, 256, 110 + k * 82));
  if (opt.arrow) { c.lineWidth = 18; c.beginPath(); c.moveTo(320, 340); c.lineTo(320, 290); c.lineTo(220, 250); c.stroke(); }
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const face = new THREE.Mesh(new THREE.PlaneGeometry(2.0, 1.5), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.6 })); face.position.y = 2.1; face.position.z = 0.03;
  const back = new THREE.Mesh(roundBox(2.06, 1.56, 0.05, 0.02, 4), flat('#9aa0a6', { flatShading: false })); back.position.y = 2.1; g.add(back, face);
  for (const s of [-0.7, 0.7]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 2.9, 16), flat('#9aa0a6', { flatShading: false })); p.position.set(s, 1.45, -0.04); g.add(p); }
  g.position.set(x, 0, z); g.rotation.y = opt.yaw ?? 0; scene.add(shadow(g)); return g;
}

// a small yellow digger parked in the closed lane, facing -Z, arm resting
export function digger(scene, x, z) {
  const g = new THREE.Group(), Y = new THREE.MeshStandardMaterial({ color: '#e2c45a', roughness: 0.55 }), D = new THREE.MeshStandardMaterial({ color: '#3b3f45', roughness: 0.8 });
  for (const s of [-1, 1]) {
    const tr = new THREE.Mesh(new THREE.CapsuleGeometry(0.32, 2.0, 6, 24), D); tr.rotation.x = Math.PI / 2; tr.position.set(s * 0.85, 0.34, 0); g.add(tr);
  }
  const turret = new THREE.Mesh(roundBox(1.9, 0.7, 2.2, 0.12), Y); turret.position.y = 1.05; g.add(turret);
  const cab = new THREE.Mesh(roundBox(0.95, 1.05, 1.05, 0.08), Y); cab.position.set(-0.4, 1.9, -0.35); g.add(cab);
  const gl = new THREE.Mesh(roundBox(0.9, 0.55, 0.98, 0.05), new THREE.MeshStandardMaterial({ color: '#2b3038', roughness: 0.2, metalness: 0.3 })); gl.position.set(-0.4, 2.05, -0.36); gl.scale.set(1.04, 1, 1.04); g.add(gl);
  const boom = new THREE.Mesh(roundBox(0.3, 0.32, 2.4, 0.06), Y); boom.position.set(0.45, 1.9, -1.4); boom.rotation.x = -0.55; g.add(boom);
  const stick = new THREE.Mesh(roundBox(0.24, 0.26, 1.7, 0.05), Y); stick.position.set(0.45, 1.6, -2.85); stick.rotation.x = 0.9; g.add(stick);
  const bucket = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 0.6, 24, 1, false, 0, Math.PI), D); bucket.rotation.set(0, 0, Math.PI / 2); bucket.position.set(0.45, 0.45, -3.3); g.add(bucket);
  const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.09, 24, 16), new THREE.MeshStandardMaterial({ color: '#ffb347', emissive: '#ff9a1f', emissiveIntensity: 2.5 })); beacon.position.set(-0.4, 2.5, -0.35); g.add(beacon);
  g.position.set(x, 0.05, z); scene.add(shadow(g)); beacon.castShadow = false; return g;
}

// Road along Z centred on x, with kerbs, verges, fence posts and trees. closure: the right lane is closed from
// z1 (merge point, where the cones reach the lane line) down to z0, with a cone taper `taper` metres long.
export function road(world, opt = {}) {
  const S = world.scene, x = opt.x ?? 0, z0 = opt.z0 ?? -160, z1 = opt.z1 ?? 220, lanes = 2, w = lanes * LANE_W, len = z1 - z0, zc = (z0 + z1) / 2;
  const g = new THREE.Group(); g.position.x = x; S.add(g);
  const asphalt = new THREE.Mesh(new THREE.PlaneGeometry(w, len, 4, 64), new THREE.MeshStandardMaterial({ color: opt.asphalt ?? PALETTE.asphaltDay, roughness: 0.95 }));
  asphalt.rotation.x = -Math.PI / 2; asphalt.position.set(0, 0.05, zc); asphalt.receiveShadow = true; g.add(asphalt);
  const mk = new THREE.MeshStandardMaterial({ color: PALETTE.marking, roughness: 0.8 });
  for (const ex of [-w / 2 + 0.25, w / 2 - 0.25]) { const l = new THREE.Mesh(new THREE.PlaneGeometry(0.15, len), mk); l.rotation.x = -Math.PI / 2; l.position.set(ex, 0.12, zc); l.receiveShadow = true; g.add(l); }
  for (let z = z0; z < z1; z += 9) { const d = new THREE.Mesh(new THREE.PlaneGeometry(0.14, 3), mk); d.rotation.x = -Math.PI / 2; d.position.set(0, 0.12, z); d.receiveShadow = true; g.add(d); }
  for (const s of [-1, 1]) {
    const k = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.16, len, 2, 1, 32), new THREE.MeshStandardMaterial({ color: PALETTE.concrete, roughness: 0.9 })); k.position.set(s * (w / 2 + 1.1), 0.08, zc); k.receiveShadow = true; g.add(k);
    const verge = new THREE.Mesh(new THREE.PlaneGeometry(6, len), new THREE.MeshStandardMaterial({ color: '#848a4c', roughness: 1 })); verge.rotation.x = -Math.PI / 2; verge.position.set(s * (w / 2 + 5.2), 0.025, zc); verge.receiveShadow = true; g.add(verge);
    const fx = s * (w / 2 + 7.8), posts = new THREE.Group(), wood = flat(PALETTE.wood);
    for (let z = z0; z <= z1; z += 3) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.95, 16), wood); p.position.set(fx, 0.47, z); posts.add(p); }
    for (const y of [0.35, 0.75]) { const r = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.07, len), wood); r.position.set(fx, y, zc); posts.add(r); }
    if (opt.fence !== false) g.add(shadow(posts));
  }
  const cones = [];
  if (opt.closure) {
    const { z0: c0, z1: c1, taper } = opt.closure;
    for (let z = c1; z <= c1 + taper; z += 2.0) { const u = (z - c1) / taper; cones.push(hcone(g, LANE_W * u + 0.05 * (1 - u), z)); }   // taper from the lane line out to the right kerb
    for (let z = c1 - 3; z >= c0; z -= 4) cones.push(hcone(g, 0.15, z));
    const strip = new THREE.Mesh(new THREE.PlaneGeometry(0.3, c1 - c0), new THREE.MeshStandardMaterial({ color: '#e8a23c', roughness: 0.8 })); strip.rotation.x = -Math.PI / 2; strip.position.set(0.45, 0.125, (c0 + c1) / 2); g.add(strip);
  }
  return { group: g, x, w, cones, lane: k => x + (k === 0 ? -LANE_W / 2 : LANE_W / 2) };
}

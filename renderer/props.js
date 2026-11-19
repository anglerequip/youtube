// Reusable low-poly props in the house style: cars, roads, fences, cones, lamps.
import * as THREE from 'three';
import { PALETTE } from './world.js';

const flat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0, flatShading: true, ...extra });
const shadow = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };

// Boxy 1990s car, ~4.2 m long, facing -Z. Returns a group with .setBrake(0..1).
export function car(color, kind = 'hatch', roofRack = false) {
  const g = new THREE.Group();
  const body = flat(color, { roughness: 0.55 });
  const glass = flat('#2b3038', { roughness: 0.25, metalness: 0.2 });
  const L = kind === 'estate' ? 4.4 : 4.1, Wd = 1.75;
  const lower = new THREE.Mesh(new THREE.BoxGeometry(Wd, 0.62, L), body); lower.position.y = 0.55;
  const cabinL = kind === 'sedan' ? L * 0.48 : kind === 'estate' ? L * 0.66 : L * 0.56;
  const cabinZ = kind === 'sedan' ? 0.05 : 0.35;
  const cabin = new THREE.Mesh(taperedBox(Wd * 0.9, 0.56, cabinL, 0.8, 0.82), body); cabin.position.set(0, 1.14, cabinZ);
  // glass band slightly proud of the cabin so windows read from every side
  const win = new THREE.Mesh(taperedBox(Wd * 0.9 * 0.97, 0.3, cabinL * 0.97, 0.86, 0.88), glass); win.scale.set(1.03, 1, 1.03);
  win.position.set(0, 1.15, cabinZ);
  g.add(lower, cabin, win);
  const wheelGeo = new THREE.CylinderGeometry(0.33, 0.33, 0.24, 10); wheelGeo.rotateZ(Math.PI / 2);
  const wheelMat = flat('#1d1d20');
  for (const [x, z] of [[-0.8, -1.3], [0.8, -1.3], [-0.8, 1.3], [0.8, 1.3]]) {
    const w = new THREE.Mesh(wheelGeo, wheelMat); w.position.set(x, 0.33, z * L / 4.1); g.add(w);
  }
  // tail lights (rear is +Z) and plate
  const tailMat = new THREE.MeshStandardMaterial({ color: '#7a1416', emissive: PALETTE.red, emissiveIntensity: 0.15, roughness: 0.4 });
  for (const x of [-0.62, 0.62]) {
    const tl = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.16, 0.04), tailMat); tl.position.set(x, 0.68, L / 2 + 0.01); g.add(tl);
  }
  const plate = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.12, 0.03), flat('#e8e6df')); plate.position.set(0, 0.5, L / 2 + 0.01); g.add(plate);
  // brake glow on the road behind the car
  const glowMat = new THREE.MeshBasicMaterial({ color: '#ff2a1f', transparent: true, opacity: 0, depthWrite: false,
    blending: THREE.AdditiveBlending, map: radialTexture() });
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(2.0, 1.3), glowMat); glow.rotation.x = -Math.PI / 2; glow.position.set(0, 0.03, L / 2 + 0.55);
  g.add(glow);
  if (roofRack) for (const x of [-0.6, 0.6]) {
    const bar = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, cabinL * 0.9), flat('#2a2a2c')); bar.position.set(x, 1.42, cabinZ); g.add(bar);
  }
  // picture review (other lane, round 8): at 5.5x the lit tail lights tone-mapped to pale pink while the glow
  // read as a red puddle; a lower, saturated emission keeps them red, the glow is tighter under the bumper
  g.setBrake = b => { tailMat.emissiveIntensity = 0.15 + 2.4 * b; glowMat.opacity = 0.42 * b; };
  return shadow(g);
}

// Box whose top face is shrunk (sx, sz): a simple low-poly car cabin.
function taperedBox(w, h, d, sx, sz) {
  const g = new THREE.BoxGeometry(w, h, d); const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) if (p.getY(i) > 0) { p.setX(i, p.getX(i) * sx); p.setZ(i, p.getZ(i) * sz); }
  g.computeVertexNormals(); return g;
}

let _radial;
function radialTexture() {
  if (_radial) return _radial;
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128); _radial = new THREE.CanvasTexture(c); return _radial;
}

// Straight road along Z from z0 to z1, `lanes` lanes of 3.6 m, kerb strips each side.
export function straightRoad(scene, { z0 = -200, z1 = 40, lanes = 2, asphalt = PALETTE.asphaltDay } = {}) {
  const g = new THREE.Group(); const w = lanes * 3.6, len = z1 - z0, zc = (z0 + z1) / 2;
  const road = new THREE.Mesh(new THREE.PlaneGeometry(w, len), new THREE.MeshStandardMaterial({ color: asphalt, roughness: 0.95 }));
  road.rotation.x = -Math.PI / 2; road.position.set(0, 0.02, zc); road.receiveShadow = true; g.add(road);
  const mk = new THREE.MeshStandardMaterial({ color: PALETTE.marking, roughness: 0.8 });
  for (const x of [-w / 2 + 0.25, w / 2 - 0.25]) {
    const line = new THREE.Mesh(new THREE.PlaneGeometry(0.15, len), mk); line.rotation.x = -Math.PI / 2; line.position.set(x, 0.03, zc); line.receiveShadow = true; g.add(line);
  }
  for (let l = 1; l < lanes; l++) for (let z = z0; z < z1; z += 9) {
    const d = new THREE.Mesh(new THREE.PlaneGeometry(0.14, 3), mk); d.rotation.x = -Math.PI / 2; d.position.set(-w / 2 + l * 3.6, 0.03, z); d.receiveShadow = true; g.add(d);
  }
  for (const s of [-1, 1]) {
    const k = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.12, len), flat(PALETTE.concrete)); k.position.set(s * (w / 2 + 1.1), 0.06, zc); k.receiveShadow = true; g.add(k);
  }
  scene.add(g); return g;
}

export function fence(scene, x, z0, z1, step = 3) {
  const g = new THREE.Group(); const m = flat(PALETTE.wood);
  for (let z = z0; z <= z1; z += step) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.9, 0.1), m); p.position.set(x, 0.45, z); g.add(p); }
  for (const y of [0.35, 0.75]) { const r = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.07, z1 - z0), m); r.position.set(x, y, (z0 + z1) / 2); g.add(r); }
  scene.add(shadow(g)); return g;
}

export function cone(scene, x, z) {
  const g = new THREE.Group();
  const c = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.6, 8), flat('#e8762c')); c.position.y = 0.3;
  const band = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.15, 0.1, 8), flat('#f2f0ea')); band.position.y = 0.34;
  const base = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.05, 0.45), flat('#e8762c')); base.position.y = 0.025;
  g.add(c, band, base); g.position.set(x, 0, z); scene.add(shadow(g)); return g;
}

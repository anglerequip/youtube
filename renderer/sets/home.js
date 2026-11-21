// Reusable set (CLAUDE.md "Autopilot efficiency": one home set shared by the dog and cat videos).
// A warm, daylit cut-away kitchen + living room: no ceiling, no front wall, open toward +z.
// Kitchen on the left (x < 0, tiled floor, counter and window on the back wall, fridge in the corner);
// living room on the right (x > 0, wooden floor, tall bookshelf on the back wall, sofa on the right wall,
// a floor cushion and a rug). Everything stays inside x -3.2..3.2, z -2.4..2.6.
//
//   import { home } from '../sets/home.js';
//   const H = home(world, { cushion: true });   // H.anchors: { bowl, bowl2, shelfTop, cushion, window }
import * as THREE from 'three';
import { MAT } from '../materials.js';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.8, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };
function box(P, w, h, d, m, x, y, z, seg = 2) {
  const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d, seg, seg, seg), m); o.position.set(x, y, z);
  o.castShadow = o.receiveShadow = true; P.add(o); return o;
}
// soft rounded box (cushions, sofa seat) by pushing a subdivided box toward a superellipsoid
export function softBox(w, h, d, r = 0.5, seg = 24) {
  const g = new THREE.BoxGeometry(w, h, d, seg, Math.max(6, seg / 2), seg), P = g.attributes.position, v = new THREE.Vector3();
  for (let i = 0; i < P.count; i++) {
    v.fromBufferAttribute(P, i);
    const nx = v.x / (w / 2), ny = v.y / (h / 2), nz = v.z / (d / 2);
    const k = Math.pow(Math.abs(nx), 6) + Math.pow(Math.abs(ny), 3) + Math.pow(Math.abs(nz), 6);
    const f = 1 - r * 0.22 * Math.max(0, k - 1);
    P.setXYZ(i, v.x * (1 - r * 0.1 * ny * ny), v.y * Math.max(0.55, f), v.z * (1 - r * 0.1 * ny * ny));
  }
  g.computeVertexNormals(); return g;
}

// floor tiles as a canvas texture (warm terracotta and cream checker, thin grout)
function tileTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
  const n = 8, s = 512 / n;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    g.fillStyle = (i + j) % 2 ? '#c9a27e' : '#e6dccb'; g.fillRect(i * s, j * s, s, s);
    g.fillStyle = 'rgba(0,0,0,0.04)'; g.fillRect(i * s + s * 0.1, j * s + s * 0.1, s * 0.5, s * 0.3);
  }
  g.strokeStyle = '#a89684'; g.lineWidth = 3;
  for (let k = 0; k <= n; k++) { g.beginPath(); g.moveTo(k * s, 0); g.lineTo(k * s, 512); g.stroke(); g.beginPath(); g.moveTo(0, k * s); g.lineTo(512, k * s); g.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t;
}

function books(P, x0, x1, y, z, seed) {
  let s = seed; const R = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const cols = ['#8a3b33', '#2e5d73', '#c9a77c', '#4f6b3a', '#a99bc4', '#e2c45a', '#6b4a6e', '#d9c7a0', '#3f5a52'];
  let x = x0;
  while (x < x1 - 0.04) {
    const w = 0.025 + R() * 0.03, h = 0.2 + R() * 0.1, lean = R() < 0.1 ? 0.15 : 0;
    const b = box(P, w, h, 0.2, std(cols[Math.floor(R() * cols.length)], { roughness: 0.7 }), x + w / 2, y + h / 2, z, 1);
    b.rotation.z = lean; x += w + 0.004 + (lean ? 0.03 : 0);
  }
}

function plant(P, x, z, s = 1) {
  const g = new THREE.Group();
  const pot = new THREE.Mesh(new THREE.LatheGeometry([[0, 0], [0.12, 0], [0.15, 0.24], [0.16, 0.26], [0.0, 0.26]].map(p => new THREE.Vector2(...p)), 40), MAT.ceramic('#c46a4a'));
  g.add(pot);
  const leafM = std('#5f7d3a', { roughness: 0.7, side: THREE.DoubleSide });
  for (let k = 0; k < 9; k++) {
    const a = k * 2.4, h = 0.35 + 0.18 * ((k * 37) % 5) / 5;
    const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.09, 24, 12), leafM);
    leaf.scale.set(0.5, 1.6, 0.18); leaf.position.set(Math.cos(a) * 0.08, 0.26 + h * 0.6, Math.sin(a) * 0.08);
    leaf.rotation.set(Math.sin(a) * 0.6, a, Math.cos(a) * 0.6); g.add(leaf);
  }
  g.scale.setScalar(s); g.position.set(x, 0, z); P.add(shadowed(g)); return g;
}

export function bowl(color = '#c3c7cc', r = 0.11) {
  const g = new THREE.Group();
  const pts = [[0.0, 0.0], [r * 0.82, 0.0], [r * 0.9, 0.01], [r * 1.0, 0.055], [r * 1.05, 0.07], [r * 0.98, 0.072], [r * 0.9, 0.02], [0.0, 0.016]];
  const steel = new THREE.MeshStandardMaterial({ color, metalness: 0.85, roughness: 0.28, side: THREE.DoubleSide, envMapIntensity: 1.0 });
  const b = new THREE.Mesh(new THREE.LatheGeometry(pts.map(p => new THREE.Vector2(...p)), 64), steel); g.add(b);
  const water = new THREE.Mesh(new THREE.CircleGeometry(r * 0.94, 64), new THREE.MeshPhysicalMaterial({ color: '#8fc3d8', roughness: 0.05, transmission: 0.3, transparent: true, opacity: 0.85 }));
  water.rotation.x = -Math.PI / 2; water.position.y = 0.05; g.add(water); g.userData.water = water;
  return shadowed(g);
}

export function home(world, opt = {}) {
  const S = world.scene, root = new THREE.Group(); S.add(root);
  const X0 = -3.2, X1 = 3.2, Z0 = -2.4, Z1 = 2.6, H = 2.7, t = 0.12;
  // floors: tiles in the kitchen, boards in the living room (tops 5 mm above the outdoor ground plane)
  const tiles = tileTexture(); tiles.repeat.set(3.2 / 0.6, (Z1 - Z0) / 0.6);
  const kf = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.06, Z1 - Z0), new THREE.MeshStandardMaterial({ map: tiles, roughness: 0.55 }));
  kf.position.set(-1.6, -0.025, (Z0 + Z1) / 2); kf.receiveShadow = true; root.add(kf);
  const lf = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.06, Z1 - Z0), MAT.wood('#a27a52'));
  lf.position.set(1.6, -0.025, (Z0 + Z1) / 2); lf.receiveShadow = true; root.add(lf);
  const sill = box(root, 0.05, 0.012, Z1 - Z0, std('#8a6a48'), 0, 0.006, (Z0 + Z1) / 2);
  // walls: back wall with a window over the counter, left and right walls
  const wallK = std('#e2d6bf', { roughness: 0.95 }), wallL = std('#b9c4b0', { roughness: 0.95 }), trim = std('#f0ebe0', { roughness: 0.6 });
  const wx0 = -2.3, wx1 = -0.9, wy0 = 1.15, wy1 = 2.1;
  box(root, wx0 - X0, H, t, wallK, (X0 + wx0) / 2, H / 2, Z0 - t / 2);
  box(root, 0 - wx1, H, t, wallK, wx1 / 2, H / 2, Z0 - t / 2);
  box(root, wx1 - wx0, wy0, t, wallK, (wx0 + wx1) / 2, wy0 / 2, Z0 - t / 2);
  box(root, wx1 - wx0, H - wy1, t, wallK, (wx0 + wx1) / 2, (wy1 + H) / 2, Z0 - t / 2);
  box(root, X1, H, t, wallL, X1 / 2, H / 2, Z0 - t / 2);
  for (const [w, h, x, y] of [[wx1 - wx0 + 0.08, 0.06, (wx0 + wx1) / 2, wy0], [wx1 - wx0 + 0.08, 0.06, (wx0 + wx1) / 2, wy1], [0.06, wy1 - wy0, wx0, (wy0 + wy1) / 2], [0.06, wy1 - wy0, wx1, (wy0 + wy1) / 2], [0.035, wy1 - wy0, (wx0 + wx1) / 2, (wy0 + wy1) / 2]])
    box(root, w, h, 0.08, trim, x, y, Z0 - 0.02);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(wx1 - wx0, wy1 - wy0), new THREE.MeshPhysicalMaterial({ color: '#cfe0ea', transparent: true, opacity: 0.18, roughness: 0.05 }));
  glass.position.set((wx0 + wx1) / 2, (wy0 + wy1) / 2, Z0 - 0.03); root.add(glass);
  box(root, t, H, Z1 - Z0 + 0.6, wallK, X0 - t / 2, H / 2, (Z0 + Z1) / 2 + 0.3);
  box(root, t, H, Z1 - Z0 + 0.6, wallL, X1 + t / 2, H / 2, (Z0 + Z1) / 2 + 0.3);
  for (const [x0, x1] of [[X0, 0], [0, X1]]) box(root, x1 - x0, 0.1, 0.025, trim, (x0 + x1) / 2, 0.05, Z0 + 0.012);
  // kitchen: counter with cabinets along the back wall, a sink, a kettle, a fridge in the left corner
  const cab = std('#8fa6c8', { roughness: 0.55 }), top = std('#e9e5dc', { roughness: 0.35 });
  const cx0 = -2.45, cx1 = -0.35, cz = Z0 + 0.32;
  box(root, cx1 - cx0, 0.86, 0.6, cab, (cx0 + cx1) / 2, 0.45, cz, 3);
  box(root, cx1 - cx0 + 0.04, 0.04, 0.64, top, (cx0 + cx1) / 2, 0.9, cz);
  for (let k = 0; k < 4; k++) {                     // cabinet doors and handles
    const x = cx0 + (k + 0.5) * (cx1 - cx0) / 4;
    box(root, (cx1 - cx0) / 4 - 0.03, 0.74, 0.012, std('#9db2d0', { roughness: 0.5 }), x, 0.47, cz + 0.305);
    const h = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.12, 16), std('#d9d4c8', { metalness: 0.7, roughness: 0.3 }));
    h.position.set(x + 0.17, 0.62, cz + 0.32); root.add(h);
  }
  const sink = box(root, 0.5, 0.02, 0.36, std('#b9bdc2', { metalness: 0.8, roughness: 0.3 }), (wx0 + wx1) / 2, 0.915, cz);
  const tap = new THREE.Mesh(new THREE.TorusGeometry(0.09, 0.012, 16, 48, Math.PI), std('#cfd3d8', { metalness: 0.85, roughness: 0.25 }));
  tap.position.set((wx0 + wx1) / 2, 1.0, cz - 0.17); root.add(tap);
  const kettle = new THREE.Mesh(new THREE.SphereGeometry(0.1, 40, 30), MAT.ceramic('#e2c45a')); kettle.scale.set(1, 0.9, 1);
  kettle.position.set(-0.65, 1.0, cz); kettle.castShadow = true; root.add(kettle);
  const fridge = box(root, 0.7, 1.85, 0.66, MAT.ceramic('#e6e3dc'), X0 + 0.38, 0.925, Z0 + 0.36, 3);
  box(root, 0.02, 0.5, 0.03, std('#b9bdc2', { metalness: 0.7, roughness: 0.3 }), X0 + 0.66, 1.25, Z0 + 0.71);
  box(root, 0.66, 0.012, 0.012, std('#c9c4b8'), X0 + 0.38, 1.25, Z0 + 0.695);
  // a few wall tiles behind the counter
  box(root, cx1 - cx0, 0.4, 0.015, std('#f2efe8', { roughness: 0.4 }), (cx0 + cx1) / 2, 1.12, Z0 + 0.008);
  // living room: tall bookshelf on the back wall, sofa on the right wall, rug, plant, framed picture
  const shelfX = opt.shelfX ?? 1.25, shelfW = 1.0, shelfH = 2.05, shelfD = 0.34, wood = MAT.wood('#8a6342');
  const shelf = new THREE.Group();
  box(shelf, 0.04, shelfH, shelfD, wood, -shelfW / 2, shelfH / 2, 0); box(shelf, 0.04, shelfH, shelfD, wood, shelfW / 2, shelfH / 2, 0);
  box(shelf, shelfW, 0.02, shelfD, wood, 0, 0.01, -shelfD / 2 + 0.01);
  for (const y of [0.06, 0.5, 0.95, 1.4, shelfH]) box(shelf, shelfW + 0.04, 0.035, shelfD, wood, 0, y, 0);
  box(shelf, shelfW, shelfH, 0.015, std('#6e4f36'), 0, shelfH / 2, -shelfD / 2 + 0.008);
  books(shelf, -shelfW / 2 + 0.04, shelfW / 2 - 0.05, 0.08, 0.01, 3); books(shelf, -shelfW / 2 + 0.04, shelfW / 2 - 0.3, 0.52, 0.01, 7);
  books(shelf, -shelfW / 2 + 0.25, shelfW / 2 - 0.04, 0.97, 0.01, 11); books(shelf, -shelfW / 2 + 0.04, shelfW / 2 - 0.45, 1.42, 0.01, 17);
  shelf.position.set(shelfX, 0, Z0 + shelfD / 2 + 0.01); root.add(shelf);
  const sofa = new THREE.Group(), fab = std('#c9a77c', { roughness: 0.95 }), fab2 = std('#b8956a', { roughness: 0.95 });
  const seat = new THREE.Mesh(softBox(0.8, 0.22, 1.9, 0.6), fab); seat.position.set(0, 0.32, 0); sofa.add(seat);
  const base = new THREE.Mesh(softBox(0.86, 0.22, 2.0, 0.3), fab2); base.position.set(0, 0.13, 0); sofa.add(base);
  const back = new THREE.Mesh(softBox(0.22, 0.62, 2.0, 0.6), fab2); back.position.set(0.32, 0.6, 0); sofa.add(back);
  for (const s of [-1, 1]) { const arm = new THREE.Mesh(softBox(0.86, 0.42, 0.2, 0.7), fab2); arm.position.set(0, 0.42, s * 0.98); sofa.add(arm); }
  for (const s of [-1, 1]) { const c = new THREE.Mesh(softBox(0.18, 0.4, 0.45, 1.0), std(s < 0 ? '#2e8f86' : '#e2c45a', { roughness: 0.95 })); c.position.set(0.15, 0.58, s * 0.5); c.rotation.z = 0.15; sofa.add(c); }
  sofa.position.set(X1 - 0.5, 0, 0.55); root.add(shadowed(sofa));
  const rug = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.0, 0.012, 72), std('#a5584a', { roughness: 1 }));
  rug.scale.set(1.1, 1, 0.8); rug.position.set(1.4, 0.006, 0.9); rug.receiveShadow = true; root.add(rug);
  const rugIn = new THREE.Mesh(new THREE.CylinderGeometry(0.78, 0.78, 0.014, 72), std('#e5d8bd', { roughness: 1 }));
  rugIn.scale.set(1.1, 1, 0.8); rugIn.position.set(1.4, 0.008, 0.9); rugIn.receiveShadow = true; root.add(rugIn);
  plant(root, 2.55, Z0 + 0.35, 1.2); plant(root, -0.15, Z0 + 0.3, 0.8);
  box(root, 0.62, 0.46, 0.03, std('#3a2e24'), 2.45, 1.7, Z0 + 0.02);
  box(root, 0.54, 0.38, 0.032, std('#8fa6c8', { roughness: 0.9 }), 2.45, 1.7, Z0 + 0.025);
  // optional big floor cushion below the bookshelf (the falling cat lands here)
  let cushion = null;
  if (opt.cushion) {
    cushion = new THREE.Mesh(softBox(0.85, 0.2, 0.75, 1.0), std('#d9c7a0', { roughness: 0.95 }));
    cushion.position.set(shelfX, 0.1, Z0 + 0.95); cushion.castShadow = cushion.receiveShadow = true; root.add(cushion);
    const piping = new THREE.Mesh(new THREE.TorusGeometry(0.4, 0.012, 10, 80), std('#a5584a'));
    piping.rotation.x = Math.PI / 2; piping.scale.set(1.0, 0.86, 1); piping.position.set(shelfX, 0.12, Z0 + 0.95); root.add(piping);
  }
  // daylight through the window: a soft warm fill so the cut-away interior is never dim
  const fill = new THREE.PointLight('#ffe6c8', 3.0, 7.0, 2); fill.position.set(0, 2.2, 1.6); root.add(fill);
  const win = new THREE.PointLight('#fff1dc', 2.0, 4.0, 2); win.position.set((wx0 + wx1) / 2, 1.7, Z0 + 0.6); root.add(win);
  // the garden beyond the window
  for (const [x, z, s] of [[-2.0, -6.5, 1.6], [-4.5, -8.0, 1.9], [0.5, -9.5, 2.1], [3.5, -7.0, 1.7]]) world.roundTree(x, z, s);
  world.conifer(-6.0, -6.0, 2.0);
  return {
    root, shelf, cushion,
    anchors: { bowl: [-0.6, 0, 0.75], bowl2: [-1.6, 0, 1.05], shelfTop: [shelfX, shelfH + 0.02, Z0 + shelfD / 2 + 0.01],
               cushion: [shelfX, 0.2, Z0 + 0.95], window: [(wx0 + wx1) / 2, 1.6, Z0], counter: [(cx0 + cx1) / 2, 0.92, cz] },
    bounds: { X0, X1, Z0, Z1, H },
  };
}

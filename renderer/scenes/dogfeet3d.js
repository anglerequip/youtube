// Why your dog sleeps on your feet (content/episodes/dog-feet/plan.py).
// A cut-away bedroom at night (no ceiling, open at the front): the wizard in bed under a duvet, a scruffy dog
// asleep across his feet, the woman standing at the foot end. Bedside lamp, moonlit window, a door with warm
// light under it. Cutaways far away: a wolf family in a snowy clearing and a puppy pile in a basket.
// This file only draws what the plan lists.
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { dog } from '../dog.js';
import { MAT } from '../materials.js';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.8, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };
const box = (S, w, h, d, m, x, y, z) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d, 2, 2, 2), m); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; S.add(o); return o; };
const smooth = t => t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t);

// a soft box (mattress, pillow): a subdivided box whose corners are rounded by pushing vertices toward an ellipsoid
function softBox(w, h, d, r = 0.3, seg = 24) {
  const g = new THREE.BoxGeometry(w, h, d, seg, Math.max(4, seg / 3), seg), P = g.attributes.position, v = new THREE.Vector3();
  for (let i = 0; i < P.count; i++) {
    v.fromBufferAttribute(P, i);
    const nx = v.x / (w / 2), ny = v.y / (h / 2), nz = v.z / (d / 2);
    const k = Math.pow(Math.abs(nx), 6) + Math.pow(Math.abs(ny), 4) + Math.pow(Math.abs(nz), 6);
    const f = 1 - r * 0.25 * Math.max(0, k - 1);
    P.setXYZ(i, v.x * (1 - r * 0.12 * Math.abs(ny) * Math.abs(nx)), v.y * Math.max(0.6, f), v.z * (1 - r * 0.12 * Math.abs(ny) * Math.abs(nz)));
  }
  g.computeVertexNormals(); return g;
}

function room(S, L) {
  const floorM = MAT.wood('#7a5a3e'), wallM = std('#7d7466', { roughness: 0.95 }), trimM = std('#d8d0c0', { roughness: 0.7 });
  // floor boards
  box(S, 4.0, 0.06, 3.6, floorM, 0.4, -0.03, 0.1);
  const X0 = -1.6, X1 = 2.4, Z0 = -1.6, Hh = 2.6, t = 0.1;
  // back wall with a window opening (x 0.05..1.05, y 0.95..1.95)
  const wx0 = 0.05, wx1 = 1.05, wy0 = 0.95, wy1 = 1.95;
  box(S, wx0 - X0, Hh, t, wallM, (X0 + wx0) / 2, Hh / 2, Z0 - t / 2);
  box(S, X1 - wx1, Hh, t, wallM, (wx1 + X1) / 2, Hh / 2, Z0 - t / 2);
  box(S, wx1 - wx0, wy0, t, wallM, (wx0 + wx1) / 2, wy0 / 2, Z0 - t / 2);
  box(S, wx1 - wx0, Hh - wy1, t, wallM, (wx0 + wx1) / 2, (wy1 + Hh) / 2, Z0 - t / 2);
  // window frame, mullions, sill and pale glass
  const fr = std('#e2dccd', { roughness: 0.6 });
  for (const [w, h, x, y] of [[1.08, 0.05, 0.55, wy0], [1.08, 0.05, 0.55, wy1], [0.05, 1.05, wx0, 1.45], [0.05, 1.05, wx1, 1.45], [0.03, 1.0, 0.55, 1.45], [1.0, 0.03, 0.55, 1.45]])
    box(S, w, h, 0.07, fr, x, y, Z0 - 0.02);
  box(S, 1.2, 0.04, 0.16, fr, 0.55, wy0 - 0.03, Z0 + 0.05);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 1.0), new THREE.MeshPhysicalMaterial({ color: '#9fb4d8', transparent: true, opacity: 0.12, roughness: 0.05 }));
  glass.position.set(0.55, 1.45, Z0 - 0.03); S.add(glass);
  // curtains: wavy fabric panels either side of the window
  const curtM = std('#6f5b78', { roughness: 0.95, side: THREE.DoubleSide });
  for (const s of [-1, 1]) {
    const g = new THREE.PlaneGeometry(0.42, 1.55, 40, 8), P = g.attributes.position;
    for (let i = 0; i < P.count; i++) P.setZ(i, 0.035 * Math.sin(P.getX(i) * 38) + 0.01 * Math.sin(P.getY(i) * 6));
    g.computeVertexNormals();
    const c = new THREE.Mesh(g, curtM); c.position.set(s < 0 ? wx0 - 0.17 : wx1 + 0.17, 1.38, Z0 + 0.06); c.castShadow = c.receiveShadow = true; S.add(c);
  }
  const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 1.7, 24), std('#3b3f45', { metalness: 0.6, roughness: 0.4 }));
  rod.rotation.z = Math.PI / 2; rod.position.set(0.55, 2.17, Z0 + 0.07); S.add(rod);
  // left wall (behind the headboard)
  box(S, t, Hh, 3.6, wallM, X0 - t / 2, Hh / 2, 0.2);
  // right wall with a door opening (z -1.2..-0.3, y 0..2.05)
  const dz0 = -1.2, dz1 = -0.3, dh = 2.05;
  box(S, t, Hh, dz0 - Z0, wallM, X1 + t / 2, Hh / 2, (Z0 + dz0) / 2);
  box(S, t, Hh, 2.0 - dz1, wallM, X1 + t / 2, Hh / 2, (dz1 + 2.0) / 2);
  box(S, t, Hh - dh, dz1 - dz0, wallM, X1 + t / 2, (dh + Hh) / 2, (dz0 + dz1) / 2);
  for (const [w, h, d, x, y, z] of [[0.13, 0.06, 1.0, X1, dh + 0.03, (dz0 + dz1) / 2], [0.13, dh, 0.05, X1, dh / 2, dz0], [0.13, dh, 0.05, X1, dh / 2, dz1]]) box(S, w, h, d, trimM, x, y, z);
  // door slab, ajar, swung into the room
  const door = new THREE.Group(); door.position.set(X1 - 0.02, 0, dz1);
  const slab = box(door, 0.045, dh - 0.03, dz1 - dz0 - 0.04, std('#c9bda5', { roughness: 0.7 }), 0, (dh - 0.03) / 2, -(dz1 - dz0) / 2);
  const knob = new THREE.Mesh(new THREE.SphereGeometry(0.03, 32, 24), std('#b8955a', { metalness: 0.8, roughness: 0.3 })); knob.position.set(-0.04, 1.0, -(dz1 - dz0) + 0.1); door.add(knob);
  door.rotation.y = 0.55; S.add(door);
  // warm hallway beyond the door: a glowing back panel, and a light spill on the floor
  const hall = new THREE.Mesh(new THREE.PlaneGeometry(0.95, 2.1), new THREE.MeshStandardMaterial({ color: '#ffcf8f', emissive: '#ffb860', emissiveIntensity: 2.4 }));
  hall.position.set(X1 + 0.5, 1.05, (dz0 + dz1) / 2); hall.rotation.y = -Math.PI / 2; S.add(hall);
  const doorLight = new THREE.PointLight('#ffbf73', 2.2, 4.5, 2); doorLight.position.set(X1 - 0.2, 1.6, (dz0 + dz1) / 2); S.add(doorLight);
  // skirting boards
  box(S, X1 - X0, 0.09, 0.02, trimM, (X0 + X1) / 2, 0.045, Z0 + 0.01);
  box(S, 0.02, 0.09, 3.6, trimM, X0 + 0.01, 0.045, 0.2);
  // rug
  const rug = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.0, 0.012, 64), std('#a5584a', { roughness: 1 }));
  rug.scale.set(1.25, 1, 0.75); rug.position.set(0.55, 0.006, 1.2); rug.receiveShadow = true; S.add(rug);
  const rugIn = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 0.014, 64), std('#d9c7a0', { roughness: 1 }));
  rugIn.scale.set(1.25, 1, 0.75); rugIn.position.set(0.55, 0.008, 1.2); rugIn.receiveShadow = true; S.add(rugIn);
  // a picture frame and a small shelf on the back wall
  box(S, 0.5, 0.38, 0.03, std('#3a2e24'), -0.8, 1.75, Z0 + 0.02);
  box(S, 0.42, 0.3, 0.032, std('#8fa6c8', { roughness: 0.9 }), -0.8, 1.75, Z0 + 0.025);
  return { door, hall };
}

function bed(S, L) {
  const wood = MAT.wood('#8a6342'), top = L.bed_top;
  const g = new THREE.Group();
  box(g, 2.45, 0.2, 1.75, wood, -0.05, 0.25, 0);                                  // frame
  for (const x of [-1.22, 1.12]) for (const z of [-0.82, 0.82]) box(g, 0.08, 0.2, 0.08, wood, x, 0.1, z);
  const head = box(g, 0.08, 1.05, 1.8, wood, -1.3, 0.62, 0);                       // headboard
  box(g, 0.1, 0.06, 1.86, wood, -1.3, 1.16, 0);
  box(g, 0.07, 0.55, 1.8, wood, 1.17, 0.36, 0);                                    // footboard
  const mat = new THREE.Mesh(softBox(2.26, 0.22, 1.62, 0.6), std('#e9e5dc', { roughness: 0.9 }));
  mat.position.set(-0.05, top - 0.11, 0); g.add(mat);
  const pil = new THREE.Mesh(softBox(0.42, 0.13, 0.72, 1.0), std('#f0ece3', { roughness: 0.85 }));
  pil.position.set(-1.0, top + 0.06, 0.0); pil.rotation.z = 0.12; g.add(pil);
  const pil2 = new THREE.Mesh(softBox(0.4, 0.12, 0.68, 1.0), std('#b9c4d6', { roughness: 0.85 }));
  pil2.position.set(-1.13, top + 0.14, -0.42); pil2.rotation.set(0.2, 0.15, 0.5); g.add(pil2);
  S.add(shadowed(g));

  // duvet: a subdivided sheet draped over the wizard's body and feet, hanging down the sides and the foot end
  const xa = -0.62, xb = 1.12, zw = 0.84, NX = 120, NZ = 90;
  const geo = new THREE.PlaneGeometry(1, 1, NX, NZ); geo.rotateX(-Math.PI / 2);
  const P = geo.attributes.position;
  const bodyH = (x, z) => {
    const across = Math.exp(-Math.pow(Math.abs(z) / 0.46, 6));
    const along = smooth((x - xa + 0.02) / 0.12);
    const feet = 0.05 * Math.exp(-Math.pow((x - 0.75) / 0.18, 2));                 // the toes push it up a little
    return (0.31 + feet) * across * along;
  };
  for (let i = 0; i < P.count; i++) {
    const u = P.getX(i) + 0.5, w = P.getZ(i) * 2;                                   // u 0..1 along, w -1..1 across
    const xEnd = xb + 0.22;                                                         // the last strip hangs over the foot end
    let x = xa + (xEnd - xa) * u, z = w * (zw + 0.24), y;
    const zc = Math.min(Math.abs(z), zw), xc = Math.min(x, xb);
    y = top + 0.035 + bodyH(xc, z * zw / Math.max(zw, Math.abs(z))) + 0.008 * Math.sin(x * 23 + z * 9);
    if (Math.abs(z) > zw) { const k = (Math.abs(z) - zw) / 0.24; y = top + 0.035 - 0.22 * k; z = Math.sign(z) * (zw + 0.03 + 0.03 * k); }
    if (x > xb) { const k = (x - xb) / 0.22; y = Math.min(y, top + 0.035) - 0.2 * k; x = xb + 0.03 + 0.02 * k; }
    P.setXYZ(i, x, y, z);
  }
  geo.computeVertexNormals();
  // a soft check pattern in vertex colours (powder blue and cream)
  const col = new Float32Array(P.count * 3), A = new THREE.Color('#8fa6c8'), B = new THREE.Color('#c9d3e0'), c = new THREE.Color();
  for (let i = 0; i < P.count; i++) {
    const u = (P.getX(i) + 0.5), w = P.getZ(i);
    const k = ((Math.floor((i % (NX + 1)) / 10) + Math.floor(Math.floor(i / (NX + 1)) / 10)) % 2);
    c.copy(k ? A : B); col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const duvet = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide }));
  duvet.castShadow = duvet.receiveShadow = true; S.add(duvet);
  // the turned-down sheet edge across his chest
  const fold = new THREE.Mesh(new THREE.CapsuleGeometry(0.035, 1.0, 8, 32), std('#f0ece3', { roughness: 0.85 }));
  fold.rotation.x = Math.PI / 2; fold.position.set(xa + 0.02, top + 0.33, 0); fold.scale.set(1, 1, 1); fold.castShadow = true; S.add(fold);
  const duvetTop = (x, z) => top + 0.035 + bodyH(Math.min(x, xb), z);
  return { duvetTop };
}

function nightstand(S, L) {
  const g = new THREE.Group(), wood = MAT.wood('#6e4f36');
  box(g, 0.45, 0.5, 0.4, wood, 0, 0.25, 0);
  box(g, 0.38, 0.12, 0.02, std('#5a3f2a'), 0, 0.32, 0.205);
  const knob = new THREE.Mesh(new THREE.SphereGeometry(0.015, 24, 16), std('#b8955a', { metalness: 0.8, roughness: 0.3 })); knob.position.set(0, 0.32, 0.22); g.add(knob);
  // lamp: turned base and a glowing shade
  const base = new THREE.Mesh(new THREE.LatheGeometry([[0.0, 0], [0.07, 0], [0.075, 0.02], [0.03, 0.06], [0.04, 0.16], [0.012, 0.24], [0.0, 0.24]].map(p => new THREE.Vector2(...p)), 32), std('#3f5a52', { roughness: 0.4 }));
  base.position.y = 0.5; g.add(base);
  const shade = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.13, 0.17, 48, 1, true),
    new THREE.MeshStandardMaterial({ color: '#ffe4b5', emissive: '#ffbf70', emissiveIntensity: 2.0, side: THREE.DoubleSide, roughness: 0.8 }));
  shade.position.y = 0.82; g.add(shade);
  const bulb = new THREE.PointLight('#ffc27a', 2.4, 5.0, 2); bulb.position.y = 0.8; bulb.castShadow = false; g.add(bulb);
  // a book and a glass of water
  box(g, 0.16, 0.03, 0.22, std('#8a3b33'), -0.12, 0.515, 0.05);
  const glass = new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.024, 0.1, 32, 1, true), new THREE.MeshPhysicalMaterial({ color: '#e8f0f2', transparent: true, opacity: 0.35, roughness: 0.05 }));
  glass.position.set(0.14, 0.55, 0.08); g.add(glass);
  g.position.set(-1.05, 0, -1.15); S.add(g);
  g.traverse(o => { if (o.isMesh && o !== shade) { o.castShadow = true; o.receiveShadow = true; } });
}

// snow ground with gentle drifts for the wolf cutaway
function snowField(S, cx, cz, r) {
  const g = new THREE.CircleGeometry(r, 96, 0, Math.PI * 2); g.rotateX(-Math.PI / 2);
  const P = g.attributes.position;
  // re-subdivide by displacing a fine ring mesh instead: use a plane for even detail
  const pl = new THREE.PlaneGeometry(r * 2, r * 2, 140, 140); pl.rotateX(-Math.PI / 2);
  const Q = pl.attributes.position;
  for (let i = 0; i < Q.count; i++) {
    const x = Q.getX(i), z = Q.getZ(i), d = Math.hypot(x, z);
    const h = 0.05 * Math.sin(x * 1.3) * Math.cos(z * 1.1) + 0.03 * Math.sin(x * 3.7 + z * 2.1);
    Q.setY(i, d > r ? -0.2 : Math.max(0.005, 0.04 + h) * smooth((r - d) / 1.5));
  }
  pl.computeVertexNormals();
  const m = new THREE.Mesh(pl, std('#e3e8ee', { roughness: 0.9 })); m.position.set(cx, 0, cz); m.receiveShadow = true; S.add(m);
}

function basket(S, x, z) {
  const g = new THREE.Group();
  const wick = std('#b08850', { roughness: 0.95 });
  const pts = []; for (let k = 0; k <= 24; k++) { const u = k / 24; pts.push(new THREE.Vector2(0.42 + 0.08 * u, 0.03 + 0.2 * u)); }
  const wall = new THREE.Mesh(new THREE.LatheGeometry(pts, 64), new THREE.MeshStandardMaterial({ color: '#b08850', roughness: 0.95, side: THREE.DoubleSide }));
  const W = wall.geometry.attributes.position;
  for (let i = 0; i < W.count; i++) { const a = Math.atan2(W.getZ(i), W.getX(i)), y = W.getY(i); const s = 1 + 0.02 * Math.sin(a * 48 + y * 60); W.setX(i, W.getX(i) * s); W.setZ(i, W.getZ(i) * s); }
  wall.geometry.computeVertexNormals(); g.add(wall);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.03, 16, 64), wick); rim.rotation.x = Math.PI / 2; rim.position.y = 0.23; g.add(rim);
  const floor = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.03, 64), wick); floor.position.y = 0.015; g.add(floor);
  // a rumpled blanket inside
  const bl = new THREE.PlaneGeometry(0.84, 0.84, 60, 60); bl.rotateX(-Math.PI / 2);
  const B = bl.attributes.position;
  for (let i = 0; i < B.count; i++) { const bx = B.getX(i), bz = B.getZ(i); const d = Math.hypot(bx, bz); B.setY(i, 0.05 + 0.025 * Math.sin(bx * 14) * Math.cos(bz * 11) + (d > 0.38 ? (d - 0.38) * 0.6 : 0)); if (d > 0.42) { B.setX(i, bx * 0.42 / d); B.setZ(i, bz * 0.42 / d); } }
  bl.computeVertexNormals();
  g.add(new THREE.Mesh(bl, std('#c96a5a', { roughness: 1, side: THREE.DoubleSide })));
  g.position.set(x, 0, z); S.add(shadowed(g));
  // a small rug under it
  const rug = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.0, 0.01, 64), std('#d9c7a0', { roughness: 1 })); rug.position.set(x, 0.005, z); rug.receiveShadow = true; S.add(rug);
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  world.ground(600); world.hills(12, 130);
  room(S, L);
  const { duvetTop } = bed(S, L);
  nightstand(S, L);

  // the wizard lying on his back: his up (y) runs along -x, his face (z) points at the ceiling
  const wiz = man();
  const basis = new THREE.Matrix4().makeBasis(new THREE.Vector3(0, 0, -1), new THREE.Vector3(-1, 0, 0), new THREE.Vector3(0, 1, 0));
  const tilt = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -0.1);     // head a little up on the pillow
  wiz.quaternion.setFromRotationMatrix(basis).premultiply(tilt);
  wiz.position.set(...L.wiz); S.add(wiz);
  // under the duvet only the head, hat, beard, hood and shoulders are ever seen: hide the rest so nothing pokes through
  wiz.traverse(o => { if (o.isMesh && (/^z_(staff|stone|fork|pouch|robe|belt|sleeve)/.test(o.name) || o.name === 'wizard')) o.visible = false; });
  const wom = woman(); wom.position.set(...L.woman); wom.rotation.y = L.woman_face; S.add(wom);
  // pure black never appears in the house style: lift near-black fabric and hair to a deep charcoal
  const lift = new THREE.Color('#3a3640').convertSRGBToLinear();
  for (const p of [wiz, wom]) p.traverse(o => {
    if (!o.isMesh) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || !m.color || m.isMeshBasicMaterial) continue;
      if (Math.max(m.color.r, m.color.g, m.color.b) < lift.r) { m.color.r = Math.max(m.color.r, lift.r); m.color.g = Math.max(m.color.g, lift.g); m.color.b = Math.max(m.color.b, lift.b); }
    }
  });

  // a soft warm fill from the front of the room so the woman's face and dark outfit read
  const fill = new THREE.PointLight('#ffd9b0', 1.6, 5.0, 2); fill.position.set(0.9, 2.1, 2.0); S.add(fill);
  // the dog across his feet
  const rex = dog(); rex.position.set(...L.dog); S.add(rex);

  // outside the window: trees in the dark garden and a big pale moon
  for (const [x, z, s] of [[-2.5, -6, 1.6], [2.8, -7.5, 1.9], [0.3, -11, 2.2], [5.5, -5.5, 1.5], [-6, -9, 2.0]]) world.roundTree(x, z, s);
  for (const [x, z, s] of [[-4, -5, 2.0], [4.5, -10, 2.4]]) world.conifer(x, z, s);
  const moon = new THREE.Mesh(new THREE.SphereGeometry(2.4, 48, 36), new THREE.MeshBasicMaterial({ color: '#f3f0e2' }));
  moon.position.set(6, 16, -60); S.add(moon);
  const moonGlow = new THREE.Mesh(new THREE.SphereGeometry(4.2, 32, 24), new THREE.MeshBasicMaterial({ color: '#9fb0d8', transparent: true, opacity: 0.15 }));
  moonGlow.position.copy(moon.position); S.add(moonGlow);

  // wolf family in a snowy clearing
  snowField(S, L.wolf[0], L.wolf[2], 9);
  for (const [dx, dz, s] of [[-3.2, -2.5, 2.2], [3.0, -3.5, 2.6], [-4.5, 1.5, 1.9], [4.2, 0.8, 2.3], [0.5, -5.5, 2.8], [-1.5, -4.8, 2.1], [6.5, -2, 2.4]])
    world.contactShadow(world.conifer(L.wolf[0] + dx, L.wolf[2] + dz, s), L.wolf[0] + dx, L.wolf[2] + dz, s * 0.7);
  const grey = { coat: '#8d8a84', light: '#dcd8cf', dark: '#55524d', iris: '#c99a3a', pointy: true };
  const wolves = [
    Object.assign(dog({ ...grey, scale: 1.3 }), { _p: [-0.45, 0, -0.2], _y: 0.5, _mode: 'lie' }),
    Object.assign(dog({ ...grey, coat: '#a39c90', scale: 1.22 }), { _p: [0.55, 0, -0.35], _y: -0.6, _mode: 'lie' }),
    Object.assign(dog({ ...grey, coat: '#9a958c', scale: 0.62 }), { _p: [0.05, 0, 0.35], _y: 0.2, _mode: 'curl' }),
    Object.assign(dog({ ...grey, coat: '#7d7a74', scale: 0.6 }), { _p: [-0.3, 0, 0.62], _y: 2.4, _mode: 'curl' }),
    Object.assign(dog({ ...grey, coat: '#a8a296', scale: 0.64 }), { _p: [0.45, 0, 0.5], _y: -0.3, _mode: 'lie' }),
  ];
  for (const w of wolves) { w.position.set(L.wolf[0] + w._p[0], 0.03, L.wolf[2] + w._p[2]); w.rotation.y = w._y; S.add(w); }

  // puppy pile in a basket
  basket(S, L.pups[0], L.pups[2]);
  const coats = [['#c9a77c', '#efe6d6', '#8a6a48'], ['#e6e3dc', '#f4efe6', '#b9a68a'], ['#6b5040', '#e6dccb', '#3e2c22'], ['#d9a066', '#f1e3cc', '#a2683a'], ['#b9bdc2', '#ece9e2', '#7f848a']];
  const pups = coats.map(([coat, light, dark], k) => {
    const p = dog({ coat, light, dark, scale: 0.42 + 0.03 * (k % 2) });
    const a = k * 1.25 + 0.3, r = k === 4 ? 0.0 : 0.2;
    p.position.set(L.pups[0] + Math.cos(a) * r, 0.06 + (k === 4 ? 0.06 : 0), L.pups[2] + Math.sin(a) * r);
    p.rotation.y = a + 1.6; S.add(p); return p;
  });

  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const v = new THREE.Vector3();
  const headLook = (person, target, maxYaw = 0.9) => {
    v.set(...target).sub(person.position);
    const yaw = Math.atan2(v.x, v.z) - person.rotation.y;
    const w = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    const pitch = -Math.atan2(target[1] - person.position.y - 1.5, Math.hypot(v.x, v.z));
    return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, w)), headPitch: Math.max(-0.3, Math.min(0.45, pitch)) };
  };
  const wizHead = [L.head[0], L.head[1] + 0.1, L.head[2]];
  const dogHead = [L.dog[0], L.dog[1] + 0.28, L.dog[2] + 0.3];
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(0.3, 0, 0),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      // the wizard: mouth follows his voice; head turns to the woman, lifts to look at the dog
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, headPitch: F.wiz_pitch[k], headYaw: F.wiz_yaw[k], headTilt: 0 });
      const camPos = world.camera.position.toArray();
      const lk = F.look_m[k], lm = headLook(wom, lk === 'camera' ? camPos : lk === 'dog' ? dogHead : wizHead);
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, ...lm, headTilt: 0.05 * Math.sin(t * 0.9 + 1) });
      // the dog: asleep on the feet; rolls over to face the wall near the end
      const turn = F.dog_turn[k];
      rex.rotation.y = 0.8 * Math.PI * turn;
      rex.position.set(L.dog[0] - 0.04 * Math.sin(Math.PI * turn), L.dog[1] + 0.06 * Math.sin(Math.PI * turn), L.dog[2] - 0.12 * turn);
      rex.pose({ mode: F.dog_mode[k], t, pitch: F.dog_pitch[k], yaw: F.dog_yaw[k], rest: F.dog_rest[k], blink: F.dog_blink[k],
                 mouth: F.dog_mouth[k], ears: F.dog_ears[k], tail: F.dog_tail[k], breath: 1, breathRate: 1.2 });
      // wolves rest; one parent lifts its head, the pups breathe
      const wt = F.wolf[k];
      wolves.forEach((w, q) => w.pose({ mode: w._mode, t: t + q * 1.7, pitch: q === 0 ? 0.1 - 0.15 * Math.min(1, wt / 1.5) : 0.25, rest: q === 0 ? 0.0 : (q === 1 ? 0.6 : 1.0),
                                        blink: q === 0 ? 0 : 1, ears: 0.3, breathRate: 1.5 + 0.3 * q }));
      pups.forEach((p, q) => p.pose({ mode: q === 4 ? 'lie' : 'curl', t: t + q, blink: 1, rest: 1, pitch: 0.2, breath: 1.4, breathRate: 2.2 + 0.2 * q }));
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i);
        world.setLighting(shot.lighting ?? 'moonroom', new THREE.Vector3(fp[0], 0, fp[2]));
        if (plan.bloom_threshold && shot.lighting === 'moonroom') world.bloom.threshold = plan.bloom_threshold;
        const sc = world.sun.shadow.camera, e2 = shot.lighting === 'moonroom' ? 5 : 10;
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.far = 80; sc.updateProjectionMatrix();
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.05, Math.max(0.005, d * 0.02)); world.camera.far = 500; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const fp = focalPt(i);
      const ent = Math.abs(fp[0] - L.wolf[0]) < 10 ? 'wolves' : Math.abs(fp[0] - L.pups[0]) < 10 ? 'puppies' : 'dog';
      return [{ entity: ent, part: 'subject', kind: 'thickness', p: fp, size: 0.25 }];
    },
    vars() { return {}; },
  };
}

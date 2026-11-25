// Reusable set (CLAUDE.md "Autopilot efficiency": a polar / snow set). A sunny Antarctic ice shelf at real
// scale (metres): a wide snow plain with faceted wind ridges (sastrugi), the shelf edge as a low ice cliff
// with dark sea and a few icebergs beyond it (z < EDGE_Z), low rocky mountains with snow caps on the horizon,
// and props at the section 11 budget: penguins that waddle, a small red research hut with an antenna and flag,
// and a tent. The snow is not a world.ground() mesh, so Look v3 grass never grows on it.
//
//   import { ice, penguin, hut, EDGE_Z } from '../sets/ice.js';
//   const I = ice(world, { far: 9000 });        // per frame: I.update(t, world.camera)
//   const p = penguin(1.0); p.position.set(3, 0, 40); scene.add(p); p.waddle(t);
//
// Big scenes (a 200 m giant): call I.update(...) every frame; it keeps the far plane and the sky dome large
// enough for kilometre views and sets the fog for the shot's distance (I.fogFor(distance)).
import * as THREE from 'three';

export const EDGE_Z = -700;          // the ice shelf ends here; open sea beyond (z < EDGE_Z)
const flat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.9, flatShading: true, ...x });
const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };
const seeded = s => () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
export const SNOW = '#e8edf2', SNOW_SHADE = '#c9d5e2', ICE_BLUE = '#9fc3dc', SEA = '#1b2b3b';

// gentle snow height: long wind ridges plus small bumps (metres); flat (0) inside keepFlat circles
export function snowY(x, z, keep = []) {
  let h = 0.35 * Math.sin(x * 0.021 + z * 0.006) * Math.sin(z * 0.017 - x * 0.004)
        + 0.12 * Math.sin(x * 0.13 + z * 0.05) + 0.06 * Math.sin(z * 0.31 + x * 0.11);
  for (const [cx, cz, r] of keep) {
    const d = Math.hypot(x - cx, z - cz);
    if (d < r) h *= Math.min(1, Math.max(0, (d - r * 0.6) / (r * 0.4)));
  }
  return h;
}

export function ice(world, opt = {}) {
  const S = world.scene, R = seeded(opt.seed ?? 23), keep = opt.keepFlat ?? [];
  const FAR = opt.far ?? 9000;
  // the snow plain: fine near the action (faceted ridges read as sastrugi), coarse further out
  const mk = (size, seg, cx, cz) => {
    const g = new THREE.PlaneGeometry(size, size, seg, seg); g.rotateX(-Math.PI / 2);
    const p = g.attributes.position, col = [];
    const c1 = new THREE.Color(SNOW), c2 = new THREE.Color(SNOW_SHADE), c = new THREE.Color();
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i) + cx, z = p.getZ(i) + cz;
      p.setY(i, z < EDGE_Z ? -40 : snowY(x, z, keep));
      c.copy(c1).lerp(c2, 0.25 + 0.25 * Math.sin(x * 0.011 + z * 0.007) * Math.sin(z * 0.013));
      col.push(c.r, c.g, c.b);
    }
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.computeVertexNormals();
    const m = new THREE.Mesh(g, flat('#ffffff', { vertexColors: true, roughness: 0.95 }));
    m.position.set(cx, 0, cz); m.receiveShadow = true; m.userData.noVariation = false; S.add(m); return m;
  };
  const near = mk(1200, 300, 0, -100);
  const nearHalf = 600;
  // outer ring of coarse snow (four slabs around the fine square)
  const outer = [];
  for (const [cx, cz, w, d] of [[0, -100 - nearHalf - 3000, 14000, 6000], [0, -100 + nearHalf + 3000, 14000, 6000],
                                  [-nearHalf - 3000, -100, 6000, 1200], [nearHalf + 3000, -100, 6000, 1200]]) {
    const g = new THREE.PlaneGeometry(w, d, 70, 30); g.rotateX(-Math.PI / 2);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { const x = p.getX(i) + cx, z = p.getZ(i) + cz; p.setY(i, z < EDGE_Z ? -40 : snowY(x, z) * 2 - 0.05); }
    g.computeVertexNormals();
    const m = new THREE.Mesh(g, flat(SNOW, { roughness: 0.95 })); m.position.set(cx, 0, cz); m.receiveShadow = true; S.add(m); outer.push(m);
  }
  // the shelf edge: a low ice cliff (blue-white, faceted) along z = EDGE_Z, the sea below and beyond
  const cliffG = new THREE.PlaneGeometry(14000, 44, 700, 6);
  const cp = cliffG.attributes.position;
  for (let i = 0; i < cp.count; i++) { const x = cp.getX(i); cp.setZ(i, 3 * Math.sin(x * 0.05) + 1.5 * Math.sin(x * 0.23) + (R() - 0.5) * 1.2); }
  cliffG.computeVertexNormals();
  const cliff = new THREE.Mesh(cliffG, flat(ICE_BLUE, { roughness: 0.4 })); cliff.position.set(0, -18, EDGE_Z); S.add(cliff);
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(16000, 8000), std(SEA, { roughness: 0.25, metalness: 0.1 }));
  sea.rotation.x = -Math.PI / 2; sea.position.set(0, -36, EDGE_Z - 4000); S.add(sea);
  sea.material.userData.noVariation = true;
  // icebergs: flat-topped faceted slabs out on the sea
  for (let k = 0; k < 9; k++) {
    const g = new THREE.IcosahedronGeometry(1, 2), p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { const y = p.getY(i); p.setY(i, y > 0.35 ? 0.35 + (y - 0.35) * 0.15 : y); }
    g.computeVertexNormals();
    const b = new THREE.Mesh(g, flat(k % 3 ? '#eef4f8' : '#d4e6f1', { roughness: 0.5 }));
    const s = 40 + R() * 120; b.scale.set(s * (1 + R()), s * 0.45, s * (0.7 + R() * 0.6));
    b.position.set((R() - 0.5) * 9000, -36 + s * 0.05, EDGE_Z - 600 - R() * 3500); b.rotation.y = R() * 3; S.add(b);
  }
  // low mountains (nunataks) on the horizon: dark rock with snow caps, to the sides and behind
  const rock = flat('#4f4a47'), cap = flat('#f1f4f7');
  for (let k = 0; k < 14; k++) {
    const a = (k / 14) * Math.PI * 1.4 + Math.PI * 0.8 + R() * 0.15;          // a wide arc away from the sea
    const r = 4200 + R() * 1800, h = 300 + R() * 650, w = h * (1.6 + R() * 1.4);
    const g = new THREE.ConeGeometry(w, h, 16, 6); const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { const y = p.getY(i); if (y < h / 2 - 1) { p.setX(i, p.getX(i) * (0.85 + R() * 0.3)); p.setZ(i, p.getZ(i) * (0.85 + R() * 0.3)); } }
    g.computeVertexNormals();
    const m = new THREE.Mesh(g, rock); const x = Math.sin(a) * r, z = Math.cos(a) * r;
    m.position.set(x, h / 2 - 30, z); S.add(m);
    const cg = new THREE.ConeGeometry(w * 0.42, h * 0.42, 16, 2); const c = new THREE.Mesh(cg, cap);
    c.position.set(x, h - h * 0.21 - 30 + 1, z); S.add(c);
  }

  const sky = world.skyDome, fog = S.fog;
  const I = {
    near, outer, cliff, sea,
    fogFor(dist) { fog.near = Math.max(120, dist * 3); fog.far = Math.max(2600, dist * 14); },
    update(t, camera) {
      if (camera.far < FAR) { camera.far = FAR; camera.updateProjectionMatrix(); }
      sky.scale.setScalar(FAR / 330);
    },
  };
  world.camera.far = FAR;
  return I;
}

// ---------- props ----------

// an original low-poly penguin about `h` metres tall (default 1.0): dark back, white front, a pale yellow
// throat patch, orange-black beak, flippers and feet. waddle(t, amount) rocks it side to side.
export function penguin(h = 1.0, seed = 1) {
  const g = new THREE.Group(), body = new THREE.Group(); g.add(body);
  const dark = std('#23262d', { roughness: 0.55 }), white = std('#eef0ec', { roughness: 0.6 }),
        yel = std('#e9cf7a', { roughness: 0.6 }), beakM = std('#1d1d1f'), orange = std('#e08a3a'), foot = std('#3a3532');
  const prof = [[0, 0.0], [0.04, 0.19], [0.2, 0.25], [0.45, 0.24], [0.66, 0.19], [0.78, 0.14], [0.82, 0.0]];
  const curve = new THREE.SplineCurve(prof.map(([y, r]) => new THREE.Vector2(r, y)));
  const back = new THREE.Mesh(new THREE.LatheGeometry(curve.getPoints(24), 32), dark); body.add(back);
  // the white front: a slightly larger half-lathe facing +z
  const fr = new THREE.Mesh(new THREE.LatheGeometry(curve.getPoints(24).map(v => new THREE.Vector2(v.x * 1.015, v.y)), 24, -Math.PI * 0.42, Math.PI * 0.84), white);
  fr.scale.y = 0.93; body.add(fr);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.13, 24, 16), dark); head.position.set(0, 0.86, 0.01); head.scale.set(1, 1.05, 1.1); body.add(head);
  for (const s of [-1, 1]) {
    const patch = new THREE.Mesh(new THREE.SphereGeometry(0.05, 24, 16), yel); patch.position.set(s * 0.09, 0.8, 0.06); patch.scale.set(0.6, 1.3, 0.5); body.add(patch);
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.014, 16, 12), std('#0c0c0e')); eye.position.set(s * 0.065, 0.9, 0.1); body.add(eye);
    const fl = new THREE.Mesh(new THREE.SphereGeometry(0.1, 24, 16), dark); fl.scale.set(0.18, 1.6, 0.55); fl.position.set(s * 0.235, 0.47, -0.01); fl.rotation.z = s * 0.2; body.add(fl);
    const ft = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 12), foot); ft.scale.set(1, 0.3, 1.6); ft.position.set(s * 0.08, 0.012, 0.07); g.add(ft);
  }
  const beak = new THREE.Mesh(new THREE.ConeGeometry(0.03, 0.14, 16), beakM); beak.rotation.x = Math.PI / 2 + 0.25; beak.position.set(0, 0.86, 0.16); body.add(beak);
  const stripe = new THREE.Mesh(new THREE.ConeGeometry(0.031, 0.07, 16), orange); stripe.rotation.x = Math.PI / 2 + 0.25; stripe.position.set(0, 0.855, 0.125); body.add(stripe);
  g.scale.setScalar(h);
  const ph = (seed * 1.37) % 6.28;
  g.waddle = (t, a = 1) => { body.rotation.z = 0.07 * a * Math.sin(t * 5.5 + ph); body.position.y = 0.01 * a * Math.abs(Math.sin(t * 5.5 + ph)); head.rotation.y = 0.3 * Math.sin(t * 0.7 + ph); };
  return shadowed(g);
}

// a small red research hut on skids with a white roof, a door, a window, an antenna and a flag pole
export function hut() {
  const g = new THREE.Group();
  const red = flat('#b8352f', { flatShading: false, roughness: 0.7 }), white = flat('#e7e4dc'), grey = std('#6b7076'), win = std('#2b3038', { roughness: 0.2, metalness: 0.1 });
  const box = new THREE.Mesh(new THREE.BoxGeometry(4.2, 2.4, 2.8), red); box.position.y = 1.55; g.add(box);
  const roof = new THREE.Mesh(new THREE.CylinderGeometry(1.55, 1.55, 4.4, 24, 1, false, 0, Math.PI), white);
  roof.rotation.z = Math.PI / 2; roof.rotation.y = Math.PI / 2; roof.scale.set(1, 1, 0.42); roof.position.y = 2.75; g.add(roof);
  for (const s of [-1, 1]) { const sk = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.2, 0.2), grey); sk.position.set(0, 0.2, s * 1.1); g.add(sk);
    for (const x of [-1.6, 1.6]) { const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.25, 16), grey); leg.position.set(x, 0.38, s * 1.1); g.add(leg); } }
  const door = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.7, 0.05), flat('#8e2a25')); door.position.set(-1.0, 1.25, 1.42); g.add(door);
  const w = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.6, 0.05), win); w.position.set(0.8, 1.9, 1.42); g.add(w);
  const ant = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 3.2, 16), grey); ant.position.set(1.6, 4.4, -0.8); g.add(ant);
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 4.5, 16), grey); pole.position.set(-3.2, 2.25, 0.6); g.add(pole);
  const flagG = new THREE.PlaneGeometry(1.1, 0.65, 12, 4); flagG.translate(0.55, 0, 0);
  const flag = new THREE.Mesh(flagG, std('#e2c45a', { side: THREE.DoubleSide, roughness: 0.8 })); flag.position.set(-3.2, 4.15, 0.6); g.add(flag);
  const fp = flagG.attributes.position, fx = Float32Array.from({ length: fp.count }, (_, i) => fp.getX(i));
  g.wave = t => { for (let i = 0; i < fp.count; i++) fp.setZ(i, 0.12 * fx[i] * Math.sin(t * 6 - fx[i] * 4)); fp.needsUpdate = true; flagG.computeVertexNormals(); };
  return shadowed(g);
}

// a small dome tent (orange) with guy lines
export function tent(color = '#d9813a') {
  const g = new THREE.Group();
  const m = new THREE.Mesh(new THREE.SphereGeometry(1.2, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), flat(color, { flatShading: false }));
  m.scale.set(1.3, 0.85, 1); g.add(m);
  const door = new THREE.Mesh(new THREE.CircleGeometry(0.45, 24, 0, Math.PI), flat('#5a3a22')); door.position.set(0, 0.0, 1.0); door.rotation.x = -0.25; g.add(door);
  return shadowed(g);
}

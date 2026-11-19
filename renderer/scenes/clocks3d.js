// Your head is older than your feet (content/episodes/head-ages-faster/plan.py).
// One small diorama world: a faceless wooden toy figure beside a post with a clock at head height and one at
// its feet, a mast with clocks at four heights, two atomic clocks on tables (one jacked up 33 cm), and a road
// with a car under a toy GPS satellite. Clock readings, the lift, the car and the map pin all come from the
// plan's frames; this file only draws them. Pulses ("ticks") are rings that expand once per displayed second.
import * as THREE from 'three';
import { PALETTE } from '../world.js';
import { car as makeCar } from '../props.js';
import { MAT, haloSprite } from '../materials.js';

const flat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, flatShading: true, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };
const RED = '#ff3b30';

// An analogue clock facing +z: cream face, dark rim, 12 marks, hour/minute hands and a red second hand,
// plus a thin pulse ring that expands once per displayed second.
function makeClock(r, opts = {}) {
  const g = new THREE.Group();
  const rim = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.12, r * 1.12, r * 0.22, 32), flat('#2d2a27', { flatShading: false, roughness: 0.5 }));
  rim.rotation.x = Math.PI / 2; g.add(rim);
  const face = new THREE.Mesh(new THREE.CircleGeometry(r, 40), new THREE.MeshStandardMaterial({ color: '#efe9da', roughness: 0.6 }));
  face.position.z = r * 0.115; g.add(face);
  const mk = flat('#2b2b2b');
  for (let k = 0; k < 12; k++) {
    const a = k / 12 * Math.PI * 2, big = k % 3 === 0;
    const m = new THREE.Mesh(new THREE.BoxGeometry(r * (big ? 0.07 : 0.04), r * (big ? 0.2 : 0.12), r * 0.02), mk);
    m.position.set(Math.sin(a) * r * 0.82, Math.cos(a) * r * 0.82, r * 0.125); m.rotation.z = -a; g.add(m);
  }
  const hand = (len, w, col, z) => {
    const p = new THREE.Group(); p.position.z = z;
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, len, r * 0.02), flat(col)); m.position.y = len / 2 - len * 0.12; p.add(m);
    g.add(p); return p;
  };
  const hourH = hand(r * 0.5, r * 0.09, '#2b2b2b', r * 0.13), minH = hand(r * 0.78, r * 0.06, '#2b2b2b', r * 0.14);
  const secH = hand(r * 0.86, r * 0.03, PALETTE.red, r * 0.15);
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.07, r * 0.07, r * 0.05, 12), flat(PALETTE.red));
  hub.rotation.x = Math.PI / 2; hub.position.z = r * 0.16; g.add(hub);
  const ringM = new THREE.MeshBasicMaterial({ color: opts.ring ?? RED, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
  const ring = new THREE.Mesh(new THREE.RingGeometry(r * 1.0, r * 1.08, 48), ringM); ring.position.z = r * 0.05; g.add(ring);
  const halo = haloSprite(opts.halo ?? '#ffd9a8', r * 4.5, 0); g.add(halo);
  shadowed(g); ring.castShadow = false; halo.castShadow = false;
  g.set = (sec, prevSec, glow = 0) => {
    const fast = sec - prevSec > 0.3;                      // time-lapse: second hand would strobe, hide it
    secH.visible = !fast;
    secH.rotation.z = -((sec % 60) / 60) * Math.PI * 2;
    minH.rotation.z = -((sec / 60) % 60) / 60 * Math.PI * 2;
    hourH.rotation.z = -((sec / 3600) % 12) / 12 * Math.PI * 2;
    const fr = fast ? 1 : sec % 1;
    ring.scale.setScalar(1 + 0.75 * fr); ringM.opacity = fast ? 0 : 0.8 * (1 - fr) ** 2;
    halo.material.opacity = 0.35 * glow;
  };
  return g;
}

// Faceless wooden toy figure (artist's mannequin), 1.75 m tall, facing +z.
function figure() {
  const g = new THREE.Group(), w = MAT.wood('#c9a77c'), j = flat('#a8865e');
  const cap = (r, len, x, y, z, rx = 0, rz = 0, m = w) => {
    const c = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 4, 10), m); c.position.set(x, y, z); c.rotation.set(rx, 0, rz); g.add(c); return c;
  };
  const ball = (r, x, y, z, m = j) => { const b = new THREE.Mesh(new THREE.SphereGeometry(r, 12, 10), m); b.position.set(x, y, z); g.add(b); return b; };
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.105, 18, 14), w); head.scale.set(0.9, 1.15, 0.95); head.position.y = 1.62; g.add(head);
  cap(0.04, 0.06, 0, 1.47, 0);                         // neck
  cap(0.16, 0.26, 0, 1.2, 0); ball(0.13, 0, 0.98, 0);  // chest, pelvis
  for (const s of [-1, 1]) {
    ball(0.05, s * 0.21, 1.36, 0);                                     // shoulder
    cap(0.042, 0.22, s * 0.25, 1.17, 0.0, 0, s * 0.12);                 // upper arm
    ball(0.04, s * 0.28, 1.0, 0.02);
    cap(0.036, 0.2, s * 0.29, 0.84, 0.04, -0.1, s * 0.04);              // forearm
    cap(0.035, 0.07, s * 0.3, 0.68, 0.06, 0, 0);                        // hand
    ball(0.055, s * 0.09, 0.9, 0);
    cap(0.058, 0.3, s * 0.095, 0.68, 0, 0, 0);                          // thigh
    ball(0.05, s * 0.095, 0.47, 0.01);
    cap(0.048, 0.28, s * 0.095, 0.27, 0, 0, 0);                         // shin
    const foot = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.06, 0.24), w); foot.position.set(s * 0.095, 0.03, 0.05); g.add(foot);
  }
  return shadowed(g);
}

// toy GPS satellite: gold body, two blue solar wings, a dish
function satellite() {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(new THREE.BoxGeometry(2.2, 2.2, 3.0), MAT.anodised('#c9a24a')));
  const pm = new THREE.MeshStandardMaterial({ color: '#2f4f86', roughness: 0.35, metalness: 0.4 });
  for (const s of [-1, 1]) {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.15, 0.15), MAT.brushedSteel()); arm.position.x = s * 1.8; g.add(arm);
    const p = new THREE.Mesh(new THREE.BoxGeometry(5.0, 2.0, 0.08), pm); p.position.x = s * 4.9; g.add(p);
  }
  const dish = new THREE.Mesh(new THREE.ConeGeometry(0.9, 0.5, 16, 1, true), MAT.ceramic()); dish.position.y = -1.4; dish.rotation.x = Math.PI; g.add(dish);
  return g;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  world.camera.far = 500; world.camera.updateProjectionMatrix();
  world.ground(900); world.hills(12, 160); world.hills(14, 260);

  // ---- the figure on a small round patio, and the clock post beside it
  const patio = new THREE.Mesh(new THREE.CylinderGeometry(1.7, 1.75, 0.06, 40), MAT.concrete('#a89684'));
  patio.position.y = 0.03; patio.receiveShadow = true; S.add(patio);
  const fig = figure(); fig.position.set(...L.fig); S.add(fig);
  const post = new THREE.Mesh(new THREE.BoxGeometry(0.07, 1.75, 0.07), MAT.wood('#8a6a48'));
  post.position.set(L.post_x, 0.9, 0.05); post.castShadow = post.receiveShadow = true; S.add(post);
  const headClk = makeClock(0.13, { halo: '#ffc58a' }); headClk.position.set(...L.head_clk); S.add(headClk);
  const feetClk = makeClock(0.13, { halo: '#a9c4ff' }); feetClk.position.set(...L.feet_clk); S.add(feetClk);

  // ---- the mast with four clocks
  const [tx, , tz] = L.tower;
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.45, 25, 8), MAT.concrete('#beb7a4'));
  mast.position.set(tx, 12.5, tz); mast.castShadow = mast.receiveShadow = true; S.add(mast);
  const towerClks = L.tower_ys.map(y => { const c = makeClock(1.3); c.position.set(tx, y, tz + 0.6); S.add(c); return c; });
  const base = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.5, 0.3, 16), MAT.concrete('#a89684')); base.position.set(tx, 0.15, tz); base.receiveShadow = true; S.add(base);

  // ---- the two atomic clocks on wooden tables; the left table can jack up
  const [lx, , lz] = L.lab;
  const tables = [], clocksA = [];
  for (const s of [-1, 1]) {
    const tg = new THREE.Group(); tg.position.set(lx + s * L.table_dx, 0, lz);
    const top = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.05, 0.6), MAT.wood('#9a7650')); top.position.y = L.table_top - 0.025; tg.add(top);
    const legs = [];
    for (const [x, z] of [[-0.35, -0.25], [0.35, -0.25], [-0.35, 0.25], [0.35, 0.25]]) {
      const leg = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1, 0.05), MAT.wood('#7a5c3c')); leg.position.set(x, 0, z); tg.add(leg); legs.push(leg);
    }
    const box = new THREE.Group();
    const shell = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.3, 0.34), MAT.ceramic('#e6e3dc')); shell.position.y = 0.15; box.add(shell);
    const win = new THREE.Mesh(new THREE.CircleGeometry(0.07, 20), flat('#1d2230')); win.position.set(0, 0.16, 0.171); box.add(win);
    const ion = new THREE.Mesh(new THREE.SphereGeometry(0.018, 12, 10), MAT.emissive('#8f7cff', 3)); ion.position.set(0, 0.16, 0.175); box.add(ion);
    const ringM = new THREE.MeshBasicMaterial({ color: '#b9adff', transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.075, 0.085, 32), ringM); ring.position.set(0, 0.16, 0.176); box.add(ring);
    box.position.y = L.table_top; tg.add(box);
    S.add(shadowed(tg)); ring.castShadow = false;
    tables.push({ g: tg, top, legs, box }); clocksA.push({ ion, ring, ringM });
  }

  // ---- road, car, map pin and the satellite
  const rx = L.road_x, len = 900, zc = -350;
  const lay = (m, k) => { m.polygonOffset = true; m.polygonOffsetFactor = -k; m.polygonOffsetUnits = -k; return m; };
  const plane = (w, l, mat, x, y) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, l), mat); m.rotation.x = -Math.PI / 2; m.position.set(x, y, zc); m.receiveShadow = true; S.add(m); return m; };
  plane(7.2, len, lay(new THREE.MeshStandardMaterial({ color: PALETTE.asphaltDay, roughness: 0.95 }), 1), rx, 0.02);
  const mk = lay(new THREE.MeshStandardMaterial({ color: PALETTE.marking, roughness: 0.8 }), 2);
  for (const x of [-3.35, 3.35]) plane(0.15, len, mk, rx + x, 0.03);
  for (let z = 90; z > -800; z -= 9) { const d = new THREE.Mesh(new THREE.PlaneGeometry(0.14, 3), mk); d.rotation.x = -Math.PI / 2; d.position.set(rx, 0.031, z); S.add(d); }
  for (const s of [-1, 1]) { const k = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.1, len), lay(flat(PALETTE.concrete), 1)); k.position.set(rx + s * 4.6, 0.05, zc); k.receiveShadow = true; S.add(k); }
  const hero = makeCar('#8fa6c8', 'estate', true); S.add(hero);
  const others = [];
  for (let k = 0; k < 6; k++) { const c = makeCar(PALETTE.cars[k % PALETTE.cars.length], ['hatch', 'sedan', 'estate'][k % 3]); c.rotation.y = Math.PI; S.add(c); others.push(c); }
  const ringMat = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.9, depthWrite: false });
  const trueRing = new THREE.Mesh(new THREE.RingGeometry(2.6, 2.8, 48), ringMat); trueRing.rotation.x = -Math.PI / 2; S.add(trueRing);
  const pin = new THREE.Group();
  const pinM = MAT.emissive('#c92a2e', 0.6);
  const pinHead = new THREE.Mesh(new THREE.SphereGeometry(1.0, 16, 12), pinM); pinHead.position.y = 3.6; pin.add(pinHead);
  const pinTip = new THREE.Mesh(new THREE.ConeGeometry(0.75, 2.4, 16), pinM); pinTip.rotation.x = Math.PI; pinTip.position.y = 2.0; pin.add(pinTip);
  const pinRing = new THREE.Mesh(new THREE.RingGeometry(2.0, 2.3, 48), new THREE.MeshBasicMaterial({ color: RED, transparent: true, opacity: 0.85, depthWrite: false }));
  pinRing.rotation.x = -Math.PI / 2; pinRing.position.y = 0.06; pin.add(pinRing);
  shadowed(pin); pinRing.castShadow = false; S.add(pin);
  const sat = satellite(); sat.scale.setScalar(1.9); S.add(sat);

  // ---- sparse trees and a couple of props, clear of the sets and the road
  const clear = (x, z) => Math.hypot(x, z) < 6 || Math.hypot(x - tx, z - tz) < 5 || Math.hypot(x - lx, z - lz) < 4 || Math.abs(x - rx) < 8;
  for (let i = 0; i < 70; i++) {
    const x = -60 + world.rand() * 110, z = -120 + world.rand() * 140;
    if (clear(x, z)) continue;
    const s = 0.9 + world.rand() * 1.1;
    const t = world.rand() < 0.35 ? world.conifer(x, z, s * 1.1) : world.roundTree(x, z, s);
    world.contactShadow(t, x, z, s);
  }

  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(0, 0, 0),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.head.length - 1), p = Math.max(0, k - 1);
      headClk.set(F.head[k], F.head[p], F.warm[k]);
      feetClk.set(F.feet[k], F.feet[p], F.warm[k] * 0.8);
      towerClks.forEach((c, j) => c.set(F.tower[k][j], F.tower[p][j], 0));
      // atomic clocks: the left table rises by frames.lift (legs stretch: a jack under the top)
      const lift = F.lift[k];
      const tl = tables[0];
      tl.top.position.y = L.table_top - 0.025 + lift; tl.box.position.y = L.table_top + lift;
      for (const tb of tables) for (const leg of tb.legs) { const h = tb.top.position.y; leg.scale.y = h; leg.position.y = h / 2; }
      clocksA.forEach((c, j) => { const fr = F.lab[k][j] % 1; c.ring.scale.setScalar(1 + 1.3 * fr); c.ringM.opacity = 0.9 * (1 - fr) ** 2; c.ion.material.emissiveIntensity = 2 + 3 * (1 - fr) ** 4; });
      // the hero car drives towards -z in the right-hand lane; oncoming cars in the other lane
      const cz = F.car_z[k];
      hero.position.set(rx - 1.8, 0, cz); trueRing.position.set(rx - 1.8, 0.05, cz);
      others.forEach((c, j) => c.position.set(rx + 1.8, 0, -80 - 70 * j - 330 + 11.0 * t));
      const off = F.pin[k];
      pin.position.set(rx - 1.8 + off * 0.12, 0, cz - 8 - off);
      pin.visible = t >= plan.timing.day[0] - 0.4;
      trueRing.visible = pin.visible;
      sat.position.set(rx + L.sat[0] - L.road_x, L.sat[1], cz + L.sat[2]);
      sat.rotation.set(0.15, 0.3 + t * 0.02, 0.08);
      // the sun's shadow box follows the subject of each shot, sized to it
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i), big = fp[1] > 4 || shot.lighting === 'key' && Math.abs(fp[0] - rx) < 12;
        const c = new THREE.Vector3(fp[0], 0, fp[2]);
        world.setLighting(shot.lighting ?? 'key', c);
        const sc = world.sun.shadow.camera, e = big ? 30 : 6;
        sc.left = -e; sc.right = e; sc.top = e; sc.bottom = -e; sc.far = 120; sc.updateProjectionMatrix();
      }
      if (Math.abs(focalPt(i)[0] - rx) < 12) {            // road shots: keep the shadow box on the moving car
        const c = new THREE.Vector3(rx, 0, cz);
        world.sun.target.position.copy(c);
        const d = world.sun.position.clone().sub(world.sun.target.position);
        world.sun.position.copy(c).add(d.setLength(30));
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.1, Math.max(0.02, d * 0.02)); world.camera.far = 500; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const t = i / plan.fps, tm = plan.timing;
      if (t >= tm.day[0] - 0.3) {
        const cz = F.car_z[Math.min(i, F.car_z.length - 1)];
        return [{ entity: 'car', part: 'car length', kind: 'thickness', p: [rx - 1.8, 0.7, cz], size: 4.2 }];
      }
      return [{ entity: 'clocks', part: 'clock face', kind: 'thickness', p: focalPt(i), size: 0.26 }];
    },
    vars(i) { return {}; },
  };
}

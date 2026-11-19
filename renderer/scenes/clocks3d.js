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

// A small dark display plate with a label and a value (canvas texture), e.g. "HEAD 0:17.2".
function readout(label, w = 0.34, h = 0.13, dark = false) {
  const c = document.createElement('canvas'); c.width = 512; c.height = 196; const g = c.getContext('2d');
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
  let last = null;
  m.setText = v => {
    if (v === last) return; last = v;
    g.clearRect(0, 0, 512, 196);
    g.fillStyle = dark ? '#1b1f24' : '#e5e2d6'; g.beginPath(); g.roundRect(4, 4, 504, 188, dark ? 14 : 30); g.fill();
    g.fillStyle = dark ? '#9aa3ab' : '#6d675c'; g.font = '700 50px Poppins'; g.textAlign = 'center'; g.textBaseline = 'top'; g.fillText(label, 256, 14);
    g.fillStyle = dark ? '#ff6a5c' : '#c92a2e'; g.font = '800 86px Poppins'; g.fillText(v ?? '', 256, 70);
    tex.needsUpdate = true;
  };
  return m;
}

// Faceless wooden toy figure (artist's mannequin), 1.75 m tall, facing +z.
function figure() {
  const g = new THREE.Group(), w = MAT.wood('#c9a77c'), j = flat('#a8865e');
  const cap = (r, len, x, y, z, rx = 0, rz = 0, m = w) => {
    const c = new THREE.Group(); c.position.set(x, y, z); c.rotation.set(rx, 0, rz);
    c.add(new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 12, 1, true), m));
    for (const e of [-1, 1]) { const cap = new THREE.Mesh(new THREE.IcosahedronGeometry(r, 1), m); cap.position.y = e * len / 2; c.add(cap); }
    g.add(c); return c;
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
  // gold-foil body: a faceted box with a darker band and a silver top deck
  const foil = new THREE.MeshStandardMaterial({ color: '#c99a3a', roughness: 0.7, metalness: 0.2, flatShading: true });
  const body = new THREE.Mesh(new THREE.CylinderGeometry(1.25, 1.25, 3.0, 8), foil); body.rotation.x = Math.PI / 2; g.add(body);
  const band = new THREE.Mesh(new THREE.CylinderGeometry(1.28, 1.28, 0.5, 8), flat('#6b5a2e')); band.rotation.x = Math.PI / 2; g.add(band);
  const deck = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.6, 0.2), flat('#a9aeb3', { roughness: 0.8 })); deck.position.z = 1.6; g.add(deck);
  for (const [x, y] of [[0.5, 0.5], [-0.5, 0.4], [0.2, -0.6]]) {   // antenna rods
    const a = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.6, 6), flat('#a9aeb3', { roughness: 0.8 })); a.rotation.x = Math.PI / 2; a.position.set(x, y, -2.3); g.add(a);
  }
  // solar wings: blue cells in a grid with silver frames
  const pm = new THREE.MeshStandardMaterial({ color: '#2f4f86', roughness: 0.6, metalness: 0.2, emissive: '#1c2f55', emissiveIntensity: 0.25 });
  const frame = flat('#a9aeb3', { roughness: 0.8 });
  for (const s of [-1, 1]) {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.15, 0.15), frame); arm.position.x = s * 1.9; g.add(arm);
    for (let c = 0; c < 3; c++) {
      const p = new THREE.Mesh(new THREE.BoxGeometry(1.55, 2.0, 0.08), pm); p.position.x = s * (3.4 + c * 1.65); g.add(p);
    }
  }
  const dish = new THREE.Mesh(new THREE.ConeGeometry(0.9, 0.5, 16, 1, true), MAT.ceramic()); dish.position.y = -1.4; dish.rotation.x = Math.PI; g.add(dish);
  return g;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  world.camera.far = 500; world.camera.updateProjectionMatrix();
  world.ground(2400); world.hills(12, 160); world.hills(14, 260);

  // ---- the figure on a small round patio, and the clock post beside it
  const patio = new THREE.Mesh(new THREE.CylinderGeometry(1.7, 1.75, 0.06, 40), MAT.concrete('#a89684'));
  patio.position.y = 0.03; patio.receiveShadow = true; S.add(patio);
  const fig = figure(); fig.position.set(...L.fig); S.add(fig);
  const post = new THREE.Mesh(new THREE.BoxGeometry(0.07, 1.75, 0.07), MAT.wood('#8a6a48'));
  post.position.set(L.post_x, 0.9, 0.05); post.castShadow = post.receiveShadow = true; S.add(post);
  const headClk = makeClock(0.13, { halo: '#ffc58a' }); headClk.position.set(...L.head_clk); S.add(headClk);
  const feetClk = makeClock(0.13, { halo: '#a9c4ff' }); feetClk.position.set(...L.feet_clk); S.add(feetClk);
  const headRd = readout('HEAD', 0.48, 0.18), feetRd = readout('FEET', 0.48, 0.18);
  headRd.position.set(L.head_clk[0] + 0.42, L.head_clk[1], L.head_clk[2] + 0.02);
  feetRd.position.set(L.feet_clk[0] + 0.42, L.feet_clk[1], L.feet_clk[2] + 0.02);
  S.add(headRd, feetRd);
  const figSet = [patio, fig, post, headClk, feetClk];

  // ---- the mast with four clocks
  const [tx, , tz] = L.tower;
  const mastH = L.tower_ys[L.tower_ys.length - 1] + 2;
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.45, mastH, 8), MAT.concrete('#beb7a4'));
  mast.position.set(tx, mastH / 2, tz); mast.castShadow = mast.receiveShadow = true; S.add(mast);
  const towerClks = L.tower_ys.map(y => { const c = makeClock(1.3); c.position.set(tx, y, tz + 0.6); S.add(c); return c; });
  const towerRds = L.tower_ys.map((y, j) => { const r = readout(['LOW', 'MIDDLE', 'HIGH', 'TOP'][j], 0.5, 0.19); r.scale.setScalar(6.5); r.position.set(tx + 3.6, y, tz + 0.7); S.add(r); return r; });
  const base = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.5, 0.3, 16), MAT.concrete('#a89684')); base.position.set(tx, 0.15, tz); base.receiveShadow = true; S.add(base);
  const towerSet = [mast, base, ...towerClks, ...towerRds];

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
    // an optical atomic clock as a lab instrument (round 3 review: the white box read as a loudspeaker):
    // a low grey base unit with a big digital time display on its front, a clear glass vacuum chamber on top
    // with the single glowing ion inside, and a red laser beam crossing the chamber
    const box = new THREE.Group();
    const shell = new THREE.Mesh(new THREE.BoxGeometry(0.56, 0.24, 0.36), flat('#8f959b', { roughness: 0.75, metalness: 0.1, flatShading: false })); shell.position.y = 0.12; box.add(shell);
    const ch = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.2, 20, 1, true),
      new THREE.MeshStandardMaterial({ color: '#c9d6e0', roughness: 0.45, metalness: 0, transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthWrite: false }));
    ch.position.set(0, 0.35, 0); box.add(ch);
    for (const y of [0.245, 0.455]) { const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.02, 20), flat('#3b3f45', { roughness: 0.6, metalness: 0.1 })); cap.position.set(0, y, 0); box.add(cap); }
    const ion = new THREE.Mesh(new THREE.SphereGeometry(0.016, 12, 10), MAT.emissive('#8f7cff', 4)); ion.position.set(0, 0.35, 0); box.add(ion);
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.003, 0.003, 0.5, 6), MAT.emissive('#ff3b30', 1.6)); beam.rotation.z = Math.PI / 2; beam.position.set(0, 0.35, 0); box.add(beam);
    const ringM = new THREE.MeshBasicMaterial({ color: '#b9adff', transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.03, 0.036, 32), ringM); ring.position.set(0, 0.35, 0.0); box.add(ring);
    box.position.y = L.table_top; tg.add(box);
    S.add(shadowed(tg)); ring.castShadow = false; ch.castShadow = false; beam.castShadow = false;
    const rd = readout(s < 0 ? 'LIFTED' : 'STAYS', 0.46, 0.176, true);
    rd.position.set(0, 0.12, 0.182); box.add(rd);           // the display is the front panel
    tables.push({ g: tg, top, legs, box, rd }); clocksA.push({ ion, ring, ringM });
  }
  const labSet = tables.map(t => t.g);

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
  sat.traverse(o => { o.castShadow = false; });              // far outside the shadow box (round 3: cut shadow)
  const satRd = readout('SATELLITE', 0.5, 0.19); satRd.scale.setScalar(13); S.add(satRd);
  const carRd = readout('GROUND', 0.5, 0.19); carRd.scale.setScalar(4.5); S.add(carRd);
  const satClk = makeClock(0.75); satClk.position.set(0, 0, 1.75); sat.add(satClk);
  const roadSet = [hero, trueRing, pin, sat, ...others];
  sat.traverse(o => { o.castShadow = false; });                      // incl. its clock
  for (const c of others) c.traverse(o => { o.castShadow = false; });   // oncoming cars pass outside the shadow box

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
      const set = F.set[k];
      for (const o of figSet) o.visible = set === 'fig';
      for (const o of towerSet) o.visible = set === 'tower';
      for (const o of labSet) o.visible = set === 'lab';
      const ro = F.readout[k];
      headRd.visible = feetRd.visible = set === 'fig' && !!ro;
      if (ro) { headRd.setText(ro[0]); feetRd.setText(ro[1]); }
      tables.forEach((tb, j) => tb.rd.setText(F.lab_readout[k][j]));
      const sr = F.sat_readout[k];
      satClk.set(F.sat_clk[k][0], F.sat_clk[Math.max(0, k - 1)][0], 0);
      satRd.visible = carRd.visible = !!sr && set === 'road';
      if (sr) { satRd.setText(sr[0]); carRd.setText(sr[1]); }
      headClk.set(F.head[k], F.head[p], F.warm[k]);
      feetClk.set(F.feet[k], F.feet[p], F.warm[k] * 0.8);
      towerClks.forEach((c, j) => c.set(F.tower[k][j], F.tower[p][j], 0));
      towerRds.forEach((r, j) => r.setText(`${Math.floor(F.tower[k][j] / 60)}:${(F.tower[k][j] % 60).toFixed(1).padStart(4, '0')}`));
      // atomic clocks: the left table rises by frames.lift (legs stretch: a jack under the top)
      const lift = F.lift[k];
      const tl = tables[0];
      tl.top.position.y = L.table_top - 0.025 + lift; tl.box.position.y = L.table_top + lift;
      for (const tb of tables) for (const leg of tb.legs) { const h = tb.top.position.y; leg.scale.y = h; leg.position.y = h / 2; }
      clocksA.forEach((c, j) => { const fr = F.lab[k][j] % 1; c.ring.scale.setScalar(1 + 1.3 * fr); c.ringM.opacity = 0.9 * (1 - fr) ** 2; c.ion.material.emissiveIntensity = 1.2 + 1.4 * (1 - fr) ** 4; });
      // the hero car drives towards -z in the right-hand lane; oncoming cars in the other lane
      const cz = F.car_z[k];
      hero.position.set(rx - 1.8, 0, cz); trueRing.position.set(rx - 1.8, 0.05, cz);
      others.forEach((c, j) => c.position.set(rx + 1.8, 0, -80 - 70 * j - 330 + 11.0 * t));
      const off = F.pin[k];
      pin.position.set(rx - 1.8 + off * 0.12, 0, cz - 8 - off);
      pin.visible = false;
      hero.visible = set === 'road'; for (const o of others) o.visible = set === 'road';
      trueRing.visible = set === 'road' && t >= plan.timing.day[0] - 0.4;
      sat.position.set(rx + L.sat[0] - L.road_x + F.sat_dx[k], L.sat[1], cz + L.sat[2]);
      sat.rotation.set(0.15, 0.3 + t * 0.02, 0.08);
      satRd.position.set(sat.position.x, sat.position.y - 5.6, sat.position.z + 2);
      if (t >= plan.timing.gps_close) {          // close on the satellite: the ground readout stacks under it
        carRd.scale.setScalar(13); carRd.position.copy(satRd.position).add(new THREE.Vector3(0, -2.7, 0));
      } else { carRd.scale.setScalar(4.5); carRd.position.set(rx - 1.8, 3.4, cz + 0.5); }
      sat.visible = set === 'road' && t < plan.timing.day[0] - 0.4;           // not in the map-pin shot (round 1: a cropped fragment)
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

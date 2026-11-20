// An original smooth, high-poly domestic cat for the diorama world (CLAUDE.md section 11 budget).
// Real size (about 0.25 m at the shoulder), faces +z, paws on y = 0. Ginger tabby by default; pass colours
// for other coats. Two body set-ups share one head: a sitting cat and a standing / crouching / walking cat.
//
//   import { cat, mouse } from '../cat.js';
//   const c = cat({ coat: '#d9893f', stripe: '#a9581f' }); c.position.set(x, y, z); scene.add(c);
//   c.pose({ mode: 'sit'|'stand'|'crouch'|'lie', blink: 0..1, yaw, pitch, mouth: 0..1, walk: phase, tail: 0..1, t,
//           fold: 0..1 (lie: stretched -> loaf), hunch: 0..1, ears: 0..1, heat: 0..1, heatBody: 0..1 });
import * as THREE from 'three';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.8, metalness: 0, ...x });

function mesh(geo, m, parent, x = 0, y = 0, z = 0) {
  const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; o.receiveShadow = true;
  parent.add(o); return o;
}
const grp = (parent, x = 0, y = 0, z = 0) => { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; };
function ell(parent, m, rx, ry, rz, x = 0, y = 0, z = 0, seg = 48) {
  const o = mesh(new THREE.SphereGeometry(1, seg, Math.round(seg * 0.75)), m, parent, x, y, z); o.scale.set(rx, ry, rz); o.userData.prim = 'ell'; return o;
}
// tapered tube along a smooth curve (legs, tail, whiskers)
function strand(points, r, m, parent, taper = u => 1, seg = 40, rad = 20) {
  const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)));
  const g = new THREE.TubeGeometry(curve, seg, r, rad, false), P = g.attributes.position, v = new THREE.Vector3(), c = new THREE.Vector3();
  for (let i = 0; i <= seg; i++) {
    const u = i / seg; curve.getPointAt(u, c); const f = Math.max(0.05, taper(u));
    for (let j = 0; j <= rad; j++) { const k = i * (rad + 1) + j; v.fromBufferAttribute(P, k).sub(c).multiplyScalar(f); P.setXYZ(k, c.x + v.x, c.y + v.y, c.z + v.z); }
  }
  g.computeVertexNormals();
  const o = mesh(g, m, parent); o.userData.prim = { type: 'tube', curve, r, taper };
  // round end caps
  o.userData.caps = [0, 1].map(u => { const p = curve.getPointAt(u); const c = mesh(new THREE.SphereGeometry(r * Math.max(0.05, taper(u)), 24, 16), m, parent, p.x, p.y, p.z); c.userData.prim = 'ell'; return c; });
  return o;
}

// tabby stripes as vertex colours: dark bands where sin(axis * freq + wobble) is high
function stripes(o, base, dark, axis = 'z', freq = 60, width = 0.55, belly = null) {
  const g = o.geometry.clone(); o.geometry = g;
  const P = g.attributes.position, n = P.count, col = new Float32Array(n * 3);
  const A = new THREE.Color(base), B = new THREE.Color(dark), W = new THREE.Color('#f1e3cc'), c = new THREE.Color();
  const v = new THREE.Vector3();
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(P, i).multiply(o.scale);
    const a = v[axis], wob = 0.6 * Math.sin(v.x * 40 + v.y * 23) + 0.4 * Math.sin(v.z * 31);
    const s = Math.sin(a * freq + wob);
    c.copy(A).lerp(B, THREE.MathUtils.smoothstep(s, width, width + 0.25) * 0.85);
    if (belly && belly(v)) c.lerp(W, belly(v));
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  o.material = o.material.clone(); o.material.vertexColors = true; o.material.color.set('#ffffff');
}

function makeHead(opt, m) {
  const head = new THREE.Group(), U = head.userData;
  const skull = ell(head, m.fur, 0.064, 0.056, 0.06, 0, 0, 0, 72);
  stripes(skull, opt.coat, opt.stripe, 'y', 120, 0.6, v => (v.z > 0.035 && v.y < -0.005 ? Math.min(1, (v.z - 0.035) * 60) : 0));
  for (const s of [-1, 1]) ell(head, m.fur, 0.03, 0.026, 0.03, s * 0.036, -0.018, 0.024, 48);       // cheeks
  for (const s of [-1, 1]) ell(head, m.cream, 0.019, 0.015, 0.016, s * 0.0145, -0.024, 0.05, 48);   // muzzle pads
  ell(head, m.cream, 0.016, 0.01, 0.014, 0, -0.038, 0.042, 40);                                      // chin
  const nose = ell(head, m.nose, 0.0085, 0.006, 0.006, 0, -0.012, 0.061, 32); nose.rotation.x = 0.3;
  // mouth: a dark opening under the muzzle that opens for a meow, with a little pink tongue
  const mouth = grp(head, 0, -0.033, 0.047); U.mouth = mouth; mouth.userData.noArea = true;
  const inside = ell(mouth, m.mouth, 0.012, 0.008, 0.008, 0, 0, 0, 32); U.inside = inside;
  ell(mouth, m.nose, 0.007, 0.003, 0.006, 0, -0.004, 0.001, 24);
  // eyes: big amber-green irises, vertical slit pupils, glossy cornea; eyelids close by scaling the eye group
  U.eyes = [];
  for (const s of [-1, 1]) {
    const eye = grp(head, s * 0.025, 0.008, 0.049); eye.rotation.y = s * 0.32; eye.userData.noArea = true;
    ell(eye, m.lid, 0.0175, 0.0145, 0.008, 0, 0, -0.002, 40);
    const iris = ell(eye, m.iris, 0.0155, 0.0128, 0.007, 0, 0, 0.001, 48);
    const pupil = ell(eye, m.pupil, 0.0035, 0.0105, 0.004, 0, 0, 0.0055, 32); U.pupils = (U.pupils || []).concat(pupil);
    ell(eye, m.cornea, 0.0158, 0.013, 0.0078, 0, 0, 0.0016, 48);
    ell(eye, m.glint, 0.0028, 0.0028, 0.001, s * -0.004, 0.005, 0.009, 16);
    // upper lid (fur) that drops for a blink
    const lid = ell(eye, m.fur, 0.0185, 0.0155, 0.0095, 0, 0.026, 0.0005, 40); U.lids = (U.lids || []).concat(lid);
    U.eyes.push(eye);
  }
  // ears: smooth cones, thin, with pink inner cones and a tuft
  for (const s of [-1, 1]) {
    const ear = grp(head, s * 0.036, 0.046, -0.004); ear.rotation.set(-0.12, 0, -s * 0.38); ear.userData.side = s; U.ears = (U.ears || []).concat(ear);
    const outer = mesh(new THREE.ConeGeometry(0.024, 0.05, 40, 6), m.fur, ear, 0, 0.022, 0); outer.scale.z = 0.42;
    const inner = mesh(new THREE.ConeGeometry(0.016, 0.036, 40, 4), m.ear, ear, 0, 0.018, 0.0055); inner.scale.z = 0.25;
  }
  // whiskers
  const wh = grp(head); wh.userData.noArea = true;
  for (const s of [-1, 1]) for (const k of [0, 1, 2]) {
    const y = -0.02 - k * 0.005;
    strand([[s * 0.018, y, 0.06], [s * 0.05, y + 0.004 - k * 0.003, 0.064], [s * 0.085, y - 0.002 - k * 0.007, 0.055]], 0.0007, m.whisker, wh, u => 1 - 0.7 * u, 12, 6);
  }
  head.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return head;
}

export function cat(opt = {}) {
  opt = { coat: '#d58a43', stripe: '#a2561f', iris: '#b7b23c', scale: 1, ...opt };
  const m = {
    fur: std(opt.coat, { roughness: 0.9 }), cream: std('#efe2c8', { roughness: 0.9 }), nose: std('#c97a7a', { roughness: 0.6 }),
    mouth: std('#3a1e1e', { roughness: 0.8 }), lid: std('#2a2018'), iris: std(opt.iris, { roughness: 0.35 }),
    pupil: std('#0c0b0a', { roughness: 0.3 }), cornea: new THREE.MeshPhysicalMaterial({ color: '#ffffff', transparent: true, opacity: 0.18, roughness: 0.05, clearcoat: 1 }),
    glint: new THREE.MeshBasicMaterial({ color: '#fffaf0' }), ear: std('#d9a09a'), whisker: std('#f4efe6', { roughness: 0.5 }),
    paw: std('#efe2c8', { roughness: 0.9 }),
  };
  const root = new THREE.Group(); root.name = 'cat';
  const body = grp(root); body.scale.setScalar(opt.scale);
  const belly = v => (v.y < -0.02 ? Math.min(1, (-0.02 - v.y) * 25) : 0);

  // ---- sitting body
  const sit = grp(body);
  const haunch = ell(sit, m.fur, 0.088, 0.115, 0.11, 0, 0.105, -0.03, 64); stripes(haunch, opt.coat, opt.stripe, 'y', 70, 0.55);
  const chest = ell(sit, m.fur, 0.066, 0.1, 0.07, 0, 0.18, 0.025, 64); chest.rotation.x = 0.25;
  stripes(chest, opt.coat, opt.stripe, 'y', 70, 0.65, v => (v.z > 0.03 ? Math.min(1, (v.z - 0.03) * 40) : 0));
  for (const s of [-1, 1]) {
    const thigh = ell(sit, m.fur, 0.042, 0.06, 0.082, s * 0.068, 0.06, -0.01, 48); stripes(thigh, opt.coat, opt.stripe, 'z', 90, 0.6);
    ell(sit, m.paw, 0.022, 0.014, 0.04, s * 0.07, 0.012, 0.045, 32);                          // hind paws
    strand([[s * 0.032, 0.17, 0.065], [s * 0.034, 0.09, 0.075], [s * 0.035, 0.03, 0.078]], 0.017, m.fur, sit, u => 1 - 0.25 * u);
    ell(sit, m.paw, 0.02, 0.014, 0.027, s * 0.035, 0.013, 0.088, 32);                         // front paws
  }
  const sitTail = grp(sit, 0, 0.03, -0.12); root.userData.sitTail = sitTail;
  const tailCurve = (k) => [[0, 0, 0], [0.06, -0.02, -0.02], [0.13, -0.022, 0.05], [0.14 + 0.02 * k, -0.02, 0.13], [0.1, -0.018, 0.18]];
  const sitTailMesh = strand(tailCurve(0), 0.016, m.fur, sitTail, u => 1 - 0.35 * u, 48);
  stripes(sitTailMesh, opt.coat, opt.stripe, 'x', 90, 0.4);
  const sitNeck = grp(sit, 0, 0.265, 0.045);

  // ---- standing body (also crouch and walk)
  const stand = grp(body); stand.visible = false;
  const torso = ell(stand, m.fur, 0.072, 0.078, 0.19, 0, 0.2, 0, 64); stripes(torso, opt.coat, opt.stripe, 'z', 70, 0.5, belly);
  ell(stand, m.fur, 0.064, 0.07, 0.07, 0, 0.215, 0.13, 48);                                    // shoulders
  ell(stand, m.fur, 0.068, 0.072, 0.07, 0, 0.205, -0.12, 48);                                  // hips
  const legs = [];
  for (const [x, z] of [[-0.04, 0.13], [0.04, 0.13], [-0.045, -0.13], [0.045, -0.13]]) {
    const hip = grp(stand, x, 0.19, z);
    const upper = strand([[0, 0, 0], [0, -0.08, z < 0 ? -0.015 : 0.005], [0, -0.17, 0.004]], z < 0 ? 0.022 : 0.018, m.fur, hip, u => 1 - 0.3 * u);
    ell(hip, m.paw, 0.02, 0.013, 0.028, 0, -0.178, 0.012, 32);
    legs.push(hip);
  }
  const standTail = grp(stand, 0, 0.23, -0.18);
  const stMesh = strand([[0, 0, 0], [0, 0.05, -0.08], [0, 0.15, -0.12], [0, 0.24, -0.1], [0, 0.28, -0.06]], 0.016, m.fur, standTail, u => 1 - 0.35 * u, 48);
  stripes(stMesh, opt.coat, opt.stripe, 'y', 90, 0.4);
  const standNeck = grp(stand, 0, 0.26, 0.17);

  // ---- lying body: `fold` 0 = stretched out flat (legs forward and back, tail straight), 1 = the loaf
  // (front paws tucked under the chest, hind legs under the hips, tail wrapped along the side).
  // Legs and tail have their own materials so a scene can make them glow (heat-loss view).
  const lie = grp(body); lie.visible = false;
  m.limb = std(opt.coat, { roughness: 0.9 }); m.limbPaw = std('#efe2c8', { roughness: 0.9 });
  const lieTorso = grp(lie);
  const ltorso = ell(lieTorso, m.fur, 0.09, 0.083, 0.165, 0, 0.085, -0.02, 72); stripes(ltorso, opt.coat, opt.stripe, 'z', 70, 0.5, belly);
  const lchest = ell(lieTorso, m.fur, 0.077, 0.086, 0.082, 0, 0.096, 0.11, 64);
  stripes(lchest, opt.coat, opt.stripe, 'y', 70, 0.65, v => (v.z > 0.04 ? Math.min(1, (v.z - 0.04) * 35) : 0));
  const lhips = ell(lieTorso, m.fur, 0.086, 0.08, 0.08, 0, 0.09, -0.13, 64); stripes(lhips, opt.coat, opt.stripe, 'y', 70, 0.55);
  for (const s of [-1, 1]) { const th = ell(lieTorso, m.fur, 0.042, 0.058, 0.078, s * 0.072, 0.072, -0.1, 48); stripes(th, opt.coat, opt.stripe, 'z', 90, 0.6); }
  const lieLegs = [];
  for (const [x, z, front] of [[-0.042, 0.12, 1], [0.042, 0.12, 1], [-0.05, -0.15, 0], [0.05, -0.15, 0]]) {
    const hip = grp(lie, x, 0.02, z), leg = grp(hip);
    strand([[0, 0, 0], [0, -0.075, front ? 0.004 : -0.006], [0, -0.15, 0]], front ? 0.018 : 0.021, m.limb, leg, u => 1 - 0.25 * u);
    ell(leg, m.limbPaw, 0.021, 0.029, 0.013, 0, -0.158, 0, 40);
    lieLegs.push({ hip, leg, front });
  }
  const lieTail = grp(lie, 0, 0.03, -0.2);
  const tailStraight = [[0, 0, 0], [0, -0.012, -0.08], [0.01, -0.014, -0.16], [0.0, -0.014, -0.24], [-0.012, -0.014, -0.3]];
  const tailWrap = [[0, 0, 0], [0.06, -0.016, -0.02], [0.098, -0.017, 0.05], [0.094, -0.017, 0.13], [0.05, -0.018, 0.185]];
  let tailFold = -1;
  const buildTail = f => {
    for (const c of [...lieTail.children]) { lieTail.remove(c); c.geometry.dispose(); }
    const pts = tailStraight.map((p, k) => p.map((v, j) => v + (tailWrap[k][j] - v) * f));
    const tm = strand(pts, 0.016, m.limb, lieTail, u => 1 - 0.35 * u, 48);
    stripes(tm, opt.coat, opt.stripe, 'x', 90, 0.4);
    tm.material = m.limb.clone(); tm.material.vertexColors = true; tm.material.color.set('#ffffff'); m.tailMat = tm.material;
    tailFold = f;
  };
  buildTail(1);
  const lieNeck = grp(lie, 0, 0.16, 0.15);
  root.userData.lie = { legs: lieLegs, tail: lieTail };

  const head = makeHead(opt, m);
  const neckJoint = new THREE.Group(); neckJoint.add(head); head.position.set(0, 0.035, 0.03);
  sitNeck.add(neckJoint);
  const H = head.userData;
  root.traverse(o => { if (o.isMesh && !o.material.isMeshBasicMaterial && !o.material.transparent) { o.castShadow = true; o.receiveShadow = true; } });

  const furMats = new Set();
  root.traverse(o => { if (o.isMesh && (o.material === m.fur || o.material.vertexColors) && o.parent !== lieTail) furMats.add(o.material); });
  root.pose = (p = {}) => {
    const mode = p.mode ?? 'sit', t = p.t ?? 0;
    const standing = mode === 'stand' || mode === 'crouch', lying = mode === 'lie';
    sit.visible = mode === 'sit'; stand.visible = standing; lie.visible = lying;
    (standing ? standNeck : lying ? lieNeck : sitNeck).add(neckJoint);
    // ears: 0 = upright, 1 = flattened out to the sides (a tense or unwell cat)
    const ea = p.ears ?? 0;
    for (const e of H.ears) e.rotation.set(-0.12 - 0.35 * ea, 0, -e.userData.side * (0.38 + 0.75 * ea));
    // heat-loss glow on legs and tail (and a faint warm body), for the thermal-style beat
    const heat = p.heat ?? 0, hb = p.heatBody ?? 0;
    for (const mm of [m.limb, m.limbPaw, m.tailMat]) { mm.emissive.set('#ff2a1a'); mm.emissiveIntensity = 3.0 * heat; }
    for (const fm of furMats) { fm.emissive.set('#ff8a3c'); fm.emissiveIntensity = 0.35 * hb; }
    neckJoint.rotation.set(p.pitch ?? 0, p.yaw ?? 0, p.tilt ?? 0, 'YXZ');
    const bl = Math.min(1, Math.max(0, p.blink ?? 0));
    for (const lid of H.lids) { lid.visible = bl > 0.02; lid.position.y = 0.02 * (1 - bl); lid.scale.y = 0.0155 * (0.6 + 0.4 * bl); }
    for (const pu of H.pupils) pu.scale.x = 0.0035 * (p.pupil ?? 1);
    const mo = p.mouth ?? 0;
    H.inside.scale.set(0.012, 0.002 + 0.011 * mo, 0.008); H.mouth.position.y = -0.033 - 0.004 * mo;
    // tail: a slow sway; flick when `tail` is high
    const sway = 0.18 * Math.sin(t * 1.3) + 0.35 * (p.tail ?? 0) * Math.sin(t * 7);
    sitTail.rotation.y = sway; standTail.rotation.z = sway * 0.6;
    if (lying) {
      const f = Math.min(1, Math.max(0, p.fold ?? 1)), hu = Math.min(1, Math.max(0, p.hunch ?? 0));
      const tf = Math.min(1, Math.max(0, p.tailFold ?? f));
      if (Math.abs(tf - tailFold) > 0.004) buildTail(tf);
      lieTail.rotation.y = 0.04 * Math.sin(t * 0.9) * (1 - tf) + (p.tail ?? 0) * 0.12 * Math.sin(t * 5);
      // hunched: the back rises and rounds, the head drops and pulls in
      lieTorso.position.y = 0.012 * hu; lieTorso.scale.set(1 - 0.04 * hu, 1 + 0.12 * hu, 1 - 0.06 * hu);
      for (const L of lieLegs) {
        const hipY = 0.02 + 0.03 * f;
        L.hip.position.y = hipY;
        // folding: front legs swing down and back under the chest, hind legs forward under the hips, both shortening
        // until they are hidden inside the body (a true loaf shows no feet)
        const th = L.front ? -Math.PI / 2 + (Math.PI / 2 + 1.2) * f : Math.PI / 2 - (Math.PI / 2 + 1.2) * f;
        let len = 1 - 0.88 * f;
        const c = Math.cos(th); if (c > 0.01) len = Math.min(len, (hipY - 0.004) / (0.165 * c));
        L.leg.rotation.x = th; L.leg.scale.set(1 - 0.5 * f, Math.max(0.05, len), 1 - 0.3 * f);
        L.hip.position.z = (L.front ? 0.12 : -0.15) + (L.front ? -0.02 : 0.03) * f;
      }
      lieNeck.position.set(0, 0.125 + 0.035 * f - 0.035 * hu, 0.17 - 0.02 * f - 0.02 * hu);
    }
    if (standing) {
      const crouch = mode === 'crouch' ? 1 : 0;
      stand.position.y = -0.075 * crouch; stand.rotation.x = 0.0;
      const w = p.walk;
      legs.forEach((leg, k) => {
        const ph = w === undefined ? 0 : Math.sin(w + (k === 0 || k === 3 ? 0 : Math.PI));
        leg.rotation.x = 0.35 * ph * (w === undefined ? 0 : 1);
        leg.scale.y = 1 - 0.42 * crouch;
      });
      standNeck.position.set(0, 0.26 - 0.05 * crouch, 0.17 + 0.02 * crouch);
    }
  };
  root.pose();
  root.headWorld = (v = new THREE.Vector3()) => head.getWorldPosition(v);
  root.userData.head = head;
  return root;
}

// a small grey field mouse, faces +z
export function mouse() {
  const g = new THREE.Group(), fur = std('#8b8178', { roughness: 0.9 }), pink = std('#d7a2a0');
  ell(g, fur, 0.022, 0.018, 0.035, 0, 0.018, 0, 40);
  ell(g, fur, 0.014, 0.013, 0.018, 0, 0.022, 0.034, 32);
  for (const s of [-1, 1]) { const e = ell(g, pink, 0.008, 0.008, 0.002, s * 0.009, 0.034, 0.03, 24); e.rotation.y = s * 0.4; }
  ell(g, std('#2a2020'), 0.003, 0.003, 0.003, 0, 0.022, 0.052, 12);
  strand([[0, 0.012, -0.03], [0.01, 0.006, -0.06], [-0.01, 0.003, -0.09]], 0.0025, pink, g, u => 1 - 0.6 * u, 24, 10);
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return g;
}

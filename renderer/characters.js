// Counterphysical presenters. v6 (default): Blender-built models from tools/blender/presenters.py, exported to
// assets/characters/{wizard,woman}.glb and preloaded by boot.js (loadPresenters). If the GLBs are not loaded,
// man()/woman() fall back to the procedural v5 models below (same pose API).
//
// v5: two original, smooth high-poly characters that sit in the diorama world.
// Bodies are continuous lathe/tube surfaces (no stacked blocks), heads are 72x54 sculpted ellipsoids with
// layered eyes, lips and strand-built hair. They replace the faceless wooden toy figure.
//
//   import { man, woman } from '../characters.js';     // man() is the wizard, woman() the young woman
//   const p = woman(); p.position.set(x, 0, z); scene.add(p);
//   p.pose({ talk: 0..1, blink: 0..1, wave: 0..1, point: 0..1, headYaw, headPitch, headTilt, walk: phase, t });
//
// Both stand on y = 0, face +z and are real-world size. Joints are pivot groups in p.rig. Both are original
// designs, not modelled on any real person or existing character (see CLAUDE.md section 11).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

// ---------- v6: Blender GLB presenters ----------
const GLB = {};
export async function loadPresenters(base = '/assets/characters/') {
  const loader = new GLTFLoader();
  await Promise.all(['wizard', 'woman'].map(async k => {
    try { GLB[k] = (await loader.loadAsync(`${base}${k}.glb`)).scene; } catch (e) { console.warn(`presenter ${k}.glb not loaded`, e); }
  }));
  return Object.keys(GLB);
}
export const presentersLoaded = () => !!(GLB.wizard && GLB.woman);

function fromGLB(kind, name) {
  const root = new THREE.Group(); root.name = name;
  const model = SkeletonUtils.clone(GLB[kind]); root.add(model);
  const find = (pre) => { let f = null; model.traverse(o => { if (!f && o.name === pre) f = o; }); return f; };
  const all = (pre) => { const r = []; model.traverse(o => { if (o.name.startsWith(pre)) r.push(o); }); return r; };
  model.traverse(o => {
    if (o.isMesh) {
      o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false;
      // plain standard materials: Blender sheen exports as MeshPhysicalMaterial with zero sheen roughness, which
      // renders NaN pixels (black blooms) in this pipeline, and standard is cheaper anyway
      const m = o.material;
      if (m && m.isMeshPhysicalMaterial) {
        o.material = new THREE.MeshStandardMaterial({ name: m.name, color: m.color, roughness: m.roughness, metalness: m.metalness,
          emissive: m.emissive, emissiveIntensity: m.emissiveIntensity, map: m.map, normalMap: m.normalMap, side: m.side });
      }
    }
  });
  model.updateMatrixWorld(true);
  // bones are named after the joint at their END (e.g. 'elbow_L' = shoulder->elbow, the upper arm)
  const B = { head: 'head', neck: 'neck', armL: 'elbow_L', armR: 'elbow_R', elbowL: 'wrist_L', elbowR: 'wrist_R',
              legL: 'thigh_L', legR: 'thigh_R', kneeL: 'calf_L', kneeR: 'calf_R', spine: 'chest' };
  const rig = {}, rest = {};
  const rootInv = new THREE.Quaternion();
  for (const [k, n] of Object.entries(B)) {
    const b = find(n); if (!b) continue; rig[k] = b;
    const pq = new THREE.Quaternion(); b.parent.getWorldQuaternion(pq);
    rest[k] = { q0: b.quaternion.clone(), pq, pqi: pq.clone().invert() };
  }
  rig.staff = find('z_staff'); rig.crystal = find('z_stone');
  const tmpQ = new THREE.Quaternion(), tmpE = new THREE.Euler();
  // rotate a bone by Euler angles expressed in the character's own frame (x right->left, y up, z forward)
  const rot = (k, x = 0, y = 0, z = 0, order = 'XYZ') => {
    const r = rest[k]; if (!r) return;
    tmpQ.setFromEuler(tmpE.set(x, y, z, order));
    rig[k].quaternion.copy(r.pqi).multiply(tmpQ).multiply(r.pq).multiply(r.q0);
  };
  const lower = find('lip_lower') ?? all('lip_lower')[0];
  const lowerRest = lower ? lower.position.clone() : null, lowerDown = new THREE.Vector3();
  if (lower) {
    const pq = new THREE.Quaternion(), ps = new THREE.Vector3(); lower.parent.getWorldQuaternion(pq); lower.parent.getWorldScale(ps);
    lowerDown.set(0, -1, 0).applyQuaternion(pq.invert()).divide(ps);
  }
  const eyes = [...all('eye_'), ...all('iris'), ...all('pupil')];
  const headBone = rig.head; const hp = new THREE.Vector3(); if (headBone) headBone.getWorldPosition(hp);
  root.rig = rig; root.height = kind === 'wizard' ? 2.0 : 1.69; root.faceY = kind === 'wizard' ? 1.69 : 1.585;
  root.pose = (p = {}) => {
    const talk = p.talk ?? 0, wave = p.wave ?? 0, point = p.point ?? 0, t = p.t ?? 0;
    if (lower) lower.position.copy(lowerRest).addScaledVector(lowerDown, 0.007 * talk);
    const closed = (p.blink ?? 0) > 0.5; for (const e of eyes) e.visible = !closed;
    rot('head', p.headPitch ?? 0, p.headYaw ?? 0, p.headTilt ?? 0, 'YXZ');
    rot('armR', -0.15 * wave, 0, -2.4 * wave);
    rot('elbowR', 0, 0, -0.9 * wave - 0.25 * Math.sin(t * 9) * wave);
    rot('armL', -1.15 * point, 0, 0.45 * point);
    rot('elbowL', -0.2 * point, 0, 0);
    const w = p.walk;
    if (w !== undefined) {
      const robe = kind === 'wizard', sw = Math.sin(w) * (robe ? 0.12 : 0.3), kb = robe ? 0.2 : 0.55;   // legs stay inside the robe
      rot('legL', -sw); rot('legR', sw);
      rot('kneeL', Math.max(0, -Math.sin(w + 0.6)) * kb); rot('kneeR', Math.max(0, Math.sin(w + 0.6)) * kb);
      if (!wave) rot('armR', sw * 0.5);
      if (!point && kind !== 'wizard') rot('armL', -sw * 0.5);
      model.position.y = Math.abs(Math.cos(w)) * 0.015;
    } else if (p.sit) {                    // sitting on a seat about 0.45 m high (thighs forward, shins down)
      const s = p.sit; rot('legL', -1.45 * s); rot('legR', -1.45 * s); rot('kneeL', 1.45 * s); rot('kneeR', 1.45 * s);
      model.position.y = -(kind === 'wizard' ? 0.46 : 0.42) * s;
    } else { for (const j of ['legL', 'legR', 'kneeL', 'kneeR']) rot(j); model.position.y = 0; }
  };
  root.pose();
  return root;
}

const mat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.75, metalness: 0, ...x });

function add(geo, m, parent, x = 0, y = 0, z = 0) {
  const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; o.receiveShadow = true;
  parent.add(o); return o;
}
const grp = (parent, x = 0, y = 0, z = 0) => { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; };
const ell = (parent, m, rx, ry, rz, x = 0, y = 0, z = 0, seg = 40) => {
  const o = add(new THREE.SphereGeometry(1, seg, Math.round(seg * 0.75)), m, parent, x, y, z); o.scale.set(rx, ry, rz); return o;
};

// a closed, smooth body of revolution hanging DOWN from the parent's origin: r(t), t = 0 top .. 1 bottom
function tube(len, rf, m, parent, { rad = 40, seg = 36, dz = 1 } = {}) {
  const pts = [], r0 = rf(0), r1 = rf(1);
  for (let k = 0; k <= 8; k++) { const a = k / 8 * Math.PI / 2; pts.push(new THREE.Vector2(r1 * Math.sin(a), -len - r1 * 0.6 * Math.cos(a))); }
  for (let k = 1; k < seg; k++) { const t = 1 - k / seg; pts.push(new THREE.Vector2(rf(t), -t * len)); }
  for (let k = 0; k <= 8; k++) { const a = k / 8 * Math.PI / 2; pts.push(new THREE.Vector2(r0 * Math.cos(a), r0 * 0.6 * Math.sin(a))); }
  const o = add(new THREE.LatheGeometry(pts, rad), m, parent); o.scale.z = dz; return o;
}
// body of revolution from a (y, r) profile listed bottom to top (r should reach 0 at both ends)
function lathe(profile, m, parent, { rad = 64, dz = 1, phi0 = 0, phiLen = Math.PI * 2, smooth = 4 } = {}) {
  const c = new THREE.SplineCurve(profile.map(([y, r]) => new THREE.Vector2(r, y)));
  const g = new THREE.LatheGeometry(c.getPoints(profile.length * smooth), rad, phi0, phiLen);
  const o = add(g, m, parent); o.scale.z = dz; return o;
}
// a tapered, optionally flattened strand along a smooth curve (hair locks, beard, moustache, staff, hat)
function strand(points, r, m, parent, { taper = u => Math.min(1, (u + 0.04) / 0.16) * (1 - 0.85 * u ** 1.6), flatDir = null, flat = 1, seg = 64, rad = 16 } = {}) {
  const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)));
  const g = new THREE.TubeGeometry(curve, seg, r, rad, false), P = g.attributes.position, v = new THREE.Vector3(), c = new THREE.Vector3(), n = new THREE.Vector3();
  for (let i = 0; i <= seg; i++) {
    const u = i / seg; curve.getPointAt(u, c); const f = Math.max(0.02, taper(u));
    if (flatDir) n.copy(typeof flatDir === 'function' ? flatDir(c) : flatDir).normalize();
    for (let j = 0; j <= rad; j++) {
      const idx = i * (rad + 1) + j; v.fromBufferAttribute(P, idx).sub(c).multiplyScalar(f);
      if (flatDir) v.addScaledVector(n, -(1 - flat) * v.dot(n));
      P.setXYZ(idx, c.x + v.x, c.y + v.y, c.z + v.z);
    }
  }
  g.computeVertexNormals();
  return add(g, m, parent);
}

// ---------- head ----------
// Unit sphere -> sculpted head: narrower jaw, shaped chin, slight cheekbones, then scaled to (a, b, c).
function headShape(o) {
  const def = (x, y, z) => {
    if (y < 0) {
      const t = -y;
      x *= 1 - (1 - o.jawW) * t ** 1.6 - o.chinV * t ** 5;
      z = z * (1 - 0.1 * t * t) + o.chinFwd * t ** 3 * Math.max(0, z);
    }
    if (z > 0) x *= 1 + o.cheek * Math.exp(-(((y + 0.15) / 0.22) ** 2));
    if (y > 0.2) z *= 1 - 0.06 * (y - 0.2);
    return new THREE.Vector3(x * o.a, y * o.b, z * o.c);
  };
  const dir = (lon, lat) => [Math.cos(lat) * Math.sin(lon), Math.sin(lat), Math.cos(lat) * Math.cos(lon)];
  // point on the head at longitude/latitude (lon 0 = front centre, +x = the character's left), pushed out by off
  const at = (lon, lat, off = 0) => {
    const e = 1e-3, p = def(...dir(lon, lat)), q1 = def(...dir(lon + e, lat)), q2 = def(...dir(lon, lat + e));
    const nrm = q1.sub(p).cross(q2.sub(p)).normalize(); if (nrm.dot(p) < 0) nrm.negate();
    return { p: p.clone().addScaledVector(nrm, off), n: nrm };
  };
  return { def, at };
}

function makeHead(o) {
  const head = new THREE.Group();
  const { def, at } = headShape(o);
  const g = new THREE.SphereGeometry(1, 72, 54), P = g.attributes.position;
  for (let i = 0; i < P.count; i++) { const v = def(P.getX(i), P.getY(i), P.getZ(i)); P.setXYZ(i, v.x, v.y, v.z); }
  g.computeVertexNormals();
  add(g, o.skin, head);
  const face = (m, lon, lat, off = 0) => { const { p, n } = at(lon, lat, off); m.position.copy(p); m.lookAt(p.clone().add(n)); head.add(m); return m; };

  for (const s of [-1, 1]) {                                     // ears
    const e = new THREE.Group(); face(e, s * 1.5, -0.06, -0.004); e.rotateY(s * -0.5);
    ell(e, o.skin, o.earW, o.earH, 0.01, 0, 0, 0, 24);
    ell(e, o.skinShade, o.earW * 0.55, o.earH * 0.6, 0.006, 0, 0, 0.005, 20);
  }
  const nb = new THREE.Group(); face(nb, 0, -0.08, 0.0);          // nose bridge + tip + nostril shadows
  if (o.bridge !== false) ell(nb, o.skin, o.noseR * 0.55, o.noseL * 0.55, o.noseR * 0.6, 0, -o.noseL * 0.1, 0.002, 24);
  const nt = new THREE.Group(); face(nt, 0, o.noseLat, 0.0);
  ell(nt, o.skin, o.noseR, o.noseR * 0.82, o.noseR * 0.85, 0, 0, o.noseR * 0.35, 28);
  for (const s of [-1, 1]) ell(nt, o.skinShade, o.noseR * 0.32, o.noseR * 0.2, o.noseR * 0.3, s * o.noseR * 0.55, -o.noseR * 0.55, o.noseR * 0.25, 16);

  // eyes: white, iris, pupil, glint, upper lash line (+ optional wing), lower lash hint; inner group squashes to blink
  const eyes = [];
  const white = mat('#f6f2ec', { roughness: 0.3 }), irisM = mat(o.iris, { roughness: 0.25 }), pupilM = mat('#0d0b0c', { roughness: 0.2 });
  const glintM = new THREE.MeshBasicMaterial({ color: '#ffffff' }), lashM = mat(o.lash, { roughness: 0.5 });
  for (const s of [-1, 1]) {
    const e = new THREE.Group(); face(e, s * o.eyeLon, o.eyeLat, -0.0035); e.rotateZ(s * o.eyeTilt);
    const lid = grp(e);
    ell(lid, white, o.eyeW, o.eyeH, 0.006, 0, 0, 0, 36);
    ell(lid, irisM, o.irisR, o.irisR, 0.005, 0, -o.eyeH * 0.08, 0.0025, 32);
    ell(lid, pupilM, o.irisR * 0.45, o.irisR * 0.45, 0.004, 0, -o.eyeH * 0.08, 0.0045, 24);
    ell(lid, glintM, o.irisR * 0.22, o.irisR * 0.22, 0.002, -s * o.irisR * 0.35, o.irisR * 0.3, 0.0065, 12);
    const arc = Math.PI * 0.95;
    const up = add(new THREE.TorusGeometry(o.eyeW * 1.02, o.lashT, 10, 40, arc), lashM, e, 0, -o.eyeH * 0.02, 0.003);
    up.rotation.z = (Math.PI - arc) / 2; up.scale.y = o.eyeH / o.eyeW * 1.05;
    if (o.flick) {
      const f = add(new THREE.ConeGeometry(o.lashT * 1.1, o.eyeW * 0.55, 12), lashM, e, s * o.eyeW * 1.12, o.eyeH * 0.35, 0.003);
      f.rotation.z = -s * 1.05;
    }
    const lo = add(new THREE.TorusGeometry(o.eyeW * 0.98, o.lashT * 0.35, 6, 32, Math.PI * 0.8), o.skinShade, e, 0, o.eyeH * 0.05, 0.002);
    lo.rotation.z = Math.PI * 1.1; lo.scale.y = o.eyeH / o.eyeW;
    const b = new THREE.Group(); face(b, s * o.eyeLon * 1.05, o.browLat, 0.0005); b.rotateZ(s * o.browTilt);
    const br = add(new THREE.TorusGeometry(o.browR, o.browT, 8, 36, 1.15), mat(o.browC), b, 0, -o.browR * 0.9, 0);
    br.rotation.z = Math.PI / 2 - 0.575; br.scale.set(1, 0.5, 0.5);
    eyes.push(lid);
  }
  // mouth: two-lobed upper lip, fuller lower lip, dark interior that opens for talking
  const mo = new THREE.Group(); face(mo, 0, o.mouthLat, -0.001);
  const lipM = mat(o.lip, { roughness: 0.45 });
  const inside = ell(mo, mat('#4a1f22'), o.mouthW * 0.85, 0.001, 0.004, 0, -0.0005, 0.0005, 24);
  for (const s of [-1, 1]) {
    const u = ell(mo, lipM, o.mouthW * 0.6, o.upperLip, 0.0055, s * o.mouthW * 0.42, o.upperLip * 0.85, 0.0015, 28);
    u.rotation.z = s * -0.18;
  }
  const lower = ell(mo, lipM, o.mouthW * 0.82, o.lowerLip, 0.006, 0, -o.lowerLip * 1.05, 0.0015, 28);
  for (const s of [-1, 1]) ell(mo, o.skinShade, 0.0018, 0.0018, 0.002, s * o.mouthW * 1.02, 0.0012, 0.0005, 10);
  if (o.blush) for (const s of [-1, 1]) {
    const bl = new THREE.Mesh(new THREE.CircleGeometry(1, 32), new THREE.MeshBasicMaterial({ color: o.blush, transparent: true, opacity: 0.16, depthWrite: false }));
    face(bl, s * 0.62, -0.28, 0.0008); bl.scale.set(0.018, 0.012, 1);
  }
  head.userData = { eyes, inside, lower, lowerY: lower.position.y, at };
  return head;
}

// ---------- shared body ----------
function makePerson(o) {
  const root = new THREE.Group(); root.name = o.name;
  const rig = {}, k = o.height / 1.78;
  const body = grp(root); body.scale.setScalar(k); rig.body = body;
  const hipY = 0.93;
  for (const s of [-1, 1]) {                                     // legs
    const hip = grp(body, s * o.hipX, hipY, 0);
    tube(0.46, t => o.thighR * (1.12 - 0.42 * t + 0.08 * Math.sin(t * Math.PI)), o.pants, hip);
    const knee = grp(hip, 0, -0.46, 0);
    add(new THREE.SphereGeometry(o.thighR * 0.72, 32, 24), o.pants, knee);
    tube(0.42, t => o.shinR * (1.0 + 0.14 * Math.sin(Math.min(1, t * 2.2) * Math.PI) - 0.42 * t * t), o.pants, knee);
    const ankle = grp(knee, 0, -0.42, 0);
    ell(ankle, o.shoe, o.shoeW / 2, 0.04, 0.125, 0, -0.012, 0.04, 40);
    ell(ankle, o.sole, o.shoeW / 2 * 1.06, 0.016, 0.132, 0, -0.036, 0.042, 40);
    rig[s < 0 ? 'legR' : 'legL'] = hip; rig[s < 0 ? 'kneeR' : 'kneeL'] = knee;
  }
  lathe(o.lowerProfile, o.pants, body, { dz: o.dz });
  const torso = lathe(o.torsoProfile, o.top, body, { dz: o.dz });
  if (o.bust) {                                                  // gentle, modest chest shaping on the front
    const P = torso.geometry.attributes.position;
    for (let i = 0; i < P.count; i++) {
      const x = P.getX(i), y = P.getY(i), z = P.getZ(i); if (z <= 0) continue;
      const w = Math.exp(-(((y - o.bust.y) / 0.05) ** 2)) * Math.exp(-(((Math.abs(x) - 0.06) / 0.05) ** 2));
      P.setZ(i, z + o.bust.d * w);
    }
    torso.geometry.computeVertexNormals();
  }
  if (o.outfit) o.outfit(body, o);
  tube(0.13, t => o.neckR * (1 + 0.15 * t), o.skin, grp(body, 0, o.shoulderY + 0.12, 0));
  const neck = grp(body, 0, o.shoulderY + 0.05, 0);
  const head = makeHead(o.headOpts);
  head.position.set(0, o.headOpts.b * 0.9 + 0.01, 0.012); neck.add(head);
  if (o.hair) o.hair(head, o);
  rig.neck = neck; rig.head = head;
  for (const s of [-1, 1]) {                                     // arms
    const sh = grp(body, s * o.shoulderX, o.shoulderY - 0.035, 0);
    add(new THREE.SphereGeometry(o.armR * 1.15, 40, 30), o.sleeve, sh);
    tube(0.29, t => o.armR * (1.1 - 0.25 * t), o.sleeve, sh);
    const elbow = grp(sh, 0, -0.28, 0);
    add(new THREE.SphereGeometry(o.armR * 0.84, 32, 24), o.sleeve, elbow);
    tube(0.25, t => o.foreR * (1.08 + 0.06 * Math.sin(t * Math.PI) - 0.34 * t), o.foreMat, elbow);
    const wrist = grp(elbow, 0, -0.25, 0);
    if (o.cuff) o.cuff(wrist, o);
    ell(wrist, o.skin, 0.03, 0.045, 0.016, 0, -0.04, 0.004, 32);
    ell(wrist, o.skin, 0.027, 0.03, 0.014, 0, -0.08, 0.006, 32);
    strand([[s * -0.022, -0.02, 0.012], [s * -0.03, -0.05, 0.018], [s * -0.026, -0.07, 0.02]], 0.0085, o.skin, wrist, { seg: 16, rad: 10 });
    sh.rotation.z = s * 0.08;
    rig[s < 0 ? 'armR' : 'armL'] = sh; rig[s < 0 ? 'elbowR' : 'elbowL'] = elbow; rig[s < 0 ? 'wristR' : 'wristL'] = wrist;
  }
  if (o.extra) o.extra(body, o, rig);
  root.traverse(m => { if (m.isMesh && !(m.material && m.material.isMeshBasicMaterial)) { m.castShadow = true; m.receiveShadow = true; } else if (m.isMesh) m.castShadow = false; });
  root.rig = rig; root.height = o.height;
  root.faceY = (o.shoulderY + 0.05 + o.headOpts.b * 0.9) * k;
  const U = head.userData;
  root.pose = (p = {}) => {
    const talk = p.talk ?? 0, wave = p.wave ?? 0, point = p.point ?? 0, t = p.t ?? 0;
    U.inside.scale.y = 0.001 + 0.011 * talk; U.lower.position.y = U.lowerY - 0.008 * talk;
    for (const e of U.eyes) e.scale.y = Math.max(0.06, 1 - (p.blink ?? 0));
    neck.rotation.set(p.headPitch ?? 0, p.headYaw ?? 0, p.headTilt ?? 0);
    rig.armR.rotation.set(-0.15 * wave, 0, -0.08 - 2.5 * wave);
    rig.elbowR.rotation.set(0, 0, -0.9 * wave + 0.25 * Math.sin(t * 9) * wave);
    rig.armL.rotation.set(-1.05 * point, 0, 0.08 + 0.75 * point);
    rig.elbowL.rotation.set(-0.15 * point, 0, 0);
    if (o.armRest && !point) o.armRest(rig, p);
    const w = p.walk;
    if (w !== undefined) {
      const sw = Math.sin(w) * 0.45;
      rig.legL.rotation.x = sw; rig.legR.rotation.x = -sw;
      rig.kneeL.rotation.x = Math.max(0, -Math.sin(w + 0.6)) * 0.7; rig.kneeR.rotation.x = Math.max(0, Math.sin(w + 0.6)) * 0.7;
      if (!wave) rig.armR.rotation.x = sw * 0.6;
      if (!point && !o.armRest) rig.armL.rotation.x = -sw * 0.6;
      body.position.y = Math.abs(Math.cos(w)) * 0.02 * k;
    } else { for (const j of ['legL', 'legR', 'kneeL', 'kneeR']) rig[j].rotation.x = 0; body.position.y = 0; }
  };
  root.pose();
  return root;
}

// ---------- 1) the wizard ----------
// An original wizard: midnight-blue robe with a warm gold hem and cuffs, a short shoulder mantle, a tall soft
// hat with a gentle bend and a gold band, a chestnut beard and moustache greying at the edges, and a gnarled
// wooden staff topped with a small glowing amber crystal (the only emissive, so it blooms).
export function man(opt = {}) {
  if (GLB.wizard && !opt.procedural) return fromGLB('wizard', 'presenter-wizard');
  return manV5(opt);
}
function manV5(opt = {}) {
  const skin = mat(opt.skin ?? '#dcab8c', { roughness: 0.62 }), skinShade = mat('#c99173', { roughness: 0.7 });
  const robe = mat(opt.robe ?? '#2c3a5c', { roughness: 0.82 }), robeDark = mat('#233049', { roughness: 0.85 });
  const robeDS = robe.clone(); robeDS.side = THREE.DoubleSide;
  const gold = mat('#c9a24a', { roughness: 0.4, metalness: 0.55 });
  const beardM = mat(opt.beard ?? '#6f5847', { roughness: 0.7 }), beardGrey = mat('#9a8c80', { roughness: 0.7 });
  const beardDS = beardM.clone(); beardDS.side = THREE.DoubleSide;
  const wood = mat('#6b4a2e', { roughness: 0.8 });
  const ring = (r, tube, y, sy, parent) => { const m = add(new THREE.TorusGeometry(r, tube, 12, 96), gold, parent, 0, y, 0); m.rotation.x = Math.PI / 2; m.scale.set(1, sy, 1); return m; };
  return makePerson({
    name: 'presenter-wizard', height: opt.height ?? 1.78,
    skin, top: robe, sleeve: robe, foreMat: robe, pants: robeDark,
    shoe: mat('#3a2a20', { roughness: 0.6 }), sole: mat('#21170f'), shoeW: 0.11,
    dz: 0.66, shoulderY: 1.43, shoulderX: 0.2, hipX: 0.09, thighR: 0.085, shinR: 0.064, armR: 0.058, foreR: 0.05, neckR: 0.055,
    lowerProfile: [[0.84, 0], [0.845, 0.11], [0.88, 0.16], [0.95, 0.172], [1.03, 0.18], [1.06, 0]],
    torsoProfile: [[1.0, 0], [1.005, 0.18], [1.1, 0.188], [1.24, 0.2], [1.35, 0.205], [1.41, 0.185], [1.455, 0.13], [1.475, 0.07], [1.48, 0]],
    headOpts: {
      a: 0.098, b: 0.12, c: 0.108, jawW: 0.86, chinV: 0.05, chinFwd: 0.05, cheek: 0.03, skin, skinShade,
      earW: 0.013, earH: 0.028, noseR: 0.0125, noseL: 0.036, noseLat: -0.3,
      eyeLon: 0.37, eyeLat: 0.05, eyeTilt: 0.0, eyeW: 0.0125, eyeH: 0.0076, irisR: 0.0069, iris: '#4a6a86', lash: '#3a2c22', lashT: 0.0012,
      browLat: 0.28, browR: 0.016, browT: 0.0032, browTilt: -0.08, browC: '#8a7a6c',
      mouthLat: -0.58, mouthW: 0.016, upperLip: 0.0028, lowerLip: 0.0038, lip: '#a46a5e',
    },
    cuff: (wrist, o) => {                                          // wide bell sleeve end with a gold band
      add(new THREE.CylinderGeometry(o.foreR * 1.15, o.foreR * 1.6, 0.1, 48, 1, true), robeDS, wrist, 0, 0.035, 0);
      ring(o.foreR * 1.58, 0.005, -0.014, 1, wrist);
    },
    outfit: (body) => {
      lathe([[0.03, 0], [0.032, 0.235], [0.2, 0.225], [0.5, 0.205], [0.8, 0.19], [1.04, 0.19], [1.08, 0]], robe, body, { dz: 0.78, rad: 72 });
      ring(0.234, 0.009, 0.045, 0.78, body);                       // gold hem
      add(new THREE.BoxGeometry(0.03, 0.4, 0.012, 1, 8, 1), gold, body, 0, 1.18, 0.138).rotation.x = -0.05;
      const belt = add(new THREE.TorusGeometry(0.188, 0.011, 12, 96), mat('#5a3e2a', { roughness: 0.6 }), body, 0, 1.04, 0);
      belt.rotation.x = Math.PI / 2; belt.scale.set(1, 0.68, 1);
      add(new THREE.TorusGeometry(0.018, 0.005, 10, 24), gold, body, 0, 1.04, 0.13);
      lathe([[1.24, 0], [1.245, 0.235], [1.32, 0.235], [1.4, 0.215], [1.45, 0.15], [1.475, 0.09], [1.48, 0]], robeDark, body, { dz: 0.7, rad: 72 });
      ring(0.234, 0.006, 1.25, 0.7, body);
    },
    hair: (head, o) => {
      const { a, b, c } = o.headOpts, at = head.userData.at;
      const side = add(new THREE.SphereGeometry(1, 64, 32, Math.PI * 0.86, Math.PI * 1.28, Math.PI * 0.3, Math.PI * 0.28), beardDS, head, 0, b * 0.02, -c * 0.02);
      side.scale.set(a * 1.06, b * 1.05, c * 1.07);
      const chin = at(0, -0.9, 0).p;
      const mass = ell(head, beardM, a * 0.78, 0.07, c * 0.5, 0, chin.y - 0.03, chin.z - c * 0.38, 56);
      for (let i = 0; i <= 14; i++) {                              // beard locks over the mass, outer ones greyer
        const u = i / 14 - 0.5, s0 = at(u * 1.6, -0.55 - 0.2 * Math.abs(u), 0.006).p;
        const end = [s0.x * 0.35, chin.y - 0.085 + 0.03 * Math.abs(u), chin.z - 0.005 - 0.03 * Math.abs(u)];
        const mid = [s0.x * 0.8, (s0.y + end[1]) / 2, Math.max(s0.z, end[2]) + 0.012];
        strand([s0.toArray(), mid, end], 0.016 - 0.008 * Math.abs(u), Math.abs(u) > 0.36 ? beardGrey : beardM, head, { flatDir: q => new THREE.Vector3(q.x * 0.3, 0, 1), flat: 0.45, seg: 40, rad: 14 });
      }
      for (const s of [-1, 1]) {                                   // moustache
        const p0 = at(s * 0.03, -0.44, 0.004).p, p1 = at(s * 0.32, -0.55, 0.004).p, p2 = at(s * 0.5, -0.7, 0.002).p;
        strand([p0.toArray(), p1.toArray(), p2.toArray()], 0.011, beardM, head, { taper: u => 0.75 + 0.35 * Math.sin(u * Math.PI) - 0.6 * u ** 3, flatDir: new THREE.Vector3(0, 0, 1), flat: 0.55, seg: 32, rad: 14 });
      }
      const hat = grp(head, 0, b * 0.62, -c * 0.06); hat.rotation.x = -0.12;
      lathe([[-0.008, 0], [-0.01, 0.06], [-0.012, 0.15], [-0.004, 0.2], [0.004, 0.205], [0.006, 0.14], [0.008, 0.06], [0.01, 0]], robe, hat, { rad: 96 });
      const conePts = [];
      for (let i = 0; i <= 20; i++) { const u = i / 20; conePts.push([Math.sin(u * 1.6) * 0.06 * u * u, 0.005 + u * 0.36, -0.03 * u ** 3]); }
      strand(conePts, 0.112, robe, hat, { taper: u => Math.max(0.03, (1 - u) ** 1.15), seg: 80, rad: 48 });
      ring(0.106, 0.011, 0.03, 1, hat);
      for (const [u, ang] of [[0.25, 0.6], [0.45, -0.9], [0.62, 2.4]]) {
        const st = add(new THREE.OctahedronGeometry(0.012, 0), gold, hat, Math.sin(ang) * 0.112 * (1 - u) + Math.sin(u * 1.6) * 0.06 * u * u, 0.005 + u * 0.36, Math.cos(ang) * 0.112 * (1 - u));
        st.scale.set(1, 1, 0.4); st.lookAt(st.position.clone().multiplyScalar(2));
      }
    },
    extra: (body, o, rig) => {
      const staff = grp(rig.wristL, 0, -0.06, 0.03); rig.staff = staff;
      const pts = []; for (let i = 0; i <= 12; i++) { const u = i / 12; pts.push([0.012 * Math.sin(u * 9), -0.95 + u * 1.75, 0.01 * Math.cos(u * 7)]); }
      strand(pts, 0.017, wood, staff, { taper: u => 0.85 + 0.25 * u, seg: 80, rad: 16 });
      const top = grp(staff, 0, 0.82, 0);
      for (let i = 0; i < 3; i++) {
        const a = i / 3 * Math.PI * 2;
        strand([[0.01 * Math.cos(a), -0.02, 0.01 * Math.sin(a)], [0.035 * Math.cos(a), 0.03, 0.035 * Math.sin(a)], [0.012 * Math.cos(a + 0.6), 0.075, 0.012 * Math.sin(a + 0.6)]], 0.008, wood, top, { seg: 24, rad: 10 });
      }
      const crystal = add(new THREE.OctahedronGeometry(0.026, 1), new THREE.MeshStandardMaterial({ color: '#ffb35c', emissive: '#ff9a3c', emissiveIntensity: 2.2, roughness: 0.3 }), top, 0, 0.05, 0);
      crystal.scale.set(1, 1.5, 1); rig.crystal = crystal;
    },
    armRest: (rig) => { rig.armL.rotation.set(-0.35, 0, 0.12); rig.elbowL.rotation.set(-0.75, 0, 0); rig.staff.rotation.set(1.1, 0, -0.2); },
  });
}

// ---------- 2) the young woman ----------
// Slim, friendly and polished: long glossy black hair with a soft side-swept fringe, warm hazel eyes with a
// subtle wing, natural rose lips; fitted plum knit top, dark slim jeans, white trainers.
export function woman(opt = {}) {
  if (GLB.woman && !opt.procedural) return fromGLB('woman', 'presenter-woman');
  return womanV5(opt);
}
function womanV5(opt = {}) {
  const skin = mat(opt.skin ?? '#f0cdb6', { roughness: 0.55 }), skinShade = mat('#e0b096', { roughness: 0.6 });
  const hairM = mat(opt.hair ?? '#241a1a', { roughness: 0.38, side: THREE.DoubleSide }), hairHi = mat('#3d2b26', { roughness: 0.35 });
  const top = mat(opt.top ?? '#6a4466', { roughness: 0.85 });
  const jeans = mat(opt.jeans ?? '#2c3140', { roughness: 0.8 });
  return makePerson({
    name: 'presenter-woman', height: opt.height ?? 1.7,
    skin, top, sleeve: top, foreMat: top, pants: jeans,
    shoe: mat('#f1efea', { roughness: 0.55 }), sole: mat('#d9d4ca'), shoeW: 0.088,
    dz: 0.62, shoulderY: 1.43, shoulderX: 0.172, hipX: 0.084, thighR: 0.07, shinR: 0.052, armR: 0.04, foreR: 0.034, neckR: 0.041,
    lowerProfile: [[0.84, 0], [0.845, 0.11], [0.88, 0.152], [0.95, 0.158], [1.02, 0.14], [1.06, 0.128], [1.065, 0]],
    torsoProfile: [[1.03, 0], [1.035, 0.13], [1.1, 0.118], [1.19, 0.13], [1.28, 0.148], [1.36, 0.155], [1.415, 0.14], [1.45, 0.095], [1.47, 0.05], [1.475, 0]],
    bust: { y: 1.28, d: 0.022 },
    headOpts: {
      a: 0.088, b: 0.11, c: 0.1, jawW: 0.72, chinV: 0.1, bridge: false, chinFwd: 0.06, cheek: 0.05, skin, skinShade,
      earW: 0.011, earH: 0.023, noseR: 0.008, noseL: 0.026, noseLat: -0.3,
      eyeLon: 0.38, eyeLat: 0.05, eyeTilt: 0.06, eyeW: 0.0145, eyeH: 0.0096, irisR: 0.0086, iris: '#6b4a2c', lash: '#141113', lashT: 0.0016, flick: true,
      browLat: 0.3, browR: 0.017, browT: 0.0021, browTilt: -0.04, browC: '#2a2226',
      mouthLat: -0.6, mouthW: 0.0155, upperLip: 0.003, lowerLip: 0.0042, lip: '#c06c72', blush: '#e8908f',
    },
    outfit: (body) => {
      const band = add(new THREE.TorusGeometry(0.05, 0.006, 12, 48), mat('#5a3858'), body, 0, 1.462, 0);
      band.rotation.x = Math.PI / 2; band.scale.set(1, 0.85, 1);
      const belt = add(new THREE.TorusGeometry(0.129, 0.006, 10, 96), mat('#1c1c20', { roughness: 0.5 }), body, 0, 1.055, 0);
      belt.rotation.x = Math.PI / 2; belt.scale.set(1, 0.62, 1);
    },
    hair: (head, o) => {
      const { a, b, c } = o.headOpts, at = head.userData.at;
      const cap = add(new THREE.SphereGeometry(1, 72, 48, 0, Math.PI * 2, 0, Math.PI * 0.56), hairM, head, 0, b * 0.04, -c * 0.03);
      cap.scale.set(a * 1.09, b * 1.07, c * 1.11); cap.rotation.x = -0.66;
      const back = lathe([[-0.31, 0], [-0.305, 0.075], [-0.25, 0.1], [-0.17, 0.098], [-0.1, 0.085], [-0.03, 0.093], [0.04, 0.096], [0.07, 0.07], [0.09, 0]], hairM, head, { rad: 96, dz: 0.82, phi0: Math.PI * 0.3, phiLen: Math.PI * 1.4 });
      back.position.z = -0.012;
      const scalp = (lon, lat, off = 0.006) => at(lon, lat, off).p;
      for (const s of [-1, 1]) for (let i = 0; i < 3; i++) {        // face-framing locks in front of the shoulders
        const p0 = scalp(s * (1.05 + i * 0.12), 0.55), p1 = scalp(s * (1.25 + i * 0.1), 0.0, 0.01), p2 = scalp(s * (1.2 + i * 0.08), -0.65, 0.016);
        strand([p0.toArray(), p1.toArray(), p2.toArray(), [p2.x * 1.12, p2.y - 0.08, p2.z + 0.015 - i * 0.01], [p2.x * 1.25, p2.y - 0.19, p2.z + 0.01 - i * 0.012]],
          0.019, hairM, head, { flatDir: q => new THREE.Vector3(q.x, 0, q.z * 0.6), flat: 0.45, taper: u => Math.min(1, (u + 0.1) / 0.2) * (1 - 0.7 * u ** 2), seg: 64, rad: 16 });
      }
      for (let i = 0; i < 9; i++) {                                 // soft side-swept fringe from a part on her left
        const f = i / 8;
        const p0 = scalp(0.42 - f * 0.1, 1.15 - f * 0.04, 0.018), p1 = scalp(0.1 - f * 0.22, 0.9 - f * 0.1, 0.015), p2 = scalp(-0.45 - f * 0.2, 0.66 - f * 0.12, 0.013), p3 = scalp(-1.0 - f * 0.12, 0.36 - f * 0.12, 0.009);
        strand([p0.toArray(), p1.toArray(), p2.toArray(), p3.toArray()], 0.019, i % 3 === 1 ? hairHi : hairM, head, { flatDir: q => q.clone().normalize(), flat: 0.3, seg: 64, rad: 16, taper: u => Math.min(1, (u + 0.05) / 0.2) * (1 - 0.8 * u ** 1.4) });
      }
      for (const s of [-1, 1]) { const e = scalp(s * 1.5, -0.2, 0.004); add(new THREE.SphereGeometry(0.0035, 16, 12), mat('#d6d9de', { metalness: 0.9, roughness: 0.2 }), head, e.x, e.y, e.z); }
    },
  });
}

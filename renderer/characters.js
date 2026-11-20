// Counterphysical presenters: two original low-poly people in the house diorama style (CLAUDE.md
// "VISUAL BLUEPRINT"): chunky, flat-shaded clothes, lightly smoothed skin, muted pastel colours.
// They replace the faceless wooden toy figure.
//
//   import { man, woman } from '../characters.js';
//   const p = man(); p.position.set(x, 0, z); scene.add(p);
//   p.pose({ talk: 0..1, wave: 0..1, point: 0..1, headYaw: rad, headPitch: rad, blink: 0..1, walk: phase });
//
// Each figure stands on y = 0, faces +z, and is real-world size (man 1.78 m, woman 1.66 m), so it sits
// next to the cars and props at the same scale. Arms, forearms, legs and head are pivot groups
// (p.rig.*) so scenes can pose them directly too. Everything is procedural geometry made here.
import * as THREE from 'three';

const flat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, metalness: 0, flatShading: true, ...x });
const soft = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.7, metalness: 0, ...x });

function mesh(geo, mat, x = 0, y = 0, z = 0, parent = null) {
  const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z);
  m.castShadow = true; m.receiveShadow = true;
  if (parent) parent.add(m);
  return m;
}
const group = (x = 0, y = 0, z = 0, parent = null) => { const g = new THREE.Group(); g.position.set(x, y, z); if (parent) parent.add(g); return g; };
// capsule hanging DOWN from its parent's origin: total length len (incl. caps), radius r
function limb(r, len, mat, parent, seg = 20) {
  const m = mesh(new THREE.CapsuleGeometry(r, Math.max(0.001, len - 2 * r), 6, seg), mat, 0, -len / 2, 0, parent);
  return m;
}
// tapered 8-sided segment hanging down from y0 to y1 (y0 > y1), elliptical cross-section (depth factor dz)
function taper(rTop, rBot, y0, y1, mat, parent, dz = 0.7, sides = 24) {
  const m = mesh(new THREE.CylinderGeometry(rTop, rBot, y0 - y1, sides), mat, 0, (y0 + y1) / 2, 0, parent);
  m.scale.z = dz; m.rotation.y = Math.PI / sides; return m;
}

// ---------- the head: skin ellipsoid, ears, nose, eyes with catchlights, brows, mouth (talks) ----------
function makeHead(o) {
  const head = new THREE.Group();
  const { a, b, c } = o;                       // ellipsoid radii x, y, z
  const sg = new THREE.SphereGeometry(1, 50, 40), P = sg.attributes.position;
  for (let i = 0; i < P.count; i++) {          // narrow the lower half into a soft jaw and chin
    const y = P.getY(i); if (y >= 0) continue;
    const t = -y; P.setX(i, P.getX(i) * (1 - (1 - o.jawW) * t * t)); P.setZ(i, P.getZ(i) * (1 - 0.12 * t * t) + 0.06 * t * t * Math.max(0, P.getZ(i)));
  }
  sg.computeVertexNormals();
  const skull = mesh(sg, o.skin, 0, 0, 0, head); skull.scale.set(a, b, c);
  // point on the front surface of the skull at (x, y), pushed out by d
  const surf = (x, y, d = 0) => {
    const k = 1 - (x / a) ** 2 - (y / b) ** 2;
    return new THREE.Vector3(x, y, c * Math.sqrt(Math.max(0.02, k)) + d);
  };
  for (const s of [-1, 1]) {
    const ear = mesh(new THREE.SphereGeometry(1, 22, 16), o.skin, s * a * 0.97, -b * 0.08, -c * 0.05, head);
    ear.scale.set(0.018, 0.034, 0.024);
  }
  const nose = mesh(new THREE.SphereGeometry(1, 22, 16), o.skin, 0, 0, 0, head);
  nose.scale.set(o.noseR, o.noseL * 0.55, o.noseR * 0.9);
  nose.position.copy(surf(0, -b * 0.2, -o.noseR * 0.2));
  // eyes: dark iris discs set into the surface, white catchlight, upper lid line
  const eyes = [];
  const irisM = soft(o.iris, { roughness: 0.25 }), whiteM = new THREE.MeshBasicMaterial({ color: '#fbf8f2' });
  const lidM = soft(o.lash);
  for (const s of [-1, 1]) {
    const p = surf(s * o.eyeX, o.eyeY, -0.004);
    const eye = group(p.x, p.y, p.z, head);
    eye.rotation.y = s * Math.asin(Math.min(0.9, p.x / a)) * 0.6;
    const iris = mesh(new THREE.SphereGeometry(1, 25, 18), irisM, 0, 0, 0, eye); iris.scale.set(o.eyeW, o.eyeH, 0.008);
    iris.castShadow = false;
    const glint = mesh(new THREE.SphereGeometry(1, 14, 11), whiteM, s * -o.eyeW * 0.3, o.eyeH * 0.35, 0.007, eye);
    glint.scale.setScalar(o.eyeW * 0.28); glint.castShadow = false;
    const lid = mesh(new THREE.BoxGeometry(o.eyeW * 2.3, o.lidT, 0.012), lidM, 0, o.eyeH * o.lidUp, 0.002, eye);
    lid.rotation.z = s * -0.18; lid.castShadow = false;
    if (o.lashFlick) {                         // small outer flick: a stylised lash, not a copy of anyone's
      const f = mesh(new THREE.BoxGeometry(o.eyeW * 0.7, o.lidT * 0.9, 0.01), lidM, s * o.eyeW * 1.25, o.eyeH * 1.15, 0.002, eye);
      f.rotation.z = s * 0.55; f.castShadow = false;
    }
    // brow
    const bp = surf(s * o.eyeX * 1.05, o.eyeY + o.browUp, 0.002);
    const brow = mesh(new THREE.BoxGeometry(o.eyeW * 2.6, o.browT, 0.014), soft(o.browC), bp.x, bp.y, bp.z, head);
    brow.rotation.set(-0.15, s * Math.asin(Math.min(0.9, bp.x / a)) * 0.7, s * o.browTilt); brow.castShadow = false;
    eyes.push({ iris, eye });
  }
  // mouth: a dark slot with a lip-coloured upper and lower edge; scale.y opens it for talking
  const mp = surf(0, o.mouthY, -0.002);
  const mouth = group(mp.x, mp.y, mp.z, head); mouth.rotation.x = -0.25;
  const inside = mesh(new THREE.SphereGeometry(1, 25, 14), soft('#5a2a26'), 0, -0.004, 0.001, mouth);
  inside.scale.set(o.mouthW * 1.1, 0.001, 0.004); inside.castShadow = false;
  const arcA = 1.25, R = o.mouthW * 2.0;           // smile line: lower arc of a small circle
  const upper = mesh(new THREE.TorusGeometry(R, o.lipT, 8, 28, arcA), soft(o.lip), 0, R * 0.92, 0.003, mouth);
  upper.rotation.z = -Math.PI / 2 - arcA / 2; upper.castShadow = false;
  const lower = new THREE.Object3D(); mouth.add(lower);
  // smile: corners lift slightly
  head.userData = { eyes, mouth, inside, upper, lower, surf, smile: o.smile ?? 0.3 };
  return head;
}

function setMouth(head, open) {
  const { inside } = head.userData;
  inside.scale.y = 0.001 + 0.013 * open;
}
function setBlink(head, v) {
  for (const { iris } of head.userData.eyes) iris.scale.y = Math.max(0.08, 1 - v) * iris.userData.h;
}

// ---------- shared body builder ----------
function makePerson(o) {
  const root = new THREE.Group(); root.name = o.name;
  const rig = {};
  const H = o.height, k = H / 1.78;              // proportions are designed at 1.78 m and scaled
  const body = group(0, 0, 0, root); body.scale.setScalar(k);
  rig.body = body;

  // legs: pivots at the hips
  const hipY = 0.93;
  for (const s of [-1, 1]) {
    const hip = group(s * o.hipX, hipY, 0, body);
    limb(o.thighR, 0.47, o.pants, hip);
    const knee = group(0, -0.45, 0, hip);
    limb(o.shinR, 0.42, o.pants, knee);
    if (o.cuff) { const cf = mesh(new THREE.CylinderGeometry(o.shinR * 1.12, o.shinR * 1.12, 0.035, 24), o.cuff, 0, -0.37, 0, knee); }
    const ankle = group(0, -0.4, 0, knee);
    const shoe = mesh(new THREE.BoxGeometry(o.shoeW, 0.075, 0.25, 3, 2, 6), o.shoe, 0, -0.045, 0.045, ankle);
    const sole = mesh(new THREE.BoxGeometry(o.shoeW * 1.04, 0.022, 0.26), o.sole, 0, -0.078, 0.045, ankle);
    const toe = mesh(new THREE.SphereGeometry(1, 22, 14), o.shoe, 0, -0.05, 0.16, ankle); toe.scale.set(o.shoeW / 2, 0.04, 0.05);
    rig[s < 0 ? 'legR' : 'legL'] = hip; rig[s < 0 ? 'kneeR' : 'kneeL'] = knee;
  }
  // pelvis + torso
  taper(o.hipR, o.hipR * 0.98, 1.02, 0.86, o.pants, body, 0.66);
  if (o.belt) taper(o.waistR * 1.03, o.waistR * 1.03, 1.035, 1.0, o.belt, body, 0.66);
  const chest = taper(o.chestR, o.waistR, o.shoulderY + 0.02, 1.0, o.top, body, o.chestDz);
  if (o.jacket) o.jacket(body, o);
  // neck + head
  mesh(new THREE.CylinderGeometry(o.neckR, o.neckR * 1.12, 0.1, 24), o.skin, 0, o.shoulderY + 0.03, 0, body);
  if (o.collar) o.collar(body, o);
  const neck = group(0, o.shoulderY + 0.06, 0, body);
  const head = makeHead(o.headOpts);
  head.position.set(0, o.headOpts.b * 0.78, 0.01); neck.add(head);
  for (const { iris } of head.userData.eyes) iris.userData.h = iris.scale.y;
  o.hair(head, o);
  rig.neck = neck; rig.head = head;
  // arms: pivots at the shoulders, hanging down, slightly away from the body
  for (const s of [-1, 1]) {
    const sh = group(s * o.shoulderX, o.shoulderY - 0.03, 0, body);
    mesh(new THREE.SphereGeometry(o.armR * 1.08, 25, 18), o.sleeve, -Math.sign(sh.position.x) * 0.012, -0.01, 0, sh);
    limb(o.armR, 0.3, o.sleeve, sh);
    const elbow = group(0, -0.28, 0, sh);
    limb(o.foreR, 0.26, o.foreMat, elbow);
    if (o.cuffSleeve) mesh(new THREE.CylinderGeometry(o.armR * 1.15, o.armR * 1.1, 0.05, 24), o.sleeve, 0, 0.0, 0, elbow);
    const wrist = group(0, -0.25, 0, elbow);
    const hand = mesh(new THREE.SphereGeometry(1, 25, 18), o.skin, 0, -0.045, 0.005, wrist); hand.scale.set(0.036, 0.055, 0.026);
    const thumb = mesh(new THREE.CapsuleGeometry(0.011, 0.03, 4, 12), o.skin, s * -0.025, -0.03, 0.02, wrist); thumb.rotation.z = s * 0.5;
    sh.rotation.z = s * 0.07;
    rig[s < 0 ? 'armR' : 'armL'] = sh; rig[s < 0 ? 'elbowR' : 'elbowL'] = elbow;
  }
  if (o.extra) o.extra(body, o);
  root.traverse(m => { if (m.isMesh && m.castShadow !== false) { m.castShadow = true; m.receiveShadow = true; } });

  root.rig = rig;
  root.height = H;
  // headTop and face height in world units (for camera framing)
  root.faceY = (o.shoulderY + 0.06 + o.headOpts.b * 0.78) * k;
  root.pose = (p = {}) => {
    const talk = p.talk ?? 0, wave = p.wave ?? 0, point = p.point ?? 0;
    setMouth(head, talk);
    setBlink(head, p.blink ?? 0);
    neck.rotation.set(p.headPitch ?? 0, p.headYaw ?? 0, p.headTilt ?? 0);
    // right arm (screen-left when facing camera) waves; left arm points forward-out
    rig.armR.rotation.set(-0.15 * wave, 0, -0.07 - 2.5 * wave);
    rig.elbowR.rotation.set(0, 0, -0.9 * wave + (wave ? 0.25 * Math.sin((p.t ?? 0) * 9) * wave : 0));
    rig.armL.rotation.set(-1.05 * point, 0, 0.07 + 0.75 * point);
    rig.elbowL.rotation.set(-0.15 * point, 0, 0);
    const w = p.walk;
    if (w !== undefined) {
      const sw = Math.sin(w) * 0.45;
      rig.legL.rotation.x = sw; rig.legR.rotation.x = -sw;
      rig.kneeL.rotation.x = Math.max(0, -Math.sin(w + 0.6)) * 0.7; rig.kneeR.rotation.x = Math.max(0, Math.sin(w + 0.6)) * 0.7;
      if (!wave) rig.armR.rotation.x = sw * 0.7;
      if (!point) rig.armL.rotation.x = -sw * 0.7;
      body.position.y = Math.abs(Math.cos(w)) * 0.02 * k;
    } else { for (const j of ['legL', 'legR', 'kneeL', 'kneeR']) rig[j].rotation.x = 0; body.position.y = 0; }
  };
  root.pose();
  return root;
}

// ---------- 1) the man: everyday, normal-looking ----------
export function man(opt = {}) {
  const skin = soft(opt.skin ?? '#d6a283'), skinShade = soft(opt.skinShade ?? '#c98f70');
  const hairC = opt.hair ?? '#3b2a20';
  const hairM = flat(hairC, { roughness: 0.9, side: THREE.DoubleSide });
  return makePerson({
    name: 'presenter-man', height: opt.height ?? 1.78,
    skin, skinShade,
    top: flat(opt.shirt ?? '#8fa6c8'),                 // powder-blue shirt
    sleeve: flat(opt.shirt ?? '#8fa6c8'), foreMat: skin, cuffSleeve: true,
    pants: flat(opt.pants ?? '#3c4352'), belt: flat('#4a3526'),
    shoe: flat('#5b4030'), sole: flat('#2f2620'),
    chestR: 0.205, waistR: 0.17, hipR: 0.165, chestDz: 0.62, shoulderX: 0.23, shoulderY: 1.43,
    hipX: 0.092, thighR: 0.084, shinR: 0.066, armR: 0.056, foreR: 0.046, neckR: 0.052, shoeW: 0.105,
    headOpts: {
      a: 0.098, b: 0.122, c: 0.108, jawW: 0.8, skin, skinShade,
      eyeX: 0.036, eyeY: 0.01, eyeW: 0.011, eyeH: 0.0125, iris: '#3a2c22', lash: '#2a1f18', lidT: 0.004,
      browC: hairC, browUp: 0.032, browT: 0.0075, browTilt: 0.04, noseR: 0.0115, noseL: 0.026, lidUp: 1.2,
      mouthY: -0.06, mouthW: 0.016, lip: '#8a5246', lipT: 0.0032,
    },
    collar: (body, o) => {                             // open shirt collar: two flat wings and a V of skin
      for (const s of [-1, 1]) {
        const w = mesh(new THREE.BoxGeometry(0.075, 0.012, 0.06), o.top, s * 0.045, o.shoulderY + 0.035, 0.07, body);
        w.rotation.set(0.5, s * -0.5, s * -0.35);
      }
      const v = mesh(new THREE.ConeGeometry(0.035, 0.08, 3), o.skin, 0, o.shoulderY - 0.02, 0.118, body);
      v.rotation.set(Math.PI + 0.25, 0, 0); v.scale.z = 0.3;
      for (let i = 0; i < 4; i++) mesh(new THREE.SphereGeometry(0.006, 11, 7), flat('#e6e3dc'), 0, o.shoulderY - 0.09 - i * 0.1, 0.125 - i * 0.004, body);
    },
    hair: (head, o) => {                               // short, tidy, side-parted; faceted
      const { a, b, c } = o.headOpts;
      const cap = mesh(new THREE.SphereGeometry(1, 32, 22, 0, Math.PI * 2, 0, 1.45), hairM, 0, b * 0.04, -c * 0.06, head);
      cap.scale.set(a * 1.1, b * 1.06, c * 1.08); cap.rotation.x = -0.5;
      const back = mesh(new THREE.SphereGeometry(1, 25, 20), hairM, 0, -b * 0.15, -c * 0.38, head); back.scale.set(a * 0.98, b * 0.72, c * 0.62);
      const quiff = mesh(new THREE.IcosahedronGeometry(1, 2), hairM, -a * 0.1, b * 0.74, c * 0.45, head);
      quiff.scale.set(a * 1.0, b * 0.28, c * 0.45); quiff.rotation.set(0.25, 0.3, 0.12);
    },
  });
}

// ---------- 2) the woman: an original design, friendly and approachable ----------
// Auburn high ponytail with a swept side fringe, teal cropped jacket over a cream top, slate trousers,
// white trainers. Her own face (round eyes, freckle-free, soft smile); not modelled on any real person
// or existing character.
export function woman(opt = {}) {
  const skin = soft(opt.skin ?? '#e7bc9c'), skinShade = soft(opt.skinShade ?? '#dba98a');
  const hairC = opt.hair ?? '#8a4630';
  const hairM = flat(hairC, { roughness: 0.85, side: THREE.DoubleSide }), hairDark = flat('#6e3523', { roughness: 0.85 });
  const jacketC = opt.jacket ?? '#2e8f86';
  const jacketM = flat(jacketC);
  return makePerson({
    name: 'presenter-woman', height: opt.height ?? 1.66,
    skin, skinShade,
    top: flat(opt.top ?? '#ece6d8'), sleeve: jacketM, foreMat: jacketM, cuffSleeve: false,
    pants: flat(opt.pants ?? '#4b5263'), cuff: flat('#4b5263'),
    shoe: flat('#efece6'), sole: flat('#c9a77c'),
    chestR: 0.17, waistR: 0.135, hipR: 0.158, chestDz: 0.64, shoulderX: 0.195, shoulderY: 1.42,
    hipX: 0.088, thighR: 0.08, shinR: 0.06, armR: 0.049, foreR: 0.041, neckR: 0.044, shoeW: 0.095,
    headOpts: {
      a: 0.104, b: 0.128, c: 0.114, jawW: 0.72, skin, skinShade,
      eyeX: 0.038, eyeY: 0.006, eyeW: 0.0135, eyeH: 0.0158, iris: '#4a3a2a', lash: '#2a1c16', lidT: 0.005, lashFlick: true, lidUp: 1.3,
      browC: '#6e3523', browUp: 0.034, browT: 0.0055, browTilt: 0.015, noseR: 0.0095, noseL: 0.022,
      mouthY: -0.064, mouthW: 0.017, lip: '#b8605a', lipT: 0.0042,
    },
    jacket: (body, o) => {                             // open cropped jacket: wider shell, cream top shows in front
      const shell = taper(o.chestR * 1.1, o.waistR * 1.18, o.shoulderY + 0.03, 1.08, jacketM, body, o.chestDz * 1.05);
      shell.material = jacketM;
      // front opening: a cream panel slightly proud of the shell
      const panel = mesh(new THREE.BoxGeometry(0.085, o.shoulderY - 1.07, 0.02), o.top, 0, (o.shoulderY + 1.08) / 2 - 0.02, o.chestR * 0.72, body);
      panel.rotation.x = 0.06;
      // lapels
      for (const s of [-1, 1]) {
        const l = mesh(new THREE.BoxGeometry(0.03, 0.17, 0.014), flat('#277a72'), s * 0.055, o.shoulderY - 0.08, o.chestR * 0.74, body);
        l.rotation.set(0.1, 0, s * 0.32);
      }
      // jacket hem band
      taper(o.waistR * 1.22, o.waistR * 1.22, 1.1, 1.06, flat('#277a72'), body, o.chestDz * 1.05);
      // cream top shows below the jacket
      taper(o.waistR * 1.04, o.waistR * 1.08, 1.06, 0.99, o.top, body, 0.68);
    },
    collar: (body, o) => {
      const v = mesh(new THREE.ConeGeometry(0.03, 0.06, 3), o.skin, 0, o.shoulderY, 0.105, body);
      v.rotation.set(Math.PI + 0.3, 0, 0); v.scale.z = 0.3;
    },
    hair: (head, o) => {
      const { a, b, c } = o.headOpts;
      const cap = mesh(new THREE.SphereGeometry(1, 36, 25, 0, Math.PI * 2, 0, 1.5), hairM, 0, b * 0.05, -c * 0.04, head);
      cap.scale.set(a * 1.1, b * 1.07, c * 1.1); cap.rotation.x = -0.42;
      const back = mesh(new THREE.SphereGeometry(1, 29, 22), hairM, 0, -b * 0.1, -c * 0.36, head); back.scale.set(a * 1.03, b * 0.8, c * 0.66);
      // swept side fringe: three faceted locks sweeping from the right part across the forehead
      const locks = [[-0.35, 0.74, 0.6, 1.05, 0.2, -0.5], [0.12, 0.7, 0.66, 0.9, 0.2, -0.35], [0.55, 0.6, 0.62, 0.7, 0.2, -0.2]];
      for (const [x, y, z, sx, sy, rz] of locks) {
        const l = mesh(new THREE.IcosahedronGeometry(1, 2), hairM, a * x, b * y, c * z, head);
        l.scale.set(a * 0.55 * sx, b * sy, c * 0.3); l.rotation.set(0.5, 0, rz);
      }
      // side strands framing the face, down to the jaw
      for (const s of [-1, 1]) {
        const st = mesh(new THREE.IcosahedronGeometry(1, 2), hairM, s * a * 0.9, -b * 0.18, c * 0.34, head);
        st.scale.set(0.009, b * 0.4, 0.018); st.rotation.set(0.1, 0, s * 0.08);
      }
      // high ponytail: tie at the crown, then a chain of tapering faceted bunches swinging down the back
      const tieP = new THREE.Vector3(0, b * 0.75, -c * 0.78);
      const tie = mesh(new THREE.TorusGeometry(0.022, 0.009, 12, 24), flat('#e2c45a'), tieP.x, tieP.y, tieP.z, head);
      tie.rotation.x = 0.9;
      const tail = group(tieP.x, tieP.y, tieP.z - 0.01, head);
      const prof = [];
      for (let k = 0; k <= 24; k++) { const u = k / 24; prof.push(new THREE.Vector2(0.004 + 0.05 * Math.sin(Math.PI * Math.pow(u, 0.7)) * (1 - 0.35 * u), -0.36 * u)); }
      const pony = mesh(new THREE.LatheGeometry(prof, 24), hairM, 0, 0.0, -0.035, tail);
      pony.scale.z = 0.8; pony.rotation.x = 0.28;
      const tip = mesh(new THREE.ConeGeometry(0.016, 0.07, 16), hairDark, 0, -0.36, -0.13, tail); tip.rotation.x = Math.PI - 0.3;
      head.userData.ponytail = tail;
      // small gold stud earrings
      for (const s of [-1, 1]) mesh(new THREE.SphereGeometry(0.0055, 11, 7), new THREE.MeshStandardMaterial({ color: '#d9b45a', metalness: 0.8, roughness: 0.3 }), s * a * 1.0, -b * 0.3, -c * 0.02, head);
    },
  });
}

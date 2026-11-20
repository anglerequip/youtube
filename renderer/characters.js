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

// ---------- 1) the man: a friendly workshop engineer ----------
// Bald on top with a short grey-brown ring of hair at the sides and back, a big bushy walrus moustache
// (no beard), round friendly face, slate-blue work coveralls with a chest pocket and zip, dark work boots.
// An original character, not modelled on any real person or existing character.
export function man(opt = {}) {
  const skin = soft(opt.skin ?? '#d9a688'), skinShade = soft(opt.skinShade ?? '#c98f70');
  const hairC = opt.hair ?? '#6b5a4c';
  const hairM = flat(hairC, { roughness: 0.9, side: THREE.DoubleSide });
  const stacheM = flat(opt.stache ?? '#5e4c3f', { roughness: 0.9 });
  const suit = flat(opt.suit ?? '#4f6d8f'), suitDark = flat('#3f5a78');
  return makePerson({
    name: 'presenter-man', height: opt.height ?? 1.78,
    skin, skinShade,
    top: suit, sleeve: suit, foreMat: suit, cuffSleeve: true,
    pants: suit, belt: suitDark,
    shoe: flat('#3a2e26'), sole: flat('#1f1a17'), shoeW: 0.115,
    chestR: 0.215, waistR: 0.19, hipR: 0.172, chestDz: 0.64, shoulderX: 0.235, shoulderY: 1.43,
    hipX: 0.094, thighR: 0.088, shinR: 0.07, armR: 0.058, foreR: 0.05, neckR: 0.056,
    headOpts: {
      a: 0.102, b: 0.12, c: 0.11, jawW: 0.86, skin, skinShade,
      eyeX: 0.037, eyeY: 0.012, eyeW: 0.0105, eyeH: 0.0118, iris: '#3c4a5a', lash: '#3a2c22', lidT: 0.004,
      browC: '#5e4c3f', browUp: 0.03, browT: 0.009, browTilt: 0.05, noseR: 0.014, noseL: 0.03, lidUp: 1.2,
      mouthY: -0.066, mouthW: 0.016, lip: '#8a5246', lipT: 0.0032,
    },
    collar: (body, o) => {                             // coverall collar, zip line, chest pocket with a pen
      for (const s of [-1, 1]) {
        const w = mesh(new THREE.BoxGeometry(0.085, 0.014, 0.07, 2, 1, 2), suitDark, s * 0.05, o.shoulderY + 0.03, 0.065, body);
        w.rotation.set(0.55, s * -0.5, s * -0.35);
      }
      mesh(new THREE.BoxGeometry(0.008, 0.42, 0.006), flat('#b9bdc2', { metalness: 0.6, roughness: 0.4 }), 0, o.shoulderY - 0.22, 0.137, body);
      const pk = mesh(new THREE.BoxGeometry(0.08, 0.075, 0.01), suitDark, 0.09, o.shoulderY - 0.13, 0.128, body); pk.rotation.y = 0.35;
      const pen = mesh(new THREE.CylinderGeometry(0.005, 0.005, 0.05, 12), flat('#c92a2e'), 0.075, o.shoulderY - 0.085, 0.131, body);
    },
    hair: (head, o) => {
      const { a, b, c } = o.headOpts;
      // horseshoe ring: a band around the back and sides, below the crown (the top stays bald)
      const ring = mesh(new THREE.SphereGeometry(1, 48, 24, Math.PI * 0.86, Math.PI * 1.28, Math.PI * 0.36, Math.PI * 0.22), hairM, 0, b * 0.02, -c * 0.02, head);
      ring.scale.set(a * 1.05, b * 1.04, c * 1.05);
      // moustache: two bushy, drooping halves meeting under the nose, covering the upper lip
      for (const s of [-1, 1]) {
        const m = mesh(new THREE.IcosahedronGeometry(1, 2), stacheM, s * 0.017, -b * 0.42, c * 0.86, head);
        m.scale.set(0.028, 0.014, 0.016); m.rotation.set(0.2, s * 0.35, s * -0.38);
        const tip = mesh(new THREE.IcosahedronGeometry(1, 2), stacheM, s * 0.036, -b * 0.5, c * 0.78, head);
        tip.scale.set(0.012, 0.016, 0.011); tip.rotation.z = s * -0.2;
      }
    },
  });
}

// ---------- 2) the woman: slim, slightly alternative look ----------
// Black layered shoulder-length hair with a long side-swept fringe and one plum streak, winged eyeliner,
// slim build and narrow face, plum zip hoodie over a charcoal tee, black skinny jeans, black trainers.
// An original character, not modelled on any real person or existing character.
export function woman(opt = {}) {
  const skin = soft(opt.skin ?? '#efcdb8'), skinShade = soft(opt.skinShade ?? '#e2b9a0');
  const hairC = opt.hair ?? '#1d1b22';
  const hairM = flat(hairC, { roughness: 0.6, side: THREE.DoubleSide }), streakM = flat(opt.streak ?? '#6a3a6e', { roughness: 0.6 });
  const hoodM = flat(opt.hoodie ?? '#5b3d5e'), hoodDark = flat('#4a3150');
  const tee = flat('#3a3b40');
  return makePerson({
    name: 'presenter-woman', height: opt.height ?? 1.68,
    skin, skinShade,
    top: tee, sleeve: hoodM, foreMat: hoodM, cuffSleeve: false,
    pants: flat(opt.pants ?? '#25262b'), cuff: flat('#25262b'),
    shoe: flat('#2a2a2e'), sole: flat('#e6e3dc'),
    chestR: 0.15, waistR: 0.118, hipR: 0.145, chestDz: 0.62, shoulderX: 0.178, shoulderY: 1.43,
    hipX: 0.082, thighR: 0.066, shinR: 0.05, armR: 0.04, foreR: 0.034, neckR: 0.04, shoeW: 0.09,
    headOpts: {
      a: 0.094, b: 0.126, c: 0.108, jawW: 0.64, skin, skinShade,
      eyeX: 0.036, eyeY: 0.008, eyeW: 0.0125, eyeH: 0.0135, iris: '#3e3428', lash: '#141216', lidT: 0.0065, lashFlick: true,
      browC: '#1d1b22', browUp: 0.03, browT: 0.005, browTilt: 0.03, noseR: 0.0085, noseL: 0.022, lidUp: 1.25,
      mouthY: -0.068, mouthW: 0.015, lip: '#a0626e', lipT: 0.0038,
    },
    jacket: (body, o) => {                             // open zip hoodie: shell, front opening, hood folded at the back
      taper(o.chestR * 1.12, o.waistR * 1.22, o.shoulderY + 0.03, 0.97, hoodM, body, o.chestDz * 1.05);
      mesh(new THREE.BoxGeometry(0.07, o.shoulderY - 0.98, 0.02), o.top, 0, (o.shoulderY + 0.97) / 2 - 0.01, o.chestR * 0.7, body);
      for (const s of [-1, 1]) mesh(new THREE.BoxGeometry(0.006, o.shoulderY - 0.98, 0.008), flat('#9a9ca2', { metalness: 0.5 }), s * 0.037, (o.shoulderY + 0.97) / 2 - 0.01, o.chestR * 0.74, body);
      taper(o.waistR * 1.26, o.waistR * 1.26, 1.0, 0.96, hoodDark, body, o.chestDz * 1.05);
      const hood = mesh(new THREE.TorusGeometry(0.085, 0.032, 12, 32, Math.PI * 1.2), hoodM, 0, o.shoulderY + 0.02, -0.03, body);
      hood.rotation.set(Math.PI / 2 + 0.25, 0, -Math.PI * 0.1 + Math.PI); hood.scale.set(1, 1.15, 1);
      for (const s of [-1, 1]) {                       // drawstrings
        const d = mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.13, 8), flat('#d8d4cc'), s * 0.05, o.shoulderY - 0.07, o.chestR * 0.78, body);
      }
    },
    collar: (body, o) => {
      const v = mesh(new THREE.CylinderGeometry(0.05, 0.055, 0.02, 24), o.top, 0, o.shoulderY + 0.01, 0.0, body);
    },
    hair: (head, o) => {
      const { a, b, c } = o.headOpts;
      const cap = mesh(new THREE.SphereGeometry(1, 48, 32, 0, Math.PI * 2, 0, 1.55), hairM, 0, b * 0.06, -c * 0.03, head);
      cap.scale.set(a * 1.12, b * 1.08, c * 1.12); cap.rotation.x = -0.32;
      // layered back and sides down to the shoulders: a flared, open-front shell
      const prof = [];
      for (let k = 0; k <= 24; k++) { const u = k / 24; prof.push(new THREE.Vector2(1.06 + 0.22 * u * u - 0.05 * Math.sin(u * Math.PI), -1.9 * u)); }
      const shell = mesh(new THREE.LatheGeometry(prof, 36, Math.PI * 0.36, Math.PI * 1.28), hairM, 0, b * 0.15, -c * 0.06, head);
      shell.scale.set(a, b * 0.95, c * 0.95);
      // long side-swept fringe from a deep left part across the forehead, over one brow
      const locks = [[0.45, 0.62, 0.74, 1.0, 0.15, 0.4], [0.05, 0.46, 0.86, 1.05, 0.15, 0.5], [-0.4, 0.3, 0.86, 0.8, 0.14, 0.62]];
      locks.forEach(([x, y, z, sx, sy, rz], k) => {
        const l = mesh(new THREE.IcosahedronGeometry(1, 2), k === 1 ? streakM : hairM, a * x, b * y, c * z, head);
        l.scale.set(a * 0.55 * sx, b * sy, c * 0.16); l.rotation.set(0.3, 0, rz);
      });
      // small silver hoop in each ear
      for (const s of [-1, 1]) {
        const h = mesh(new THREE.TorusGeometry(0.009, 0.0018, 8, 20), new THREE.MeshStandardMaterial({ color: '#c3c7cc', metalness: 0.9, roughness: 0.3 }), s * a * 1.0, -b * 0.36, -c * 0.02, head);
        h.rotation.y = Math.PI / 2;
      }
    },
  });
}

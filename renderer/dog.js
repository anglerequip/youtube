// An original smooth, high-poly mid-size mixed-breed dog for the diorama world (CLAUDE.md section 11 budget).
// Real size (about 0.5 m at the shoulder when standing), faces +z, belly on y = 0. Scruffy tan coat with a
// white chest and muzzle by default; pass colours for other coats (wolves, puppies).
// Two body set-ups share one head: lying down ('lie', the sphinx pose, head up or resting on the paws) and
// curled up asleep ('curl', nose tucked toward the tail).
//
//   import { dog } from '../dog.js';
//   const d = dog({ coat: '#b98a55' }); d.position.set(x, y, z); scene.add(d);
//   d.pose({ mode: 'lie'|'curl', t, yaw, pitch, blink: 0..1, mouth: 0..1, ears: 0..1, tail: 0..1, breath: 0..1 });
import * as THREE from 'three';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, metalness: 0, ...x });

function mesh(geo, m, parent, x = 0, y = 0, z = 0) {
  const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; o.receiveShadow = true;
  parent.add(o); return o;
}
const grp = (parent, x = 0, y = 0, z = 0) => { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; };

// smooth ellipsoid with a little shaggy noise on the surface (fur that isn't a plastic ball)
function ell(parent, m, rx, ry, rz, x = 0, y = 0, z = 0, seg = 56, shag = 0.04) {
  const g = new THREE.SphereGeometry(1, seg, Math.round(seg * 0.75));
  if (shag > 0) {
    const P = g.attributes.position, v = new THREE.Vector3();
    for (let i = 0; i < P.count; i++) {
      v.fromBufferAttribute(P, i);
      const n = Math.sin(v.x * 23.1 + v.y * 7.3) * Math.sin(v.y * 19.7 + v.z * 11.9) * Math.sin(v.z * 17.3 + v.x * 5.1);
      v.multiplyScalar(1 + shag * n); P.setXYZ(i, v.x, v.y, v.z);
    }
    g.computeVertexNormals();
  }
  const o = mesh(g, m, parent, x, y, z); o.scale.set(rx, ry, rz); return o;
}

// tapered tube along a smooth curve (legs, tail)
function strand(points, r, m, parent, taper = u => 1, seg = 40, rad = 20) {
  const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)));
  const g = new THREE.TubeGeometry(curve, seg, r, rad, false), P = g.attributes.position, v = new THREE.Vector3(), c = new THREE.Vector3();
  for (let i = 0; i <= seg; i++) {
    const u = i / seg; curve.getPointAt(u, c); const f = Math.max(0.05, taper(u));
    for (let j = 0; j <= rad; j++) { const k = i * (rad + 1) + j; v.fromBufferAttribute(P, k).sub(c).multiplyScalar(f); P.setXYZ(k, c.x + v.x, c.y + v.y, c.z + v.z); }
  }
  g.computeVertexNormals();
  const o = mesh(g, m, parent);
  for (const u of [0, 1]) { const p = curve.getPointAt(u); mesh(new THREE.SphereGeometry(r * Math.max(0.05, taper(u)), 20, 14), m, parent, p.x, p.y, p.z); }
  return o;
}

// coat colour as vertex colours: base coat, lighter patch where `white(v)` is high, darker saddle where `dark(v)` is high
function coat(o, base, light, darkC, white = null, dark = null) {
  const g = o.geometry.clone(); o.geometry = g;
  const P = g.attributes.position, n = P.count, col = new Float32Array(n * 3);
  const A = new THREE.Color(base), W = new THREE.Color(light), D = new THREE.Color(darkC), c = new THREE.Color(), v = new THREE.Vector3();
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(P, i).multiply(o.scale);
    const speck = 0.06 * Math.sin(v.x * 90 + v.y * 70) * Math.sin(v.z * 80);     // a little fur mottling
    c.copy(A).offsetHSL(0, 0, speck);
    if (dark) c.lerp(D, Math.min(1, Math.max(0, dark(v))));
    if (white) c.lerp(W, Math.min(1, Math.max(0, white(v))));
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  o.material = o.material.clone(); o.material.vertexColors = true; o.material.color.set('#ffffff');
}

function makeHead(opt, m) {
  const head = new THREE.Group(), U = head.userData;
  const skull = ell(head, m.fur, 0.085, 0.078, 0.092, 0, 0, 0, 72, 0.03);
  coat(skull, opt.coat, opt.light, opt.dark, v => (v.z > 0.05 && v.y < 0.0 ? (v.z - 0.05) * 30 : 0), v => (v.y > 0.03 ? (v.y - 0.03) * 12 : 0));
  // brow ridge and cheeks give the face its shape
  for (const s of [-1, 1]) ell(head, m.fur, 0.034, 0.02, 0.03, s * 0.035, 0.035, 0.065, 40, 0.02);
  for (const s of [-1, 1]) { const ch = ell(head, m.fur, 0.045, 0.045, 0.05, s * 0.05, -0.03, 0.04, 48, 0.05); coat(ch, opt.coat, opt.light, opt.dark, v => (v.y < 0 ? -v.y * 25 : 0)); }
  // muzzle: a rounded box shape forward of the eyes, white-ish
  const muz = ell(head, m.fur, 0.048, 0.042, 0.075, 0, -0.03, 0.105, 64, 0.025);
  coat(muz, opt.light, opt.light, opt.coat, null, v => (v.y > 0.02 ? (v.y - 0.02) * 30 : 0));
  const nose = ell(head, m.nose, 0.022, 0.016, 0.014, 0, -0.012, 0.177, 40, 0); nose.rotation.x = 0.2;
  for (const s of [-1, 1]) ell(head, m.nostril, 0.005, 0.004, 0.003, s * 0.009, -0.014, 0.19, 16, 0);
  // jaw: hinges open for a yawn, with a pink tongue
  const jaw = grp(head, 0, -0.055, 0.06); U.jaw = jaw;
  const chin = ell(jaw, m.fur, 0.04, 0.02, 0.07, 0, -0.005, 0.045, 48, 0.02); coat(chin, opt.light, opt.light, opt.light);
  ell(jaw, m.mouth, 0.034, 0.012, 0.06, 0, 0.008, 0.045, 40, 0);
  const tongue = ell(jaw, m.tongue, 0.025, 0.007, 0.05, 0, 0.012, 0.055, 32, 0); U.tongue = tongue;
  // eyes: warm brown, glossy, with lids that drop for a blink or sleep
  U.lids = [];
  for (const s of [-1, 1]) {
    const eye = grp(head, s * 0.04, 0.018, 0.07); eye.rotation.y = s * 0.35;
    ell(eye, m.lidDark, 0.019, 0.017, 0.01, 0, 0, -0.002, 40, 0);
    ell(eye, m.iris, 0.016, 0.015, 0.009, 0, 0, 0.001, 48, 0);
    ell(eye, m.pupil, 0.008, 0.008, 0.004, 0, 0, 0.0075, 32, 0);
    ell(eye, m.cornea, 0.0165, 0.0155, 0.0095, 0, 0, 0.0016, 48, 0);
    ell(eye, m.glint, 0.003, 0.003, 0.001, s * -0.005, 0.005, 0.0105, 16, 0);
    const lid = ell(eye, m.fur, 0.0205, 0.0185, 0.0115, 0, 0.03, 0.0005, 40, 0); U.lids.push(lid);
  }
  // floppy ears: soft flaps that hang by the cheeks and lift a little when the dog listens
  U.ears = []; U.pointy = !!opt.pointy;
  if (opt.pointy) {
    for (const s of [-1, 1]) {
      const ear = grp(head, s * 0.05, 0.06, -0.02); ear.rotation.z = -s * 0.25;
      const o = mesh(new THREE.ConeGeometry(0.03, 0.075, 40, 6), m.fur, ear, 0, 0.035, 0); o.scale.z = 0.45;
      const inn = mesh(new THREE.ConeGeometry(0.019, 0.05, 32, 4), m.ear, ear, 0, 0.028, 0.008); inn.scale.z = 0.3;
      U.ears.push(ear);
    }
    head.traverse(o => { if (o.isMesh) o.castShadow = true; });
    return head;
  }
  for (const s of [-1, 1]) {
    const ear = grp(head, s * 0.07, 0.05, -0.01);
    const flap = ell(ear, m.ear, 0.018, 0.07, 0.045, s * 0.012, -0.055, 0.0, 48, 0.02);
    flap.rotation.z = s * 0.15;
    coat(flap, opt.dark, opt.coat, opt.dark, null, v => (v.y < -0.04 ? 1 : 0));
    U.ears.push(ear);
  }
  head.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return head;
}

export function dog(opt = {}) {
  opt = { coat: '#b8875a', light: '#efe6d6', dark: '#7a5534', scale: 1, ...opt };
  const m = {
    fur: std(opt.coat, { roughness: 0.92 }), nose: std('#2a2321', { roughness: 0.35 }), nostril: std('#141010'),
    mouth: std('#4a2424', { roughness: 0.8 }), tongue: std('#d9827e', { roughness: 0.5 }), lidDark: std('#2d221b'),
    iris: std(opt.iris ?? '#6b4426', { roughness: 0.3 }), pupil: std('#120e0c', { roughness: 0.25 }),
    cornea: new THREE.MeshPhysicalMaterial({ color: '#ffffff', transparent: true, opacity: 0.16, roughness: 0.05, clearcoat: 1 }),
    glint: new THREE.MeshBasicMaterial({ color: '#fffaf0' }), ear: std(opt.dark, { roughness: 0.92 }), paw: std(opt.light, { roughness: 0.92 }),
  };
  const root = new THREE.Group(); root.name = 'dog';
  const body = grp(root); body.scale.setScalar(opt.scale);
  const white = v => (v.y < -0.04 ? (-0.04 - v.y) * 14 : 0) + (v.z > 0.12 ? (v.z - 0.12) * 6 : 0);
  const saddle = v => (v.y > 0.06 ? (v.y - 0.06) * 10 : 0);

  // ---- lying down (sphinx): chest up, front legs forward, hind legs folded at the sides
  const lie = grp(body);
  const breathe = grp(lie);
  const torso = ell(breathe, m.fur, 0.135, 0.115, 0.27, 0, 0.115, -0.03, 72, 0.035); coat(torso, opt.coat, opt.light, opt.dark, white, saddle);
  const chest = ell(breathe, m.fur, 0.125, 0.135, 0.12, 0, 0.15, 0.17, 64, 0.04); coat(chest, opt.coat, opt.light, opt.dark, v => (v.z > 0.04 ? (v.z - 0.04) * 16 : 0), saddle);
  const rump = ell(breathe, m.fur, 0.13, 0.11, 0.12, 0, 0.11, -0.25, 64, 0.04); coat(rump, opt.coat, opt.light, opt.dark, null, saddle);
  for (const s of [-1, 1]) {
    const thigh = ell(lie, m.fur, 0.06, 0.085, 0.12, s * 0.12, 0.08, -0.22, 56, 0.04); coat(thigh, opt.coat, opt.light, opt.dark, null, saddle);
    strand([[s * 0.13, 0.03, -0.14], [s * 0.135, 0.022, -0.06], [s * 0.13, 0.02, 0.0]], 0.024, m.fur, lie, u => 1 - 0.2 * u);   // hind lower leg
    ell(lie, m.paw, 0.03, 0.02, 0.045, s * 0.125, 0.02, 0.02, 32, 0.02);                                                         // hind paw
    strand([[s * 0.07, 0.11, 0.2], [s * 0.07, 0.04, 0.28], [s * 0.065, 0.026, 0.4]], 0.028, m.fur, lie, u => 1 - 0.18 * u);      // front leg
    ell(lie, m.paw, 0.032, 0.022, 0.048, s * 0.064, 0.022, 0.44, 32, 0.02);                                                      // front paw
    for (const k of [-1, 0, 1]) ell(lie, m.paw, 0.008, 0.006, 0.01, s * 0.064 + k * 0.014, 0.012, 0.485, 12, 0);              // toes
  }
  const lieTail = grp(lie, 0, 0.12, -0.35); root.userData.lieTail = lieTail;
  const tl = strand([[0, 0, 0], [0.04, -0.05, -0.08], [0.12, -0.09, -0.08], [0.2, -0.1, 0.0], [0.24, -0.1, 0.08]], 0.03, m.fur, lieTail, u => 1 - 0.55 * u, 48);
  coat(tl, opt.coat, opt.light, opt.dark, v => (v.x > 0.21 ? 1 : 0));
  const lieNeck = grp(lie, 0, 0.25, 0.22);
  const neck = ell(lieNeck, m.fur, 0.085, 0.1, 0.08, 0, -0.03, 0.0, 56, 0.05); coat(neck, opt.coat, opt.light, opt.dark, v => (v.z > 0.02 ? 1 : 0), saddle);

  // ---- curled up asleep: the body bends round into a doughnut, nose tucked by the tail
  const curl = grp(body); curl.visible = false;
  const arc = new THREE.TorusGeometry(0.16, 0.11, 40, 96, Math.PI * 1.55);
  const P = arc.attributes.position, v = new THREE.Vector3();
  for (let i = 0; i < P.count; i++) { v.fromBufferAttribute(P, i); const n = Math.sin(v.x * 40) * Math.sin(v.y * 37) * Math.sin(v.z * 31); v.multiplyScalar(1 + 0.03 * n); P.setXYZ(i, v.x, v.y, v.z); }
  arc.computeVertexNormals();
  const ring = mesh(arc, m.fur, curl, 0, 0.1, 0); ring.rotation.x = -Math.PI / 2; ring.scale.set(1, 1, 0.9);
  coat(ring, opt.coat, opt.light, opt.dark, v => (v.z < -0.06 ? (-0.06 - v.z) * 12 : 0), v => (v.z > 0.05 ? (v.z - 0.05) * 14 : 0));
  ell(curl, m.fur, 0.12, 0.1, 0.12, 0.16, 0.1, 0.0, 56, 0.04);                     // shoulders where the arc starts
  ell(curl, m.fur, 0.12, 0.095, 0.12, -0.1, 0.095, 0.13, 56, 0.04);                // hips where it ends
  for (const s of [-1, 1]) ell(curl, m.paw, 0.03, 0.02, 0.045, 0.2 + s * 0.04, 0.025, 0.14, 32, 0.02);
  const curlTail = grp(curl, -0.17, 0.08, 0.15);
  strand([[0, 0, 0], [0.1, -0.02, 0.08], [0.22, -0.03, 0.09], [0.3, -0.04, 0.04]], 0.028, m.fur, curlTail, u => 1 - 0.5 * u, 40);
  const curlNeck = grp(curl, 0.24, 0.19, 0.2);

  const head = makeHead(opt, m);
  const neckJoint = new THREE.Group(); neckJoint.add(head); head.position.set(0, 0.06, 0.04);
  lieNeck.add(neckJoint);
  const H = head.userData;
  root.traverse(o => { if (o.isMesh && !o.material.isMeshBasicMaterial && !o.material.transparent) { o.castShadow = true; o.receiveShadow = true; } });

  root.pose = (p = {}) => {
    const mode = p.mode ?? 'lie', t = p.t ?? 0;
    const curled = mode === 'curl';
    lie.visible = !curled; curl.visible = curled;
    if (curled) { curlNeck.add(neckJoint); neckJoint.rotation.set(0.3 + (p.pitch ?? 0), -1.75 + (p.yaw ?? 0), 0.35, 'YXZ'); head.position.set(0, 0.0, 0.0); }
    else {
      lieNeck.add(neckJoint); neckJoint.rotation.set(p.pitch ?? 0, p.yaw ?? 0, p.tilt ?? 0, 'YXZ'); head.position.set(0, 0.06, 0.04);
      const rest = Math.min(1, Math.max(0, p.rest ?? 0));          // 1 = chin down on the front paws
      lieNeck.position.set(0, 0.25 - 0.16 * rest, 0.22 + 0.1 * rest);
    }
    const bl = Math.min(1, Math.max(0, p.blink ?? 0));
    for (const lid of H.lids) { lid.visible = bl > 0.02; lid.position.y = 0.024 * (1 - bl); }
    const mo = Math.min(1, Math.max(0, p.mouth ?? 0));
    H.jaw.rotation.x = 0.55 * mo; H.tongue.position.z = 0.055 + 0.02 * mo;
    const ears = p.ears ?? 0;
    if (!H.pointy) H.ears.forEach((e, k) => { const s = k ? 1 : -1; e.rotation.set(-0.5 * ears, 0, s * (0.15 + 0.9 * ears)); });
    const br = 1 + 0.025 * Math.sin(t * (p.breathRate ?? 1.4)) * (p.breath ?? 1);
    breathe.scale.set(br, br, 1);
    const wag = 0.15 * Math.sin(t * 1.1) + 0.45 * (p.tail ?? 0) * Math.sin(t * 11);
    lieTail.rotation.y = wag; curlTail.rotation.y = wag * 0.4;
  };
  root.pose();
  root.headWorld = (vv = new THREE.Vector3()) => head.getWorldPosition(vv);
  root.userData.head = head;
  return root;
}

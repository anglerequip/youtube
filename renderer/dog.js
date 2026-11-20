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
  const skull = ell(head, m.fur, 0.085, 0.078, 0.092, 0, 0, 0, 72, 0.008);
  coat(skull, opt.coat, opt.light, opt.dark, v => (v.z > 0.05 && v.y < 0.0 ? (v.z - 0.05) * 30 : 0), v => (v.y > 0.03 ? (v.y - 0.03) * 12 : 0));
  // brow ridge and cheeks give the face its shape
  for (const s of [-1, 1]) ell(head, m.fur, 0.03, 0.016, 0.028, s * 0.035, 0.033, 0.062, 40, 0.0);
  for (const s of [-1, 1]) { const ch = ell(head, m.fur, 0.038, 0.038, 0.046, s * 0.046, -0.026, 0.04, 48, 0.01); coat(ch, opt.coat, opt.light, opt.dark, v => (v.y < 0 ? -v.y * 25 : 0)); }
  // muzzle: a rounded box shape forward of the eyes, white-ish
  const muz = ell(head, m.fur, 0.048, 0.042, 0.075, 0, -0.03, 0.105, 64, 0.006);
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
    const flap = ell(ear, m.ear, 0.018, 0.07, 0.045, s * 0.012, -0.055, 0.0, 48, 0.005);
    flap.rotation.z = s * 0.15;
    coat(flap, opt.dark, opt.coat, opt.dark, null, v => (v.y < -0.04 ? 1 : 0));
    U.ears.push(ear);
  }
  head.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return head;
}

// one continuous furry body swept along a spine: tail root (s = 0) -> rump -> waist -> chest -> neck (s = 1).
// The cross-section is an ellipse (half-width rx, half-height ry) that follows the spine, so there are no joins.
// spine(s) -> Vector3 position; frameUp(s, tangent) -> the body's "back" direction at s.
const PROFILE = [[0.0, 0.07, 0.065], [0.06, 0.112, 0.1], [0.16, 0.13, 0.118], [0.32, 0.118, 0.11], [0.5, 0.112, 0.108],
                 [0.66, 0.13, 0.13], [0.76, 0.122, 0.128], [0.86, 0.088, 0.095], [1.0, 0.07, 0.078]];
function profileAt(s) {
  let k = 0; while (k < PROFILE.length - 2 && PROFILE[k + 1][0] < s) k++;
  const [s0, a0, b0] = PROFILE[k], [s1, a1, b1] = PROFILE[k + 1], u = Math.min(1, Math.max(0, (s - s0) / (s1 - s0)));
  const e = u * u * (3 - 2 * u);
  let rx = a0 + (a1 - a0) * e, ry = b0 + (b1 - b0) * e;
  if (s < 0.06) { const c = Math.sqrt(Math.max(0, 1 - Math.pow(1 - s / 0.06, 2))); rx *= 0.35 + 0.65 * c; ry *= 0.35 + 0.65 * c; }
  return [rx, ry];
}
class Loft {
  constructor(m, parent, NS = 72, NA = 56) {
    this.NS = NS; this.NA = NA;
    const g = new THREE.BufferGeometry(), n = (NS + 1) * (NA + 1) + 2;
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    const idx = [];
    for (let i = 0; i < NS; i++) for (let j = 0; j < NA; j++) {
      const a = i * (NA + 1) + j, b = a + NA + 1;
      idx.push(a, b, a + 1, b, b + 1, a + 1);
    }
    const c0 = (NS + 1) * (NA + 1), c1 = c0 + 1;                 // caps: the rump end and the neck end
    for (let j = 0; j < NA; j++) { idx.push(c0, j + 1, j); const L = NS * (NA + 1); idx.push(c1, L + j, L + j + 1); }
    g.setIndex(idx);
    this.g = g; this.mesh = mesh(g, m, parent);
  }
  // build the surface; noise(s, a) adds a little fur texture; col(s, a, side, up) -> THREE.Color
  set(spine, upAt, breath = 1, col = null) {
    const { NS, NA, g } = this, P = g.attributes.position, C = g.attributes.color;
    const p = new THREE.Vector3(), q = new THREE.Vector3(), T = new THREE.Vector3(), U = new THREE.Vector3(), Sd = new THREE.Vector3(), v = new THREE.Vector3();
    for (let i = 0; i <= NS; i++) {
      const s = i / NS; spine(s, p); spine(Math.min(1, s + 0.01), q); spine(Math.max(0, s - 0.01), v); T.subVectors(q, v).normalize();
      upAt(s, T, U); Sd.crossVectors(U, T).normalize(); U.crossVectors(T, Sd).normalize();
      let [rx, ry] = profileAt(s);
      const bw = s > 0.12 && s < 0.8 ? breath : 1; rx *= bw; ry *= bw;
      for (let j = 0; j <= NA; j++) {
        const a = j / NA * Math.PI * 2, ca = Math.cos(a), sa = Math.sin(a);
        const fur = 1 + 0.012 * Math.sin(a * 23 + s * 61) * Math.sin(a * 17 - s * 47) + 0.006 * Math.sin(a * 41 + s * 113);
        // a slightly flatter belly: squash the lower half
        const yy = sa < 0 ? sa * 0.86 : sa;
        v.copy(p).addScaledVector(Sd, ca * rx * fur).addScaledVector(U, yy * ry * fur);
        const k = i * (NA + 1) + j; P.setXYZ(k, v.x, v.y, v.z);
        if (col) { const c = col(s, ca, sa); C.setXYZ(k, c.r, c.g, c.b); }
      }
    }
    const c0 = (NS + 1) * (NA + 1);
    spine(0, p); spine(0.01, q); T.subVectors(q, p).normalize(); P.setXYZ(c0, p.x - T.x * 0.012, p.y - T.y * 0.012, p.z - T.z * 0.012);
    spine(1, p); P.setXYZ(c0 + 1, p.x, p.y, p.z);
    if (col) { const c = col(0, 0, 0); C.setXYZ(c0, c.r, c.g, c.b); const d = col(1, 0, 1); C.setXYZ(c0 + 1, d.r, d.g, d.b); }
    P.needsUpdate = true; if (col) C.needsUpdate = true;
    g.computeVertexNormals(); g.computeBoundingSphere();
  }
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
  const furV = std('#ffffff', { roughness: 0.92, vertexColors: true });
  const root = new THREE.Group(); root.name = 'dog';
  const body = grp(root); body.scale.setScalar(opt.scale);
  const A = new THREE.Color(opt.coat), W = new THREE.Color(opt.light), D = new THREE.Color(opt.dark), cc = new THREE.Color();
  const sm = (a, b, x) => { const u = Math.min(1, Math.max(0, (x - a) / (b - a))); return u * u * (3 - 2 * u); };
  // coat on the swept body: darker saddle along the back, white belly and a white bib on the chest and throat
  const bodyCol = (s, ca, sa) => {
    cc.copy(A).lerp(D, 0.35 * sm(0.45, 0.85, sa) * sm(0.08, 0.25, s) * (1 - sm(0.7, 0.85, s)));
    const bib = sm(0.58, 0.85, s) * sm(-0.15, -0.6, sa);              // chest and throat, front/underside
    const belly = sm(-0.45, -0.8, sa);
    return cc.lerp(W, Math.min(1, bib + belly));
  };

  // ---- lying down (sphinx): chest up, front legs forward, hind legs folded at the sides
  const lie = grp(body);
  const lieBody = new Loft(furV, lie);
  const lieSpine = new THREE.CatmullRomCurve3([new THREE.Vector3()], false, 'centripetal');
  const setLieSpine = (rest) => {
    const r = rest, P = (a, b, c) => new THREE.Vector3(a, b, c);
    lieSpine.points = [P(0, 0.12, -0.36), P(0, 0.125, -0.24), P(0, 0.118, -0.06), P(0, 0.13, 0.1), P(0, 0.17 - 0.03 * r, 0.21 + 0.03 * r),
                       P(0, 0.26 - 0.13 * r, 0.27 + 0.04 * r)];
    lieSpine.updateArcLengths();
  };
  const lieUp = (s, T, U) => U.set(0, 1, 0).addScaledVector(T, -T.y).normalize();
  for (const s of [-1, 1]) {
    // haunch: a broad flattened mound on each hip, sunk into the body so it reads as one shape
    const th = ell(lie, m.fur, 0.05, 0.08, 0.125, s * 0.075, 0.078, -0.21, 64, 0.006); coat(th, opt.coat, opt.light, opt.dark, null, v => (v.y > 0.03 ? 0.35 * Math.min(1, (v.y - 0.03) * 25) : 0));
    strand([[s * 0.11, 0.035, -0.15], [s * 0.115, 0.026, -0.06], [s * 0.11, 0.024, 0.0]], 0.026, m.fur, lie, u => 1 - 0.25 * u);   // hind lower leg
    ell(lie, m.paw, 0.032, 0.022, 0.046, s * 0.108, 0.022, 0.025, 40, 0.0);                                                      // hind paw
    strand([[s * 0.07, 0.1, 0.12], [s * 0.072, 0.05, 0.21], [s * 0.068, 0.034, 0.32]], 0.037, m.fur, lie, u => 1 - 0.2 * u);     // front leg
    ell(lie, m.paw, 0.036, 0.025, 0.052, s * 0.068, 0.025, 0.36, 40, 0.0);                                                        // front paw
    for (const k of [-1, 0, 1]) ell(lie, m.paw, 0.009, 0.007, 0.011, s * 0.068 + k * 0.015, 0.013, 0.408, 16, 0);              // toes
  }
  const lieTail = grp(lie, 0, 0.11, -0.34); root.userData.lieTail = lieTail;
  const tl = strand([[0, 0, 0], [0.03, -0.04, -0.08], [0.1, -0.08, -0.1], [0.19, -0.09, -0.04], [0.24, -0.09, 0.05]], 0.032, m.fur, lieTail, u => 1 - 0.6 * u, 48);
  coat(tl, opt.coat, opt.light, opt.dark, v => (v.x > 0.2 ? 1 : 0));

  // ---- curled up asleep: the same swept body bent round into a ring, nose tucked toward the tail
  const curl = grp(body); curl.visible = false;
  const curlBody = new Loft(furV, curl);
  const R0 = 0.19, a0 = -0.15 * Math.PI, a1 = 1.3 * Math.PI;
  const curlSpine = (s, out) => { const a = a0 + (a1 - a0) * s, r = R0 * (1 - 0.18 * s); return out.set(Math.cos(a) * r, 0.11 + 0.02 * Math.sin(Math.PI * s), Math.sin(a) * r); };
  const curlUp = (s, T, U) => { const a = a0 + (a1 - a0) * s; U.set(Math.cos(a), 0.35, Math.sin(a)).normalize(); return U; };
  curlBody.set(curlSpine, curlUp, 1, bodyCol);
  for (const s of [0, 1]) ell(curl, m.paw, 0.034, 0.022, 0.048, -0.02 + s * 0.07, 0.025, -0.04 + s * 0.03, 40, 0);          // front paws by the nose
  const curlTail = grp(curl, Math.cos(a0) * R0, 0.08, Math.sin(a0) * R0);
  strand([[0, 0, 0], [-0.05, -0.02, 0.1], [-0.12, -0.03, 0.17], [-0.2, -0.04, 0.18]], 0.03, m.fur, curlTail, u => 1 - 0.55 * u, 40);
  const curlEnd = new THREE.Vector3(); curlSpine(1, curlEnd);
  const curlNeck = grp(curl, curlEnd.x, curlEnd.y + 0.02, curlEnd.z);

  const head = makeHead(opt, m);
  const neckJoint = new THREE.Group(); neckJoint.add(head); head.position.set(0, 0.04, 0.05);
  lie.add(neckJoint);
  const H = head.userData;
  root.traverse(o => { if (o.isMesh && !o.material.isMeshBasicMaterial && !o.material.transparent) { o.castShadow = true; o.receiveShadow = true; } });

  let lastRest = -1, lastBr = -1;
  const sp = (s, out) => out.copy(lieSpine.getPointAt(Math.min(1, Math.max(0, s))));
  const tipL = new THREE.Vector3(), tipC = new THREE.Vector3(); curlSpine(0.999, tipC);
  root.pose = (p = {}) => {
    const mode = p.mode ?? 'lie', t = p.t ?? 0;
    const curled = mode === 'curl';
    lie.visible = !curled; curl.visible = curled;
    const br = 1 + 0.02 * Math.sin(t * (p.breathRate ?? 1.4)) * (p.breath ?? 1);
    if (curled) {
      curlNeck.add(neckJoint);
      // the head lies on top of the ring, facing along the body's curve and turned in toward the tail
      const yawC = Math.atan2(-(curlEnd.x - tipC.x), -(curlEnd.z - tipC.z));
      neckJoint.rotation.set(0.35 + (p.pitch ?? 0), Math.atan2(curlEnd.z, -curlEnd.x) * 0 + yawC + 0.25 + (p.yaw ?? 0), 0.25, 'YXZ');
      neckJoint.position.set(0, 0, 0); head.position.set(0, 0.02, 0.03);
      if (Math.abs(br - lastBr) > 0.002) { curlBody.set(curlSpine, curlUp, br, null); lastBr = br; }
    } else {
      lie.add(neckJoint);
      const rest = Math.min(1, Math.max(0, p.rest ?? 0));          // 1 = chin down on the front paws
      if (Math.abs(rest - lastRest) > 0.004 || Math.abs(br - lastBr) > 0.002) {
        setLieSpine(rest); lieBody.set(sp, lieUp, br, lastRest < 0 ? bodyCol : null); lastRest = rest; lastBr = br;
      }
      sp(1, tipL); neckJoint.position.copy(tipL);
      neckJoint.rotation.set((p.pitch ?? 0) + 0.25 * rest, p.yaw ?? 0, p.tilt ?? 0, 'YXZ'); head.position.set(0, 0.03 - 0.01 * rest, 0.04 + 0.02 * rest);
    }
    const bl = Math.min(1, Math.max(0, p.blink ?? 0));
    for (const lid of H.lids) { lid.visible = bl > 0.02; lid.position.y = 0.024 * (1 - bl); }
    const mo = Math.min(1, Math.max(0, p.mouth ?? 0));
    H.jaw.rotation.x = 0.55 * mo; H.tongue.position.z = 0.055 + 0.02 * mo;
    const ears = p.ears ?? 0;
    if (!H.pointy) H.ears.forEach((e, k) => { const s = k ? 1 : -1; e.rotation.set(-0.5 * ears, 0, s * (0.15 + 0.9 * ears)); });
    const wag = 0.15 * Math.sin(t * 1.1) + 0.45 * (p.tail ?? 0) * Math.sin(t * 11);
    lieTail.rotation.y = wag; curlTail.rotation.y = wag * 0.4;
  };
  // first build with colours (the curl colours are set above)
  setLieSpine(0); lieBody.set(sp, lieUp, 1, bodyCol); lastRest = 0; lastBr = 1;
  root.pose();
  root.headWorld = (vv = new THREE.Vector3()) => head.getWorldPosition(vv);
  root.userData.head = head;
  return root;
}

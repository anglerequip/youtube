// An original peacock-mantis-shrimp-like stomatopod and a sea snail for the diorama world (CLAUDE.md section 11
// budget: hero spheres 48x36, tubes 24 radial). Faces +x, belly on y = 0, about 1 unit long at scale 1 (scale it
// down for a real-size animal). Green carapace and abdomen, orange legs, stalked eyes, two folded club arms.
//
//   import { mantisShrimp, seaSnail } from '../shrimp.js';
//   const s = mantisShrimp(); s.scale.setScalar(0.15); scene.add(s);
//   s.pose({ strike: 0..1, load: 0..1, t, eyes: [yawL, yawR] });   // strike 0 folded .. 1 fully thrown
//   const n = seaSnail(); n.set({ crack: 0..1, t });               // 0 whole, .5 first crack, 1 broken
import * as THREE from 'three';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.45, metalness: 0.05, ...x });
const sm = (a, b, x) => { const u = Math.min(1, Math.max(0, (x - a) / (b - a))); return u * u * (3 - 2 * u); };
const lerp = (a, b, u) => a + (b - a) * u;

function ell(par, m, rx, ry, rz, x = 0, y = 0, z = 0, seg = 48) {
  const o = new THREE.Mesh(new THREE.SphereGeometry(1, seg, Math.round(seg * 0.75)), m); o.scale.set(rx, ry, rz); o.position.set(x, y, z);
  o.castShadow = o.receiveShadow = true; par.add(o); return o;
}
function cap(par, m, r, len, seg = 24) {
  const o = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 6, seg), m); o.castShadow = true; par.add(o); return o;
}
// a rod from the group origin along +x (capsule rotated), length len
function rod(par, m, r, len, seg = 24) {
  const g = new THREE.Group(); par.add(g);
  const c = cap(g, m, r, len, seg); c.rotation.z = -Math.PI / 2; c.position.x = len / 2;
  return g;
}

export function mantisShrimp(opt = {}) {
  const root = new THREE.Group(); root.name = 'mantis';
  const green = std(opt.body ?? '#3f9a5a', { roughness: 0.35 }), teal = std('#2e8f86', { roughness: 0.35 });
  const orange = std('#e8762c', { roughness: 0.45 }), pink = std('#d4567a', { roughness: 0.35 }), cream = std('#efe2c4', { roughness: 0.5 });
  const blue = std('#3f6fb5', { roughness: 0.35 });
  const body = new THREE.Group(); body.position.y = 0.13; root.add(body);
  // carapace (head shield) and thorax
  ell(body, green, 0.17, 0.085, 0.1, 0.28, 0.02, 0, 64);
  ell(body, teal, 0.08, 0.06, 0.09, 0.1, 0.0, 0, 48);
  // abdomen: six segments tapering back, alternating green / teal edges, then a fan tail
  const segs = [];
  for (let k = 0; k < 6; k++) {
    const x = 0.0 - k * 0.085, r = 0.1 - k * 0.006;
    const s = ell(body, k % 2 ? green : std('#4ba865', { roughness: 0.35 }), 0.06, r * 0.8, r, x, 0.0 - k * 0.004, 0, 48);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(r * 0.92, 0.008, 12, 48), std('#2c6b40', { roughness: 0.4 })); rim.rotation.y = Math.PI / 2; rim.position.set(x - 0.035, -k * 0.004, 0); body.add(rim);
    segs.push(s);
  }
  const tail = new THREE.Group(); tail.position.set(-0.53, -0.02, 0); body.add(tail);
  ell(tail, green, 0.07, 0.02, 0.06, -0.04, 0, 0, 40);
  for (const s of [-1, 1]) {
    const u = ell(tail, orange, 0.075, 0.012, 0.035, -0.05, 0, s * 0.06, 40); u.rotation.y = s * 0.5;
    ell(tail, blue, 0.025, 0.014, 0.015, -0.08, 0.004, s * 0.08, 24);
  }
  // walking legs and swimmerets (orange)
  for (let k = 0; k < 3; k++) for (const s of [-1, 1]) {
    const l = rod(body, orange, 0.009, 0.1, 16); l.position.set(0.06 - k * 0.07, -0.05, s * 0.07); l.rotation.set(s * -0.5, 0, -1.7);
  }
  for (let k = 0; k < 5; k++) for (const s of [-1, 1]) { const p = ell(body, orange, 0.02, 0.008, 0.03, -0.05 - k * 0.085, -0.075, s * 0.035, 24); p.rotation.x = s * 0.4; }
  // head: stalked eyes, antennae with orange scales
  const head = new THREE.Group(); head.position.set(0.44, 0.03, 0); body.add(head);
  const eyes = [];
  for (const s of [-1, 1]) {
    const stalk = new THREE.Group(); stalk.position.set(0.0, 0.03, s * 0.025); head.add(stalk);
    const st = cap(stalk, teal, 0.012, 0.06, 24); st.position.y = 0.035;
    const eye = new THREE.Group(); eye.position.y = 0.08; stalk.add(eye);
    ell(eye, std('#5aa36a', { roughness: 0.25 }), 0.026, 0.03, 0.026, 0, 0.0, 0, 48);
    ell(eye, std('#e2c45a', { roughness: 0.25 }), 0.027, 0.006, 0.027, 0, 0.0, 0, 48);        // the mid band
    ell(eye, std('#141210', { roughness: 0.2 }), 0.008, 0.014, 0.008, 0.022, 0.0, 0, 24);
    stalk.rotation.z = -0.25; stalk.rotation.x = s * -0.2;
    eyes.push(stalk);
    const ant = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([[0.02, 0.0, 0], [0.12, 0.04, s * 0.04], [0.25, 0.1, s * 0.1], [0.36, 0.1, s * 0.18]].map(p => new THREE.Vector3(...p))), 40, 0.004, 12), orange);
    ant.position.z = s * 0.02; head.add(ant);
    const scale = ell(head, orange, 0.06, 0.008, 0.025, 0.06, 0.0, s * 0.06, 32); scale.rotation.y = -s * 0.5;
  }
  // the two club arms under the head: merus (upper arm) -> club (propodus + heel). Folded like a jackknife.
  const arms = [];
  for (const s of [-1, 1]) {
    const sh = new THREE.Group(); sh.position.set(0.38, 0.0, s * 0.055); body.add(sh);
    const merus = rod(sh, green, 0.022, 0.16, 24);
    // the saddle spring: a hyperbolic-paraboloid patch on top of the merus near the shoulder; it squashes when loaded
    const saddleGeo = new THREE.PlaneGeometry(0.06, 0.04, 24, 16), P = saddleGeo.attributes.position;
    for (let i = 0; i < P.count; i++) { const x = P.getX(i) / 0.03, y = P.getY(i) / 0.02; P.setZ(i, 0.012 * (x * x - y * y)); }
    saddleGeo.computeVertexNormals();
    const saddleM = std('#e2c45a', { roughness: 0.3, emissive: '#ff9a1f', emissiveIntensity: 0, side: THREE.DoubleSide });
    const saddle = new THREE.Mesh(saddleGeo, saddleM); saddle.rotation.x = -Math.PI / 2; saddle.position.set(0.04, 0.026, 0); merus.add(saddle);
    const latch = ell(merus, std('#2a2321', { roughness: 0.4 }), 0.012, 0.009, 0.012, 0.015, -0.022, 0, 24);
    const elbow = new THREE.Group(); elbow.position.x = 0.16; merus.add(elbow);
    const club = rod(elbow, teal, 0.018, 0.12, 24);
    const heel = ell(club, pink, 0.034, 0.03, 0.03, 0.13, 0, 0, 48);
    const dactyl = rod(club, cream, 0.008, 0.07, 16); dactyl.position.x = 0.14; dactyl.rotation.z = 2.6;
    arms.push({ sh, merus, elbow, saddle, saddleM, latch, heel });
  }
  root.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  const hv = new THREE.Vector3();
  root.pose = (p = {}) => {
    const st = Math.min(1, Math.max(0, p.strike ?? 0)), ld = Math.min(1, Math.max(0, p.load ?? 0)), t = p.t ?? 0;
    for (const a of arms) {
      // folded: merus points down and back, club folded up along it; thrown: merus forward-down, club straight out
      a.sh.rotation.z = lerp(-2.6 - 0.12 * ld, -0.25, st);
      a.elbow.rotation.z = lerp(-2.7, 0.3, st);
      a.saddle.scale.set(1, 1, 1 - 0.55 * ld);
      a.saddleM.emissiveIntensity = 1.4 * ld;
    }
    const ey = p.eyes ?? [0.25 * Math.sin(t * 0.9), -0.25 * Math.sin(t * 0.7 + 1)];
    eyes.forEach((e, k) => { e.rotation.y = ey[k]; });
    tail.rotation.z = 0.06 * Math.sin(t * 1.3);
    segs.forEach((s, k) => { s.position.y = 0.004 * Math.sin(t * 2 + k); });
  };
  root.pose();
  // world position of a club heel (the hitting surface)
  root.heelWorld = (v = new THREE.Vector3()) => arms[1].heel.getWorldPosition(v);
  return root;
}

// a sea snail in a spiral (turbinate) shell, faces +x; the shell can crack (dark lines, then shards)
export function seaSnail(opt = {}) {
  const root = new THREE.Group();
  const shellM = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.55, vertexColors: true });
  // the shell: a tube along a conical helix whose radius grows toward the opening
  const N = 220, pts = [], turns = 3.6, H = 0.2, R0 = 0.008, R1 = 0.042;
  for (let k = 0; k <= N; k++) {
    const u = k / N, a = u * turns * Math.PI * 2, r = lerp(0.004, 0.05, Math.pow(u, 1.2));
    pts.push(new THREE.Vector3(Math.cos(a) * r, H * (1 - u), Math.sin(a) * r));
  }
  const curve = new THREE.CatmullRomCurve3(pts);
  const geo = new THREE.TubeGeometry(curve, 320, 1, 32, false), P = geo.attributes.position, c = new THREE.Vector3(), v = new THREE.Vector3();
  const col = new Float32Array(P.count * 3), A = new THREE.Color('#e9dcc2'), B = new THREE.Color('#9a5a3a'), C = new THREE.Color();
  for (let i = 0; i <= 320; i++) {
    const u = i / 320; curve.getPointAt(u, c); const r = lerp(R0, R1, Math.pow(u, 1.15));
    for (let j = 0; j <= 32; j++) {
      const k = i * 33 + j; v.fromBufferAttribute(P, k).sub(c).multiplyScalar(r); P.setXYZ(k, c.x + v.x, c.y + v.y, c.z + v.z);
      C.copy(A).lerp(B, 0.7 * sm(0.5, 0.9, Math.sin(u * 60)));
      col[k * 3] = C.r; col[k * 3 + 1] = C.g; col[k * 3 + 2] = C.b;
    }
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3)); geo.computeVertexNormals();
  const shell = new THREE.Mesh(geo, shellM); shell.castShadow = shell.receiveShadow = true;
  const sg = new THREE.Group(); sg.add(shell); sg.rotation.z = -1.2; sg.position.set(0, 0.05, 0); root.add(sg);
  // the snail's foot and head peeking out
  const foot = ell(root, std('#b9a68a', { roughness: 0.7 }), 0.07, 0.018, 0.04, 0.04, 0.012, 0, 40);
  for (const s of [-1, 1]) { const tn = rod(root, std('#b9a68a'), 0.004, 0.04, 12); tn.position.set(0.1, 0.02, s * 0.012); tn.rotation.set(s * 0.4, 0, 0.6); }
  // cracks: dark thin strips over the shell; shards: faceted pieces that fly off
  const crackM = new THREE.MeshBasicMaterial({ color: '#2a1d16' });
  const cracks = [];
  for (let k = 0; k < 7; k++) {
    const a = k * 0.9, pts2 = [];
    for (let j = 0; j < 6; j++) pts2.push(new THREE.Vector3(0.07 * Math.cos(a + j * 0.25) + 0.006 * Math.sin(j * 3 + k), 0.06 + 0.012 * j * (k % 2 ? 1 : -1), 0.07 * Math.sin(a + j * 0.25)));
    const cr = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts2), 24, 0.0025, 8), crackM); cr.visible = false; root.add(cr); cracks.push(cr);
  }
  const shardM = std('#e9dcc2', { roughness: 0.6, flatShading: true });
  const shards = [];
  for (let k = 0; k < 9; k++) {
    const s = new THREE.Mesh(new THREE.IcosahedronGeometry(0.012 + 0.006 * (k % 3), 1), shardM); s.visible = false; s.castShadow = true;
    const a = k * 0.7;
    s.userData.v = [0.25 + 0.4 * Math.cos(a) * 0.5, 0.35 + 0.2 * ((k * 5) % 3), 0.4 * Math.sin(a)]; root.add(s); shards.push(s);
  }
  root.set = (p = {}) => {
    const cr = p.crack ?? 0, tau = p.shardT ?? 0;
    cracks.forEach((c, k) => { c.visible = cr >= (k < 3 ? 0.4 : 0.9); });
    shards.forEach(s => {
      s.visible = cr >= 0.9 && tau > 0 && tau < 1.2;
      const v = s.userData.v; s.position.set(0.04 + v[0] * tau, 0.09 + v[1] * tau - 0.5 * tau * tau, v[2] * tau); s.rotation.set(tau * 5, tau * 3, 0);
    });
    sg.rotation.x = 0.04 * Math.sin((p.t ?? 0) * 0.5);
  };
  root.set();
  return root;
}

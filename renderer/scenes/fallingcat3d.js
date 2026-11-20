// How a falling cat turns over (content/episodes/falling-cat/plan.py).
// The shared daylight home set (renderer/sets/home.js) with a floor cushion under the tall bookshelf. A ginger
// tabby asleep on its back on the top shelf rolls off and falls (slow motion, labelled), bends at the waist and turns
// its front and back halves separately: front legs tucked while the front half turns a lot and the back half a
// little the other way, then the reverse, and lands feet down on the cushion. Coloured rings with riders show each
// half's turn. A chronophotograph wall of six frames for the history beat; a kitten for the kittens beat.
// This file only draws what the plan lists.
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { cat } from '../cat.js';
import { home } from '../sets/home.js';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, ...x });
const sm = (a, b, x) => { const u = Math.min(1, Math.max(0, (x - a) / (b - a))); return u * u * (3 - 2 * u); };

// ---- a two-half cat for the twist. Faces +x, origin at the waist, belly toward local -y.
// set({ rollF, rollR, bend, tuckF, tuckR }) : each half rolls about its own spine axis; bend folds both halves
// down at the waist; tuckF / tuckR fold the front / hind legs in against the body (1) or stretch them out (0).
function twistCat(opt = {}) {
  const coat = opt.coat ?? '#d9893f', stripe = opt.stripe ?? '#a9581f', cream = '#f2e3c9';
  const furV = std('#ffffff', { roughness: 0.9, vertexColors: true });
  const root = new THREE.Group();
  const A = new THREE.Color(coat), Sx = new THREE.Color(stripe), W = new THREE.Color(cream), c = new THREE.Color(), v = new THREE.Vector3();
  // ellipsoid painted as a tabby: stripes across the back along x, cream belly underneath
  const tabby = (par, rx, ry, rz, x, y, z, seg = 56, stripes = true) => {
    const g = new THREE.SphereGeometry(1, seg, Math.round(seg * 0.75)), P = g.attributes.position, col = new Float32Array(P.count * 3);
    for (let i = 0; i < P.count; i++) {
      v.fromBufferAttribute(P, i);
      const wx = x + v.x * rx;
      c.copy(A);
      if (stripes) c.lerp(Sx, 0.75 * sm(0.55, 0.9, Math.sin(wx * 70)) * sm(-0.1, 0.4, v.y));
      c.lerp(W, sm(-0.15, -0.6, v.y));
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
    }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const o = new THREE.Mesh(g, furV); o.scale.set(rx, ry, rz); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; par.add(o); return o;
  };
  const plain = (par, m, rx, ry, rz, x, y, z, seg = 40) => { const o = new THREE.Mesh(new THREE.SphereGeometry(1, seg, Math.round(seg * 0.75)), m); o.scale.set(rx, ry, rz); o.position.set(x, y, z); o.castShadow = true; par.add(o); return o; };
  const leg = (par, x, y, z, len, r, m) => {
    const g = new THREE.Group(); g.position.set(x, y, z); par.add(g);
    const tube = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 6, 24), m); tube.position.y = -len / 2; tube.castShadow = true; g.add(tube);
    plain(g, std(cream, { roughness: 0.9 }), r * 1.15, r * 0.8, r * 1.5, r * 0.4, -len - r * 0.6, 0, 24);
    return g;
  };
  const legM = std(coat, { roughness: 0.9 });
  // front half: bend frame (fb) -> roll frame (fr)
  const fb = new THREE.Group(); root.add(fb);
  const fr = new THREE.Group(); fb.add(fr);
  tabby(fr, 0.15, 0.085, 0.09, 0.1, 0, 0);
  const head = new THREE.Group(); head.position.set(0.27, 0.035, 0); fr.add(head);
  tabby(head, 0.065, 0.06, 0.07, 0, 0, 0, 56);
  plain(head, std(cream, { roughness: 0.9 }), 0.035, 0.025, 0.04, 0.05, -0.022, 0, 40);
  plain(head, std('#c46a6a', { roughness: 0.4 }), 0.008, 0.006, 0.01, 0.083, -0.008, 0, 24);
  for (const s of [-1, 1]) {
    const ear = new THREE.Mesh(new THREE.ConeGeometry(0.026, 0.05, 32), legM); ear.position.set(-0.01, 0.058, s * 0.035); ear.rotation.x = s * -0.35; ear.castShadow = true; head.add(ear);
    const inner = new THREE.Mesh(new THREE.ConeGeometry(0.016, 0.035, 32), std('#e3a7a0')); inner.position.set(0.004, 0.054, s * 0.035); inner.rotation.x = s * -0.35; head.add(inner);
    plain(head, std('#8fae3a', { roughness: 0.25 }), 0.012, 0.016, 0.014, 0.052, 0.012, s * 0.03, 32);
    plain(head, std('#141210', { roughness: 0.2 }), 0.004, 0.013, 0.006, 0.062, 0.012, s * 0.031, 24);
    for (const k of [0, 1]) { const w = new THREE.Mesh(new THREE.CylinderGeometry(0.0012, 0.0006, 0.09, 8), std('#f4efe6')); w.position.set(0.06, -0.02 + k * 0.01, s * 0.06); w.rotation.set(s * 1.25, 0, 0.15 - 0.25 * k); head.add(w); }
  }
  const fl = [-1, 1].map(s => leg(fr, 0.16, -0.05, s * 0.045, 0.13, 0.017, legM));
  // back half: bend frame (rb) -> roll frame (rr)
  const rb = new THREE.Group(); root.add(rb);
  const rr = new THREE.Group(); rb.add(rr);
  tabby(rr, 0.15, 0.09, 0.095, -0.1, 0, 0);
  const hl = [-1, 1].map(s => leg(rr, -0.17, -0.05, s * 0.05, 0.15, 0.02, legM));
  const tailPts = [[-0.24, 0.02, 0], [-0.32, 0.05, 0.0], [-0.4, 0.09, 0.03], [-0.46, 0.15, 0.05]].map(p => new THREE.Vector3(...p));
  const tail = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(tailPts), 40, 0.018, 20), std(coat)); tail.castShadow = true; rr.add(tail);
  plain(rr, std(stripe), 0.022, 0.022, 0.022, -0.46, 0.15, 0.05, 24);
  // the rings: drawn in the bend frame (they stay put); a rider on each ring turns with its half
  const ring = (par, rollPar, rad, color, x) => {
    const g = new THREE.Group(); g.position.x = x; par.add(g);
    const m = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.0, depthWrite: false });
    const t = new THREE.Mesh(new THREE.TorusGeometry(rad, 0.006, 12, 96), m); t.rotation.y = Math.PI / 2; g.add(t);
    const rider = new THREE.Mesh(new THREE.ConeGeometry(0.02, 0.05, 32), m); rider.position.set(x, rad, 0); rollPar.add(rider);
    return { g, m, rider };
  };
  const ringF = ring(fb, fr, 0.15, '#2e8f86', 0.1), ringR = ring(rb, rr, 0.15, '#e2c45a', -0.1);
  root.traverse(o => { if (o.isMesh && o.material.isMeshBasicMaterial) o.castShadow = false; });
  root.set = (p = {}) => {
    const bend = p.bend ?? 0;
    fb.rotation.set(0, 0, 0.45 * bend); rb.rotation.set(0, 0, -0.45 * bend);       // fold nose and hips up: toward the belly of an upside-down cat
    fr.rotation.x = p.rollF ?? 0; rr.rotation.x = p.rollR ?? 0;
    const tf = p.tuckF ?? 0, tr = p.tuckR ?? 0;
    fl.forEach(l => { l.rotation.z = 1.35 * tf - 0.15 * (1 - tf); });                // tucked: folded forward against the chest
    hl.forEach(l => { l.rotation.z = 1.25 * tr - 0.35 * (1 - tr); });                // tucked: drawn up under the belly
    tail.rotation.x = 0.3 * Math.sin((p.t ?? 0) * 1.7);
    const ro = p.rings ?? 0;
    [[ringF, p.dir?.[0] ?? 1], [ringR, p.dir?.[1] ?? 1]].forEach(([R, d]) => {
      R.m.opacity = 0.85 * ro; R.g.visible = R.rider.visible = ro > 0.01;
      R.rider.rotation.x = d >= 0 ? Math.PI / 2 : -Math.PI / 2;             // points the way that half is turning
    });
  };
  root.set();
  return root;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  world.ground(600); world.hills(12, 130);
  const H = home(world, { cushion: true });
  const kitty = twistCat(); S.add(kitty);
  const wiz = man(); wiz.position.set(...L.wiz); wiz.rotation.y = L.wiz_face; S.add(wiz);
  const wom = woman(); wom.position.set(...L.woman); wom.rotation.y = L.woman_face; S.add(wom);
  const lift = new THREE.Color('#3a3640').convertSRGBToLinear();
  for (const p of [wiz, wom]) p.traverse(o => {
    if (!o.isMesh) return;
    if (/^z_(staff|stone|fork)/.test(o.name)) { o.visible = false; return; }
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || !m.color || m.isMeshBasicMaterial) continue;
      if (Math.max(m.color.r, m.color.g, m.color.b) < lift.r) { m.color.r = Math.max(m.color.r, lift.r); m.color.g = Math.max(m.color.g, lift.g); m.color.b = Math.max(m.color.b, lift.b); }
    }
  });
  const kit = cat({ scale: 0.55, coat: '#d9893f', stripe: '#a9581f' }); kit.position.set(...L.kitten); kit.rotation.y = L.kitten_yaw; S.add(kit);

  // the chronophotograph wall: six dark frames, 2 x 3, each holding one phase of the turn
  const ch = new THREE.Group(); ch.position.set(...L.chrono); S.add(ch);
  const wall = new THREE.Mesh(new THREE.BoxGeometry(3.2, 4.2, 0.1, 2, 2, 1), std('#d9c7a0', { roughness: 0.95 })); wall.position.set(0, 2.0, -0.1); wall.receiveShadow = true; ch.add(wall);
  const floor = new THREE.Mesh(new THREE.BoxGeometry(6, 0.1, 4), MATfloor()); floor.position.set(0, -0.05, 1.6); floor.receiveShadow = true; ch.add(floor);
  const phases = plan.layout.chrono_phases;
  const frameCats = phases.map((ph, k) => {
    const col = k % 2, row = Math.floor(k / 2);
    const x = col ? 0.5 : -0.5, y = 3.15 - row * 1.0;
    const panel = new THREE.Mesh(new THREE.BoxGeometry(0.92, 0.9, 0.04, 2, 2, 1), std('#2a2420', { roughness: 0.9 })); panel.position.set(x, y, -0.02); ch.add(panel);
    const rim = new THREE.Mesh(new THREE.BoxGeometry(0.98, 0.96, 0.03), std('#8a6342', { roughness: 0.7 })); rim.position.set(x, y, -0.04); ch.add(rim);
    for (let g = -1; g <= 1; g++) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.004, 0.86, 0.002), new THREE.MeshBasicMaterial({ color: '#6e655c' })); l.position.set(x + g * 0.25, y, 0.002); ch.add(l); }
    const c = twistCat({ coat: '#e8dcc6', stripe: '#b9a68a' }); c.scale.setScalar(1.0); c.position.set(x + 0.06, y, 0.25);
    c.set({ ...ph, rings: 0 }); ch.add(c);
    return c;
  });
  const lampC = new THREE.PointLight('#fff1dc', 3.0, 8, 2); lampC.position.set(0, 2.5, 2.5); ch.add(lampC);

  S.updateMatrixWorld(true);
  const wp = new THREE.Vector3();
  S.traverse(o => {
    if (!o.isMesh || !o.castShadow) return;
    o.getWorldPosition(wp);
    const near = (Math.abs(wp.x) < 4 && wp.z > -3 && wp.z < 3) || Math.hypot(wp.x - L.chrono[0], wp.z - L.chrono[2]) < 8;
    if (!near) o.castShadow = false;
  });
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const v = new THREE.Vector3();
  const headLook = (person, target, maxYaw = 0.9, eye = 1.5) => {
    v.set(...target).sub(person.position);
    let yaw = Math.atan2(v.x, v.z) - person.rotation.y; yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    const pitch = -Math.atan2(target[1] - person.position.y - eye, Math.hypot(v.x, v.z));
    return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, yaw)), headPitch: Math.max(-0.45, Math.min(0.5, pitch)) };
  };
  const wizHead = [L.wiz[0], 1.65, L.wiz[2]], womHead = [L.woman[0], 1.55, L.woman[2]];
  const catPt = [0, 0, 0], kitPt = [L.kitten[0], 0.3, L.kitten[2]];
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(1.0, 0, -1.0),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      kitty.position.set(F.cat_x[k], F.cat_y[k], F.cat_z[k]);
      kitty.rotation.set(0, F.cat_yaw[k], 0);
      kitty.set({ rollF: F.roll_f[k], rollR: F.roll_r[k], bend: F.bend[k], tuckF: F.tuck_f[k], tuckR: F.tuck_r[k], rings: F.rings[k], t,
                  dir: [F.dir_f[k], F.dir_r[k]] });
      catPt[0] = F.cat_x[k]; catPt[1] = F.cat_y[k]; catPt[2] = F.cat_z[k];
      kit.visible = F.kitten_on[k] > 0;
      kit.pose({ mode: 'sit', t, blink: (t % 3.3) < 0.12 ? 1 : 0, pitch: -0.1, yaw: 0.2 * Math.sin(t * 0.8), tail: 0.3 });
      const lw = F.look_w[k], lm = F.look_m[k];
      const tw = lw === 'woman' ? womHead : lw === 'kitten' ? kitPt : catPt;
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, ...headLook(wiz, tw, 0.9, 1.6), headTilt: 0.04 * Math.sin(t * 0.7), point: F.wiz_point[k] });
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, ...headLook(wom, lm === 'cat' ? catPt : wizHead), headTilt: 0.05 * Math.sin(t * 0.9 + 1), point: F.woman_point[k] });
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i);
        world.setLighting(shot.lighting ?? 'key', new THREE.Vector3(fp[0], 0, fp[2]));
        const sc = world.sun.shadow.camera, e2 = 5;
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.far = 80; sc.updateProjectionMatrix();
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.05, Math.max(0.005, d * 0.02)); world.camera.far = 500; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const fp = focalPt(i);
      const ent = Math.hypot(fp[0] - L.chrono[0], fp[2] - L.chrono[2]) < 8 ? 'halves' : 'cat';
      return [{ entity: ent, part: 'subject', kind: 'thickness', p: fp, size: 0.25 }];
    },
    vars() { return {}; },
  };
}

function MATfloor() { return std('#a27a52', { roughness: 0.7 }); }

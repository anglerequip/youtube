// How dogs drink (content/episodes/dog-drinking/plan.py).
// The shared daylight home set (renderer/sets/home.js): a dog lies at a steel water bowl in the kitchen and laps,
// flinging droplets; the wizard watches, the woman explains; a cat drinks neatly at a second bowl.
// Two slow-motion macro rigs far away (labelled as an illustration): a big stylised dog muzzle whose tongue curls
// backwards, slaps the water, pulls up a column and bites it off; and a cat muzzle that only touches the surface.
// This file only draws what the plan lists.
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { dog } from '../dog.js';
import { cat } from '../cat.js';
import { home, bowl, softBox } from '../sets/home.js';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.8, ...x });
const clamp01 = x => Math.min(1, Math.max(0, x));
const smooth = t => { t = clamp01(t); return t * t * (3 - 2 * t); };
const lerp = (a, b, u) => a + (b - a) * u;
const waterMat = () => new THREE.MeshPhysicalMaterial({ color: '#9fd0e6', roughness: 0.15, metalness: 0,
  transparent: true, opacity: 0.82, emissive: '#3d7f9c', emissiveIntensity: 0.12, clearcoat: 0.3, clearcoatRoughness: 0.3 });

// ---- one slow-motion lapping rig: a big stylised muzzle over a big bowl. style 'dog' or 'cat'.
// phase (0..1 per lap): 0-.25 tongue goes down (curling backwards), .25-.3 slap, .3-.55 yank up with the column
// following, .55-.62 jaw snaps shut on the column top, .62-.8 the rest of the column falls back, .62-.9 the ladle
// of leftover water is flung out sideways, .9-1 the jaw opens again.
function lapRig(S, O, style) {
  const g = new THREE.Group(); g.position.set(...O); S.add(g);
  const isDog = style === 'dog';
  const fur = std(isDog ? '#b8875a' : '#d9893f', { roughness: 0.92 }), light = std(isDog ? '#efe6d6' : '#f2e3c9', { roughness: 0.92 });
  const SURF = 0.62, CX = 0.45, DEEP = isDog ? -0.1 : 0.03, HY = isDog ? 0 : -1.05;   // HY: the cat's head sits lower, closer to the water   // the dog plunges the tongue in; the cat only touches
  // floor, back wall and the bowl
  const tiles = new THREE.Mesh(new THREE.BoxGeometry(16, 0.1, 12), std('#d8cbb6', { roughness: 0.6 })); tiles.position.set(0, -0.05, -1); tiles.receiveShadow = true; g.add(tiles);
  for (let k = -7; k <= 7; k++) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.003, 12), std('#b5a58f')); l.position.set(k * 1.1, 0.002, -1); g.add(l); }
  for (let k = -5; k <= 4; k++) { const l = new THREE.Mesh(new THREE.BoxGeometry(16, 0.003, 0.03), std('#b5a58f')); l.position.set(0, 0.002, k * 1.1); g.add(l); }
  const wall = new THREE.Mesh(new THREE.BoxGeometry(16, 9, 0.2), std(isDog ? '#e2d6bf' : '#b9c4b0', { roughness: 0.95 })); wall.position.set(0, 4.5, -6.5); wall.receiveShadow = true; g.add(wall);
  const cab = new THREE.Mesh(new THREE.BoxGeometry(7, 2.8, 1.2, 4, 4, 4), std('#8fa6c8', { roughness: 0.55 })); cab.position.set(-3.5, 1.4, -5.6); cab.receiveShadow = true; g.add(cab);
  const B = bowl(isDog ? '#c3c7cc' : '#d9b3a6', 2.6 / 1.05); B.scale.set(1, 0.62 / 0.05 * 0.065, 1); B.position.set(CX, 0, 0);
  B.userData.water.visible = false; g.add(B);
  B.traverse(o => { if (o.isMesh) { o.material = o.material.clone(); o.material.metalness = 0.35; o.material.roughness = 0.5; } });   // no sun glints blooming at this scale
  const surf = new THREE.Mesh(new THREE.CircleGeometry(2.35, 96), new THREE.MeshStandardMaterial({ color: '#8cc2d9', roughness: 0.45, transparent: true, opacity: 0.92 })); surf.rotation.x = -Math.PI / 2; surf.position.set(CX, SURF, 0); g.add(surf);

  // muzzle (faces +x): skull, upper jaw, nose, eye, ear and a hinged lower jaw
  const head = new THREE.Group(); head.position.y = HY; g.add(head);
  const ell = (m, rx, ry, rz, x, y, z, par = head, seg = 64) => { const o = new THREE.Mesh(new THREE.SphereGeometry(1, seg, Math.round(seg * 0.75)), m); o.scale.set(rx, ry, rz); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; par.add(o); return o; };
  const L = isDog ? 1 : 0.75;                        // the cat's muzzle is shorter and rounder
  ell(fur, 1.5, 1.35, 1.25, -2.6 * L - 0.4, 3.35, 0);
  ell(fur, 1.55 * L, 0.55, 0.72, -0.75 * L, 2.85, 0);
  ell(light, 1.2 * L, 0.32, 0.6, -0.55 * L, 2.5, 0);
  ell(std('#2a2321', { roughness: 0.35 }), isDog ? 0.3 : 0.16, isDog ? 0.24 : 0.12, isDog ? 0.32 : 0.18, 0.75 * L, 3.02, 0);
  for (const s of [-1, 1]) {
    ell(std('#f3efe6', { roughness: 0.3 }), 0.2, 0.2, 0.2, -1.75 * L, 3.75, s * 0.78, head, 48);
    ell(std(isDog ? '#5b3a20' : '#7a9a3a', { roughness: 0.3 }), 0.12, 0.13, 0.12, -1.62 * L, 3.77, s * 0.86, head, 48);
    ell(std('#120e0c'), isDog ? 0.07 : 0.03, 0.09, 0.07, -1.56 * L, 3.77, s * 0.92, head, 32);
    if (isDog) { const ear = ell(std('#7a5534', { roughness: 0.92 }), 0.55, 1.0, 0.18, -2.9, 3.3, s * 1.2); ear.rotation.x = s * 0.25; }
    else { const ear = new THREE.Mesh(new THREE.ConeGeometry(0.45, 0.9, 32), fur); ear.position.set(-2.8 * L, 4.5, s * 0.75); ear.rotation.x = s * -0.3; ear.castShadow = true; head.add(ear); }
  }
  if (!isDog) for (const s of [-1, 1]) for (const k of [0, 1, 2]) {         // whiskers
    const w = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.004, 1.4, 16), std('#f4efe6')); w.position.set(0.1, 2.75 + k * 0.1, s * 0.75); w.rotation.set(s * 1.3, 0, 0.2 - k * 0.15); head.add(w);
  }
  const jaw = new THREE.Group(); jaw.position.set(-1.9 * L, 2.45, 0); head.add(jaw);
  const jawM = ell(light, 1.3 * L, 0.26, 0.55, 1.15 * L, -0.12, 0, jaw);
  const mouthIn = ell(std('#5a2a2a', { roughness: 0.7 }), 1.25 * L, 0.2, 0.5, -0.65 * L, 2.48, 0);
  // the tongue: a wide flat tube along a curve in the xy plane, rebuilt when its shape changes
  const tongueM = std('#d9827e', { roughness: 0.45 });
  const tongue = new THREE.Mesh(new THREE.BufferGeometry(), tongueM); tongue.castShadow = true; tongue.scale.z = 1.9; g.add(tongue);
  const tipPt = new THREE.Vector3();
  let lastKey = '';
  const setTongue = (ext, curl) => {
    const key = ext.toFixed(3) + curl.toFixed(3);
    if (key === lastKey) return; lastKey = key;
    const yTip = lerp(2.2 + HY, SURF + DEEP, ext);
    const P = (x, y) => new THREE.Vector3(x, y, 0);
    const y1 = lerp(2.3 + HY, 1.75 + HY * 0.75, ext);
    const pts = [P(-0.2, 2.42 + HY), P(CX - 0.05, y1), P(CX + 0.12, (y1 + yTip) / 2), P(CX + 0.05, yTip + 0.06)];
    if (curl > 0.01) pts.push(P(CX - 0.18 * curl, yTip + 0.02 + 0.08 * curl), P(CX - 0.38 * curl, yTip + 0.22 * curl));
    const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal');
    const geo = new THREE.TubeGeometry(curve, 64, isDog ? 0.17 : 0.11, 24, false);
    const Pp = geo.attributes.position, c = new THREE.Vector3(), v = new THREE.Vector3();
    for (let i = 0; i <= 64; i++) {                            // flatten across the curve's normal plane a little, taper the tip
      curve.getPointAt(i / 64, c); const f = 1 - 0.35 * smooth((i / 64 - 0.6) / 0.4);
      for (let j = 0; j <= 24; j++) { const k = i * 25 + j; v.fromBufferAttribute(Pp, k).sub(c); v.x *= f * 0.7; v.y *= f * 0.7; v.z *= f; Pp.setXYZ(k, c.x + v.x, c.y + v.y, c.z + v.z); }
    }
    geo.computeVertexNormals(); tongue.geometry.dispose(); tongue.geometry = geo;
    curve.getPointAt(0.78, tipPt);
  };
  // the water column: a lathe between y0 and y1, wide at the foot, a neck, and a bulb at the top
  const col = new THREE.Mesh(new THREE.BufferGeometry(), waterMat()); col.position.set(CX, 0, 0); g.add(col);
  const rad = isDog ? 1 : 0.6;
  const setColumn = (y0, y1, foot) => {
    if (y1 - y0 < 0.03) { col.visible = false; return; }
    col.visible = true;
    const pts = [];
    for (let k = 0; k <= 30; k++) {
      const y = y0 + (y1 - y0) * k / 30, u = k / 30;
      const r = rad * (0.1 + 0.05 * Math.sin(Math.PI * u) + 0.32 * foot * Math.exp(-(y - SURF) / 0.12) + 0.1 * smooth((u - 0.75) / 0.25) * (1 - smooth((u - 0.97) / 0.03)));
      pts.push(new THREE.Vector2(Math.max(0.005, r), y));
    }
    pts.unshift(new THREE.Vector2(0.001, y0)); pts.push(new THREE.Vector2(0.001, y1));
    const geo = new THREE.LatheGeometry(pts, 48); col.geometry.dispose(); col.geometry = geo;
  };
  // ripples and flung droplets
  const ripples = [0, 1].map(() => { const r = new THREE.Mesh(new THREE.TorusGeometry(1, 0.025, 12, 96), waterMat()); r.rotation.x = Math.PI / 2; r.position.set(CX, SURF + 0.01, 0); g.add(r); return r; });
  const drops = [];
  for (let k = 0; k < (isDog ? 14 : 0); k++) {
    const d = new THREE.Mesh(new THREE.SphereGeometry(0.05 + 0.04 * ((k * 7) % 3) / 2, 24, 16), waterMat());
    const a = (k / 14) * Math.PI * 2;
    d.userData.v = [0.9 * Math.cos(a) + 0.4, 1.8 + 0.6 * ((k * 5) % 4) / 3, 2.4 * Math.sin(a)];
    g.add(d); drops.push(d);
  }
  g.traverse(o => { if (o.isMesh && o.material.transparent) o.castShadow = false; });
  return {
    group: g,
    set(phase) {
      const p = ((phase % 1) + 1) % 1, slow = 1;
      let ext, curl, open;
      if (p < 0.25) { ext = smooth(p / 0.25) * slow; curl = isDog ? 0.3 + 0.7 * smooth(p / 0.2) : 0.1; open = 0.5; }
      else if (p < 0.3) { ext = slow; curl = isDog ? 1 : 0.1; open = 0.5; }
      else if (p < 0.55) { ext = slow * (1 - 0.85 * smooth((p - 0.3) / 0.25)); curl = isDog ? 1 : 0.1; open = 0.5; }
      else if (p < 0.62) { ext = slow * 0.15 * (1 - smooth((p - 0.55) / 0.07)); curl = isDog ? 1 : 0.1; open = 0.5 - 0.45 * smooth((p - 0.55) / 0.07); }
      else if (p < 0.9) { ext = 0; curl = isDog ? 1 : 0.1; open = 0.05; }
      else { ext = 0; curl = isDog ? 1 - 0.7 * smooth((p - 0.9) / 0.1) : 0.1; open = 0.05 + 0.45 * smooth((p - 0.9) / 0.1); }
      jaw.rotation.z = -0.32 * open + 0.02;
      setTongue(ext, curl);
      const yTip = lerp(2.2 + HY, SURF + DEEP, ext);
      // the column: rises under the tongue while it is pulled up; cut at the bite; the rest falls back
      const cut = 2.05 + HY;
      if (p >= 0.3 && p < 0.6) setColumn(SURF - 0.02, Math.min(cut, yTip + 0.05), 1);
      else if (p >= 0.6 && p < 0.82) { const u = smooth((p - 0.6) / 0.22); setColumn(SURF - 0.02, lerp(cut - 0.08, SURF, u), 1 - u); }
      else setColumn(0, 0, 0);
      // ripples: from the slap (0.25) and from the column falling back (0.8)
      [[0.25, 0], [0.8, 1]].forEach(([p0, k]) => {
        const u = p - p0, r = ripples[k];
        r.visible = u > 0 && u < 0.35; const s = 0.3 + 6 * u; r.scale.set(s, s, 1 + 2 * u); r.material.opacity = 0.8 * (1 - u / 0.35);
      });
      // ladle droplets: flung out of the curled tongue as the jaw snaps (slow motion: tau in rig seconds)
      for (const d of drops) {
        const tau = (p - 0.6) * 2.2;
        d.visible = tau > 0 && tau < 1.4;
        if (!d.visible) continue;
        const v = d.userData.v;
        d.position.set(CX - 0.2 + v[0] * tau, 2.15 + HY + v[1] * tau - 4.9 * 0.5 * tau * tau * 1.2, v[2] * tau);
        if (d.position.y < SURF && Math.hypot(d.position.x - CX, d.position.z) < 2.35) d.visible = false;
        if (d.position.y < 0.03) d.visible = false;
      }
      tongue.visible = true; mouthIn.visible = true;
    },
  };
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  world.ground(600); world.hills(12, 130);
  const H = home(world, {});
  const b1 = bowl(); b1.position.set(...L.bowl); S.add(b1);
  const b2 = bowl('#d9b3a6', 0.085); b2.position.set(...L.bowl2); S.add(b2);
  // a mat under the dog's bowl, and the puddles of the mess (they grow over the video)
  const mat = new THREE.Mesh(softBox(0.55, 0.012, 0.4, 0.4, 16), std('#a5584a', { roughness: 1 })); mat.position.set(L.bowl[0], 0.006, L.bowl[2]); mat.receiveShadow = true; S.add(mat);
  const puddles = [[0.25, 0.32, 0.14], [-0.05, -0.36, 0.1], [0.42, -0.12, 0.08], [0.1, 0.5, 0.07], [-0.2, 0.44, 0.06]].map(([dx, dz, r], k) => {
    const g = new THREE.CircleGeometry(r, 48), P = g.attributes.position;
    for (let i = 1; i < P.count; i++) { const a = Math.atan2(P.getY(i), P.getX(i)), f = 1 + 0.18 * Math.sin(a * 3 + k) + 0.1 * Math.sin(a * 5 + 2 * k); P.setXY(i, P.getX(i) * f, P.getY(i) * f); }
    const m = new THREE.Mesh(g, new THREE.MeshPhysicalMaterial({ color: '#cfe4ee', roughness: 0.02, transparent: true, opacity: 0.55, clearcoat: 1 }));
    m.rotation.x = -Math.PI / 2; m.position.set(L.bowl[0] + dx, 0.004 + 0.0005 * k, L.bowl[2] + dz); m.userData.k = k; S.add(m); return m;
  });
  // a small high-speed camera on a tripod, aimed at the bowl (shown from "filmed" on)
  const rig = new THREE.Group();
  for (let k = 0; k < 3; k++) { const a = k * 2.094; const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.01, 0.62, 16), std('#3b3f45', { metalness: 0.5, roughness: 0.4 })); leg.position.set(Math.cos(a) * 0.12, 0.3, Math.sin(a) * 0.12); leg.rotation.set(Math.sin(a) * 0.35, 0, -Math.cos(a) * 0.35); rig.add(leg); }
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.11, 0.12, 2, 2, 2), std('#4a4f57', { roughness: 0.5 })); body.position.y = 0.66; rig.add(body);
  const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.045, 0.1, 32), std('#2b3038', { roughness: 0.3 })); lens.rotation.z = Math.PI / 2; lens.position.set(-0.12, 0.66, 0); rig.add(lens);
  const rec = new THREE.Mesh(new THREE.SphereGeometry(0.012, 24, 16), new THREE.MeshStandardMaterial({ color: '#c92a2e', emissive: '#ff3b30', emissiveIntensity: 3 })); rec.position.set(0.0, 0.73, 0.062); rig.add(rec);
  rig.position.set(...L.tripod); rig.rotation.y = L.tripod_yaw; rig.traverse(o => { if (o.isMesh) o.castShadow = true; }); S.add(rig);

  const rex = dog(); rex.position.set(...L.dog); rex.rotation.y = L.dog_yaw; S.add(rex);
  const tom = cat(); tom.position.set(...L.cat); tom.rotation.y = L.cat_yaw; S.add(tom);
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
  // real-time droplets flung from the dog's mouth while he laps
  const dropM = new THREE.MeshPhysicalMaterial({ color: '#d6ecf5', roughness: 0.02, transparent: true, opacity: 0.85, emissive: '#6aa8c4', emissiveIntensity: 0.35, clearcoat: 1 });
  const drops = Array.from({ length: 22 }, (_, k) => {
    const d = new THREE.Mesh(new THREE.SphereGeometry(0.0045 + 0.0018 * (k % 3), 16, 12), dropM);
    const a = (k * 2.39996) % (Math.PI * 2);
    d.userData = { ph: (k * 0.137) % 1, v: [0.25 + 0.5 * Math.cos(a) * 0.4, 0.9 + 0.5 * ((k * 3) % 5) / 4, 0.9 * Math.sin(a)] };
    S.add(d); return d;
  });
  const dogRig = lapRig(S, L.macro, 'dog');
  const catRig = lapRig(S, L.macro_cat, 'cat');

  // shadows only near the room and the two macro rigs
  S.updateMatrixWorld(true);
  const wp = new THREE.Vector3();
  S.traverse(o => {
    if (!o.isMesh || !o.castShadow) return;
    o.getWorldPosition(wp);
    const near = (Math.abs(wp.x) < 4 && wp.z > -3 && wp.z < 3) || Math.hypot(wp.x - L.macro[0], wp.z - L.macro[2]) < 9 || Math.hypot(wp.x - L.macro_cat[0], wp.z - L.macro_cat[2]) < 9;
    if (!near) o.castShadow = false;
  });
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const v = new THREE.Vector3(), mz = new THREE.Vector3();
  const headLook = (person, target, maxYaw = 0.9, eye = 1.5) => {
    v.set(...target).sub(person.position);
    let yaw = Math.atan2(v.x, v.z) - person.rotation.y; yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    const pitch = -Math.atan2(target[1] - person.position.y - eye, Math.hypot(v.x, v.z));
    return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, yaw)), headPitch: Math.max(-0.3, Math.min(0.5, pitch)) };
  };
  const dogHead = [0, 0, 0], wizHead = [L.wiz[0], 1.65, L.wiz[2]], womHead = [L.woman[0], 1.55, L.woman[2]], catHead = [L.cat[0], 0.2, L.cat[2]];
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(-0.5, 0, 0.8),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      // the dog laps: quick head bobs with the mouth opening, ears flopping, droplets flying
      const lap = F.dog_lap[k], ph = t * 2.6 * Math.PI * 2;
      rex.pose({ mode: 'lie', t, pitch: F.dog_pitch[k] + 0.08 * lap * Math.sin(ph), yaw: F.dog_yaw[k], rest: 0, blink: F.dog_blink[k],
                 mouth: lap * (0.35 + 0.35 * Math.max(0, Math.sin(ph))) + F.dog_mouth[k], ears: 0.15 + 0.25 * lap * Math.abs(Math.sin(ph)), tail: F.dog_tail[k], breath: 1 });
      rex.updateMatrixWorld(true); rex.headWorld(mz); dogHead[0] = mz.x; dogHead[1] = mz.y; dogHead[2] = mz.z;
      const fwd = new THREE.Vector3(Math.sin(L.dog_yaw), 0, Math.cos(L.dog_yaw)), side = new THREE.Vector3(fwd.z, 0, -fwd.x);
      const mouthP = mz.clone().addScaledVector(fwd, 0.12).add(new THREE.Vector3(0, -0.08, 0));
      for (const d of drops) {
        const u = d.userData, tau = ((t * 1.1 + u.ph) % 1) * 0.45, on = lap > 0.5 && F.drops[k] > 0;
        const p = mouthP.clone().addScaledVector(fwd, u.v[0] * tau).addScaledVector(side, u.v[2] * tau); p.y += u.v[1] * tau - 4.9 * tau * tau;
        d.visible = on && p.y > 0.01; d.position.copy(p);
      }
      const mess = F.mess[k];
      puddles.forEach(m => { const s = clamp01(mess * 1.6 - m.userData.k * 0.15); m.visible = s > 0.02; m.scale.setScalar(Math.max(0.01, s)); });
      rig.visible = F.tripod[k] > 0; rec.visible = (t % 1.0) < 0.6;
      // the cat drinks neatly: tiny head dips, almost no mouth
      const cl = F.cat_lap[k];
      tom.pose({ mode: 'crouch', t, pitch: 0.55 + 0.04 * cl * Math.sin(t * 4 * Math.PI * 2), yaw: 0, blink: cl > 0 ? 0.6 : (t % 4.1 < 0.12 ? 1 : 0), mouth: 0.15 * cl, tail: 0.1 });
      // presenters
      const lw = F.look_w[k], lm = F.look_m[k];
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, ...headLook(wiz, lw === 'woman' ? womHead : lw === 'cat' ? catHead : dogHead, 0.9, 1.6), headTilt: 0.04 * Math.sin(t * 0.7), point: F.wiz_point[k] });
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, ...headLook(wom, lm === 'dog' ? dogHead : lm === 'cat' ? catHead : wizHead), headTilt: 0.05 * Math.sin(t * 0.9 + 1), point: F.woman_point[k] });
      dogRig.set(F.lap[k]); catRig.set(F.lap_cat[k]);
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i);
        world.setLighting(shot.lighting ?? 'key', new THREE.Vector3(fp[0], 0, fp[2]));
        const sc = world.sun.shadow.camera, e2 = Math.abs(fp[0]) > 10 ? 9 : 5;
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
      const ent = Math.hypot(fp[0] - L.macro[0], fp[2] - L.macro[2]) < 8 ? 'water' : Math.hypot(fp[0] - L.macro_cat[0], fp[2] - L.macro_cat[2]) < 8 ? 'cat' : 'dog';
      return [{ entity: ent, part: 'subject', kind: 'thickness', p: fp, size: 0.25 }];
    },
    vars() { return {}; },
  };
}

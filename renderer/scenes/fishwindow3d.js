// A fish sees the whole sky through one small circle (content/episodes/fish-window/plan.py).
// The shared lake set (renderer/sets/lake.js): the wizard (with a fishing rod) and the woman on the bank, a trout
// hovering 1 m under the surface off the bank. Diagram ("xray") shots make the water clearer and draw the light
// paths the plan computed with Snell's law: warm sky rays that bend at the surface and meet at the fish's eye, the
// 97-degree cone they fill, the window ring on the surface, and a red ray from the wizard's eye. Underwater shots
// use the set's mirror sheet (Snell's window around the camera). This file only draws what the plan lists.
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { lake, fish, rod, BANK_Y } from '../sets/lake.js';

export function presenters(S, L) {
  const wiz = man(); wiz.position.set(...L.wiz); wiz.rotation.y = L.wiz_face; S.add(wiz);
  const wom = woman(); wom.position.set(...L.woman); wom.rotation.y = L.woman_face; S.add(wom);
  // v7 presenters: keep their own colours (look v3 lights dark cloth properly). Only the wizard's staff, glowing
  // stone and potion vials go, so his hand is free for the rod and nothing glows by a lake in daylight.
  for (const p of [wiz, wom]) p.traverse(o => {
    if (o.isSprite || o.isPointLight) { o.visible = false; return; }
    if (o.isMesh && /^z_(staff|stone|fork|vial|cork|cage|knot)/.test(o.name)) o.visible = false;
    if (o.isMesh && o.material && /potion/.test(o.material.name || '')) o.visible = false;
  });
  return { wiz, wom };
}

// the wizard's robe is one rigid piece hanging from his hips: when he sits on a low boat seat its lower part would
// poke through the hull. For seated scenes shorten it to seat level (his trousers show below, as when you sit in a
// long coat) and drop the hem band and the stars that were on the cut part. Call once, before posing.
export function seatRobe(wiz, cutY = 0.47) {
  const hide = [], robe = wiz.getObjectByName('z_robe');
  if (!robe) return;
  wiz.updateMatrixWorld(true);
  const rw = new THREE.Vector3(); robe.getWorldPosition(rw);
  const cutW = rw.y + cutY - wiz.position.y, v = new THREE.Vector3();
  robe.geometry = robe.geometry.clone();
  const P = robe.geometry.attributes.position;
  for (let i = 0; i < P.count; i++) if (P.getY(i) < cutY) P.setY(i, cutY);
  P.needsUpdate = true; robe.geometry.computeVertexNormals(); robe.geometry.computeBoundingSphere();
  wiz.traverse(o => {
    if (!o.isMesh) return;
    if (/^z_robe_hem/.test(o.name)) hide.push(o);
    else if (/^z_star/.test(o.name)) { o.getWorldPosition(v); if (v.y - wiz.position.y < cutW + 0.05) hide.push(o); }
  });
  for (const o of hide) o.visible = false;
}

// the rod rides in the wizard's left hand (where his hidden staff is), tilted forward over the water. Call
// place(tiltDeg, yawOffset) each frame after posing him, then rod.set(bend, lineEnd).
export function rodInHand(S, wiz, opt = {}) {
  const r = rod(S, opt.len ?? 2.4);
  const hand = opt.hand ?? 'hand_L';
  let st = null; wiz.traverse(o => { if (!st && o.isBone && o.name === hand) st = o; });
  const hp = new THREE.Vector3(), fwd = new THREE.Vector3(), d = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
  r.place = (tilt = 55, yaw = 0, back = 0.12, toward = null) => {
    wiz.updateMatrixWorld(true);
    if (st) st.getWorldPosition(hp); else hp.copy(wiz.position).add(new THREE.Vector3(0, 1.0, 0));
    const a = wiz.rotation.y + yaw;
    fwd.set(Math.sin(a), 0, Math.cos(a));
    const tr = THREE.MathUtils.degToRad(tilt);
    d.copy(fwd).multiplyScalar(Math.sin(tr)).addScaledVector(up, Math.cos(tr)).normalize();
    r.position.copy(hp).addScaledVector(d, -back);             // the butt sits a little behind the hand
    r.quaternion.setFromUnitVectors(up, d);
    // roll about the rod so it bends (its local -z) toward `toward` (the line's far end), if given
    if (toward) {
      const cur = new THREE.Vector3(0, 0, -1).applyQuaternion(r.quaternion);
      const want = new THREE.Vector3(...toward).sub(r.position); want.addScaledVector(d, -want.dot(d));
      if (want.lengthSq() > 1e-6) {
        want.normalize();
        const ang = Math.atan2(d.dot(new THREE.Vector3().crossVectors(cur, want)), cur.dot(want));
        r.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(d, ang));
      }
    }
    r.updateMatrixWorld(true);
  };
  return r;
}

export function headLook(person, target, maxYaw = 0.9, eye = 1.5) {
  const v = new THREE.Vector3(...target).sub(person.position);
  let yaw = Math.atan2(v.x, v.z) - person.rotation.y; yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));
  const pitch = -Math.atan2(target[1] - person.position.y - eye, Math.hypot(v.x, v.z));
  return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, yaw)), headPitch: Math.max(-0.45, Math.min(0.5, pitch)) };
}

// a thin tube along a polyline whose visible length grows with setDrawRange (rays that draw themselves)
export function rayTube(points, color, r = 0.012, opacity = 0.95) {
  const path = new THREE.CurvePath();
  for (let k = 0; k + 1 < points.length; k++) path.add(new THREE.LineCurve3(new THREE.Vector3(...points[k]), new THREE.Vector3(...points[k + 1])));
  const seg = 64 * (points.length - 1), rad = 12;
  const g = new THREE.TubeGeometry(path, seg, r, rad, false);
  const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, toneMapped: false }));
  m.renderOrder = 5; m.userData.total = g.index.count; m.userData.step = rad * 6;
  m.setProgress = p => { const n = Math.floor(Math.max(0, Math.min(1, p)) * seg) * rad * 6; g.setDrawRange(0, n); m.visible = n > 0; };
  return m;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  const LK = lake(world, { keepClear: [[-3, 3]] });
  const trout = fish('trout', 0.5); const len = trout.len;
  trout.rotation.y = -Math.PI / 2;                                  // facing the bank (+z)
  trout.position.set(L.eye[0], L.eye[1] - 0.025 * len, L.eye[2] - 0.36 * len); S.add(trout);
  const { wiz, wom } = presenters(S, L);
  const fr = rodInHand(S, wiz);
  const logM = new THREE.MeshStandardMaterial({ color: '#6e5236', roughness: 0.9 });
  const log = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.22, 1.6, 24), logM); log.rotation.z = Math.PI / 2;
  log.position.set(L.wiz[0] + 0.1, BANK_Y + 0.21, L.wiz[2] + 0.32); log.castShadow = log.receiveShadow = true; S.add(log);
  for (const s of [-1, 1]) { const end = new THREE.Mesh(new THREE.CircleGeometry(0.2, 24), new THREE.MeshStandardMaterial({ color: '#b58a5a', roughness: 0.9 })); end.position.set(L.wiz[0] + 0.1 + s * 0.801, BANK_Y + 0.21, L.wiz[2] + 0.32); end.rotation.y = s * Math.PI / 2; S.add(end); }
  const fanM = plan.layout.fan.map((r, k) => { const m = rayTube(r.pts, r.edge ? '#ffd27a' : '#fff1c2', r.edge ? 0.016 : 0.011); S.add(m); return m; });
  const headM = rayTube(L.stand_ray, '#e5484d', 0.02); S.add(headM);
  // the cone of light under the window and the window ring on the surface
  const coneG = new THREE.ConeGeometry(L.r_win, Math.abs(L.eye[1]), 96, 1, true); coneG.rotateX(Math.PI); coneG.translate(0, -Math.abs(L.eye[1]) / 2, 0);
  const cone = new THREE.Mesh(coneG, new THREE.MeshBasicMaterial({ color: '#ffe9b0', transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false, toneMapped: false }));
  cone.position.set(L.eye[0], 0, L.eye[2]); cone.renderOrder = 4; S.add(cone);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(L.r_win, 0.018, 12, 128), new THREE.MeshBasicMaterial({ color: '#fff6dc', transparent: true, opacity: 0, depthWrite: false, toneMapped: false }));
  ring.rotation.x = Math.PI / 2; ring.position.set(L.eye[0], 0.03, L.eye[2]); ring.renderOrder = 6; S.add(ring);

  // shadows only near the action (trees further away would fall off the shadow box)
  S.updateMatrixWorld(true);
  const wp = new THREE.Vector3();
  S.traverse(o => { if (o.isMesh && o.castShadow) { o.getWorldPosition(wp); if (Math.hypot(wp.x - 0.5, wp.z - 1) > 8) o.castShadow = false; } });
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const wizHead = [L.wiz[0], BANK_Y + 1.65, L.wiz[2]], womHead = [L.woman[0], BANK_Y + 1.55, L.woman[2]];
  const water = [L.eye[0], -0.2, L.eye[2]], sky = [L.wiz[0], 6, L.wiz[2] - 6];
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(0.5, 0, 0.5),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      LK.update(t, world.camera);
      const xr = F.xray[k] > 0;
      LK.opacity = xr ? 0.32 : 0.8;
      trout.swim(t, F.fish_swim[k]);
      trout.position.y = L.eye[1] - 0.025 * len + 0.015 * Math.sin(t * 1.3);
      fanM.forEach((m, j) => m.setProgress(xr ? F.rays[k] * 1.25 - j * 0.02 : 0));
      headM.setProgress(xr ? F.head_ray[k] : 0);
      cone.material.opacity = xr ? 0.22 * F.cone[k] : 0;
      ring.material.opacity = xr ? 0.95 * F.ring[k] : 0;
      const sit = F.sit[k];
      const lw = F.look_w[k], lm = F.look_m[k];
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, sit, wave: F.wiz_wave[k], point: 0.12, ...headLook(wiz, lw === 'sky' ? sky : lw === 'water' ? water : womHead, 0.9, 1.6), headTilt: 0.04 * Math.sin(t * 0.7) });
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, point: F.woman_point[k], ...headLook(wom, lm === 'water' ? water : wizHead, 0.5), headTilt: 0.05 * Math.sin(t * 0.9 + 1) });
      fr.place(58 - 18 * sit, 0.15);
      fr.set(0.1, [L.eye[0] + 0.3, -0.02, L.eye[2] + 1.6], 0.3);
      if (shot !== lastShot) {
        lastShot = shot;
        if (plan.bloom_threshold) world.bloom.threshold = plan.bloom_threshold;
        const sc = world.sun.shadow.camera, e2 = 8;
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.far = 80; sc.updateProjectionMatrix();
      }
    },
    afterCamera(i) {
      LK.afterCamera(world.camera);
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.05, Math.max(0.005, d * 0.02)); world.camera.far = 600; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      return [{ entity: 'window', part: 'subject', kind: 'thickness', p: [L.eye[0], 0, L.eye[2]], size: 0.4 }];
    },
    vars() { return {}; },
  };
}

// Why 24 fps looks smooth in films but choppy in games (content/episodes/frame-rate-blur/plan.py).
// The shared street set (renderer/sets/street.js): a straight road, verges, trees, a few parked cars. On the near
// verge the wizard kicks a red ball along the grass. The plan says, per frame, how the ball is shown:
//   live_game  : slowed down, drawn the way a game draws it: one sharp ball per 1/24 s frame, jumping between them
//   live_film  : slowed down, drawn the way a film camera records it: each frame a streak covering the first half of
//                the frame interval (shutter open for half the frame)
//   strip_game / strip_film / strip_60 : frozen copies of every frame laid along the path at once
// Ball positions are the plan's projectile (positions per frame time), so spacing = speed / fps exactly.
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { road, hcar } from '../sets/street.js';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.55, ...x });

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  world.ground(700); world.hills(14, 180);
  road(world, { x: 0, z0: -170, z1: 230 });
  const rnd = (() => { let s = 11; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); })();
  for (let z = -150; z < 220; z += 10) for (const side of [-1, 1]) {
    if (rnd() < 0.5) continue;
    const x = side * (14 + rnd() * 16);
    if (side > 0 && x < 22 && z > -14 && z < 22) continue;              // keep the kick area clear
    (rnd() < 0.35 ? world.conifer(x, z, 1.4 + rnd()) : world.roundTree(x, z, 1.3 + rnd()));
  }
  const cols = ['#d9c7a0', '#8fa6c8', '#e2c45a', '#a99bc4', '#b9bdc2'];
  [[-1.8, -12, 'hatch'], [-1.8, 9, 'estate'], [1.8, 26, 'sedan'], [-1.8, 34, 'hatch'], [1.8, -30, 'estate']].forEach(([x, z, k], j) => {
    const c = hcar(cols[j], k); c.position.set(x, 0.05, z); c.rotation.y = x > 0 ? Math.PI : 0; S.add(c);
  });
  // the ball and its frame copies
  const R = L.ball_r;
  const red = std('#c92a2e', { roughness: 0.45 }), seam = std('#e8e6df', { roughness: 0.6 });
  const mkBall = () => {
    const g = new THREE.Group();
    const s = new THREE.Mesh(new THREE.SphereGeometry(R, 48, 36), red); s.castShadow = true; g.add(s);
    const band = new THREE.Mesh(new THREE.TorusGeometry(R * 1.002, R * 0.07, 12, 48), seam); g.add(band);
    return g;
  };
  const ball = mkBall(); S.add(ball);
  const sharp = [], streaks = [];
  for (let k = 0; k < 64; k++) { const b = mkBall(); b.visible = false; S.add(b); sharp.push(b); }
  const smearM = new THREE.MeshStandardMaterial({ color: '#c92a2e', roughness: 0.5, transparent: true, opacity: 0.82 });
  for (let k = 0; k < 32; k++) {
    const m = new THREE.Mesh(new THREE.CapsuleGeometry(R, 1, 8, 32), smearM); m.castShadow = true; m.visible = false; S.add(m); streaks.push(m);
  }
  const P = tb => {             // projectile from the kick point (tb in s of real flight time)
    const t = Math.max(0, Math.min(L.t_land, tb));
    return [L.p0[0], R + L.v[1] * t - 0.5 * 9.81 * t * t, L.p0[2] + L.v[2] * t];
  };
  const up = new THREE.Vector3(0, 1, 0), a = new THREE.Vector3(), b = new THREE.Vector3();
  // CapsuleGeometry scales its caps too when scaled in y; rebuild per streak length instead (cached by length)
  const capCache = new Map();
  const capsule = len => { const key = Math.round(len * 200); if (!capCache.has(key)) capCache.set(key, new THREE.CapsuleGeometry(R, Math.max(0.001, key / 200), 8, 32)); return capCache.get(key); };
  const setStreak = (m, t0, t1) => {
    a.set(...P(t0)); b.set(...P(t1));
    const d = b.clone().sub(a), len = d.length();
    m.geometry = capsule(len); m.scale.set(1, 1, 1);
    m.position.copy(a).add(b).multiplyScalar(0.5);
    m.quaternion.setFromUnitVectors(up, len > 1e-5 ? d.normalize() : up);
    m.visible = true;
  };

  const wiz = man(); wiz.position.set(...L.wiz); wiz.rotation.y = L.wiz_face; S.add(wiz);
  const wom = woman(); wom.position.set(...L.woman); wom.rotation.y = L.woman_face; S.add(wom);
  const lift = new THREE.Color('#3a3640').convertSRGBToLinear();
  for (const p of [wiz, wom]) p.traverse(o => {
    if (!o.isMesh) return;
    if (/^z_(staff|stone|fork)/.test(o.name)) { o.visible = false; return; }
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || !m.color || m.isMeshBasicMaterial) continue;
      if (Math.max(m.color.r, m.color.g, m.color.b) < lift.r) { m.color.r = Math.max(m.color.r, lift.r); m.color.g = Math.max(m.color.g, lift.g); m.color.b = Math.max(m.color.b, lift.b); }
      // her black outfit and hair crush to pure black on the shadow side; a faint emissive floor keeps their folds visible
      if (p === wom && 'emissive' in m && Math.max(m.color.r, m.color.g, m.color.b) < 0.1) { m.emissive = new THREE.Color('#2a2730'); m.emissiveIntensity = 1; }
    }
  });
  // only the kick area casts shadows (distant trees would fall off the shadow box)
  S.updateMatrixWorld(true);
  const wp = new THREE.Vector3();
  S.traverse(o => { if (o.isMesh && o.castShadow) { o.getWorldPosition(wp); if (Math.hypot(wp.x - 8, wp.z - 1) > 13) o.castShadow = false; } });
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const v = new THREE.Vector3();
  const headLook = (person, target, maxYaw = 0.9, eye = 1.5) => {
    v.set(...target).sub(person.position);
    let yaw = Math.atan2(v.x, v.z) - person.rotation.y; yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    const pitch = -Math.atan2(target[1] - person.position.y - eye, Math.hypot(v.x, v.z));
    return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, yaw)), headPitch: Math.max(-0.45, Math.min(0.5, pitch)) };
  };
  const wizHead = [L.wiz[0], 1.65, L.wiz[2]], womHead = [L.woman[0], 1.55, L.woman[2]], cam = [0, 0, 0];
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(L.p0[0], 0, L.p0[2] + 4),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.mode.length - 1), mode = F.mode[k], tb = F.tb[k];
      sharp.forEach(s => { s.visible = false; }); streaks.forEach(s => { s.visible = false; });
      ball.visible = false;
      if (mode === 'rest') { ball.visible = true; ball.position.set(...P(0)); }
      else if (mode === 'live_game') { const f = Math.floor(tb * 24 + 1e-6) / 24; ball.visible = true; ball.position.set(...P(f)); ball.rotation.z = -f * 40; }
      else if (mode === 'live_film') { const f = Math.floor(tb * 24 + 1e-6) / 24; setStreak(streaks[0], f, f + 1 / 48); }
      else if (mode === 'strip_game' || mode === 'strip_60') {
        const fps = mode === 'strip_60' ? 60 : 24, nmax = Math.floor(L.t_land * fps + 1e-6);
        for (let j = 0; j <= nmax && j < sharp.length; j++) { sharp[j].visible = true; sharp[j].position.set(...P(j / fps)); sharp[j].rotation.z = -j / fps * 40; }
      } else if (mode === 'strip_film') {
        const nmax = Math.floor(L.t_land * 24 + 1e-6);
        for (let j = 0; j <= nmax && j < streaks.length; j++) setStreak(streaks[j], j / 24, Math.min(L.t_land, j / 24 + 1 / 48));
      }
      const bp = ball.visible ? ball.position.toArray() : P(Math.min(tb, L.t_land));
      const lw = F.look_w[k], lm = F.look_m[k];
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, ...headLook(wiz, lw === 'woman' ? womHead : bp, 0.9, 1.6), headTilt: 0.04 * Math.sin(t * 0.7), point: F.wiz_point[k] });
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, ...headLook(wom, lm === 'ball' ? bp : wizHead, 0.6), headTilt: 0.05 * Math.sin(t * 0.9 + 1), point: F.woman_point[k] });
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i);
        world.setLighting(shot.lighting ?? 'day', new THREE.Vector3(fp[0], 0, fp[2]));
        if (plan.bloom_threshold) world.bloom.threshold = plan.bloom_threshold;   // setLighting resets it
        const sc = world.sun.shadow.camera, e2 = 16;
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.near = -100; sc.far = 200; sc.updateProjectionMatrix();
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.max(0.05, d * 0.03); world.camera.far = 1200; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      return [{ entity: 'ball', part: 'subject', kind: 'thickness', p: focalPt(i), size: 0.25 }];
    },
    vars() { return {}; },
  };
}

// The zipper merge (content/episodes/zipper-merge/plan.py). Street set: renderer/sets/street.js.
// A straight two-lane road with the right lane closed (cones, sign, digger); 20 queued cars and a teal car that
// uses the empty lane; the presenters on the grass verge. Two frozen comparison roads far to the left.
// This file only draws what the plan lists (car positions come from the plan's queue model).
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { road, hcar, sign, digger, LANE_W } from '../sets/street.js';

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  world.ground(700); world.hills(14, 180);
  const closure = { z0: -60, z1: 0, taper: 16 };
  const main = road(world, { x: 0, z0: -170, z1: 230, closure });
  digger(main.group, LANE_W / 2, -16);
  sign(S, LANE_W + 2.6, 46, ['RIGHT LANE', 'CLOSED'], { yaw: -0.25, arrow: true });
  const zipSign = sign(S, LANE_W + 2.6, 22, ['USE BOTH', 'LANES', 'TAKE TURNS'], { yaw: -0.25, bg: '#e2c45a' });
  // comparison roads (frozen queues), and the empty road for "merge early"
  const ga = road(world, { x: L.ghost_a, z0: -120, z1: 200, closure, fence: false });
  const gb = road(world, { x: L.ghost_b, z0: -120, z1: 200, closure, fence: false });
  for (const R of [ga, gb]) digger(R.group, LANE_W / 2, -16);

  // trees along both verges and in the fields (sparse; long shadows)
  const rnd = (() => { let s = 7; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); })();
  for (let z = -150; z < 220; z += 11) {
    for (const side of [-1, 1]) {
      if (rnd() < 0.45) continue;
      const x = side * (13 + rnd() * 14);
      if (side < 0 && x < -12 && x > -72) continue;                    // keep the comparison roads clear
      (rnd() < 0.35 ? world.conifer(x, z, 1.4 + rnd()) : world.roundTree(x, z, 1.3 + rnd()));
    }
  }
  for (let k = 0; k < 18; k++) world.roundTree(-76 - rnd() * 40, -100 + rnd() * 300, 1.4 + rnd());

  // main-road cars: 20 in the queue model + the teal cutter
  const cars = [];
  for (let k = 0; k < L.n_cars; k++) {
    const col = k === L.wiz_car ? '#d9c7a0' : L.colors[(k * 3 + 1) % L.colors.length];
    const c = hcar(col, L.kinds[k % 3], k % 5 === 2); S.add(c); cars.push(c);
  }
  const cutter = hcar('#2e8f86', 'hatch'); S.add(cutter); cars.push(cutter);
  // frozen comparison queues: A = 20 in the left lane; B = 12 left + 8 right
  const ghostA = [], ghostB = [];
  for (let k = 0; k < L.n_cars; k++) {
    const a = hcar(L.colors[(k * 3 + 1) % L.colors.length], L.kinds[k % 3]); a.position.set(ga.lane(0), 0, L.front + L.spacing * k); a.position.y = 0.05; a.setBrake(1); S.add(a); ghostA.push(a);
    const right = k >= L.b_left, r = right ? k - L.b_left : k;
    const b = hcar(L.colors[(k * 3 + 1) % L.colors.length], L.kinds[k % 3]); b.position.set(gb.lane(right ? 1 : 0), 0, L.front + L.spacing * r); b.position.y = 0.05; b.setBrake(1); S.add(b); ghostB.push(b);
  }
  const early = hcar('#c9a77c', 'estate', true); S.add(early);

  const wiz = man(); wiz.position.set(...L.wiz); S.add(wiz);
  const wom = woman(); wom.position.set(...L.woman); S.add(wom);
  const lift = new THREE.Color('#3a3640').convertSRGBToLinear();
  for (const p of [wiz, wom]) p.traverse(o => {
    if (!o.isMesh) return;
    if (/^z_(staff|stone|fork)/.test(o.name)) { o.visible = false; return; }
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || !m.color || m.isMeshBasicMaterial) continue;
      if (Math.max(m.color.r, m.color.g, m.color.b) < lift.r) { m.color.r = Math.max(m.color.r, lift.r); m.color.g = Math.max(m.color.g, lift.g); m.color.b = Math.max(m.color.b, lift.b); }
    }
  });
  // presenters face the road (-x), turned a little toward each other
  wiz.rotation.y = -Math.PI / 2 - 0.35; wom.rotation.y = -Math.PI / 2 + 0.55;

  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const v = new THREE.Vector3();
  const headLook = (person, target, maxYaw = 0.9, eye = 1.5) => {
    v.set(...target).sub(person.position);
    let yaw = Math.atan2(v.x, v.z) - person.rotation.y; yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    const pitch = -Math.atan2(target[1] - person.position.y - eye, Math.hypot(v.x, v.z));
    return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, yaw)), headPitch: Math.max(-0.3, Math.min(0.45, pitch)) };
  };
  const wizHead = [L.wiz[0], 1.65, L.wiz[2]], womHead = [L.woman[0], 1.55, L.woman[2]], merge = [0, 0.8, 2.0];
  const brake = new Array(cars.length).fill(1);
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(0, 0, 10),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.car_x.length - 1), kp = Math.max(0, k - 1);
      cars.forEach((c, j) => {
        const x = F.car_x[k][j], z = F.car_z[k][j], dx = x - F.car_x[kp][j], dz = z - F.car_z[kp][j];
        c.visible = z > -300; c.position.set(x, 0.05, z);
        c.rotation.y = Math.abs(dz) > 1e-3 ? Math.atan2(-dx, -dz) * 1.0 : 0;     // nose along the direction of travel
        const kw = Math.max(0, k - 8), speed = k > kw ? Math.hypot(x - F.car_x[kw][j], z - F.car_z[kw][j]) * plan.fps / (k - kw) : 0;   // speed over ~0.27 s: per-frame steps stutter
        // hysteresis: a car creeping at about 1.5 m/s must not blink its brake lights every frame
        if (speed < 1.1) brake[j] = 1; else if (speed > 2.2) brake[j] = 0;
        c.setBrake(brake[j]);
      });
      const g = F.ghost[k];
      ghostA.forEach(c => { c.visible = g === 1; }); ghostB.forEach(c => { c.visible = g === 1; });
      early.visible = g === 2; early.position.set(F.early[k][0], 0.05, F.early[k][1]);
      const kp2 = Math.max(0, k - 1); const ex = F.early[k][0] - F.early[kp2][0], ez = F.early[k][1] - F.early[kp2][1];
      early.rotation.y = Math.abs(ez) > 1e-3 ? Math.atan2(-ex, -ez) : 0; early.setBrake(0);
      zipSign.visible = F.zip_sign[k] > 0;
      const cut = [cutter.position.x, 0.9, cutter.position.z];
      const lw = F.look_w[k], lm = F.look_m[k];
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, ...headLook(wiz, lw === 'woman' ? womHead : lw === 'cutter' ? cut : merge, 0.9, 1.6),
                 headTilt: 0.04 * Math.sin(t * 0.7), point: F.wiz_point[k] });
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, ...headLook(wom, lm === 'road' ? merge : wizHead), headTilt: 0.05 * Math.sin(t * 0.9 + 1), point: F.woman_point[k] });
      // this runs before the camera moves, so place the shadow box from the shot's own key for this frame, centred
      // between where the camera stands and what it looks at (the ground it actually sees); it follows moving shots
      const fp = focalPt(i), cp = shot.pos ? shot.pos[Math.min(shot.pos.length - 1, Math.max(0, i - (shot.i0 ?? 0)))] : [world.camera.position.x, world.camera.position.y, world.camera.position.z];
      const far = cp[1] > 40, ctr = new THREE.Vector3((cp[0] + fp[0]) / 2, 0, (cp[2] + fp[2]) / 2);
      if (shot !== lastShot) {
        lastShot = shot;
        world.setLighting(shot.lighting ?? 'day', ctr);
        if (far) { S.fog.near = 260; S.fog.far = 700; }        // the high comparison shot looks through no haze
        const sc = world.sun.shadow.camera, span = Math.hypot(cp[0] - fp[0], cp[2] - fp[2]);
        const e2 = far ? 165 : Math.max(48, 0.6 * span + 0.9 * cp[1] + 22);
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.near = -300; sc.far = 400; sc.updateProjectionMatrix();   // the sun sits only 30 m out: a negative near keeps casters behind it
      } else {
        const off = world.sun.position.clone().sub(world.sun.target.position);
        world.sun.target.position.copy(ctr); world.sun.position.copy(ctr).add(off);
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.max(0.1, d * 0.04); world.camera.far = 1200; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const fp = focalPt(i);
      return [{ entity: 'queues', part: 'subject', kind: 'thickness', p: fp, size: 1.0 }];
    },
    vars() { return {}; },
  };
}

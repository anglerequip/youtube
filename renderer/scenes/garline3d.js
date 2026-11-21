// A 153-pound fish on 2-pound line (content/episodes/gar-two-pound-line/plan.py).
// The shared lake set: the rowing boat out on the lake, the wizard on the bow seat with a bent rod, the woman on the
// stern seat behind him, both facing the bow. A big gar-like fish (our own model, 2.2 m like the reported catch)
// runs out ahead of the boat on a thin line. The plan computes the fight (where the fish is, the line tension, how
// much line slips off the reel); the tension meter is a 2D overlay (renderer/overlays.js `tension`). Two arrows on
// the fish show its weight and the water pushing up, nearly equal. This file only draws what the plan lists.
import * as THREE from 'three';
import { lake, fish, rowboat, net } from '../sets/lake.js';
import { presenters, seatRobe, headLook, rodInHand } from './fishwindow3d.js';

function arrow(color, len) {
  const g = new THREE.Group(), m = new THREE.MeshStandardMaterial({ color, roughness: 0.5, emissive: color, emissiveIntensity: 0.25 });
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 1, 24), m); shaft.position.y = 0.5; g.add(shaft);
  const head = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.2, 24), m); head.position.y = 1.0; g.add(head);
  g.setLen = L => { shaft.scale.y = Math.max(0.01, L - 0.2); shaft.position.y = (L - 0.2) / 2; head.position.y = L - 0.1; };
  g.setLen(len); g.renderOrder = 7;
  return g;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  const LK = lake(world, { keepClear: [[-5, 5]], jettyX: 7.5 });
  const boat = rowboat('#8fa6c8'); boat.rotation.y = Math.PI / 2; boat.position.set(L.boat[0], 0.12, L.boat[2]); S.add(boat);
  const { wiz, wom } = presenters(S, L);
  seatRobe(wiz);
  const gar = fish('gar', L.fish_len); S.add(gar);
  const fr = rodInHand(S, wiz, { len: 2.3, hand: 'hand_R' });
  const ln = net(0.24); S.add(ln); ln.visible = false;
  const wArrow = arrow('#e5484d', 0.8), bArrow = arrow('#3fc7b0', 0.8); bArrow.rotation.z = 0; wArrow.rotation.z = Math.PI;
  S.add(wArrow); S.add(bArrow);
  S.updateMatrixWorld(true);
  const wp = new THREE.Vector3();
  S.traverse(o => { if (o.isMesh && o.castShadow) { o.getWorldPosition(wp); if (Math.hypot(wp.x - L.boat[0], wp.z - L.boat[2]) > 12) o.castShadow = false; } });
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const nose = new THREE.Vector3();
  const head = { wizard: [L.wiz[0], 0.9, L.wiz[2]], woman: [L.woman[0], 0.85, L.woman[2]] };
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(L.boat[0] - 2, 0, L.boat[2]),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      LK.update(t, world.camera);
      const xr = F.xray[k] > 0;
      LK.opacity = xr ? 0.3 : F.water_op[k];
      const bob = 0.012 * Math.sin(t * 1.4);
      boat.position.y = 0.12 + bob; boat.rotation.z = 0.01 * Math.sin(t * 1.1 + 0.4) - 0.012 * F.tension[k];
      for (const [p, base] of [[wiz, L.wiz], [wom, L.woman]]) p.position.y = base[1] + bob;
      const fp = F.fish[k];
      gar.position.set(fp[0], fp[1], fp[2]); gar.rotation.set(0, fp[3], fp[4] ?? 0);
      gar.swim(t, F.fish_effort[k], F.fish_turn[k]);
      gar.updateMatrixWorld(true);
      nose.set(0.47 * L.fish_len, 0, 0); gar.localToWorld(nose);
      // forces on the fish (float beat): weight down, buoyancy up, almost equal
      const fa = F.arrows[k];
      wArrow.visible = bArrow.visible = fa > 0.01;
      if (fa > 0.01) {
        const c = gar.position;
        wArrow.position.set(c.x, c.y - 0.12, c.z - 0.25); wArrow.setLen(0.75 * fa);
        bArrow.position.set(c.x, c.y + 0.12, c.z - 0.25); bArrow.setLen(0.73 * fa);
      }
      const lw = F.look_w[k], lm = F.look_m[k];
      const fishHead = [nose.x, nose.y, nose.z];
      const tgt = s => s === 'fish' ? fishHead : s === 'wizard' ? head.wizard : s === 'woman' ? head.woman : s === 'net' ? [L.net[0], L.net[1], L.net[2]] : null;
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, sit: 1, point: F.wiz_rod_arm[k], 
                 ...headLook(wiz, tgt(lw) ?? head.woman, 0.9, 0.95), headTilt: 0.05 * Math.sin(t * 0.8) });
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, sit: 1, point: F.woman_point[k],
                 ...headLook(wom, tgt(lm) ?? head.wizard, 0.8, 0.9), headTilt: 0.05 * Math.sin(t * 0.9 + 1) });
      fr.place(F.rod_tilt[k], F.rod_yaw[k], 0.12, fishHead);
      fr.set(F.rod_bend[k], fishHead, F.line_sag[k]);
      fr.userData.spool.rotation.y = F.spool[k];
      ln.visible = F.wiz_net[k] > 0.02;
      if (ln.visible) { ln.position.set(...L.net); ln.rotation.set(0, L.net_yaw, -0.28); }
      if (shot !== lastShot) {
        lastShot = shot;
        if (plan.bloom_threshold) world.bloom.threshold = plan.bloom_threshold;
        const sc = world.sun.shadow.camera, e2 = 9;
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.far = 90; sc.updateProjectionMatrix();
      }
    },
    afterCamera(i) {
      LK.afterCamera(world.camera);
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.05, Math.max(0.005, d * 0.02)); world.camera.far = 600; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const fp = F.fish[Math.min(i, F.fish.length - 1)];
      return [{ entity: 'gar', part: 'subject', kind: 'thickness', p: [fp[0], fp[1], fp[2]], size: 0.3 }];
    },
    vars() { return {}; },
  };
}

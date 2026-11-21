// Shouting barely reaches fish, a dropped tackle box does (content/episodes/quiet-on-the-boat/plan.py).
// The shared lake set (renderer/sets/lake.js): a rowing boat out on the lake with the wizard (bow) and the woman
// (stern) sitting face to face, a trout hovering under the boat. Sound is drawn as wavefront rings on a vertical
// sheet through the boat's long axis: rings from a speaking mouth spread through the air, bounce off the water
// (mirror-image rings) and only a faint ring gets in; the tackle box hitting the floor sends strong rings through
// the water, 4.3 times faster. The plan lists every ring (start time, source, speed, strength); this file draws.
import * as THREE from 'three';
import { lake, fish, rowboat, tackleBox } from '../sets/lake.js';
import { presenters, seatRobe, headLook } from './fishwindow3d.js';

const MAXR = 48;

// a vertical sheet (the x-y plane at z = z0) that draws circular wavefronts. ring = [cx, cy, r, alpha] and
// prop = [side (+1 above water only, -1 below only), colour index, width, 0]
export function ringSheet(z0, w = 16, h = 9) {
  const R = Array.from({ length: MAXR }, () => new THREE.Vector4()), P = Array.from({ length: MAXR }, () => new THREE.Vector4());
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide, toneMapped: false,
    uniforms: { R: { value: R }, P: { value: P }, nR: { value: 0 }, below: { value: 1 },
                C0: { value: new THREE.Color('#fff3d0') }, C1: { value: new THREE.Color('#5ff0d6') }, C2: { value: new THREE.Color('#ffd27a') } },
    vertexShader: `varying vec3 wp; void main(){ vec4 w = modelMatrix * vec4(position,1.0); wp = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `
      uniform vec4 R[${MAXR}]; uniform vec4 P[${MAXR}]; uniform int nR; uniform float below; uniform vec3 C0, C1, C2;
      varying vec3 wp;
      void main(){
        float a = 0.0; vec3 col = vec3(0.0);
        for (int k = 0; k < ${MAXR}; k++) {
          if (k >= nR) break;
          vec4 r = R[k]; vec4 p = P[k];
          if (p.x * wp.y < 0.0) continue;
          float d = abs(length(wp.xy - r.xy) - r.z);
          float v = r.w * (1.0 - smoothstep(p.z * 0.4, p.z, d)) + r.w * 0.18 * (1.0 - smoothstep(p.z, p.z * 2.6, d));
          if (wp.y < 0.0) v *= below;
          vec3 c = p.y < 0.5 ? C0 : (p.y < 1.5 ? C1 : C2);
          col += c * v; a += v;
        }
        if (a < 0.02) discard;
        gl_FragColor = vec4(col / a, clamp(a, 0.0, 1.0));
      }`,
  });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
  m.position.set(0, 0, z0); m.renderOrder = 8; m.frustumCulled = false;
  m.setRings = list => {
    const n = Math.min(MAXR, list.length);
    for (let k = 0; k < n; k++) { R[k].set(...list[k][0]); P[k].set(...list[k][1]); }
    mat.uniforms.nR.value = n;
  };
  return m;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  const LK = lake(world, { keepClear: [[-4, 4]], jettyX: -6.5 });
  const boat = rowboat('#2e8f86'); boat.rotation.y = Math.PI / 2; boat.position.set(L.boat[0], 0.12, L.boat[2]); S.add(boat);
  const { wiz, wom } = presenters(S, L);
  seatRobe(wiz);
  const box = tackleBox('#c9a77c'); S.add(box);
  const trout = fish('trout', L.fish_len); S.add(trout);
  const sheet = ringSheet(L.boat[2], 18, 10); sheet.position.x = L.boat[0]; S.add(sheet);
  // mouths: where each presenter's rings start (head bone, a little forward and down), measured once seated
  const mouth = {};
  for (const [k, p] of [['wizard', wiz], ['woman', wom]]) {
    p.pose({ sit: 1 }); p.updateMatrixWorld(true);
    let hb = null; p.traverse(o => { if (!hb && o.isBone && o.name === 'head') hb = o; });
    const v = new THREE.Vector3(); if (hb) hb.getWorldPosition(v); else v.copy(p.position).add(new THREE.Vector3(0, 0.9, 0));
    const fwd = new THREE.Vector3(Math.sin(p.rotation.y), 0, Math.cos(p.rotation.y));
    v.addScaledVector(fwd, 0.1).add(new THREE.Vector3(0, -0.04, 0));
    mouth[k] = [v.x, v.y];
  }
  S.updateMatrixWorld(true);
  const wp = new THREE.Vector3();
  S.traverse(o => { if (o.isMesh && o.castShadow) { o.getWorldPosition(wp); if (Math.hypot(wp.x - L.boat[0], wp.z - L.boat[2]) > 9) o.castShadow = false; } });
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const head = { wizard: [L.wiz[0], 0.85, L.wiz[2]], woman: [L.woman[0], 0.8, L.woman[2]] };
  const fishPt = () => [trout.position.x, trout.position.y, trout.position.z];
  let lastShot = null;

  function rings(t, xr) {
    const out = [];
    for (const e of plan.rings) {
      const age = t - e.t0; if (age <= 0 || age > e.life) continue;
      const fade = (1 - age / e.life) ** 1.4 * Math.min(1, age / 0.08);
      const src = e.src === 'wizard' || e.src === 'woman' ? mouth[e.src] : e.at;
      const r = e.v * age;
      if (e.kind === 'air') {
        out.push([[src[0], src[1], r, e.a * fade], [1, 0, 0.03, 0]]);
        const h = src[1];
        if (r > h) {
          out.push([[src[0], -h, r, e.a * fade * 0.92], [1, 0, 0.03, 0]]);                         // the echo off the surface
          if (xr) out.push([[src[0], 0, (r - h) * plan.speed_ratio, e.a * fade * e.leak], [-1, 1, 0.03, 0]]);   // what gets in
        }
      } else if (e.kind === 'water') {
        out.push([[src[0], src[1], r, e.a * fade], [-1, 1, 0.045, 0]]);
      } else if (e.kind === 'race_air') {
        out.push([[src[0], src[1], r, e.a * fade], [1, 2, 0.035, 0]]);
      }
    }
    return out.sort((a, b) => b[0][3] - a[0][3]).slice(0, MAXR);
  }

  return {
    lightCenter: new THREE.Vector3(L.boat[0], 0, L.boat[2]),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      LK.update(t, world.camera);
      const xr = F.xray[k] > 0;
      LK.opacity = xr ? 0.3 : 0.8;
      // the boat rocks gently; the box's landing gives it a small jolt
      const bob = 0.012 * Math.sin(t * 1.4) - 0.012 * F.jolt[k];
      boat.position.y = 0.12 + bob; boat.rotation.z = 0.012 * Math.sin(t * 1.1 + 0.4) + 0.01 * F.jolt[k];
      for (const [p, base] of [[wiz, L.wiz], [wom, L.woman]]) p.position.y = base[1] + bob;
      box.position.set(F.box[k][0], F.box[k][1] + bob, F.box[k][2]); box.rotation.set(0, Math.PI / 2 + 0.25, F.box[k][3]);
      trout.position.set(...F.fish[k]); trout.rotation.y = F.fish_yaw[k];
      trout.swim(t, F.fish_swim[k], F.fish_turn[k]);
      sheet.material.uniforms.below.value = xr || world.camera.position.y < 0 ? 1 : 0;
      sheet.visible = F.rings_on[k] > 0; sheet.setRings(rings(t, xr));
      const lw = F.look_w[k], lm = F.look_m[k];
      const tgt = s => s === 'water' ? [L.boat[0] + 0.2, -0.6, L.boat[2] + 0.6] : s === 'box' ? [F.box[k][0], F.box[k][1], F.box[k][2]] : s === 'fish' ? fishPt() : null;
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, sit: 1, wave: F.wiz_wave[k], point: F.wiz_point[k],
                 ...headLook(wiz, tgt(lw) ?? head.woman, 0.9, 0.95), headTilt: 0.05 * Math.sin(t * 0.8) });
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, sit: 1, point: F.woman_point[k],
                 ...headLook(wom, tgt(lm) ?? head.wizard, 0.8, 0.9), headTilt: 0.05 * Math.sin(t * 0.9 + 1) });
      if (shot !== lastShot) {
        lastShot = shot;
        if (plan.bloom_threshold) world.bloom.threshold = plan.bloom_threshold;
        const sc = world.sun.shadow.camera, e2 = 7;
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
      return [{ entity: 'boat', part: 'subject', kind: 'thickness', p: [L.boat[0], 0.1, L.boat[2]], size: 1.2 }];
    },
    vars() { return {}; },
  };
}

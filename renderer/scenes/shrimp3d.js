// The mantis shrimp punch (content/episodes/mantis-shrimp-punch/plan.py).
// A dim aquarium gallery: the presenters stand at the glass of a big reef tank (sand, rocks, corals, light from
// above) where a small mantis shrimp sits by a sea snail. Far away, a big slow-motion macro reef (badged as an
// illustration): the shrimp's club arm latches and loads its saddle spring, snaps out, hits the shell, the water in
// front of the club tears into a cloud of bubbles that collapse with a tiny flash, and the shell cracks.
// This file only draws what the plan lists.
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { mantisShrimp, seaSnail } from '../shrimp.js';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, ...x });
const sh = o => { o.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } }); return o; };

let _rad;
function radial() {
  if (_rad) return _rad;
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(255,255,255,0.5)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128); _rad = new THREE.CanvasTexture(c); return _rad;
}

// a reef patch: rippled sand, rocks, corals and sunbeams, all scaled by k around (cx, y0, cz)
function reef(S, cx, y0, cz, k, rnd, keepOut) {
  const g = new THREE.Group(); g.position.set(cx, y0, cz); S.add(g);
  const sandG = new THREE.PlaneGeometry(14 * k, 10 * k, 120, 90); sandG.rotateX(-Math.PI / 2);
  const P = sandG.attributes.position;
  for (let i = 0; i < P.count; i++) { const x = P.getX(i) / k, z = P.getZ(i) / k; P.setY(i, k * (0.015 * Math.sin(x * 9 + z * 2) + 0.01 * Math.sin(z * 13))); }
  sandG.computeVertexNormals();
  const sand = new THREE.Mesh(sandG, std('#b9a77c', { roughness: 1 })); sand.receiveShadow = k > 0.5; g.add(sand);
  const clear = (x, z) => !keepOut || keepOut.every(([kx, kz, r]) => Math.hypot(x - kx, z - kz) > r);
  const rockM = [std('#7d7466', { flatShading: true }), std('#8a8070', { flatShading: true }), std('#6b6458', { flatShading: true })];
  for (let n = 0; n < 16; n++) {
    const x = (rnd() - 0.5) * 9, z = (rnd() - 0.5) * 6 - 1.0; if (!clear(x, z)) continue;
    const r = new THREE.Mesh(new THREE.IcosahedronGeometry(0.25 + rnd() * 0.35, 2), rockM[n % 3]);
    const Q = r.geometry.attributes.position; for (let i = 0; i < Q.count; i++) { const f = 1 + 0.18 * Math.sin(Q.getX(i) * 9 + n) * Math.cos(Q.getZ(i) * 7); Q.setXYZ(i, Q.getX(i) * f, Q.getY(i) * f * 0.7, Q.getZ(i) * f); }
    r.geometry.computeVertexNormals(); r.scale.setScalar(k); r.position.set(x * k, 0.05 * k, z * k); g.add(r);
  }
  const corals = ['#e8762c', '#d4567a', '#a99bc4', '#e2c45a', '#5aa36a', '#2e8f86', '#e6e3dc'];
  for (let n = 0; n < 22; n++) {
    const x = (rnd() - 0.5) * 10, z = (rnd() - 0.5) * 7 - 1.2; if (!clear(x, z)) continue;
    const col = corals[n % corals.length], c = new THREE.Group(); c.position.set(x * k, 0, z * k); c.scale.setScalar(k * (0.7 + rnd() * 0.6)); g.add(c);
    const kind = n % 3;
    if (kind === 0) {                                   // branching coral: tapered fingers
      for (let b = 0; b < 7; b++) {
        const h = 0.25 + rnd() * 0.3, a = b * 0.9;
        const f = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.035, h, 16), std(col, { roughness: 0.6 }));
        f.position.set(Math.cos(a) * 0.06, h / 2, Math.sin(a) * 0.06); f.rotation.set(Math.sin(a) * 0.35, 0, Math.cos(a) * 0.35); c.add(f);
        const tip = new THREE.Mesh(new THREE.SphereGeometry(0.02, 24, 16), std(col, { roughness: 0.5 })); tip.position.set(f.position.x * 2.2, h * 0.98, f.position.z * 2.2); c.add(tip);
      }
    } else if (kind === 1) {                            // brain coral: a bumpy dome
      const d = new THREE.Mesh(new THREE.SphereGeometry(0.2, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2), std(col, { roughness: 0.7 }));
      const Q = d.geometry.attributes.position; for (let i = 0; i < Q.count; i++) { const f = 1 + 0.05 * Math.sin(Q.getX(i) * 60) * Math.sin(Q.getZ(i) * 60); Q.setXYZ(i, Q.getX(i) * f, Q.getY(i) * f, Q.getZ(i) * f); }
      d.geometry.computeVertexNormals(); c.add(d);
    } else {                                            // sea fan: a wavy flat lattice
      const fg = new THREE.CircleGeometry(0.3, 48, 0, Math.PI); const Q = fg.attributes.position;
      for (let i = 0; i < Q.count; i++) Q.setZ(i, 0.02 * Math.sin(Q.getX(i) * 20));
      fg.computeVertexNormals();
      const fan = new THREE.Mesh(fg, std(col, { roughness: 0.8, side: THREE.DoubleSide, transparent: true, opacity: 0.9 })); fan.rotation.y = rnd() * 3; c.add(fan);
    }
  }
  sh(g); sand.castShadow = false;
  // sunbeams: soft additive shafts from above
  const beamM = new THREE.MeshBasicMaterial({ color: '#cff3ff', transparent: true, opacity: 0.07, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false });
  const beams = [];
  for (let n = 0; n < 6; n++) {
    const b = new THREE.Mesh(new THREE.CylinderGeometry(0.15 * k, 0.6 * k, 6 * k, 24, 1, true), beamM);
    b.position.set((n - 2.5) * 1.4 * k, 3 * k, (-1.5 + (n % 2)) * k); b.rotation.z = 0.25; g.add(b); beams.push(b);
  }
  return { g, beams };
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  const rnd = (() => { let s = 11; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); })();
  // ---- the aquarium gallery
  const floor = new THREE.Mesh(new THREE.BoxGeometry(12, 0.1, 12), std('#22313b', { roughness: 0.9 })); floor.position.set(0, -0.05, 1.5); floor.receiveShadow = true; S.add(floor);
  const wallM = std('#1b2a35', { roughness: 0.95 });
  for (const s of [-1, 1]) { const w = new THREE.Mesh(new THREE.BoxGeometry(0.2, 4, 12), wallM); w.position.set(s * 4.2, 2, 1.5); w.receiveShadow = true; S.add(w); }
  const back = new THREE.Mesh(new THREE.BoxGeometry(8.6, 4, 0.2), wallM); back.position.set(0, 2, 5.5); S.add(back);
  const ceil = new THREE.Mesh(new THREE.BoxGeometry(8.6, 0.2, 12), std('#14202a')); ceil.position.set(0, 4.0, 1.5); S.add(ceil);
  const bench = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.45, 0.6, 2, 2, 2), std('#5e4630', { roughness: 0.7 })); bench.position.set(0, 0.225, 4.4); bench.castShadow = bench.receiveShadow = true; S.add(bench);
  // the tank: cabinet, frame, glass front, glowing back panel, reef inside
  const T = L.tank;     // [x0, x1, y0, y1, z0, z1]  z1 = glass
  const cab = new THREE.Mesh(new THREE.BoxGeometry(T[1] - T[0] + 0.2, T[2], T[5] - T[4] + 0.2, 2, 2, 2), std('#3a2e24', { roughness: 0.6 })); cab.position.set((T[0] + T[1]) / 2, T[2] / 2, (T[4] + T[5]) / 2); cab.receiveShadow = true; S.add(cab);
  const frameM = std('#3a3640', { roughness: 0.5, metalness: 0.3 });
  for (const [w, h, d, x, y, z] of [[T[1] - T[0] + 0.2, 0.1, 0.12, (T[0] + T[1]) / 2, T[3] + 0.05, T[5]], [T[1] - T[0] + 0.2, 0.08, 0.12, (T[0] + T[1]) / 2, T[2] + 0.02, T[5]],
                                    [0.1, T[3] - T[2], 0.12, T[0] - 0.05, (T[2] + T[3]) / 2, T[5]], [0.1, T[3] - T[2], 0.12, T[1] + 0.05, (T[2] + T[3]) / 2, T[5]]]) {
    const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), frameM); b.position.set(x, y, z); S.add(b);
  }
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(T[1] - T[0], T[3] - T[2]), new THREE.MeshPhysicalMaterial({ color: '#cdeff5', transparent: true, opacity: 0.1, roughness: 0.05, side: THREE.DoubleSide, depthWrite: false }));
  glass.position.set((T[0] + T[1]) / 2, (T[2] + T[3]) / 2, T[5]); S.add(glass);
  const backPanel = new THREE.Mesh(new THREE.PlaneGeometry(T[1] - T[0], T[3] - T[2]), new THREE.MeshBasicMaterial({ color: '#2f8fa6', fog: false }));
  backPanel.position.set((T[0] + T[1]) / 2, (T[2] + T[3]) / 2, T[4] + 0.01); S.add(backPanel);
  for (const s of [-1, 1]) { const side = new THREE.Mesh(new THREE.PlaneGeometry(T[5] - T[4], T[3] - T[2]), new THREE.MeshBasicMaterial({ color: '#2a8098', fog: false, side: THREE.DoubleSide })); side.rotation.y = Math.PI / 2; side.position.set(s < 0 ? T[0] : T[1], (T[2] + T[3]) / 2, (T[4] + T[5]) / 2); S.add(side); }
  const tankReef = reef(S, (T[0] + T[1]) / 2, T[2], (T[4] + T[5]) / 2 + 0.1, 0.32, rnd, [[0.4, 0.6, 1.4], [-0.3, 1.5, 1.1]]);
  tankReef.beams.forEach(b => { b.material = b.material.clone(); b.material.opacity = 0.05; });
  const tankLight = new THREE.PointLight('#bff0ff', 6, 4.5, 2); tankLight.position.set(0, T[3] - 0.2, (T[4] + T[5]) / 2); S.add(tankLight);
  const spill = new THREE.PointLight('#9fe0ee', 6.0, 4.5, 2); spill.position.set(0, 1.5, T[5] + 0.4); S.add(spill);
  const warm = new THREE.PointLight('#ffd9b0', 3.2, 3.5, 2); warm.position.set(0.0, 2.1, -0.15); S.add(warm);
  const small = mantisShrimp(); small.scale.setScalar(L.tank_scale); small.position.set(...L.tank_shrimp); small.rotation.y = L.tank_shrimp_yaw; S.add(small);
  const smallSnail = seaSnail(); smallSnail.scale.setScalar(L.tank_scale * 1.4); smallSnail.position.set(...L.tank_snail); smallSnail.rotation.y = L.tank_shrimp_yaw + Math.PI; S.add(smallSnail);

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

  // ---- the macro reef
  const M = L.macro;
  reef(S, M[0], 0, M[2], 1.0, rnd, [[0.4, 0.0, 1.6], [1.4, 1.7, 1.2], [0.6, 1.2, 0.9]]);
  const seabed = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), std('#cbb98f', { roughness: 1 })); seabed.rotation.x = -Math.PI / 2; seabed.position.set(M[0], -0.02, M[2]); seabed.receiveShadow = true; S.add(seabed);
  const big = mantisShrimp(); big.position.set(M[0], 0, M[2]); S.add(big);
  const snail = seaSnail(); snail.scale.setScalar(L.snail_scale); snail.position.set(M[0] + L.snail_dx, 0.0, M[2]); snail.rotation.y = Math.PI; S.add(snail);
  // the bubble cloud just in front of the club's strike point
  const C = L.contact;
  const bubM = new THREE.MeshPhysicalMaterial({ color: '#e9f6ff', roughness: 0.05, metalness: 0.25, emissive: '#9fd8ff', emissiveIntensity: 0.12, transparent: true, opacity: 0.85, clearcoat: 0.4 });
  const bubbles = Array.from({ length: 70 }, (_, k) => {
    const b = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), bubM);
    const a = rnd() * Math.PI * 2, r = Math.sqrt(rnd());
    b.userData = { o: [0.02 * (rnd() - 0.3), 0.05 * r * Math.sin(a), 0.06 * r * Math.cos(a)], r: 0.004 + 0.009 * rnd() };
    S.add(b); return b;
  });
  const flash = new THREE.Sprite(new THREE.SpriteMaterial({ map: radial(), color: '#fff4d6', transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
  flash.position.set(...C); flash.scale.setScalar(0.18); S.add(flash);
  const flashLight = new THREE.PointLight('#fff1c8', 0, 1.2, 2); flashLight.position.set(...C); S.add(flashLight);
  // marine snow drifting through the macro reef
  const snowM = new THREE.MeshBasicMaterial({ color: '#e8f8ff', transparent: true, opacity: 0.55 });
  const snow = Array.from({ length: 50 }, () => { const s = new THREE.Mesh(new THREE.SphereGeometry(0.004, 12, 8), snowM); s.userData.p = [M[0] + (rnd() - 0.4) * 2.4, rnd() * 1.2, M[2] + (rnd() - 0.5) * 2.0, rnd() * 6]; S.add(s); return s; });

  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const v = new THREE.Vector3();
  const headLook = (person, target, maxYaw = 0.9, eye = 1.5) => {
    v.set(...target).sub(person.position);
    let yaw = Math.atan2(v.x, v.z) - person.rotation.y; yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    const pitch = -Math.atan2(target[1] - person.position.y - eye, Math.hypot(v.x, v.z));
    return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, yaw)), headPitch: Math.max(-0.3, Math.min(0.5, pitch)) };
  };
  const wizHead = [L.wiz[0], 1.65, L.wiz[2]], womHead = [L.woman[0], 1.55, L.woman[2]], tankPt = [L.tank_shrimp[0], L.tank_shrimp[1] + 0.05, L.tank_shrimp[2]];
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(0, 0, 0),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      big.pose({ strike: F.strike[k], load: F.load[k], t });
      snail.set({ crack: F.crack[k], shardT: F.shard_t[k], t });
      small.pose({ strike: F.tank_strike[k], t: t + 3 });
      smallSnail.set({ crack: 0, t });
      const bs = F.bub[k];
      bubbles.forEach((b, q) => { const u = b.userData; b.visible = bs > 0.01; b.scale.setScalar(Math.max(1e-4, u.r * bs * (0.6 + 0.4 * Math.sin(q + t * 3)))); b.position.set(C[0] + u.o[0], C[1] + u.o[1], C[2] + u.o[2]); });
      const fl = F.flash[k]; flash.material.opacity = 0.55 * fl; flash.scale.setScalar(0.015 + 0.035 * fl); flashLight.intensity = 0.4 * fl;
      snow.forEach(s => { const p = s.userData.p; s.position.set(p[0] + 0.05 * Math.sin(t * 0.3 + p[3]), (p[1] + 0.02 * t + p[3]) % 1.3, p[2]); });
      const lw = F.look_w[k], lm = F.look_m[k];
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, ...headLook(wiz, lw === 'woman' ? womHead : tankPt, 0.9, 1.6), headTilt: 0.04 * Math.sin(t * 0.7), point: F.wiz_point[k] });
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, ...headLook(wom, lm === 'tank' ? tankPt : wizHead), headTilt: 0.05 * Math.sin(t * 0.9 + 1), point: F.woman_point[k] });
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i);
        world.setLighting(shot.lighting ?? 'reef', new THREE.Vector3(fp[0], 0, fp[2]));
        const sc = world.sun.shadow.camera, e2 = Math.abs(fp[0]) > 10 ? 9 : 5;
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.near = -60; sc.far = 80; sc.updateProjectionMatrix();
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.05, Math.max(0.003, d * 0.02)); world.camera.far = 300; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const fp = focalPt(i);
      const ent = Math.abs(fp[0] - M[0]) < 6 ? 'shrimp' : 'reef';
      return [{ entity: ent, part: 'subject', kind: 'thickness', p: fp, size: 0.15 }];
    },
    vars() { return {}; },
  };
}

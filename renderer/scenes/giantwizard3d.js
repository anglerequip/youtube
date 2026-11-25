// What if you were a hundred times taller? (content/episodes/giant-wizard/plan.py)
// The ice set (renderer/sets/ice.js) at real scale. The wizard grows from 15x to 100x his height (200 m with the
// hat) on the Antarctic ice shelf; the woman stands at normal size in front of his boots with a few penguins, a
// red research hut and a tent. X-ray shots ghost the giant and show his two thigh bones (placed between his own hip,
// knee and ankle joints every frame) that glow, turn red under load and crack. Later he buckles at the knees,
// glows warm, steams in the cold and melts a dark ring into the snow, then shrinks back (the loop to the hook).
// This file only draws what the plan lists.
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { ice, penguin, hut, tent } from '../sets/ice.js';

function softTex() {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.5, 'rgba(255,255,255,0.45)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const seeded = s => () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);

export function headLook(person, target, maxYaw = 0.9, eye = 1.5, scale = 1) {
  const v = new THREE.Vector3(...target).sub(person.position);
  let yaw = Math.atan2(v.x, v.z) - person.rotation.y; yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));
  const pitch = -Math.atan2(target[1] - person.position.y - eye * scale, Math.hypot(v.x, v.z));
  return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, yaw)), headPitch: Math.max(-0.5, Math.min(0.5, pitch)) };
}

// a bone segment: a smooth capsule-like cylinder with rounded knobs, re-placed between two points each frame
function boneSeg(mat, knobMat) {
  const g = new THREE.Group();
  // a long bone: a lathe shaft that waists in the middle and flares to each end, capped by paired knobs (condyles)
  const prof = [];
  for (let k = 0; k <= 24; k++) { const y = -0.5 + k / 24, e = Math.abs(2 * y); prof.push(new THREE.Vector2(0.62 + 0.55 * e ** 5, y)); }
  const shaft = new THREE.Mesh(new THREE.LatheGeometry(prof, 40), mat);
  const kg = new THREE.SphereGeometry(1, 48, 36);
  const k1 = new THREE.Group(), k2 = new THREE.Group();
  for (const kk of [k1, k2]) for (const sx of [-1, 1]) { const m = new THREE.Mesh(kg, knobMat); m.position.x = sx * 0.55; m.scale.set(0.95, 0.8, 0.95); kk.add(m); }
  g.add(shaft, k1, k2);
  // cracks: jagged thin tubes around the middle of the shaft (local, unit radius)
  const cracks = new THREE.Group(); g.add(cracks);
  const R = seeded(7), crackM = new THREE.MeshBasicMaterial({ color: '#160605', toneMapped: false });
  for (let c = 0; c < 5; c++) {
    const pts = []; let a = R() * 6.28, y = (R() - 0.5) * 0.4;
    for (let k = 0; k < 7; k++) { pts.push(new THREE.Vector3(Math.cos(a) * 0.66, y, Math.sin(a) * 0.66)); a += 0.2 + R() * 0.2; y += (R() < 0.5 ? -1 : 1) * (0.06 + R() * 0.08); }
    const tub = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 64, 0.04, 8), crackM);
    cracks.add(tub);
  }
  const up = new THREE.Vector3(0, 1, 0), a = new THREE.Vector3(), d = new THREE.Vector3();
  g.place = (p0, p1, r) => {
    d.copy(p1).sub(p0); const L = d.length();
    a.copy(p0).addScaledVector(d, 0.5);
    g.position.copy(a); g.quaternion.setFromUnitVectors(up, d.normalize());
    shaft.scale.set(r, L * 0.92, r);
    k1.scale.setScalar(r * 1.35); k1.position.set(0, L * 0.46, 0);
    k2.scale.setScalar(r * 1.25); k2.position.set(0, -L * 0.46, 0);
    cracks.scale.set(r, L * 0.9, r);
  };
  g.cracks = cracks;
  return g;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  const I = ice(world, { keepFlat: [[0, 0, 110], [L.woman[0], L.woman[2], 30]] });

  // the giant
  const wiz = man(); wiz.position.set(...L.wiz); wiz.rotation.y = L.wiz_face; S.add(wiz);
  wiz.traverse(o => { if (o.isSprite || o.isPointLight) o.visible = false; });
  const wizMeshes = [];
  wiz.traverse(o => {
    if (!o.isMesh) return;
    o.material = o.material.clone();
    const m = o.material;
    o.userData.base = { emissive: m.emissive ? m.emissive.clone() : new THREE.Color(0), ei: m.emissiveIntensity ?? 1, transparent: m.transparent, opacity: m.opacity, depthWrite: m.depthWrite };
    wizMeshes.push(o);
  });
  const findBone = n => { let f = null; wiz.traverse(o => { if (!f && o.isBone && o.name === n) f = o; }); return f; };
  const J = { hipL: findBone('thigh_L'), hipR: findBone('thigh_R'), kneeL: findBone('calf_L'), kneeR: findBone('calf_R') };
  J.ankleL = J.kneeL ? J.kneeL.children.find(c => c.isBone) : null;
  J.ankleR = J.kneeR ? J.kneeR.children.find(c => c.isBone) : null;

  // the woman (normal size) and the scale props around her
  const wom = woman(); wom.position.set(...L.woman); wom.rotation.y = L.woman_face; S.add(wom);
  wom.traverse(o => { if (o.isSprite || o.isPointLight) o.visible = false; });
  const ringM = new THREE.MeshBasicMaterial({ color: '#f3f1ea', transparent: true, opacity: 0.85, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 });
  ringM.userData.noVariation = true;
  const ring = new THREE.Mesh(new THREE.RingGeometry(2.3, 2.55, 96), ringM); ring.rotation.x = -Math.PI / 2;
  ring.position.set(L.woman[0], 0.05, L.woman[2]); ring.renderOrder = 3; S.add(ring);
  const pens = [];
  const penSpots = [[3, 70, 0.3], [5.5, 73, -0.4], [-6, 66, 1.2], [-4, 80, 2.4], [16, 55, -2.0], [-12, 90, 0.8], [30, 100, -1], [-18, 103, 0.2], [38, 70, 2.7], [33, 67, -0.6], [-22, 92, -2.6]];
  penSpots.forEach(([x, z, r], k) => { const p = penguin(0.95 + 0.12 * ((k * 37) % 5) / 5, k + 1); p.position.set(x, 0, z); p.rotation.y = r; S.add(p); pens.push(p); });
  const H = hut(); H.position.set(30, 0, 52); H.rotation.y = -0.6; S.add(H);
  const T = tent(); T.position.set(-34, 0, 124); T.rotation.y = 0.5; S.add(T);
  // a few flag stakes (a route line) leading off over the ice
  const stakeM = new THREE.MeshStandardMaterial({ color: '#5b5f63', roughness: 0.6 }), flagM = new THREE.MeshStandardMaterial({ color: '#c92a2e', roughness: 0.7, side: THREE.DoubleSide });
  for (let k = 0; k < 9; k++) {
    const x = 55 + k * 22, z = 140 - k * 30;
    const st = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.6, 16), stakeM); st.position.set(x, 0.8, z); st.castShadow = true; S.add(st);
    const fl = new THREE.Mesh(new THREE.PlaneGeometry(0.35, 0.25), flagM); fl.position.set(x + 0.18, 1.45, z); fl.castShadow = true; S.add(fl);
  }

  // thigh and shin bones for the x-ray shots
  const boneM = new THREE.MeshStandardMaterial({ color: '#eef6ff', emissive: '#bfe3ff', emissiveIntensity: 0.6, roughness: 0.4, transparent: true, depthTest: true });
  const boneK = boneM;
  const bones = [boneSeg(boneM, boneK), boneSeg(boneM, boneK), boneSeg(boneM, boneK), boneSeg(boneM, boneK)];
  bones.forEach(b => { b.renderOrder = 8; b.traverse(o => { o.renderOrder = 8; }); S.add(b); });

  // steam (soft sprites rising off him), snow puffs at his boots, the melt ring
  const tex = softTex(), R = seeded(11);
  const steamM = new THREE.SpriteMaterial({ map: tex, color: '#f4f7fa', transparent: true, opacity: 0, depthWrite: false, fog: true });
  const steam = [];
  for (let k = 0; k < 90; k++) {
    const s = new THREE.Sprite(steamM); s.userData = { ph: R(), ang: R() * 6.28, rad: 0.2 + R() * 0.3, hy: 0.6 + R() * 1.3, sz: 0.14 + R() * 0.16, sp: 0.04 + R() * 0.05 };
    s.renderOrder = 9; S.add(s); steam.push(s);
  }
  const puffM = new THREE.SpriteMaterial({ map: tex, color: '#ffffff', transparent: true, opacity: 0, depthWrite: false });
  const puffs = [];
  for (let k = 0; k < 40; k++) { const s = new THREE.Sprite(puffM); s.userData = { ang: R() * 6.28, d: 0.1 + R() * 0.35, h: R(), sz: 0.08 + R() * 0.14 }; s.renderOrder = 9; S.add(s); puffs.push(s); }
  const meltM = new THREE.MeshStandardMaterial({ color: '#7f9db6', roughness: 0.15, metalness: 0.05, transparent: true, opacity: 0, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 });
  meltM.userData.noVariation = true;
  const melt = new THREE.Mesh(new THREE.CircleGeometry(1, 96), meltM); melt.rotation.x = -Math.PI / 2; melt.position.set(L.wiz[0], 0.06, L.wiz[2] + 4); melt.renderOrder = 2; S.add(melt);

  const warm = new THREE.Color('#ff6a2a'), stressC = new THREE.Color('#c92a2e'), boneC = new THREE.Color('#eef6ff'), boneE = new THREE.Color('#bfe3ff');
  const v0 = new THREE.Vector3(), v1 = new THREE.Vector3(), v2 = new THREE.Vector3();
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  let lastShot = null, lastX = -1;
  const sunDir = new THREE.Vector3();

  const api = {
    lightCenter: new THREE.Vector3(0, 0, 30),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.gscale.length - 1);
      const g = F.gscale[k], sit = F.sit[k], xr = F.xray[k] > 0;
      I.update(t, world.camera);
      // the scale ring only matters from afar: fade it in with camera distance
      ringM.opacity = 0.85 * Math.min(1, Math.max(0, (world.camera.position.distanceTo(ring.position) - 35) / 40));
      ring.visible = ringM.opacity > 0.01;
      wiz.scale.setScalar(g);
      const lw = F.look_w[k];
      const tgt = lw === 'woman' ? [L.woman[0], 1.5, L.woman[2]] : lw === 'down' ? [L.wiz[0], 0, L.wiz[2] + 60 * g / 100] : [L.wiz[0], 1.4 * g, L.wiz[2] + 300];
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t: t * 0.4, sit, wave: F.wiz_wave[k], point: F.wiz_point[k],
                 ...headLook(wiz, tgt, 0.7, 1.69 - 0.46 * sit, g), headTilt: 0.03 * Math.sin(t * 0.35) });
      // keep the robe hem on the snow when he buckles (the pose lowers the whole model)
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, point: F.woman_point[k],
                 headYaw: 0.12 * Math.sin(t * 0.5), headPitch: F.woman_up[k] ? -0.35 : 0.0, headTilt: 0.05 * Math.sin(t * 0.9 + 1) });
      pens.forEach((p, j) => p.waddle(t, j % 3 === 0 ? 1 : 0.3));
      H.wave(t);

      // heat glow and x-ray ghosting on the giant's materials
      const heat = F.heat[k];
      if (xr !== (lastX === 1) || lastX < 0) {
        for (const o of wizMeshes) {
          const m = o.material, b = o.userData.base;
          m.transparent = xr ? true : b.transparent; m.opacity = xr ? 0.2 : b.opacity; m.depthWrite = xr ? false : b.depthWrite;
          m.needsUpdate = true; o.castShadow = !xr;
        }
        lastX = xr ? 1 : 0;
      }
      // (heat is shown by steam and the melt ring only: his own colours never change, so he stays the same wizard)
      void heat;

      // bones between his joints
      wiz.updateMatrixWorld(true);
      const show = xr && J.hipL && J.kneeL;
      bones.forEach(b => { b.visible = !!show; });
      if (show) {
        const r = 0.024 * g;
        const segs = [[J.hipL, J.kneeL], [J.kneeL, J.ankleL], [J.hipR, J.kneeR], [J.kneeR, J.ankleR]];
        segs.forEach(([a, b], j) => {
          if (!a || !b) { bones[j].visible = false; return; }
          a.getWorldPosition(v0); b.getWorldPosition(v1);
          bones[j].place(v0, v1, j % 2 === 0 ? r : r * 0.8);
          bones[j].cracks.visible = j % 2 === 0 && F.crack[k] > 0.02;
          bones[j].cracks.children.forEach((c, q) => { c.visible = q / 5 < F.crack[k]; });
        });
        const st = F.stress[k], gl = F.bone_glow[k];
        boneM.color.copy(boneC).lerp(stressC, st);
        boneM.emissive.copy(boneE).lerp(stressC, st);
        boneM.emissiveIntensity = (0.25 + 0.6 * gl) * (1 + 0.6 * F.crack[k] * (0.5 + 0.5 * Math.sin(t * 18)));
        boneM.opacity = 0.35 + 0.65 * gl;
      }

      // steam: sprites rise from his shoulders and hat, scaled to him
      const sv = F.steam[k];
      steamM.opacity = 0.55 * sv;
      steam.forEach(s => {
        const u = s.userData, ph = (u.ph + t * u.sp) % 1;
        const y = (u.hy - 0.46 * sit + ph * 0.9) * g;
        s.position.set(L.wiz[0] + Math.cos(u.ang) * u.rad * g * (1 + ph * 0.8), y, L.wiz[2] + Math.sin(u.ang) * u.rad * g * (1 + ph * 0.8));
        s.scale.setScalar(u.sz * g * (0.6 + 1.6 * ph));
        s.visible = sv > 0.01;
      });
      // snow puffs: a ring of spray out from his boots
      const pf = F.puff[k];
      puffM.opacity = pf > 0 ? 0.75 * Math.sin(Math.PI * Math.min(1, pf)) : 0;
      puffs.forEach(s => {
        const u = s.userData, d = (0.15 + u.d * (0.4 + pf)) * g;
        s.position.set(L.wiz[0] + Math.cos(u.ang) * d, (0.01 + 0.05 * u.h * pf) * g, L.wiz[2] + 3 + Math.sin(u.ang) * d);
        s.scale.setScalar(u.sz * g * (0.5 + pf)); s.visible = pf > 0;
      });
      meltM.opacity = 0.55 * F.melt[k];
      melt.scale.setScalar((0.35 + 0.15 * F.melt[k]) * g); melt.visible = F.melt[k] > 0.01;

      if (shot !== lastShot) {
        lastShot = shot;
        if (plan.bloom_threshold) world.bloom.threshold = plan.bloom_threshold;
      }
      // sun and shadow box sized to what this frame looks at; fog by viewing distance
      const fp = new THREE.Vector3(...focalPt(i));
      const pos = shot.pos ? shot.pos[Math.min(Math.max(0, i - shot.i0), shot.pos.length - 1)] : [0, 0, 0];
      const dist = fp.distanceTo(new THREE.Vector3(...pos));
      const ext = Math.min(720, Math.max(14, dist * 0.9, g * 3.2));
      sunDir.copy(world.sun.position).sub(world.sun.target.position).normalize();
      const c = new THREE.Vector3(fp.x, 0, fp.z);
      if (ext > 60) { c.set(-sunDir.x, 0, -sunDir.z).normalize().multiplyScalar(g * 2.2); c.z += 30; }
      world.sun.target.position.copy(c); world.sun.position.copy(c).addScaledVector(sunDir, 900);
      const sc = world.sun.shadow.camera; sc.left = -ext; sc.right = ext; sc.top = ext; sc.bottom = -ext; sc.near = 100; sc.far = 2000; sc.updateProjectionMatrix();
      world.sun.shadow.bias = -0.0003 * Math.max(1, ext / 30);
      world.rim.position.copy(c).add(new THREE.Vector3(-300, 200, -400)); world.rim.target.position.copy(c);
      I.fogFor(dist);
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(8, Math.max(0.03, d * 0.02)); world.camera.far = 9000; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const k = Math.min(i, F.gscale.length - 1);
      return [{ entity: 'giant', part: 'subject', kind: 'thickness', p: [0, 1.0 * F.gscale[k], 0], size: 0.4 * F.gscale[k] }];
    },
    vars() { return {}; },
  };
  return api;
}

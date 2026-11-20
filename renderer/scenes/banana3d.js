// Your banana is radioactive (content/episodes/banana-radioactive/plan.py).
// A banana on a wooden picnic table in a garden, a wooden toy figure beside it, and a not-to-scale cluster of
// potassium atoms floating above the table. Every flash on the banana is a decay from the plan's real-rate Poisson
// sample; on the figure, one decay in SHOW_EVERY is drawn. This file only draws what the plan lists.
import * as THREE from 'three';
import { PALETTE } from '../world.js';
import { MAT, haloSprite } from '../materials.js';
import { figure } from './clocks3d.js';

const flat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, flatShading: true, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };

// a ripe banana: a five-sided tube along a gentle arc, tapered, with brown tips; returns the group and its centre-line
function makeBanana() {
  const pts = [];
  for (let k = 0; k <= 12; k++) { const u = k / 12, a = (u - 0.5) * 1.6; pts.push(new THREE.Vector3(Math.sin(a) * 0.11, (1 - Math.cos(a)) * 0.11, 0)); }
  const curve = new THREE.CatmullRomCurve3(pts);
  const geo = new THREE.TubeGeometry(curve, 48, 0.02, 5, false);
  const p = geo.attributes.position, uv = geo.attributes.uv, c = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    const u = uv.getX(i), r = Math.pow(Math.sin(Math.PI * Math.min(1, Math.max(0, u))), 0.55) * 0.9 + 0.1;
    curve.getPointAt(Math.min(1, u), c);
    p.setXYZ(i, c.x + (p.getX(i) - c.x) * r, c.y + (p.getY(i) - c.y) * r, c.z + (p.getZ(i) - c.z) * r);
  }
  geo.computeVertexNormals();
  const g = new THREE.Group();
  g.add(new THREE.Mesh(geo, flat('#e2c45a', { roughness: 0.6 })));
  for (const u of [0, 1]) {
    const tip = new THREE.Mesh(new THREE.ConeGeometry(0.006, 0.02, 5), flat('#5e4630'));
    const q = curve.getPointAt(u), tg = curve.getTangentAt(u);
    tip.position.copy(q); tip.quaternion.setFromUnitVectors(new THREE.Vector3(0, u ? 1 : -1, 0), tg.clone().multiplyScalar(u ? 1 : -1)); g.add(tip);
  }
  g.curve = curve; return shadowed(g);
}

function picnicTable(S) {
  const g = new THREE.Group(), w = MAT.wood('#9a7650'), d = MAT.wood('#7a5c3c');
  for (let k = -2; k <= 2; k++) { const b = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.04, 0.15), w); b.position.set(0, 0.74, k * 0.16); g.add(b); }
  for (const x of [-0.65, 0.65]) for (const s of [-1, 1]) {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.82, 0.07), d); leg.position.set(x, 0.37, s * 0.25); leg.rotation.x = s * 0.42; g.add(leg);
  }
  for (const s of [-1, 1]) { const bench = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.04, 0.24), w); bench.position.set(0, 0.44, s * 0.62); g.add(bench); }
  S.add(shadowed(g)); return g;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  world.ground(600); world.hills(12, 130);
  picnicTable(S);
  const banana = makeBanana(); banana.position.set(L.banana[0] - 0.0, L.banana[1] - 0.04, L.banana[2]); banana.rotation.y = 0.3; S.add(banana);
  const bananaHome = banana.position.clone();
  const fig = figure(); fig.position.set(...L.fig); fig.rotation.y = -0.6; S.add(fig);
  // trees and a shed, sparse, framing the garden
  for (const [x, z, s] of [[-3.5, -4, 1.6], [3.8, -5, 1.9], [-6, 0.5, 1.4], [5.5, -1.5, 1.7], [1, -8, 2.2], [-2, -9, 2.0]]) {
    const t = world.roundTree(x, z, s); world.contactShadow(t, x, z, s);
  }
  world.conifer(-7, -6, 2.0); world.conifer(7.5, -7, 2.3);
  const shed = new THREE.Group();
  const walls = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.3, 1.2), flat('#e6e3dc')); walls.position.y = 0.65; shed.add(walls);
  const roof = new THREE.Mesh(new THREE.ConeGeometry(1.25, 0.6, 4), flat('#8a6a48')); roof.position.y = 1.6; roof.rotation.y = Math.PI / 4; roof.scale.set(1, 1, 0.8); shed.add(roof);
  shed.position.set(-4.5, 0, -6.5); shed.rotation.y = 0.4; S.add(shadowed(shed)); shed.traverse(o => { o.castShadow = false; }); world.contactShadow(shed, -4.5, -6.5, 1.3);

  // decay flashes: a pool of glows and electron streaks, positioned from the plan's events
  const RED = '#ff3b30';
  const pool = Array.from({ length: 90 }, () => {
    const glow = haloSprite('#ff3b30', 0.05, 0); S.add(glow);
    const streak = new THREE.Mesh(new THREE.CylinderGeometry(0.0028, 0.0028, 1, 6), new THREE.MeshBasicMaterial({ color: '#fff0e6', transparent: true, opacity: 0, depthWrite: false }));
    S.add(streak); return { glow, streak };
  });
  const bEv = plan.banana_events, fEv = plan.body_events;
  const tmp = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);

  // the atom cluster: grey potassium (and other) atoms, one red potassium-40 that decays
  const [ax, ay, az] = L.atoms;
  const cluster = new THREE.Group(); cluster.position.set(ax, ay, az); S.add(cluster);
  const R = world.rand;
  for (let k = 0; k < 26; k++) {
    const a = new THREE.Mesh(new THREE.IcosahedronGeometry(0.028, 1), MAT.plastic(k % 3 ? '#b9bdc2' : '#a99bc4'));
    let p; do { p = new THREE.Vector3(R() - 0.5, R() - 0.5, R() - 0.5).multiplyScalar(0.36); } while (p.length() < 0.07);
    a.position.copy(p); cluster.add(a);
  }
  const k40M = MAT.plastic('#c92a2e'); k40M.emissive = new THREE.Color('#ff3b30'); k40M.emissiveIntensity = 0.35;
  const k40 = new THREE.Mesh(new THREE.IcosahedronGeometry(0.034, 2), k40M); cluster.add(k40);
  const k40Glow = haloSprite('#ff3b30', 0.16, 0.35); cluster.add(k40Glow);
  const electron = new THREE.Mesh(new THREE.SphereGeometry(0.008, 10, 8), MAT.emissive('#ffe3d6', 3)); cluster.add(electron);
  const trailM = new THREE.MeshBasicMaterial({ color: '#ffb8a0', transparent: true, opacity: 0, depthWrite: false });
  const trail = new THREE.Mesh(new THREE.CylinderGeometry(0.003, 0.003, 1, 6), trailM); cluster.add(trail);
  const eDir = new THREE.Vector3(1, 0.35, 0.25).normalize();
  const ca = new THREE.Color('#efece4'), red = new THREE.Color('#c92a2e');

  const bodyPt = (e) => { const [, h, x, z] = e; const w = h > 1.45 ? 0.08 : h > 0.95 ? 0.16 : 0.1; return tmp.set(L.fig[0] + x * w, h, L.fig[2] + z * 0.08); };
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(0, 0, 0),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.count.length - 1);
      // the banana: on the table, then carried to the figure and eaten
      const e = F.eaten[k];
      banana.visible = F.banana_on[k] > 0;
      banana.position.lerpVectors(bananaHome, new THREE.Vector3(L.fig[0] - 0.1, 1.35, L.fig[2] + 0.12), e);
      banana.scale.setScalar(1 - 0.6 * Math.max(0, e - 0.6) / 0.4);
      // flashes active now
      let used = 0;
      const life = 0.22;
      const show = (p, dir, age, big) => {
        if (used >= pool.length) return;
        const { glow, streak } = pool[used++];
        const u = age / life;
        glow.position.copy(p); glow.scale.setScalar((big ? 0.16 : 0.085) * (0.7 + 0.6 * u)); glow.material.opacity = 1.0 * (1 - u * u);
        if (dir) {
          const L2 = (big ? 0.25 : 0.12) * Math.min(1, u * 1.6);
          streak.visible = true; streak.scale.set(1, L2, 1);
          streak.position.copy(p).addScaledVector(dir, L2 / 2); streak.quaternion.setFromUnitVectors(up, dir); streak.material.opacity = 0.8 * (1 - u);
        } else streak.visible = false;
      };
      if (banana.visible && !(shot.lighting === 'golden' && focalPt(i)[1] > 1.1)) {
        for (const ev of bEv) {
          const age = t - ev[0]; if (age < 0) break; if (age > life) continue;
          banana.curve.getPointAt(ev[1], tmp); tmp.applyMatrix4(banana.matrixWorld);
          const dir = ev[3] === 'beta' ? new THREE.Vector3(Math.cos(ev[2]), 0.6, Math.sin(ev[2])).normalize() : null;
          show(tmp.clone(), dir, age, false);
        }
      }
      if (F.body_on[k]) {
        for (const ev of fEv) {
          const age = t - ev[0]; if (age < 0) break; if (age > life) continue;
          show(bodyPt(ev).clone(), null, age, true);
        }
      }
      for (let q = used; q < pool.length; q++) { pool[q].glow.material.opacity = 0; pool[q].streak.visible = false; }
      // the potassium-40 atom: waits, then fires an electron and turns into calcium (white)
      const a = F.atom[k];
      cluster.rotation.y = 0.2 + t * 0.12;
      k40.position.set(0, 0, 0.09 + 0.004 * Math.sin(t * 9));
      k40M.color.copy(red).lerp(ca, Math.min(1, a * 2)); k40M.emissiveIntensity = 0.35 * (1 - Math.min(1, a * 2));
      k40Glow.position.copy(k40.position); k40Glow.material.opacity = a > 0 ? 0.9 * Math.max(0, 1 - a * 3) + 0.0 : 0.35;
      k40Glow.scale.setScalar(a > 0 ? 0.16 + 0.5 * a : 0.16);
      electron.visible = a > 0 && a < 1;
      const dist = 0.6 * a;
      electron.position.copy(k40.position).addScaledVector(eDir, dist);
      trail.visible = a > 0 && a < 1; trail.scale.set(1, Math.max(0.001, dist), 1);
      trail.position.copy(k40.position).addScaledVector(eDir, dist / 2); trail.quaternion.setFromUnitVectors(up, eDir); trailM.opacity = 0.7 * (1 - a);
      cluster.visible = focalPt(i)[1] > 1.1 && Math.abs(focalPt(i)[0] - L.atoms[0]) < 0.3;
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i);
        world.setLighting(shot.lighting ?? 'key', new THREE.Vector3(fp[0], 0, fp[2]));
        const sc = world.sun.shadow.camera, e2 = 4;
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
      return [{ entity: fp[1] > 1.1 ? 'atoms' : 'banana', part: 'subject', kind: 'thickness', p: fp, size: fp[1] > 1.1 ? 0.06 : 0.2 }];
    },
    vars() { return {}; },
  };
}

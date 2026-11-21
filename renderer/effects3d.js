// Reusable 3D effects for the BUILD style module (docs/styles/BUILD.md). All procedural, all opt-in, all
// deterministic (seeded), so a re-render gives identical frames. Import what a scene needs:
//
//   import { snow, xray, freeze, growTo, shards } from '../effects3d.js';
//   const fx = snow(world, { center: [0, 0, 0], size: 14, count: 1400, wind: 4 });   // in build()
//   fx.update(t, { wind: 4 + 6 * u });                                              // in update()
import * as THREE from 'three';

function rng(seed) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
export const easeOutBack = u => { const c1 = 1.70158, c3 = c1 + 1; u = Math.min(1, Math.max(0, u)); return 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2); };

// Falling snow that turns into sideways streaks as the wind rises (blizzard). Flakes are thin boxes
// stretched along their velocity, so motion reads as blur without a post pass.
export function snow(world, o = {}) {
  const N = o.count ?? 1200, size = o.size ?? 12, hgt = o.height ?? 6, c = new THREE.Vector3(...(o.center ?? [0, 0, 0]));
  const r = rng(o.seed ?? 99);
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const mat = new THREE.MeshBasicMaterial({ color: o.color ?? '#f4f7fa', transparent: true, opacity: o.opacity ?? 0.75, depthWrite: false, fog: true });
  const mesh = new THREE.InstancedMesh(geo, mat, N); mesh.frustumCulled = false; mesh.renderOrder = 2;
  const seeds = Array.from({ length: N }, () => ({ x: r(), y: r(), z: r(), s: 0.6 + r() * 0.8, ph: r() * 6.28 }));
  world.scene.add(mesh);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), sc = new THREE.Vector3(), dir = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
  const flake = o.flake ?? 0.011, fall = o.fall ?? 1.1;
  return {
    mesh,
    update(t, k = {}) {
      const wind = k.wind ?? o.wind ?? 0;
      for (let i = 0; i < N; i++) {
        const f = seeds[i];
        const y = ((f.y * hgt - t * fall * f.s) % hgt + hgt) % hgt;
        const x = (((f.x * size + t * wind * f.s + Math.sin(t * 1.3 + f.ph) * 0.15) % size) + size) % size - size / 2;
        p.set(c.x + x, c.y + y, c.z + f.z * size - size / 2);
        dir.set(wind * f.s, -fall * f.s, 0); const speed = dir.length(); dir.normalize();
        q.setFromUnitVectors(up, dir);
        const len = flake * (1 + speed * (k.streak ?? o.streak ?? 0.06) * 10);
        sc.set(flake, len, flake); m.compose(p, q, sc); mesh.setMatrixAt(i, m);
      }
      mesh.instanceMatrix.needsUpdate = true;
    },
  };
}

// See-through shell (cutaway): every material under `obj` goes transparent so an inner part shows.
export function xray(obj, opacity = 0.25, tint = null) {
  obj.traverse(m => {
    if (!m.isMesh) return;
    const mats = Array.isArray(m.material) ? m.material : [m.material];
    m.material = mats.map(x => { const y = x.clone(); y.transparent = true; y.opacity = opacity; y.depthWrite = false; if (tint) y.color.set(tint); return y; });
    if (m.material.length === 1) m.material = m.material[0];
    m.castShadow = false;
  });
}

// Freeze: blend every material under `obj` toward pale ice (amount 0..1), with a faint cold emissive.
export function freeze(obj, amount, ice = '#dbe7ef') {
  const target = new THREE.Color(ice);
  obj.traverse(m => {
    if (!m.isMesh || !m.material.color) return;
    if (!m.userData.baseColor) { m.material = m.material.clone(); m.userData.baseColor = m.material.color.clone(); }
    m.material.color.copy(m.userData.baseColor).lerp(target, amount);
    m.material.roughness = 0.85 - 0.5 * amount;
    if (m.material.emissive) m.material.emissive.set('#9fc4e0').multiplyScalar(0.12 * amount);
  });
}

// Smooth grow/shrink with a little overshoot, for "your ears shrink", "the hair grows" beats.
export function growTo(obj, from, to, u) { const k = from + (to - from) * easeOutBack(u); obj.scale.setScalar(Math.max(1e-4, k)); }

// Shards: n faceted pieces that burst from a point and fall under gravity (ice cracking, a shell breaking).
export function shards(world, o = {}) {
  const N = o.count ?? 40, r = rng(o.seed ?? 7), c = new THREE.Vector3(...(o.center ?? [0, 1, 0]));
  const mat = new THREE.MeshStandardMaterial({ color: o.color ?? '#e6eef3', roughness: 0.3, metalness: 0, flatShading: true });
  const geo = new THREE.TetrahedronGeometry(o.size ?? 0.06, 1);
  const parts = Array.from({ length: N }, () => {
    const m = new THREE.Mesh(geo, mat); m.castShadow = true; m.visible = false; world.scene.add(m);
    const v = new THREE.Vector3(r() - 0.5, r() * 0.8, r() - 0.5).normalize().multiplyScalar(0.8 + r() * 1.8);
    return { m, v, spin: new THREE.Vector3(r() * 8, r() * 8, r() * 8), s: 0.6 + r() * 0.9 };
  });
  const floor = o.floor ?? 0;
  return {
    update(t) {
      const dt = t - (o.start ?? 0);
      for (const p of parts) {
        p.m.visible = dt >= 0; if (dt < 0) continue;
        p.m.position.set(c.x + p.v.x * dt, Math.max(floor + 0.02, c.y + p.v.y * dt - 4.9 * dt * dt), c.z + p.v.z * dt);
        p.m.rotation.set(p.spin.x * dt, p.spin.y * dt, p.spin.z * dt); p.m.scale.setScalar(p.s);
      }
    },
  };
}

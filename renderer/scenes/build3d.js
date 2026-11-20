// Showcase for the BUILD style module (docs/styles/BUILD.md): every reusable effect on one original
// object (a red sphere on a snowfield). Not an episode. Plan fields: fx timings (see tools/build_demo_plan.py).
import * as THREE from 'three';
import { snow, freeze, growTo, shards } from '../effects3d.js';

export function build(world, plan) {
  const S = world.scene, F = plan.fx;
  // snowfield: gently rolling white ground (high segment count so the soft light shades the dunes)
  const g = new THREE.PlaneGeometry(200, 200, 160, 160), P = g.attributes.position;
  for (let i = 0; i < P.count; i++) {
    const x = P.getX(i), y = P.getY(i), r = Math.hypot(x, y);
    P.setZ(i, r < 4 ? 0 : 0.35 * Math.sin(x * 0.21) * Math.cos(y * 0.17) * Math.min(1, (r - 4) / 6));
  }
  g.computeVertexNormals();
  const ground = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: '#dfe4ea', roughness: 0.95 }));
  ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; S.add(ground);
  // tufts of dry grass poking through (thin cones, 16 sides per the poly budget for background props)
  const tuftM = new THREE.MeshStandardMaterial({ color: '#7b7a4c', roughness: 1, flatShading: true });
  let seed = 3; const r = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 160; i++) {
    const a = r() * 6.28, d = 2.2 + r() * 16;
    for (let k = 0; k < 4; k++) {
      const b = new THREE.Mesh(new THREE.ConeGeometry(0.012, 0.18 + r() * 0.14, 6), tuftM);
      b.position.set(Math.cos(a) * d + (r() - 0.5) * 0.12, 0.09, Math.sin(a) * d + (r() - 0.5) * 0.12);
      b.rotation.set((r() - 0.5) * 0.5, 0, (r() - 0.5) * 0.5); b.castShadow = true; S.add(b);
    }
  }
  for (const [x, z, s] of [[-7, -9, 1.7], [8, -12, 2.1], [-12, -18, 2.4], [5, -20, 1.9]]) world.conifer(x, z, s);
  world.hills && world.hills(9, 110);

  const hero = new THREE.Mesh(new THREE.SphereGeometry(0.4, 64, 48),
    new THREE.MeshStandardMaterial({ color: '#c92a2e', roughness: 0.45 }));
  hero.position.set(0, 0.4, 0); hero.castShadow = true; hero.receiveShadow = true; S.add(hero);
  const fxSnow = snow(world, { center: [0, 0, 0], size: 12, height: 6, count: 1600, wind: 0.4 });
  const fxShards = shards(world, { center: [0, 0.35, 0], start: F.shatter, count: 60, size: 0.04, color: '#dfe9f0' });

  return {
    lightCenter: new THREE.Vector3(0, 0, 0),
    update(i, t) {
      const ramp = (a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
      fxSnow.update(t, { wind: 0.4 + 7 * ramp(F.wind0, F.wind1), streak: 0.08 });
      freeze(hero, ramp(F.freeze0, F.freeze1));
      const shrink = ramp(F.shrink0, F.shrink1);
      growTo(hero, 1, 0.72, shrink); hero.position.y = 0.4 * hero.scale.y;
      hero.visible = t < F.shatter;
      fxShards.update(t);
    },
    focal: () => new THREE.Vector3(0, 0.4, 0),
  };
}

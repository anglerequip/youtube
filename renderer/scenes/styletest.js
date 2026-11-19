// Style check only (not an episode): a country road with traffic, one car braking.
import * as THREE from 'three';
import { PALETTE } from '../world.js';
import { car, straightRoad, fence, cone } from '../props.js';

export function build(world, plan) {
  const S = world.scene;
  world.ground(); world.hills();
  straightRoad(S, { lanes: 2 });
  fence(S, -8.5, -180, 30); fence(S, 8.5, -180, 30);
  for (let z = 20; z > -170; z -= 7 + world.rand() * 9) {
    for (const s of [-1, 1]) {
      const x = s * (11 + world.rand() * 14);
      (world.rand() < 0.35 ? world.conifer(x, z, 1.4 + world.rand()) : world.roundTree(x, z, 1.3 + world.rand()));
    }
  }
  cone(S, 4.4, -6);
  const cars = [];
  const kinds = ['hatch', 'estate', 'sedan'];
  for (let i = 0; i < 14; i++) {
    const c = car(PALETTE.cars[i % PALETTE.cars.length], kinds[i % 3], i % 4 === 1);
    c.position.set(i % 2 ? 1.8 : 1.8, 0, -i * 9.5); S.add(c); cars.push(c);
  }
  return {
    lightCenter: new THREE.Vector3(0, 0, -10),
    update(i, t) {
      cars.forEach((c, k) => { c.position.z = -k * 9.5 - t * 6; c.setBrake(k === 0 ? 0 : (k <= 3 ? 1 : 0)); });
    },
  };
}

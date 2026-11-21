// Preview only (not an episode): the two presenters on a small round patio in the diorama world, for
// turnarounds and face close-ups. Each shot may set: turn (deg, both figures), who ('man'|'woman'|'both'),
// pose ({talk, wave, point, headYaw, ...}) and lighting.
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { car } from '../props.js';
import { PALETTE } from '../world.js';
import { MAT } from '../materials.js';

export function build(world, plan) {
  const S = world.scene;
  world.ground(); world.hills && world.hills();
  const patio = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.3, 0.08, 40), MAT.concrete('#c9c2b0'));
  patio.position.y = 0.04; patio.receiveShadow = true; patio.castShadow = true; S.add(patio);
  const lift = 0.08;
  const M = man(), Wm = woman();
  M.position.set(-0.55, lift, 0); Wm.position.set(0.55, lift, 0); S.add(M, Wm);
  for (const [x, z, s] of [[-6, -7, 1.6], [7, -9, 1.9], [-9, -16, 2.2], [4, -18, 1.7], [11, -4, 1.4]]) world.roundTree(x, z, s);
  for (const [x, z, s] of [[-12, -10, 1.6], [13, -14, 2]]) world.conifer(x, z, s);
  const c = car(PALETTE.cars[0], 'hatch', false); c.position.set(-4.5, 0, -5.5); c.rotation.y = 0.9; S.add(c);
  return {
    lightCenter: new THREE.Vector3(0, 0, 0),
    update(i, t, shot) {
      const turn = THREE.MathUtils.degToRad((shot.turn ?? 0) + (shot.spin ?? 0) * (t - shot.start));
      M.rotation.y = turn; Wm.rotation.y = turn;
      if (shot.who === 'man') { M.position.x = 0; Wm.visible = false; M.visible = true; }
      else if (shot.who === 'woman') { Wm.position.x = 0; M.visible = false; Wm.visible = true; }
      else { M.position.x = -0.55; Wm.position.x = 0.55; M.visible = Wm.visible = true; }
      const p = { ...(shot.pose ?? {}), t };
      if (shot.talky) { p.talk = Math.max(0, Math.sin(t * 11) * Math.sin(t * 3.1)) * 0.8; p.blink = (t % 3.2) < 0.12 ? 1 : 0; }
      M.pose(shot.poseMan ?? p); Wm.pose(shot.poseWoman ?? p);
    },
    focal: () => new THREE.Vector3(0, 1.0, 0),
  };
}

// Two-lane highway driven by the IDM traffic simulation (content/episodes/other-lane-faster/plan.py).
// Ego-relative world: the followed car sits at z=0 in the right lane; road texture, dashes, fences and
// trees scroll past by the ego's travelled distance (frames.scroll), so the camera and the sun's
// shadow box stay near the origin however far the car drives.
import * as THREE from 'three';
import { PALETTE } from '../world.js';
import { car, fence } from '../props.js';

const P = 180;                       // scenery repeat period (m); a multiple of the 9 m dash spacing
const TILES_BACK = 4, TILES_FWD = 1;
const Z_MIN = -430, Z_MAX = 140;     // cars outside this window are hidden

export function build(world, plan) {
  const S = world.scene, F = plan.frames, [XR, XL] = plan.lanes;
  world.camera.far = 900; world.camera.updateProjectionMatrix();
  world.skyDome.scale.setScalar(2.6);

  // grass ground, big enough for the high shots; its texture scrolls with the road
  const size = 1400;
  const gtex = world.grassTexture(); gtex.repeat.set(size / 9, size / 9);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshStandardMaterial({ map: gtex, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2; ground.position.z = -250; ground.receiveShadow = true; S.add(ground);
  world.hills(16, 330); world.hills(12, 420);

  // static road surface (uniform along z), edge lines, shoulders
  const flat = c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.95 });
  const zc = (Z_MIN - 400 + Z_MAX + 200) / 2, len = Z_MAX + 200 - (Z_MIN - 400);
  const plane = (w, l, mat, x, y) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, l), mat); m.rotation.x = -Math.PI / 2; m.position.set(x, y, zc); m.receiveShadow = true; S.add(m); return m; };
  plane(7.2, len, flat(PALETTE.asphaltDay), 0, 0.02);
  const mk = new THREE.MeshStandardMaterial({ color: PALETTE.marking, roughness: 0.8 });
  for (const x of [-3.35, 3.35]) plane(0.15, len, mk, x, 0.03);
  for (const s of [-1, 1]) {
    const k = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.1, len), flat(PALETTE.concrete)); k.position.set(s * 4.6, 0.05, zc); k.receiveShadow = true; S.add(k);
  }

  // scrolling scenery: one tile of dashes, fence and trees, repeated every P metres
  const scen = new THREE.Group(); S.add(scen);
  const tile = new THREE.Group();
  for (let z = 0; z > -P; z -= 9) {
    const d = new THREE.Mesh(new THREE.PlaneGeometry(0.14, 3), mk); d.rotation.x = -Math.PI / 2; d.position.set(0, 0.031, z); d.receiveShadow = true; tile.add(d);
  }
  const before = S.children.length;
  for (const x of [-6.4, 6.4]) fence(S, x, -P + 1.5, 0, 3);
  for (let i = 0; i < 26; i++) {
    const side = world.rand() < 0.5 ? -1 : 1, x = side * (10 + world.rand() * 38), z = -world.rand() * P;
    const s = 1.4 + world.rand() * 1.6;
    world.rand() < 0.35 ? world.conifer(x, z, s * 1.1) : world.roundTree(x, z, s);
  }
  for (const o of S.children.slice(before)) tile.add(o);     // move fence + trees into the tile
  for (let k = -TILES_FWD; k <= TILES_BACK; k++) { const c = tile.clone(); c.position.z = -k * P; scen.add(c); }

  // car pools (the hero car is separate so it can be a fixed colour)
  const cols = PALETTE.cars.filter(c => c !== '#e2c45a');
  const kinds = ['hatch', 'estate', 'sedan'];
  const pool = (n, x) => Array.from({ length: n }, () => {
    const c = car(cols[Math.floor(world.rand() * cols.length)], kinds[Math.floor(world.rand() * 3)], world.rand() < 0.2);
    c.position.x = x; S.add(c); return c;
  });
  const R = pool(plan.n_right, XR), L = pool(plan.n_left, XL);
  const hero = car('#e2c45a', 'hatch', true); hero.position.set(XR, 0, 0); S.add(hero);

  // thin white ring on the road around the followed car
  const ringMat = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.9, toneMapped: false });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(3.1, 0.07, 6, 96), ringMat);
  ring.rotation.x = Math.PI / 2; ring.scale.set(0.62, 1, 1); ring.position.set(XR, 0.05, 0.2); S.add(ring);

  let camNear = null;     // low cameras: hide same-lane cars sitting between the camera and the hero
  const place = (cars, zs, br, ego, x) => {
    for (let c = 0; c < cars.length; c++) {
      const z = zs[c];
      let vis = z !== undefined && c !== ego && z > Z_MIN && z < Z_MAX;
      if (vis && camNear && Math.hypot(x - camNear.x, z - camNear.z) < 4.5) vis = false;
      if (vis && camNear && x === XR && z > 1 && z < camNear.z + 3) vis = false;
      cars[c].visible = vis;
      if (vis) { cars[c].position.z = z; cars[c].setBrake(br[c] === '1' ? 1 : 0); }
    }
  };

  const sun = world.sun, sc = sun.shadow.camera;
  return {
    lightCenter: new THREE.Vector3(XR, 0, -10),
    update(i, t, shot) {
      const k = Math.min(i, F.right.length - 1);
      const ego = F.ego[k];
      const jj = Math.min(Math.max(0, i - (shot.i0 ?? 0)), (shot.pos?.length ?? 1) - 1);
      camNear = shot.pos && shot.pos[jj][1] < 5 ? { x: shot.pos[jj][0], z: shot.pos[jj][2] } : null;
      place(R, F.right[k], F.rb[k], ego, XR);
      place(L, F.left[k], F.lb[k], -1, XL);
      hero.setBrake(F.rb[k][ego] === '1' ? 1 : 0);
      const sz = F.scroll[k];
      scen.position.z = ((sz % P) + P) % P;
      gtex.offset.y = (sz / 9) % 1;
      ring.visible = !!(F.ring && F.ring[k]);

      // shadows and haze follow the shot: sun box centred on the look point, sized to the view
      const j = Math.min(Math.max(0, i - (shot.i0 ?? 0)), (shot.look?.length ?? 1) - 1);
      const look = shot.look ? new THREE.Vector3(...shot.look[j]) : new THREE.Vector3(XR, 0, 0);
      const cpos = shot.pos ? new THREE.Vector3(...shot.pos[j]) : new THREE.Vector3(0, 5, 10);
      const h = cpos.y, ext = Math.min(85, Math.max(14, h * 0.75 + cpos.distanceTo(look) * 0.25));
      const dir = sun.position.clone().sub(sun.target.position).normalize();
      const c0 = new THREE.Vector3(look.x * 0.5, 0, look.z);
      sun.target.position.copy(c0); sun.position.copy(c0).addScaledVector(dir, 200);
      sc.left = -ext; sc.right = ext; sc.top = ext; sc.bottom = -ext; sc.near = 50; sc.far = 400; sc.updateProjectionMatrix();
      S.fog.near = 30 + h * 0.8; S.fog.far = 170 + h * 2.6;
    },
    focal(i) {
      const k = Math.min(i, F.focal_pt.length - 1);
      return new THREE.Vector3(...F.focal_pt[k]);
    },
  };
}

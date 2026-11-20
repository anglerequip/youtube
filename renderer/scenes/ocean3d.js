// Why the ocean is blue (content/episodes/why-ocean-blue/plan.py).
// A sandy beach, a wooden pier with a small boat at its end, and a calm low-poly sea. Every water colour comes
// from the plan's absorption model: the sea seen from above, the glass and the 4 m tank, the underwater haze,
// the three light beams metre by metre, the sinking red ball and the fish in the deep. This file only draws.
import * as THREE from 'three';
import { PALETTE } from '../world.js';
import { MAT, haloSprite } from '../materials.js';

const flat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, flatShading: true, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };

function boat() {
  const g = new THREE.Group();
  const hull = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 0.7, 0.8, 8, 1), flat('#e6e3dc')); hull.scale.set(1, 1, 2.6); hull.position.y = 0.25; g.add(hull);
  const rim = new THREE.Mesh(new THREE.CylinderGeometry(1.04, 1.04, 0.12, 8), flat('#2e8f86')); rim.scale.set(1, 1, 2.6); rim.position.y = 0.68; g.add(rim);
  const seat = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.1, 0.4), MAT.wood('#8a6a48')); seat.position.y = 0.6; g.add(seat);
  const davit = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.2, 0.08), flat('#5e4630')); davit.position.set(0.9, 1.1, -1.4); g.add(davit);
  const arm = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.08, 0.08), flat('#5e4630')); arm.position.set(0.5, 1.68, -1.4); g.add(arm);
  return shadowed(g);
}

function fishMesh() {
  const g = new THREE.Group();
  const m = new THREE.MeshBasicMaterial({ color: '#c92a2e', fog: false });
  const body = new THREE.Mesh(new THREE.IcosahedronGeometry(0.5, 1), m); body.scale.set(1.5, 0.75, 0.42); g.add(body);
  const tail = new THREE.Mesh(new THREE.ConeGeometry(0.36, 0.55, 4), m); tail.rotation.z = Math.PI / 2; tail.position.x = -0.95; tail.scale.set(1, 1, 0.3); g.add(tail);
  const fin = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.4, 4), m); fin.position.set(0.05, 0.42, 0); fin.scale.set(1.5, 1, 0.3); g.add(fin);
  const eye = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 6), new THREE.MeshBasicMaterial({ color: '#f2efe6' })); eye.position.set(0.48, 0.1, 0.18); g.add(eye);
  const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 6), new THREE.MeshBasicMaterial({ color: '#111' })); pupil.position.set(0.51, 0.1, 0.21); g.add(pupil);
  g.mat = m; return g;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout, C = plan.colours;
  world.camera.far = 600; world.hills(12, 190);
  // beach (sand) on the +z side, the sea everywhere else
  const sand = new THREE.Mesh(new THREE.PlaneGeometry(400, 160), flat('#c9b48e', { flatShading: false, roughness: 1 }));
  sand.rotation.x = -Math.PI / 2; sand.position.set(0, 0.25, 110); sand.receiveShadow = true; S.add(sand);
  const grass = world.ground(800); grass.position.set(0, 0.3, 470);
  // sea surface: faceted gentle waves
  const seaG = new THREE.PlaneGeometry(420, 420, 140, 140); seaG.rotateX(-Math.PI / 2);
  const base = Float32Array.from(seaG.attributes.position.array);
  const seaM = new THREE.MeshStandardMaterial({ color: C.sea, roughness: 0.55, metalness: 0, flatShading: true, side: THREE.DoubleSide, envMapIntensity: 0.15 });
  const sea = new THREE.Mesh(seaG, seaM); sea.receiveShadow = true; S.add(sea);
  const farSea = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), seaM); farSea.rotation.x = -Math.PI / 2; farSea.position.y = -0.12; S.add(farSea);   // to the horizon
  // a wall of water around everything below the surface, so no underwater view reaches the sky
  const wall = new THREE.Mesh(new THREE.CylinderGeometry(480, 480, 80, 48, 1, true), new THREE.MeshBasicMaterial({ color: '#0b2a4a', side: THREE.BackSide }));
  wall.position.y = -40.3; S.add(wall);
  // sea floor far below (sand, hidden in haze)
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(6000, 6000), flat('#8d7f62', { flatShading: false })); floor.rotation.x = -Math.PI / 2; floor.position.y = -70; S.add(floor);
  // pier from the beach out to the rope, on posts
  const pier = new THREE.Group();
  const zs = L.pier_z, ze = 46;
  for (let z = zs; z < ze; z += 0.5) { const p = new THREE.Mesh(new THREE.BoxGeometry(3.0, 0.1, 0.44), MAT.wood(z % 1 ? '#9a7650' : '#8f6d49')); p.position.set(0, 0.9, z); pier.add(p); }
  for (let z = zs; z < ze; z += 3) for (const x of [-1.4, 1.4]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.18, 4.2, 0.18), MAT.wood('#6e5236')); p.position.set(x, -1.2, z); pier.add(p); }
  S.add(shadowed(pier));
  const bt = boat(); bt.position.set(1.0, 0.05, 2.2); S.add(bt);
  // rope from the boat's davit straight down, metre tags
  const rope = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 30, 6), flat('#d9c7a0')); rope.position.set(0, -13.3, 0); S.add(rope);
  for (let d = 1; d <= 15; d++) { const t = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.05, 10), flat('#e8e6df')); t.position.set(0, -d, 0); S.add(t); }
  const ballM = new THREE.MeshBasicMaterial({ color: C.ball_surface });
  const ball = new THREE.Mesh(new THREE.IcosahedronGeometry(0.28, 2), ballM); S.add(ball);
  // glass of water on a post, and the long tank on the deck
  const [gx, gy, gz] = L.glass;
  const postTop = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.38, 0.3), MAT.wood('#6e5236')); postTop.position.set(gx, gy - 0.2, gz); S.add(shadowed(postTop));
  const glassM = new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: 0.08, transmission: 0.0, transparent: true, opacity: 0.22, depthWrite: false });
  const glass = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.05, 0.16, 24, 1, true), glassM); glass.position.set(gx, gy + 0.08, gz); S.add(glass);
  const water = new THREE.Mesh(new THREE.CylinderGeometry(0.056, 0.048, 0.12, 24), new THREE.MeshStandardMaterial({ color: C.glass, roughness: 0.2, transparent: true, opacity: 0.55 }));
  water.position.set(gx, gy + 0.06, gz); S.add(water);
  const [tx, ty, tz] = L.tank, TL = L.tank_l;
  // a tall clear column of water (0.6 m wide, 4 m deep) with a white floor: from the top, the floor looks blue
  const colG = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, TL + 0.3, 32, 1, true), new THREE.MeshStandardMaterial({ color: '#e8f0f4', roughness: 0.1, transparent: true, opacity: 0.16, depthWrite: false, side: THREE.DoubleSide }));
  colG.position.set(tx, ty + (TL + 0.3) / 2, tz); S.add(colG);
  const colW = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, TL, 32, 1, true), new THREE.MeshStandardMaterial({ color: C.tank_side, roughness: 0.2, transparent: true, opacity: 0.3, depthWrite: false, side: THREE.DoubleSide }));
  colW.position.set(tx, ty + TL / 2, tz); S.add(colW);
  const colFloor = new THREE.Mesh(new THREE.CircleGeometry(0.32, 32), new THREE.MeshBasicMaterial({ color: C.tank })); colFloor.rotation.x = -Math.PI / 2; colFloor.position.set(tx, ty + 0.12, tz); S.add(colFloor);
  const colTop = new THREE.Mesh(new THREE.CircleGeometry(0.32, 32), new THREE.MeshStandardMaterial({ color: C.tank, roughness: 0.05, transparent: true, opacity: 0.55 })); colTop.rotation.x = -Math.PI / 2; colTop.position.set(tx, ty + TL, tz); S.add(colTop);
  const colBase = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.48, 0.2, 24), MAT.concrete('#beb7a4')); colBase.position.set(tx, ty + 0.0, tz); S.add(shadowed(colBase));
  const colRim = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.025, 8, 40), MAT.brushedSteel()); colRim.rotation.x = Math.PI / 2; colRim.position.set(tx, ty + TL + 0.3, tz); S.add(colRim);
  // a water molecule (not to scale): one big ball, two small ones
  const [mx, my, mz] = L.mole;
  const mol = new THREE.Group(); mol.position.set(mx, my, mz); S.add(mol);
  const O = new THREE.Mesh(new THREE.IcosahedronGeometry(0.42, 2), new THREE.MeshStandardMaterial({ color: '#b9c7d6', roughness: 0.5 })); mol.add(O);
  const Hs = [], bonds = [], ang = 104.5 / 2 * Math.PI / 180;
  for (const s of [-1, 1]) {
    const h = new THREE.Mesh(new THREE.IcosahedronGeometry(0.24, 2), new THREE.MeshStandardMaterial({ color: '#f3f1ea', roughness: 0.5 })); mol.add(h); Hs.push([h, s]);
    const b = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 1, 8), new THREE.MeshStandardMaterial({ color: '#e0e2e4', roughness: 0.6 })); mol.add(b); bonds.push(b);
  }
  // light beams: red, green, blue, one segment per metre, brightness from the absorption model
  const beams = plan.beams.map((col, j) => {
    const segs = [];
    for (let d = 0; d < 15; d++) {
      const m = new THREE.MeshBasicMaterial({ color: C.beam_cols[j], transparent: true, opacity: 0, depthWrite: false, blending: THREE.NormalBlending, fog: false });
      const s = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 1.0, 16, 1, true), m); s.position.set(L.beams_x[j], -d - 0.5, -4); S.add(s);
      segs.push({ m, v: (col[d] + col[d + 1]) / 2 });
    }
    return segs;
  });
  const redBeam = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 9, 12, 1, true), new THREE.MeshBasicMaterial({ color: '#ff3b30', transparent: true, opacity: 0.5, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
  redBeam.rotation.z = Math.PI / 2; redBeam.position.set(mx, my - 0.9, mz); S.add(redBeam);
  // the deep: a red fish, a diver's lamp beam
  const [fx, fy, fz] = L.fish;
  const fish = fishMesh(); fish.position.set(fx, fy, fz); fish.rotation.y = -0.5; S.add(fish);
  const lampM0 = new THREE.MeshBasicMaterial({ color: '#fff4dc', transparent: true, opacity: 0.0, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false });
  const lamp = haloSprite('#fff1d6', 1.6, 0); lamp.position.set(fx - 0.9, fy + 0.7, fz + 0.4); S.add(lamp); const lampM = lamp.material;   // a diver's torch glow
  // trees on the beach
  for (let i = 0; i < 40; i++) {
    const x = -80 + world.rand() * 160, z = 70 + world.rand() * 60;
    if (Math.abs(x) < 6) continue;
    const s = 1 + world.rand(); const t = world.rand() < 0.4 ? world.conifer(x, z, s * 1.2) : world.roundTree(x, z, s);
    t.position.y = 0.25; world.contactShadow(t, x, z, s);
  }

  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  let lastShot = null, under = null;
  const sky = world.skyDome.material.uniforms;
  return {
    lightCenter: new THREE.Vector3(0, 0, 4),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.depth.length - 1);
      // gentle waves
      const p = seaG.attributes.position;
      for (let q = 0; q < p.count; q++) {
        const x = base[q * 3], z = base[q * 3 + 2];
        p.array[q * 3 + 1] = 0.07 * Math.sin(x * 0.35 + t * 1.1) + 0.05 * Math.sin(z * 0.5 - t * 0.9) + 0.03 * Math.sin((x + z) * 0.9 + t * 1.7);
      }
      p.needsUpdate = true; seaG.computeVertexNormals();
      ball.position.set(0, F.ball_y[k], 0); ballM.color.set(F.ball_col[k]);
      // molecule: the two O-H bonds stretch and squeeze (the wobble that absorbs red)
      const w = F.wob[k];
      Hs.forEach(([h, s], j) => {
        const r = 0.62 + 0.09 * w * s, a = ang;
        h.position.set(s * Math.sin(a) * r, -Math.cos(a) * r, 0);
        const b = bonds[j]; b.position.copy(h.position).multiplyScalar(0.5); b.scale.y = r; b.rotation.z = -s * a;
      });
      mol.rotation.y = 0.3 + t * 0.15;
      beams.forEach(segs => segs.forEach(sg => { sg.m.opacity = F.beams_on[k] ? 0.75 * sg.v : 0; }));
      fish.mat.color.set(F.fish_col[k]); lampM.opacity = F.lamp[k] ? 0.55 : 0; fish.position.y = L.fish[1] + 0.05 * Math.sin(t * 1.3);
      fish.rotation.y = -0.5 + 0.08 * Math.sin(t * 0.9);
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i);
        world.setLighting(shot.lighting ?? 'key', new THREE.Vector3(fp[0], 0, fp[2]));
        const sc = world.sun.shadow.camera, e = fp[1] < -1 ? 8 : 12;
        sc.left = -e; sc.right = e; sc.top = e; sc.bottom = -e; sc.far = 120; sc.updateProjectionMatrix();
        this._base = { fog: world.scene.fog.color.clone(), near: world.scene.fog.near, far: world.scene.fog.far, hemi: world.hemi.intensity, sun: world.sun.intensity,
                       top: sky.top.value.clone(), bottom: sky.bottom.value.clone() };
      }
    },
    afterCamera(i) {
      const k = Math.min(i, F.depth.length - 1), uw = world.camera.position.y < -0.05, b = this._base;
      if (uw) {                       // underwater: haze, sky and light all take the model's water colour
        const c = new THREE.Color(F.fog[k]);
        world.scene.fog.color.copy(c); world.scene.fog.near = 0.5; world.scene.fog.far = F.fog_far[k];
        sky.top.value.copy(c); sky.bottom.value.copy(c);
        world.hemi.intensity = 0.4 + 1.2 * F.light[k]; world.sun.intensity = 0.6 + 1.2 * F.light[k];
        seaM.color.set(C.underside);
      } else if (b) {
        world.scene.fog.color.copy(b.fog); world.scene.fog.near = b.near; world.scene.fog.far = b.far;
        sky.top.value.copy(b.top); sky.bottom.value.copy(b.bottom); world.hemi.intensity = b.hemi; world.sun.intensity = b.sun;
        seaM.color.set(C.sea);
      }
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.1, Math.max(0.02, d * 0.02)); world.camera.far = 600; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const fp = focalPt(i);
      return [{ entity: fp[1] < -1 ? 'beams' : 'sea', part: 'subject', kind: 'thickness', p: fp, size: 0.5 }];
    },
    vars() { return {}; },
  };
}

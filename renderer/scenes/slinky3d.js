// Falling slinky in the house diorama style. All motion comes from the Python physics plan
// (plan.frames.coils = world-space y of every coil per frame); this file only draws it.
import * as THREE from 'three';
import { PALETTE } from '../world.js';
import { cone } from '../props.js';

const R = 0.11;             // coil radius (m)
const P = 28;               // points per turn
const SEG = 6;              // cross-section segments
const AR = 0.013, AV = 0.0033;   // ribbon half-width (radial) and half-thickness (vertical)

function slinkyMesh(N) {
  const nPts = N * P;
  const pos = new Float32Array(nPts * SEG * 3), nrm = new Float32Array(nPts * SEG * 3);
  const idx = [];
  for (let i = 0; i < nPts - 1; i++) for (let s = 0; s < SEG; s++) {
    const a = i * SEG + s, b = i * SEG + (s + 1) % SEG, c = (i + 1) * SEG + s, d = (i + 1) * SEG + (s + 1) % SEG;
    idx.push(a, c, b, b, c, d);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(nrm, 3));
  g.setIndex(idx);
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: '#c9cdd2', metalness: 0.35, roughness: 0.38 }));
  m.castShadow = true; m.receiveShadow = true;
  m.frustumCulled = false;
  m.setCoils = (ys) => {
    let k = 0;
    for (let i = 0; i < N; i++) {
      const y0 = ys[i], y1 = i < N - 1 ? ys[i + 1] : ys[i] - 0.002;
      for (let j = 0; j < P; j++) {
        const u = j / P, th = (i + u) * Math.PI * 2;
        const y = y0 + (y1 - y0) * u;
        const nx = Math.cos(th), nz = Math.sin(th);
        const cx = R * nx, cz = R * nz;
        for (let s = 0; s < SEG; s++) {
          const ph = (s / SEG) * Math.PI * 2, cr = Math.cos(ph), sr = Math.sin(ph);
          pos[k] = cx + AR * cr * nx; pos[k + 1] = y + AV * sr; pos[k + 2] = cz + AR * cr * nz;
          // normal of an ellipse cross-section (approx.)
          const ex = cr / AR, ey = sr / AV, len = Math.hypot(ex, ey);
          nrm[k] = (ex / len) * nx; nrm[k + 1] = ey / len; nrm[k + 2] = (ex / len) * nz;
          k += 3;
        }
      }
    }
    g.attributes.position.needsUpdate = true; g.attributes.normal.needsUpdate = true;
  };
  return m;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, N = F.coils[0].length;
  world.ground(); world.hills(10, 110);
  // diorama: grass, a few trees and conifers, a wooden test frame on a concrete pad
  world.scatterTrees(26, 9, 32, [0, -4]);
  world.slab(3.2, 2.2, 0.1);
  const postH = 2.85;
  for (const x of [-0.9, 0.9]) world.box(0.14, postH, 0.14, PALETTE.wood, x, postH / 2 + 0.1, 0);
  world.box(2.1, 0.16, 0.18, PALETTE.wood, 0, postH + 0.1, 0);
  world.box(0.5, 0.06, 0.6, PALETTE.woodDark, 0, 0.13, 0.8);   // small crate/board at the foot
  cone(S, 1.3, 0.7); cone(S, -1.25, 0.75);

  // clamp holding the top coil
  const jawMat = { color: '#2b2d31' };
  const jawL = world.box(0.09, 0.12, 0.08, jawMat.color, -0.13, plan.top_y + 0.05, 0);
  const jawR = world.box(0.09, 0.12, 0.08, jawMat.color, 0.13, plan.top_y + 0.05, 0);
  world.box(0.36, 0.05, 0.08, '#3a3d42', 0, plan.top_y + 0.13, 0);
  world.box(0.04, postH + 0.1 - plan.top_y - 0.15, 0.04, '#3a3d42', 0, (postH + 0.1 + plan.top_y + 0.15) / 2, 0);

  const sl = slinkyMesh(N); S.add(sl);
  // cues: red glow on the bottom coil (the phenomenon), white ring for the travelling "news"
  const bottomGlow = world.glowRing(R + 0.002, 0.009, '#ff2a1f', 4.0);
  const frontRing = world.glowRing(R + 0.03, 0.006, '#fff6e8', 3.0);

  // reference ball (falls beside the slinky at its centre-of-mass height)
  const ball = new THREE.Mesh(new THREE.IcosahedronGeometry(0.045, 2),
    new THREE.MeshStandardMaterial({ color: '#e5e2d6', emissive: '#fff1dc', emissiveIntensity: 0.35, roughness: 0.5, flatShading: true }));
  ball.castShadow = true; S.add(ball);
  const string = world.box(0.006, 1, 0.006, '#2b2d31', 0, 0, 0);   // holds the ball until release

  // steel bar lying on the pad, a striker block, and the travelling compression pulse
  const bar = plan.bar || { x0: -1.2, x1: 1.2, z: -0.62, r: 0.03 };
  const barMesh = new THREE.Mesh(new THREE.CylinderGeometry(bar.r, bar.r, bar.x1 - bar.x0, 12),
    new THREE.MeshStandardMaterial({ color: PALETTE.metal, metalness: 0.6, roughness: 0.35 }));
  barMesh.rotation.z = Math.PI / 2; barMesh.position.set((bar.x0 + bar.x1) / 2, 0.1 + bar.r, bar.z);
  barMesh.castShadow = true; barMesh.receiveShadow = true; S.add(barMesh);
  const striker = world.box(0.09, 0.09, 0.09, '#3a3d42', bar.x0 - 0.05, 0.1 + 0.045, bar.z);
  const pulse = new THREE.Mesh(new THREE.TorusGeometry(bar.r + 0.006, 0.006, 8, 32),
    new THREE.MeshStandardMaterial({ color: '#fff6e8', emissive: '#fff6e8', emissiveIntensity: 3.5 }));
  pulse.rotation.y = Math.PI / 2; S.add(pulse);
  const flash = new THREE.Mesh(new THREE.CircleGeometry(bar.r * 1.05, 16),
    new THREE.MeshStandardMaterial({ color: '#fff6e8', emissive: '#fff6e8', emissiveIntensity: 0, transparent: true }));
  flash.rotation.y = Math.PI / 2; flash.position.set(bar.x1 + 0.002, 0.1 + bar.r, bar.z); S.add(flash);

  return {
    lightCenter: new THREE.Vector3(0, 1, 0),
    update(i) {
      const k = Math.min(i, F.coils.length - 1);
      const ys = F.coils[k];
      sl.setCoils(ys);
      const open = F.clamp[k];
      jawL.position.x = -0.13 - 0.12 * open; jawR.position.x = 0.13 + 0.12 * open;
      bottomGlow.position.y = ys[N - 1]; bottomGlow.visible = F.glow[k] > 0;
      bottomGlow.material.emissiveIntensity = 4.0 * F.glow[k];
      const fi = F.front[k];
      frontRing.visible = fi >= 0; if (fi >= 0) frontRing.position.y = ys[fi];
      const b = F.ball ? F.ball[k] : null;
      ball.visible = !!b; if (b) ball.position.set(...b);
      string.visible = !!b && open < 0.5;
      if (string.visible) { const top = postH + 0.02, bot = b[1] + 0.045; string.scale.y = top - bot; string.position.set(b[0], (top + bot) / 2, 0); }
      const px = F.pulse ? F.pulse[k] : null;
      pulse.visible = px !== null && px !== undefined; if (pulse.visible) pulse.position.set(px, 0.1 + bar.r, bar.z);
      const fl = F.flash ? F.flash[k] : 0;
      flash.material.emissiveIntensity = 4 * fl; flash.visible = fl > 0;
      if (F.striker) striker.position.x = bar.x0 - 0.05 - F.striker[k];
    },
    focal(i) {
      const k = Math.min(i, F.coils.length - 1);
      if (F.focal_pt && F.focal_pt[k]) return new THREE.Vector3(...F.focal_pt[k]);
      const c = F.focal ? F.focal[k] : N - 1; return new THREE.Vector3(0, F.coils[k][c], 0); },
    vars(i) { const k = Math.min(i, F.coils.length - 1); return F.vars ? F.vars[k] : {}; },
  };
}

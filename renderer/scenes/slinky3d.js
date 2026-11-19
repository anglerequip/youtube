// Falling slinky, v2 (quality overhaul). All motion comes from the Python physics plan
// (plan.frames.coils = world-space y of every coil per frame); this file only draws it.
//
// Hero object: a flat steel ribbon helix with smooth normals, real reflections and per-coil emissive
// channels: red = the bottom coil (the phenomenon), warm white = the simulated collapse front.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { MAT, haloSprite } from '../materials.js';

const R = 0.11;               // coil radius (m)
const P = 56;                 // points per turn (smooth circle)
const SEG = 10;               // ribbon cross-section points
const AR = 0.017, AV = 0.0022;   // ribbon half-width (radial) and half-thickness (vertical): 1.6 mm gap when touching
const POST_H = 2.85, BEAM_Y = 2.95;

function ribbonSlinky(N) {
  const nPts = N * P, nV = nPts * SEG;
  const pos = new Float32Array(nV * 3), nrm = new Float32Array(nV * 3);
  const red = new Float32Array(nV), glow = new Float32Array(nV);
  const idx = [];
  for (let i = 0; i < nPts - 1; i++) for (let s = 0; s < SEG; s++) {
    const a = i * SEG + s, b = i * SEG + (s + 1) % SEG, c = (i + 1) * SEG + s, d = (i + 1) * SEG + (s + 1) % SEG;
    idx.push(a, c, b, b, c, d);
  }
  // rounded-rectangle (superellipse) cross-section: a flat ribbon with soft edges
  const prof = [];
  for (let s = 0; s < SEG; s++) {
    const ph = (s / SEG) * Math.PI * 2, c = Math.cos(ph), sn = Math.sin(ph);
    const e = 0.45;
    const px = Math.sign(c) * Math.pow(Math.abs(c), e), py = Math.sign(sn) * Math.pow(Math.abs(sn), e);
    const nx = Math.sign(c) * Math.pow(Math.abs(c), 2 - e) / AR, ny = Math.sign(sn) * Math.pow(Math.abs(sn), 2 - e) / AV;
    const l = Math.hypot(nx, ny) || 1;
    prof.push([px * AR, py * AV, nx / l, ny / l]);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(nrm, 3));
  g.setAttribute('aRed', new THREE.BufferAttribute(red, 1));
  g.setAttribute('aGlow', new THREE.BufferAttribute(glow, 1));
  g.setIndex(idx);
  const mat = MAT.springSteel();
  mat.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute float aRed; attribute float aGlow; varying float vRed; varying float vGlow;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRed = aRed; vGlow = aGlow;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vRed; varying float vGlow;')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += vec3(1.0, 0.16, 0.12) * vRed * 5.0 + vec3(1.0, 0.93, 0.82) * vGlow * 1.5;');
  };
  const m = new THREE.Mesh(g, mat);
  m.castShadow = true; m.receiveShadow = true; m.frustumCulled = false;
  m.setCoils = (ys, redPerCoil, glowPerCoil) => {
    let k = 0, v = 0;
    for (let i = 0; i < N; i++) {
      const y0 = ys[i], y1 = i < N - 1 ? ys[i + 1] : ys[i] - 0.002;
      const r0 = redPerCoil[i], r1 = i < N - 1 ? redPerCoil[i + 1] : r0;
      const g0 = glowPerCoil[i], g1 = i < N - 1 ? glowPerCoil[i + 1] : g0;
      for (let j = 0; j < P; j++) {
        const u = j / P, th = (i + u) * Math.PI * 2;
        const y = y0 + (y1 - y0) * u, rr = r0 + (r1 - r0) * u, gg = g0 + (g1 - g0) * u;
        const ox = Math.cos(th), oz = Math.sin(th);
        for (let s = 0; s < SEG; s++) {
          const [px, py, nx, ny] = prof[s];
          pos[k] = (R + px) * ox; pos[k + 1] = y + py; pos[k + 2] = (R + px) * oz;
          nrm[k] = nx * ox; nrm[k + 1] = ny; nrm[k + 2] = nx * oz;
          red[v] = rr; glow[v] = gg; k += 3; v += 1;
        }
      }
    }
    for (const n of ['position', 'normal', 'aRed', 'aGlow']) g.attributes[n].needsUpdate = true;
  };
  return m;
}

const rbox = (w, h, d, r = 0.012) => new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2, h / 2, d / 2));
function add(S, geo, mat, x, y, z, shadow = true) {
  const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z);
  m.castShadow = shadow; m.receiveShadow = true; S.add(m); return m;
}

function bolt(S, mat, x, y, z, axis = 'z') {
  const b = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.012, 12), mat);
  if (axis === 'z') b.rotation.x = Math.PI / 2; else if (axis === 'x') b.rotation.z = Math.PI / 2;
  b.position.set(x, y, z); S.add(b); return b;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, N = F.coils[0].length;
  world.ground(); world.hills(10, 95); world.hills(12, 150);

  // trees frame the set from the sides; none in the sector behind the spring (cameras look down -z)
  for (let i = 0; i < 70; i++) {
    const a = world.rand() * Math.PI * 2, r = 9 + world.rand() * 34;
    const x = r * Math.sin(a), z = r * Math.cos(a);
    const behind = z < 0 && Math.abs(Math.atan2(x, -z)) < THREE.MathUtils.degToRad(62);
    const front = z > 0 && Math.abs(Math.atan2(x, z)) < THREE.MathUtils.degToRad(35) && r < 20;
    if (behind || front) continue;
    const s = 0.8 + world.rand() * 0.9;
    world.rand() < 0.35 ? world.conifer(x, z, s * 1.1) : world.roundTree(x, z, s);
  }

  // platform: cast-stone slab with a bevel and a darker plinth
  add(S, rbox(3.4, 0.08, 2.4, 0.02), MAT.concrete('#9f998b'), 0, 0.04, 0);
  add(S, rbox(3.2, 0.06, 2.2, 0.018), MAT.concrete('#cbc4b2'), 0, 0.09, 0);

  // apparatus: bevelled timber posts and beam, steel corner brackets and foot plates with bolts
  const wood = MAT.wood('#9b7550'), steel = MAT.brushedSteel(), dark = MAT.darkSteel();
  for (const x of [-0.9, 0.9]) {
    add(S, rbox(0.13, POST_H, 0.13, 0.014), wood, x, POST_H / 2 + 0.12, 0);
    add(S, rbox(0.26, 0.012, 0.26, 0.004), steel, x, 0.126, 0);
    for (const [dx, dz] of [[-0.1, -0.1], [0.1, -0.1], [-0.1, 0.1], [0.1, 0.1]]) bolt(S, dark, x + dx, 0.134, dz, 'y');
    const sgn = Math.sign(x);
    add(S, rbox(0.012, 0.22, 0.1, 0.003), steel, x - sgn * 0.072, BEAM_Y - 0.14, 0);
    add(S, rbox(0.2, 0.012, 0.1, 0.003), steel, x - sgn * 0.17, BEAM_Y - 0.085, 0);
    bolt(S, dark, x - sgn * 0.079, BEAM_Y - 0.18, 0, 'x');
  }
  add(S, rbox(2.1, 0.15, 0.17, 0.016), wood, 0, BEAM_Y, 0);

  // release gripper: mounting plate, drop rod, cross-head, two pivoting jaws with pins
  const top = plan.top_y;
  add(S, rbox(0.24, 0.014, 0.16, 0.004), steel, 0, BEAM_Y - 0.082, 0);
  const rodLen = BEAM_Y - 0.09 - (top + 0.19);
  add(S, new THREE.CylinderGeometry(0.014, 0.014, rodLen, 16), steel, 0, top + 0.19 + rodLen / 2, 0);
  add(S, rbox(0.34, 0.05, 0.07, 0.01), dark, 0, top + 0.165, 0);
  const jawMat = MAT.anodised('#c9472f');
  const jaws = [];
  for (const sgn of [-1, 1]) {
    const pivot = new THREE.Group(); pivot.position.set(sgn * 0.15, top + 0.155, 0); S.add(pivot);
    const arm = new THREE.Mesh(rbox(0.032, 0.15, 0.05, 0.008), jawMat); arm.position.set(0, -0.07, 0);
    const tip = new THREE.Mesh(rbox(0.05, 0.03, 0.05, 0.008), jawMat); tip.position.set(-sgn * 0.018, -0.14, 0);
    [arm, tip].forEach(o => { o.castShadow = true; pivot.add(o); });
    const pin = new THREE.Mesh(new THREE.CylinderGeometry(0.009, 0.009, 0.07, 12), steel); pin.rotation.x = Math.PI / 2; pivot.add(pin);
    jaws.push({ pivot, sgn });
  }
  const glint = haloSprite('#ffffff', 0.18, 0); glint.position.set(0.04, top + 0.02, 0.06); S.add(glint);

  const sl = ribbonSlinky(N); S.add(sl);

  // bottom-coil cue: a thin ring hugging the coil plus a restrained halo (no floating neon disk)
  const ring = new THREE.Mesh(new THREE.TorusGeometry(R + AR + 0.004, 0.0035, 10, 96), MAT.emissive('#ff3b30', 6.0));
  ring.rotation.x = Math.PI / 2; S.add(ring);
  const halo = haloSprite('#ff3b30', 0.62, 0.0); S.add(halo);

  // world-anchored reference: dashed line at the bottom coil's starting height, both sides
  const refGroup = new THREE.Group(); S.add(refGroup);
  const refMat = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.9, toneMapped: false });
  for (const sgn of [-1, 1]) for (let k = 0; k < 6; k++) {
    const dash = new THREE.Mesh(new THREE.BoxGeometry(0.045, 0.0035, 0.0035), refMat);
    dash.position.set(sgn * (R + AR + 0.05 + k * 0.07), 0, 0); refGroup.add(dash);
  }
  const tick = new THREE.Mesh(new THREE.BoxGeometry(0.004, 0.05, 0.004), refMat); tick.position.set(R + AR + 0.47, 0, 0); refGroup.add(tick);
  const tick2 = tick.clone(); tick2.position.x *= -1; refGroup.add(tick2);
  const y0 = F.coils[0][N - 1];

  // reference ball (falls beside the slinky at its centre-of-mass height) and its holding thread
  const ball = add(S, new THREE.SphereGeometry(0.045, 40, 24), MAT.ceramic('#f0ece2'), 0, -5, 0);
  const thread = add(S, new THREE.CylinderGeometry(0.0025, 0.0025, 1, 6), dark, 0, -5, 0, false);

  // steel bar on two V-blocks, a small striker, the travelling pulse and an end flash
  const bar = plan.bar || { x0: -1.2, x1: 1.2, z: -0.62, r: 0.03 };
  const barY = 0.12 + 0.03 + bar.r;
  const barMesh = add(S, new THREE.CylinderGeometry(bar.r, bar.r, bar.x1 - bar.x0, 32), MAT.springSteel(), (bar.x0 + bar.x1) / 2, barY, bar.z);
  barMesh.rotation.z = Math.PI / 2;
  for (const x of [bar.x0 + 0.35, bar.x1 - 0.35]) add(S, rbox(0.08, 0.06, 0.1, 0.01), dark, x, 0.15, bar.z);
  const striker = add(S, rbox(0.1, 0.07, 0.07, 0.012), MAT.anodised('#c9472f'), bar.x0 - 0.06, barY, bar.z);
  const pulse = new THREE.Mesh(new THREE.TorusGeometry(bar.r + 0.004, 0.0045, 10, 48), MAT.emissive('#fff1dc', 7));
  pulse.rotation.y = Math.PI / 2; S.add(pulse);
  const pulseHalo = haloSprite('#fff1dc', 0.22, 0.0); S.add(pulseHalo);
  const flash = haloSprite('#fff1dc', 0.3, 0.0); flash.position.set(bar.x1 + 0.01, barY, bar.z); S.add(flash);

  const redC = new Float32Array(N), glowC = new Float32Array(N);
  return {
    lightCenter: new THREE.Vector3(0, 1, 0),
    update(i) {
      const k = Math.min(i, F.coils.length - 1);
      const ys = F.coils[k], gl = F.glow[k], fi = F.front[k];
      for (let c = 0; c < N; c++) {
        redC[c] = c >= N - 2 ? gl * (c === N - 1 ? 1 : 0.35) : 0;
        glowC[c] = fi >= 0 ? Math.exp(-((c - fi) * (c - fi)) / 2.5) : 0;
      }
      sl.setCoils(ys, redC, glowC);
      const g = F.clamp[k];                 // gripper: 0 closed, 1 open, negative = anticipation squeeze
      for (const j of jaws) j.pivot.rotation.z = -j.sgn * THREE.MathUtils.degToRad(42) * g;
      glint.material.opacity = F.glint ? F.glint[k] : 0;
      const yb = ys[N - 1];
      ring.position.y = yb; ring.visible = gl > 0.02; ring.material.emissiveIntensity = 6.0 * gl;
      halo.position.set(0, yb, 0); halo.material.opacity = 0.32 * gl;
      const ref = F.ref ? F.ref[k] : 0;
      refGroup.visible = ref > 0.01; refGroup.position.y = y0; refMat.opacity = 0.9 * ref;
      const b = F.ball ? F.ball[k] : null;
      ball.visible = !!b; if (b) ball.position.set(...b);
      thread.visible = !!b && g < 0.5;
      if (thread.visible) { const t0 = BEAM_Y - 0.08, bt = b[1] + 0.045; thread.scale.y = t0 - bt; thread.position.set(b[0], (t0 + bt) / 2, 0); }
      const px = F.pulse ? F.pulse[k] : null, on = px !== null && px !== undefined;
      pulse.visible = on; pulseHalo.material.opacity = on ? 0.5 : 0;
      if (on) { pulse.position.set(px, barY, bar.z); pulseHalo.position.set(px, barY, bar.z); }
      flash.material.opacity = F.flash ? 0.8 * F.flash[k] : 0;
      if (F.striker) striker.position.x = bar.x0 - 0.06 - F.striker[k];
    },
    focal(i) {
      const k = Math.min(i, F.coils.length - 1);
      if (F.focal_pt && F.focal_pt[k]) return new THREE.Vector3(...F.focal_pt[k]);
      const c = F.focal ? F.focal[k] : N - 1; return new THREE.Vector3(0, F.coils[k][c], 0);
    },
    vars(i) { const k = Math.min(i, F.coils.length - 1); return F.vars ? F.vars[k] : {}; },
  };
}

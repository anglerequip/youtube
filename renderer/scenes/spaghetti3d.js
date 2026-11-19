// Spaghetti snap: a dry stick held in two grips on a garden workbench. All motion (bending, the
// snap-back curvature waves, cracks, falling fragments, twist) comes from
// factory/simulation_engine/physics/spaghetti.py via plan.frames; this file only draws it.
//
// Each piece is a tube rebuilt every frame from its centreline. A thin red painted stripe along the
// stick makes twist visible; a red emissive channel shows where the stick is bent harder than when it
// first cracked (the snap-back burst).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { MAT, haloSprite } from '../materials.js';

const BENCH_Y = 0.75;            // workbench top height (sim y=0 is the bench top)
const RAD = 0.0012;              // drawn radius (m): real 0.85 mm, slightly thickened to read on a phone
const RING = 14;                 // vertices around the tube
const MAXN = 260;                // max centreline nodes per piece
const POOL = 24;

function pastaTube() {
  const nV = MAXN * RING + 2 * (RING + 1);
  const g = new THREE.BufferGeometry();
  const pos = new Float32Array(nV * 3), nor = new Float32Array(nV * 3), col = new Float32Array(nV * 3), glow = new Float32Array(nV);
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute('normal', new THREE.BufferAttribute(nor, 3).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute('aGlow', new THREE.BufferAttribute(glow, 1).setUsage(THREE.DynamicDrawUsage));
  const idx = [];
  for (let i = 0; i < MAXN - 1; i++) for (let j = 0; j < RING; j++) {
    const a = i * RING + j, b = i * RING + (j + 1) % RING, c = a + RING, d = b + RING;
    idx.push(a, c, b, b, c, d);
  }
  const capBase = MAXN * RING;      // end caps: fans, filled per frame
  g.setIndex(idx); g.userData = { capBase };
  const mat = new THREE.MeshPhysicalMaterial({ vertexColors: true, roughness: 0.42, metalness: 0, clearcoat: 0.25,
    clearcoatRoughness: 0.5, sheen: 0.2, envMapIntensity: 0.7 });
  mat.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute float aGlow; varying float vGlow;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvGlow = aGlow;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vGlow;')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += vec3(1.0, 0.2, 0.14) * vGlow * 5.5;');
  };
  const m = new THREE.Mesh(g, mat);
  m.castShadow = true; m.receiveShadow = true; m.frustumCulled = false;
  return m;
}

const PASTA = new THREE.Color('#e9c46f'), PASTA_DARK = new THREE.Color('#d9ab4f'), STRIPE = new THREE.Color('#2b3038')   // dark, so it is not confused with the red stress glow;
const cTmp = new THREE.Color();

// fill a tube from centreline arrays (sim coordinates, metres); stripe phase per node; glow per node
function setTube(m, xs, ys, zs, phase, glow, hl) {
  const n = Math.min(xs.length, MAXN);
  const g = m.geometry, P = g.attributes.position.array, N = g.attributes.normal.array, C = g.attributes.color.array, Gl = g.attributes.aGlow.array;
  for (let i = 0; i < n; i++) {
    const i0 = Math.max(0, i - 1), i1 = Math.min(n - 1, i + 1);
    let tx = xs[i1] - xs[i0], ty = ys[i1] - ys[i0]; const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
    const nx = -ty, ny = tx;              // in-plane normal; binormal is +z
    for (let j = 0; j < RING; j++) {
      const a = (j / RING) * Math.PI * 2, ca = Math.cos(a), sa = Math.sin(a);
      const ox = nx * ca, oy = ny * ca, oz = sa;
      const v = (i * RING + j) * 3;
      P[v] = xs[i] + ox * RAD; P[v + 1] = ys[i] + oy * RAD + BENCH_Y; P[v + 2] = zs + oz * RAD;
      N[v] = ox; N[v + 1] = oy; N[v + 2] = oz;
      const d = Math.cos(a - phase[i]);   // stripe: a narrow band around the surface angle `phase`
      const st = d > 0.86 ? 1 : 0;
      cTmp.copy(PASTA).lerp(PASTA_DARK, 0.35 * (1 - (ca * 0.5 + 0.5)));
      if (st) cTmp.copy(STRIPE);
      C[v] = cTmp.r; C[v + 1] = cTmp.g; C[v + 2] = cTmp.b;
      Gl[i * RING + j] = Math.min(1, glow ? glow[i] : 0) + (hl || 0);
    }
  }
  g.setDrawRange(0, (n - 1) * RING * 6);
  g.attributes.position.needsUpdate = true; g.attributes.normal.needsUpdate = true;
  g.attributes.color.needsUpdate = true; g.attributes.aGlow.needsUpdate = true;
  m.visible = n > 1;
}

const rbox = (w, h, d, r = 0.004) => new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2, h / 2, d / 2));
function add(S, geo, mat, x, y, z) { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; S.add(m); return m; }

// a grip: a small machined clamp on an arm; local +x points along the stick into the clamp
function grip(S) {
  const g = new THREE.Group(); S.add(g);
  const roll = new THREE.Group(); g.add(roll);            // rotates about the stick axis (twist)
  const body = MAT.anodised('#c9472f'), steel = MAT.brushedSteel(), dark = MAT.darkSteel();
  const add2 = (geo, mat, x, y, z, p = roll) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; p.add(m); return m; };
  add2(rbox(0.022, 0.012, 0.016, 0.003), body, -0.011, 0.0075, 0);
  add2(rbox(0.022, 0.012, 0.016, 0.003), body, -0.011, -0.0075, 0);
  add2(new THREE.CylinderGeometry(0.0025, 0.0025, 0.03, 12), steel, -0.006, 0, 0);
  const knob = add2(new THREE.CylinderGeometry(0.004, 0.004, 0.006, 16), dark, -0.016, 0.016, 0);
  add2(new THREE.CylinderGeometry(0.009, 0.009, 0.012, 24), steel, -0.028, 0, 0).rotation.z = Math.PI / 2;   // axle collar
  g.userData = { roll, knob };
  return g;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames;
  world.camera.near = 0.004; world.camera.far = 300; world.camera.updateProjectionMatrix();
  world.ground(); world.hills(10, 95); world.hills(12, 150);
  for (let i = 0; i < 60; i++) {           // garden trees, away from the bench
    const a = world.rand() * Math.PI * 2, r = 13 + world.rand() * 30;
    const x = r * Math.sin(a), z = r * Math.cos(a);
    if (z > 0 && Math.abs(Math.atan2(x, z)) < 0.6 && r < 20) continue;
    const s = 0.9 + world.rand() * 0.9;
    const tree = world.rand() < 0.35 ? world.conifer(x, z, s * 1.1) : world.roundTree(x, z, s);
    world.contactShadow(tree, x, z, s);     // outside the small, sharp shadow box around the bench
  }
  // flagstone patio + workbench
  add(S, rbox(3.0, 0.06, 2.4, 0.01), MAT.concrete('#bdb6a3'), 0, 0.03, 0);
  const wood = new THREE.MeshStandardMaterial({ color: '#a8835a', roughness: 0.7 }), woodD = new THREE.MeshStandardMaterial({ color: '#7d5d3e', roughness: 0.75 });
  add(S, rbox(0.9, 0.04, 0.5, 0.006), wood, 0, BENCH_Y - 0.02, -0.06);
  for (const x of [-0.4, 0.4]) for (const z of [-0.27, 0.15]) add(S, rbox(0.05, BENCH_Y - 0.04, 0.05, 0.006), woodD, x, (BENCH_Y - 0.04) / 2, z);
  add(S, rbox(0.82, 0.03, 0.04, 0.006), woodD, 0, 0.18, -0.06);
  // a bundle of spare spaghetti held by a band (prop)
  const bundle = new THREE.Group(); S.add(bundle);
  const pmat = new THREE.MeshStandardMaterial({ color: '#e7c26c', roughness: 0.5 });
  for (let i = 0; i < 26; i++) {
    const r = Math.sqrt(world.rand()) * 0.006, a = world.rand() * 6.28;
    const c = new THREE.Mesh(new THREE.CylinderGeometry(0.00085, 0.00085, 0.25, 6), pmat);
    c.rotation.z = Math.PI / 2; c.position.set(0.0, 0.0065 + r * Math.sin(a), r * Math.cos(a)); c.castShadow = true; bundle.add(c);
  }
  const band = new THREE.Mesh(new THREE.TorusGeometry(0.0072, 0.0016, 8, 24), MAT.plastic('#3d6f8e')); band.rotation.y = Math.PI / 2; band.position.y = 0.0065; bundle.add(band);
  bundle.position.set(0.02, BENCH_Y, -0.2); bundle.rotation.y = 0.18;

  // grip stands: posts on the board holding the grips (grips move with the stick ends)
  const gl = grip(S), gr = grip(S);
  const steel = MAT.brushedSteel();
  const postL = add(S, new THREE.CylinderGeometry(0.005, 0.005, 1, 12), steel, 0, 0, -0.035);
  const postR = add(S, new THREE.CylinderGeometry(0.005, 0.005, 1, 12), steel, 0, 0, -0.035);
  const armL = add(S, rbox(0.012, 0.012, 0.04, 0.003), steel, 0, 0, -0.018);
  const armR = add(S, rbox(0.012, 0.012, 0.04, 0.003), steel, 0, 0, -0.018);
  for (const x of [-0.16, 0.16]) add(S, rbox(0.05, 0.008, 0.05, 0.003), MAT.darkSteel(), x, BENCH_Y + 0.004, -0.035);

  const tubes = Array.from({ length: POOL }, () => { const m = pastaTube(); S.add(m); return m; });
  const flash = haloSprite('#fff1dc', 0.035, 0); S.add(flash);
  const flash2 = haloSprite('#ff6a4a', 0.06, 0); S.add(flash2);
  const ringMat = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.9, toneMapped: false });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.006, 0.00045, 8, 48), ringMat); S.add(ring);

  return {
    lightCenter: new THREE.Vector3(0, BENCH_Y, 0),
    update(i) {
      const k = Math.min(i, F.pieces.length - 1);
      const ps = F.pieces[k];
      for (let p = 0; p < POOL; p++) {
        const pc = ps[p];
        if (!pc) { tubes[p].visible = false; continue; }
        const n = pc.x.length, phase = new Array(n);
        for (let j = 0; j < n; j++) phase[j] = Math.PI / 2 - ((pc.pa ?? 0) + (pc.pb ?? 0) * (pc.s0 + (pc.s1 - pc.s0) * j / Math.max(1, n - 1)));
        setTube(tubes[p], pc.x, pc.y, pc.z ?? 0, phase, pc.e, pc.h);
      }
      const G = F.grips[k];
      [[gl, G[0], postL, armL, 0], [gr, G[1], postR, armR, G[2]]].forEach(([g, q, post, arm, roll], side) => {
        g.position.set(q[0], q[1] + BENCH_Y, 0);
        g.rotation.z = q[2];
        g.userData.roll.rotation.x = roll;
        const top = q[1] + BENCH_Y, h = top - BENCH_Y;
        post.scale.y = h; post.position.set(q[0], BENCH_Y + h / 2, -0.035);
        arm.position.set(q[0], top, -0.018);
        g.visible = post.visible = arm.visible = !F.nogrip || !F.nogrip[k];
      });
      const fl = F.flash[k];
      flash.material.opacity = fl ? 0.95 * fl[2] : 0; flash2.material.opacity = fl ? 0.5 * fl[2] : 0;
      if (fl) { flash.position.set(fl[0], fl[1] + BENCH_Y, 0.002); flash2.position.copy(flash.position); }
      const rg = F.ring[k];
      ring.visible = !!rg;
      if (rg) { ring.position.set(rg[0], rg[1] + BENCH_Y, 0); ring.rotation.order = 'ZYX'; ring.rotation.set(0, Math.PI / 2, rg[3] ?? 0); ringMat.opacity = 0.9 * rg[2]; }
    },
    probes(i) {          // every visible fragment's two ends (do pieces read as separate?) + stick thickness
      const k = Math.min(i, F.pieces.length - 1), segs = [];
      for (const pc of F.pieces[k]) {
        if (!pc || pc.x.length < 2) continue;
        const n = pc.x.length - 1, z = j => Array.isArray(pc.z) ? pc.z[j] : (pc.z ?? 0);
        segs.push([[pc.x[0], pc.y[0] + BENCH_Y, z(0)], [pc.x[n], pc.y[n] + BENCH_Y, z(n)]]);
      }
      const f = this.focal(i);
      return [{ entity: 'stick', kind: 'pieces', segs },
              { entity: 'stick', part: 'diameter', kind: 'thickness', p: [f.x, f.y, f.z], size: 2 * RAD }];
    },
    focal(i) {
      const k = Math.min(i, F.focal_pt.length - 1);
      const f = F.focal_pt[k]; return new THREE.Vector3(f[0], f[1] + BENCH_Y, f[2] ?? 0);
    },
    vars(i) { return {}; },
  };
}

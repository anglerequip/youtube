// REGRESSION FIXTURE (factory/qa tests only, never used in production): the chain fountain scene exactly as it
// shipped in commit 3f10b09, with the defect Caesar reported. The QA layers must flag it.
// Defects: beads with no links (does not read as a chain), and a black triangle where the sky dome was
// clipped by the far plane (the old World.render did not keep the dome inside the far plane).
// Chain fountain: a bead chain pours from a glass jar on a telescoping stand to a heap on the patio.
// The arch height, chain speed and stand height come from the steady-state model in
// factory/simulation_engine/physics/chain_fountain.py (plan.frames.*); this file only draws it.
//
// Beads are instanced spheres placed along the chain path every BEAD metres; every 40th bead is red
// so the chain's motion reads at video frame rates. A ghost rope path (how a rope would drape over the
// rim) can be blended in with frames.morph. The macro "lever" shows one stiff link being lifted from
// the pile while its far end presses into the pile (red glow = the pile's upward push).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { MAT, haloSprite } from '../../materials.js';

const BEAD = 0.0046, BR = 0.00215;   // bead spacing and bead radius (m)
const MAXB = 1400;
const JR = 0.045, JH = 0.11;          // jar radius and height
const NP = 600;                        // path resolution

const rbox = (w, h, d, r = 0.01) => new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2, h / 2, d / 2));
function add(S, geo, mat, x, y, z) { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; S.add(m); return m; }

// resample a polyline [[x,y],...] to NP points evenly spaced by arc length; returns {pts, len}
function resample(poly) {
  const cum = [0];
  for (let i = 1; i < poly.length; i++) cum.push(cum[i - 1] + Math.hypot(poly[i][0] - poly[i - 1][0], poly[i][1] - poly[i - 1][1]));
  const L = cum[cum.length - 1], out = []; let j = 0;
  for (let k = 0; k < NP; k++) {
    const s = (k / (NP - 1)) * L;
    while (j < poly.length - 2 && cum[j + 1] < s) j++;
    const u = (s - cum[j]) / Math.max(1e-9, cum[j + 1] - cum[j]);
    out.push([poly[j][0] + (poly[j + 1][0] - poly[j][0]) * u, poly[j][1] + (poly[j + 1][1] - poly[j][1]) * u]);
  }
  return { pts: out, len: L };
}

// fountain path: up from the pile, a smooth arch, straight down outside the jar to the floor heap
function fountainPath(p) {
  const { xr, xf, pile, top, floor } = p, w = xf - xr, a = Math.min(0.55 * w, Math.max(0.004, top - pile - 0.002));
  const poly = [[xr, pile]];
  const yA = top - a;
  for (let y = pile; y < yA; y += 0.004) poly.push([xr, y]);
  for (let k = 0; k <= 40; k++) { const f = -Math.PI / 2 + Math.PI * k / 40; poly.push([xr + w / 2 + (w / 2) * Math.sin(f), yA + a * Math.cos(f)]); }
  for (let y = yA - 0.004; y > floor; y -= 0.02) poly.push([xf, y]);
  poly.push([xf, floor]);
  return poly;
}

// how a rope would go: from the pile up to the rim, draped over the lip, down the outside of the jar
function ropePath(p) {
  const { xr, pile, floor, rim } = p, lip = 0.006;
  const poly = [[xr, pile]];
  for (let k = 1; k <= 12; k++) { const u = k / 12; poly.push([xr + (JR - lip - xr) * u, pile + (rim - pile) * Math.sin(u * Math.PI / 2)]); }
  for (let k = 0; k <= 16; k++) { const f = Math.PI - Math.PI * k / 16; poly.push([JR + lip * Math.cos(f), rim + lip * Math.sin(f) * 0.8]); }
  for (let y = rim - 0.004; y > floor; y -= 0.02) poly.push([JR + lip + 0.001, y]);
  poly.push([JR + lip + 0.001, floor]);
  return poly;
}

export function build(world, plan) {
  world.prepare = () => {};          // the old World.render: no sky-dome / far-plane guard
  const S = world.scene, F = plan.frames;
  world.camera.near = 0.003; world.camera.far = 300; world.camera.updateProjectionMatrix();
  world.ground(); world.hills(10, 95); world.hills(12, 150);
  for (let i = 0; i < 60; i++) {
    const a = world.rand() * Math.PI * 2, r = 9 + world.rand() * 32;
    const x = r * Math.sin(a), z = r * Math.cos(a);
    if (z > 0 && Math.abs(Math.atan2(x, z)) < 0.7 && r < 22) continue;
    const s = 0.9 + world.rand() * 0.9;
    world.rand() < 0.35 ? world.conifer(x, z, s * 1.1) : world.roundTree(x, z, s);
  }
  add(S, rbox(3.2, 0.06, 2.6, 0.01), MAT.concrete('#bdb6a3'), 0, -0.03, 0);   // patio slab, top at y=0

  // telescoping stand: heavy base, outer tube, inner (sliding) tube, wooden platform
  const steel = MAT.brushedSteel(), dark = MAT.darkSteel();
  add(S, new THREE.CylinderGeometry(0.17, 0.19, 0.035, 40), dark, 0, 0.0175, -0.02);
  const outer = add(S, new THREE.CylinderGeometry(0.022, 0.022, 0.9, 24), steel, 0, 0.45 + 0.035, -0.02);
  const collar = add(S, new THREE.CylinderGeometry(0.03, 0.03, 0.03, 24), dark, 0, 0.935, -0.02);
  const inner = add(S, new THREE.CylinderGeometry(0.016, 0.016, 1, 24), steel, 0, 0, -0.02);
  const plat = add(S, rbox(0.16, 0.022, 0.16, 0.006), new THREE.MeshStandardMaterial({ color: '#a8835a', roughness: 0.7 }), 0, 0, 0);

  // glass jar (cheap glass: thin transparent shell + rim highlight, no transmission pass)
  const jar = new THREE.Group(); S.add(jar);
  const glassM = new THREE.MeshPhysicalMaterial({ color: '#e8f1f2', roughness: 0.08, metalness: 0, transparent: true, opacity: 0.22,
    clearcoat: 0.3, specularIntensity: 0.5, envMapIntensity: 1.0, depthWrite: false, side: THREE.DoubleSide });
  const wall = new THREE.Mesh(new THREE.CylinderGeometry(JR, JR, JH, 64, 1, true), glassM); wall.position.y = JH / 2; jar.add(wall);
  const base = new THREE.Mesh(new THREE.CylinderGeometry(JR, JR, 0.006, 64), new THREE.MeshStandardMaterial({ color: '#e8f1f2', roughness: 0.5, transparent: true, opacity: 0.25, depthWrite: false })); base.position.y = 0.003; jar.add(base);
  const rimM = new THREE.Mesh(new THREE.TorusGeometry(JR, 0.0016, 10, 96), new THREE.MeshPhysicalMaterial({ color: '#f4fbfb', roughness: 0.05, transparent: true, opacity: 0.6, clearcoat: 1 }));
  rimM.rotation.x = Math.PI / 2; rimM.position.y = JH; jar.add(rimM);

  // bead material + instanced beads for the moving chain, the pile in the jar and the floor heap
  const beadM = new THREE.MeshStandardMaterial({ color: '#c9ccd1', metalness: 0.85, roughness: 0.28, envMapIntensity: 1.2 });
  const beadGeo = new THREE.SphereGeometry(BR, 10, 8);
  const chain = new THREE.InstancedMesh(beadGeo, beadM, MAXB); chain.castShadow = true; chain.frustumCulled = false; S.add(chain);
  chain.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const red = new THREE.Color('#c92a2e'), grey = new THREE.Color('#c9ccd1');
  for (let i = 0; i < MAXB; i++) chain.setColorAt(i, i % 40 === 0 ? red : grey);
  // pile inside the jar: a coiled mound of beads (static relative to the jar)
  const pileN = 900, pile = new THREE.InstancedMesh(beadGeo, beadM, pileN); pile.castShadow = true; jar.add(pile);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(1, 1, 1), v3 = new THREE.Vector3();
  for (let i = 0; i < pileN; i++) {
    const r = Math.sqrt(world.rand()) * (JR - 0.004), a = world.rand() * 6.283;
    let hgt = 0.006 + (plan.pile_h - 0.006) * (1 - (r / JR) ** 2 * 0.55) * world.rand() ** 0.35;
    if (r < 0.02 && Math.abs(Math.sin(a)) * r < 0.008) hgt = Math.min(hgt, plan.pile_h - 0.005);   // keep the pick-up spot clear
    m4.compose(v3.set(r * Math.cos(a), hgt, r * Math.sin(a)), q, sc); pile.setMatrixAt(i, m4);
  }
  // floor heap (grows): beads in a low cone, revealed progressively
  const heapN = 1500, heap = new THREE.InstancedMesh(beadGeo, beadM, heapN); heap.castShadow = true; S.add(heap);
  const heapPts = [];
  for (let i = 0; i < heapN; i++) { const r = Math.sqrt(world.rand()), a = world.rand() * 6.283; heapPts.push([r, a, world.rand()]); }

  // ghost rope (shown during the "rope" comparison)
  const ropeMat = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.0, depthWrite: false, toneMapped: false });
  let ropeMesh = null;

  // macro lever: one link (two beads + rod) being lifted; glow at the far end = the pile's push
  const lever = new THREE.Group(); S.add(lever);
  const linkM = new THREE.MeshStandardMaterial({ color: '#b9bdc2', metalness: 0.85, roughness: 0.3 });
  const liftM = new THREE.MeshStandardMaterial({ color: '#e3e6ea', metalness: 0.7, roughness: 0.25, emissive: '#ffffff', emissiveIntensity: 0.12 });
  const lb1 = new THREE.Mesh(beadGeo, liftM), lb2 = new THREE.Mesh(beadGeo, liftM);
  const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.0007, 0.0007, BEAD, 8), linkM);
  [lb1, lb2, rod].forEach(o => { o.castShadow = true; lever.add(o); });
  const flat = [];                                  // the next links lying on the pile
  for (let k = 0; k < 8; k++) { const b = new THREE.Mesh(beadGeo, beadM); b.castShadow = true; lever.add(b); flat.push(b); }
  const push = haloSprite('#ff3b30', 0.02, 0); lever.add(push);
  const pushDot = new THREE.Mesh(new THREE.SphereGeometry(0.0012, 12, 8), MAT.emissive('#ff3b30', 6)); lever.add(pushDot);

  const dummy = new THREE.Object3D();
  let travelled = 0;
  return {
    lightCenter: new THREE.Vector3(0, 0.8, 0),
    update(i) {
      const k = Math.min(i, F.h2.length - 1);
      const h2 = F.h2[k], h1 = F.h1[k];
      const pileY = h2, standTop = pileY - plan.pile_h - 0.011;       // jar base on platform top
      const jarBase = standTop + 0.011;
      plat.position.set(0, standTop, 0);
      inner.scale.y = Math.max(0.05, standTop - 0.9); inner.position.y = 0.9 + inner.scale.y / 2;
      jar.position.set(0, jarBase, 0);
      const p = { xr: 0.006, xf: JR + 0.032, pile: pileY, top: pileY + h1, floor: 0.004, rim: jarBase + JH };
      const fp = resample(fountainPath(p));
      const m = F.morph[k];
      let path = fp;
      if (m < 1) {
        const rp = resample(ropePath(p));
        path = { pts: fp.pts.map((q2, j) => [rp.pts[j][0] + (q2[0] - rp.pts[j][0]) * m, rp.pts[j][1] + (q2[1] - rp.pts[j][1]) * m]), len: rp.len + (fp.len - rp.len) * m };
      }
      // beads along the path, offset by the travelled distance (mod spacing)
      const off = F.dist[k] % BEAD, shift = Math.floor(F.dist[k] / BEAD);
      const nB = Math.min(MAXB, Math.floor((path.len - off) / BEAD));
      const sway = F.sway ? F.sway[k] : 0;
      for (let b = 0; b < MAXB; b++) {
        if (b >= nB) { dummy.position.set(0, -10, 0); dummy.updateMatrix(); chain.setMatrixAt(b, dummy.matrix); continue; }
        const s = off + b * BEAD, f = (s / path.len) * (NP - 1), j = Math.min(NP - 2, Math.floor(f)), u = f - j;
        const x = path.pts[j][0] + (path.pts[j + 1][0] - path.pts[j][0]) * u, y = path.pts[j][1] + (path.pts[j + 1][1] - path.pts[j][1]) * u;
        const zw = sway * Math.sin(s * 9 - F.dist[k] * 9) * Math.min(1, s * 4);
        dummy.position.set(x, y, zw); dummy.updateMatrix(); chain.setMatrixAt(b, dummy.matrix);
        chain.setColorAt(b, (b - shift) % 40 === 0 ? red : grey);
      }
      chain.instanceMatrix.needsUpdate = true; chain.instanceColor.needsUpdate = true;
      // heap on the floor below the falling leg
      const hf = F.heap[k], nH = Math.floor(heapN * hf), hr = 0.03 + 0.09 * Math.sqrt(hf);
      for (let j = 0; j < heapN; j++) {
        const [r, a, z] = heapPts[j];
        if (j >= nH) { dummy.position.set(0, -10, 0); }
        else { const rr = r * hr; dummy.position.set(p.xf + rr * Math.cos(a), BR + (1 - r) * 0.35 * hr * z, rr * Math.sin(a)); }
        dummy.updateMatrix(); heap.setMatrixAt(j, dummy.matrix);
      }
      heap.instanceMatrix.needsUpdate = true;
      // ghost rope
      const ro = F.rope ? F.rope[k] : 0;
      if (ro > 0.001) {
        if (!ropeMesh) {
          const rp = resample(ropePath(p));
          const curve = new THREE.CatmullRomCurve3(rp.pts.filter((_, j) => j % 4 === 0).map(q2 => new THREE.Vector3(q2[0], q2[1], 0.0)));
          ropeMesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 400, 0.0022, 10), ropeMat); S.add(ropeMesh);
        }
        ropeMat.opacity = 0.55 * ro; ropeMesh.visible = true;
      } else if (ropeMesh) ropeMesh.visible = false;
      // macro lever
      const lv = F.lever ? F.lever[k] : null;
      lever.visible = !!lv;
      if (lv) {
        const u = (F.dist[k] % BEAD) / BEAD, d = u * BEAD, th = Math.asin(Math.min(1, d / BEAD));
        const xl = p.xr, yl = pileY + d;
        const xr2 = xl + BEAD * Math.cos(th), yr2 = pileY;
        lb1.position.set(xl, yl, 0); lb2.position.set(xr2, yr2, 0);
        rod.position.set((xl + xr2) / 2, (yl + yr2) / 2, 0); rod.rotation.set(0, 0, Math.atan2(yl - yr2, xl - xr2) - Math.PI / 2);
        for (let j = 0; j < flat.length; j++) {
          const a = j * 0.35; flat[j].position.set(xr2 + BEAD * (j + 1) * Math.cos(a * 0.3), pileY, -BEAD * j * Math.sin(a * 0.3) * 0.6);
        }
        const g = Math.sin(Math.PI * u) * lv.glow;
        push.position.set(xr2, yr2 - BR * 0.6, 0.0005); push.material.opacity = 0.75 * g;
        pushDot.position.set(xr2, yr2 - BR * 0.9, 0); pushDot.visible = g > 0.05; pushDot.material.emissiveIntensity = 6 * g;
      }
    },
    focal(i) { const k = Math.min(i, F.focal_pt.length - 1); return new THREE.Vector3(...F.focal_pt[k]); },
    probes(i) {          // what this old scene really drew: beads only, no connector geometry
      const k = Math.min(i, F.focal_pt.length - 1);
      return [{ entity: 'chain', kind: 'chain', p: F.focal_pt[k], pitch: BEAD, bead: 2 * BR, connector: 0 }];
    },
    vars(i) { return {}; },
  };
}

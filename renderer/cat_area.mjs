// Exposed surface area of the original cat model (renderer/cat.js) in different poses.
// Used by content/episodes/cat-loaf/plan.py for the "less surface" number, labelled "our model" on screen.
//
// Method: build the cat, pose it, and walk every triangle of every body mesh (eyes, mouth and whiskers
// excluded). A triangle counts as exposed skin/fur when its centre is
//   - not inside any other body part (ellipsoids and tapered tubes are tested exactly), and
//   - not in floor contact (centre higher than CONTACT_M above the floor).
// The meshes are finely tessellated (CLAUDE.md section 11), so triangle centres sample the surface well.
//
//   node renderer/cat_area.mjs [out.json]
import * as THREE from 'three';
import { writeFileSync } from 'node:fs';
import { cat } from './cat.js';

const CONTACT_M = 0.006;

function occluders(root) {
  const list = [];
  root.traverse(o => {
    if (!o.isMesh || !o.userData.prim || !visibleChain(o) || excluded(o)) return;
    list.push(o);
  });
  return list;
}
const visibleChain = o => { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; };
const excluded = o => { for (let p = o; p; p = p.parent) if (p.userData && p.userData.noArea) return true; return false; };

const inv = new THREE.Matrix4(), lp = new THREE.Vector3(), cp = new THREE.Vector3();
function inside(o, wp) {
  inv.copy(o.matrixWorld).invert(); lp.copy(wp).applyMatrix4(inv);
  const pr = o.userData.prim;
  if (pr === 'ell') return lp.length() < o.geometry.parameters.radius * 0.999;
  if (pr.type === 'tube') {
    let best = 1e9, bu = 0;
    for (let k = 0; k <= 80; k++) { const u = k / 80; pr.curve.getPointAt(u, cp); const d = cp.distanceTo(lp); if (d < best) { best = d; bu = u; } }
    for (let h = 1 / 160; h > 1e-4; h /= 2) for (const u of [bu - h, bu + h]) {
      if (u < 0 || u > 1) continue; pr.curve.getPointAt(u, cp); const d = cp.distanceTo(lp); if (d < best) { best = d; bu = u; }
    }
    return best < pr.r * Math.max(0.05, pr.taper(bu)) * 0.999;
  }
  return false;
}

function area(root) {
  root.updateMatrixWorld(true);
  const occ = occluders(root);
  const surf = [];
  root.traverse(o => { if (o.isMesh && visibleChain(o) && !excluded(o)) surf.push(o); });
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), cen = new THREE.Vector3(), t = new THREE.Triangle();
  let total = 0, exposed = 0, contact = 0, buried = 0;
  for (const o of surf) {
    const P = o.geometry.attributes.position, I = o.geometry.index;
    const n = I ? I.count / 3 : P.count / 3;
    for (let f = 0; f < n; f++) {
      const ia = I ? I.getX(3 * f) : 3 * f, ib = I ? I.getX(3 * f + 1) : 3 * f + 1, ic = I ? I.getX(3 * f + 2) : 3 * f + 2;
      a.fromBufferAttribute(P, ia).applyMatrix4(o.matrixWorld);
      b.fromBufferAttribute(P, ib).applyMatrix4(o.matrixWorld);
      c.fromBufferAttribute(P, ic).applyMatrix4(o.matrixWorld);
      t.set(a, b, c); const A = t.getArea(); if (A <= 0) continue;
      total += A; cen.copy(a).add(b).add(c).multiplyScalar(1 / 3);
      if (cen.y < CONTACT_M) { contact += A; continue; }
      let hid = false;
      for (const q of occ) { if (q === o || (o.userData.caps && o.userData.caps.includes(q)) || (q.userData.caps && q.userData.caps.includes(o))) continue; if (inside(q, cen)) { hid = true; break; } }
      if (hid) buried += A; else exposed += A;
    }
  }
  return { exposed_m2: exposed, contact_m2: contact, buried_m2: buried, total_mesh_m2: total };
}

const POSES = {
  stretched: { mode: 'lie', fold: 0, t: 0 },
  loaf: { mode: 'lie', fold: 1, t: 0 },
  sitting: { mode: 'sit', t: 0 },
};
const out = { method: 'triangle-centre sampling of renderer/cat.js; exposed = not inside another body part and not within ' + CONTACT_M + ' m of the floor; eyes, mouth, whiskers excluded', contact_m: CONTACT_M, poses: {} };
for (const [name, p] of Object.entries(POSES)) {
  const c = cat(); c.pose(p);
  const r = area(c);
  out.poses[name] = Object.fromEntries(Object.entries(r).map(([k, v]) => [k.replace('_m2', '_cm2'), Math.round(v * 1e5) / 10]));
}
const s = out.poses.stretched.exposed_cm2, l = out.poses.loaf.exposed_cm2;
out.loaf_less_than_stretched_pct = Math.round(1000 * (1 - l / s)) / 10;
const json = JSON.stringify(out, null, 2);
if (process.argv[2]) writeFileSync(process.argv[2], json + '\n');
console.log(json);

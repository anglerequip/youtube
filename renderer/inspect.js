// Geometry, depth, shadow and screen-space inspection of a built scene (factory/qa/inspect3d.py reads it).
//
// Unlike a look at the final pixels, this inspects the scene graph itself at chosen frames, so a defect
// is found with its cause (which mesh, which plane, which shadow caster) before anything is rendered:
//   holes        frame rendered with a sentinel clear colour: any sentinel pixel is a place where the
//                world is missing (clipped sky dome, far-plane cut, gaps) and the video would show black
//   nonfinite    NaN / Infinity in vertex positions, instance matrices or the camera
//   degenerate   meshes with many zero-area triangles
//   coplanar     overlapping parallel surfaces closer together than the depth buffer can separate at
//                that distance (z-fighting), unless polygonOffset resolves them
//   depth        near/far ratio and the smallest separable distance at the subject
//   shadows      a caster whose shadow is cut by the shadow-map box edge while its shadow is in view
//                (hard, moving shadow seams on the ground)
//   probes       scene-supplied readability probes: projected thickness in pixels at 1080x1920 and at
//                phone preview sizes; fragment end gaps (do separate pieces read as separate?)
//   motion       probe positions on the next frame: sudden jumps within one shot (popping)
import * as THREE from 'three';

const SENTINEL = [255, 0, 255];
const PREVIEW = { phone: 360 / 1080, small: 270 / 1080 };

function finiteArray(a) { for (let k = 0; k < a.length; k++) if (!Number.isFinite(a[k])) return false; return true; }

function meshes(scene) {
  const out = [];
  scene.traverse(o => { if ((o.isMesh || o.isInstancedMesh) && o.geometry) out.push(o); });
  return out;
}

function visibleChain(o) { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; }

function label(o) {
  if (o.name) return o.name;
  const t = o.geometry?.type || 'mesh', s = o.geometry?.boundingSphere?.radius;
  return `${o.isInstancedMesh ? 'instanced ' : ''}${t}${s ? ` r=${s.toFixed(3)}` : ''}`;
}

// ---- one-off checks on the built scene -------------------------------------------------------------
export function staticChecks(world) {
  const out = { nonfinite: [], degenerate: [] };
  for (const o of meshes(world.scene)) {
    const pos = o.geometry.attributes.position;
    if (!pos) continue;
    if (!finiteArray(pos.array)) out.nonfinite.push(label(o));
    const idx = o.geometry.index, n = idx ? idx.count / 3 : pos.count / 3;
    if (n < 50 || n > 200000 || !visibleChain(o) || Number.isFinite(o.geometry.drawRange.count)) continue;   // skip pooled/dynamic buffers
    let bad = 0; const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
    for (let t = 0; t < n; t++) {
      const i0 = idx ? idx.getX(3 * t) : 3 * t, i1 = idx ? idx.getX(3 * t + 1) : 3 * t + 1, i2 = idx ? idx.getX(3 * t + 2) : 3 * t + 2;
      a.fromBufferAttribute(pos, i0); b.fromBufferAttribute(pos, i1); c.fromBufferAttribute(pos, i2);
      if (b.sub(a).cross(c.sub(a)).lengthSq() < 1e-20) bad++;
    }
    if (bad / n > 0.05) out.degenerate.push({ mesh: label(o), fraction: +(bad / n).toFixed(3), triangles: n });
  }
  return out;
}

// ---- sentinel render: where is the world missing? ---------------------------------------------------
let holeRT = null;
function holes(world) {
  const r = world.renderer, w = 135, h = 240;
  if (!holeRT) holeRT = new THREE.WebGLRenderTarget(w, h);
  const prevColor = new THREE.Color(); r.getClearColor(prevColor); const prevAlpha = r.getClearAlpha();
  const prevBg = world.scene.background;
  world.scene.background = null;
  r.setClearColor(new THREE.Color(SENTINEL[0] / 255, SENTINEL[1] / 255, SENTINEL[2] / 255), 1);
  r.setRenderTarget(holeRT); r.clear(); r.render(world.scene, world.camera);
  const px = new Uint8Array(w * h * 4); r.readRenderTargetPixels(holeRT, 0, 0, w, h, px);
  r.setRenderTarget(null); r.setClearColor(prevColor, prevAlpha); world.scene.background = prevBg;
  let n = 0, top = h, bottom = -1, left = w, right = -1;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const k = (y * w + x) * 4;
    if (px[k] > 245 && px[k + 1] < 10 && px[k + 2] > 245) {
      n++; const yy = h - 1 - y;                 // readPixels is bottom-up
      top = Math.min(top, yy); bottom = Math.max(bottom, yy); left = Math.min(left, x); right = Math.max(right, x);
    }
  }
  return { fraction: +(n / (w * h)).toFixed(5), bbox: n ? [left / w, top / h, (right + 1) / w, (bottom + 1) / h].map(v => +v.toFixed(3)) : null };
}

// ---- depth precision and coplanar surfaces -----------------------------------------------------------
function depthStep(d, near) { return d * d / (near * 16777216); }   // 24-bit depth: smallest separable distance at d

function thinPlanes(world) {
  const out = [], box = new THREE.Box3(), size = new THREE.Vector3();
  for (const o of meshes(world.scene)) {
    if (o.isInstancedMesh || !visibleChain(o) || o === world.skyDome) continue;
    const m = Array.isArray(o.material) ? o.material[0] : o.material;
    if (!m || m.transparent || m.depthWrite === false) continue;
    box.setFromObject(o); if (box.isEmpty()) continue; box.getSize(size);
    const dims = [size.x, size.y, size.z], big = Math.max(...dims);
    if (big <= 0) continue;
    const ax = dims.indexOf(Math.min(...dims));
    out.push({ o, m, ax, thin: dims[ax] < 1e-3 * big, lo: box.min.toArray(), hi: box.max.toArray() });
  }
  return out;
}

function coplanar(world, near) {
  const P = thinPlanes(world), hits = [], cam = world.camera.position;
  const thin = P.filter(p => p.thin);
  for (const a of thin) {
    for (const b of P) {
      if (a === b || b.ax !== a.ax) continue;
      if (b.thin && P.indexOf(b) < P.indexOf(a)) continue;
      const pa = (a.lo[a.ax] + a.hi[a.ax]) / 2;
      const pb = b.thin ? (b.lo[b.ax] + b.hi[b.ax]) / 2 : b.hi[b.ax];      // a thin plane resting on a box top
      const o1 = (a.ax + 1) % 3, o2 = (a.ax + 2) % 3;
      const ov1 = Math.min(a.hi[o1], b.hi[o1]) - Math.max(a.lo[o1], b.lo[o1]);
      const ov2 = Math.min(a.hi[o2], b.hi[o2]) - Math.max(a.lo[o2], b.lo[o2]);
      if (ov1 <= 0 || ov2 <= 0) continue;
      // the overlap rectangle; z-fighting starts where the depth step exceeds the gap: d* = sqrt(gap*near*2^24/4)
      const r1 = [Math.max(a.lo[o1], b.lo[o1]), Math.min(a.hi[o1], b.hi[o1])];
      const r2 = [Math.max(a.lo[o2], b.lo[o2]), Math.min(a.hi[o2], b.hi[o2])];
      const cp = cam.toArray(), q = [0, 0, 0]; q[a.ax] = pa;
      q[o1] = Math.min(Math.max(cp[o1], r1[0]), r1[1]); q[o2] = Math.min(Math.max(cp[o2], r2[0]), r2[1]);
      const dmin = cam.distanceTo(new THREE.Vector3(...q));
      let dmax = 0;
      for (const u of r1) for (const w of r2) { const z = [0, 0, 0]; z[a.ax] = pa; z[o1] = u; z[o2] = w; dmax = Math.max(dmax, cam.distanceTo(new THREE.Vector3(...z))); }
      const gap = Math.abs(pa - pb), dstar = Math.sqrt(gap * near * 16777216 / 4);
      const fog = world.scene.fog, fogFar = fog ? fog.near + 0.6 * (fog.far - fog.near) : Infinity;   // beyond 60% haze it cannot be seen
      const offset = a.m.polygonOffset || b.m.polygonOffset;
      const from = Math.max(dstar, dmin), to = Math.min(dmax, fogFar, world.camera.far);
      if (!offset && from < to) {
        // a point of the overlap at distance `from`, roughly towards its centre: is it in view?
        const c = [0, 0, 0]; c[a.ax] = pa; c[o1] = (r1[0] + r1[1]) / 2; c[o2] = (r2[0] + r2[1]) / 2;
        const v = new THREE.Vector3(...c).project(world.camera);
        if (Math.abs(v.x) <= 1.05 && Math.abs(v.y) <= 1.05 && v.z < 1)
          hits.push({ a: label(a.o), b: label(b.o), gap: +gap.toExponential(2), need: +(4 * depthStep(from, near)).toExponential(2),
            distance: +from.toFixed(2), unsafe_beyond_m: +dstar.toFixed(2) });
      }
    }
  }
  return hits.slice(0, 12);
}

// ---- shadow-map coverage ---------------------------------------------------------------------------
const _corners = Array.from({ length: 8 }, () => new THREE.Vector3());
function boxCorners(b) {
  let k = 0;
  for (const x of [b.min.x, b.max.x]) for (const y of [b.min.y, b.max.y]) for (const z of [b.min.z, b.max.z]) _corners[k++].set(x, y, z);
  return _corners;
}

function shadowCutoffs(world, groundY = 0) {
  const sun = world.sun;
  if (!sun.castShadow || sun.intensity <= 0) return [];
  sun.updateMatrixWorld(); sun.target.updateMatrixWorld(); sun.shadow.updateMatrices(sun);
  const S = sun.shadow.camera; S.updateMatrixWorld();
  const toShadow = new THREE.Matrix4().multiplyMatrices(S.projectionMatrix, S.matrixWorldInverse);
  const dir = new THREE.Vector3().subVectors(sun.target.getWorldPosition(new THREE.Vector3()), sun.getWorldPosition(new THREE.Vector3())).normalize();
  const cam = world.camera, fogFar = world.scene.fog ? world.scene.fog.far : 1e9;
  const out = [], b = new THREE.Box3(), m4 = new THREE.Matrix4(), v = new THREE.Vector3(), g = new THREE.Vector3();
  const test = (bb, name) => {
    const height = bb.max.y - Math.max(bb.min.y, groundY);
    if (height < 0.25) return;                       // flat casters (road slabs, kerbs): the shadow is a sliver under them
    let inS = 0;
    const cs = boxCorners(bb);
    for (const c of cs) { v.copy(c).applyMatrix4(toShadow); if (Math.abs(v.x) <= 1 && Math.abs(v.y) <= 1 && v.z >= -1 && v.z <= 1) inS++; }
    if (inS === 0 || inS === 8) return;
    if (dir.y > -1e-3) return;
    // where the shadow lands on the ground, and is that in view (and not lost in fog)?
    let seen = 0, dmin = Infinity; const sx = [], sy = [];
    for (const c of cs) {
      const s = (groundY - c.y) / dir.y; g.copy(c).addScaledVector(dir, Math.max(0, s));
      const d = cam.position.distanceTo(g);
      v.copy(g).project(cam);
      if (Math.abs(v.x) <= 1 && Math.abs(v.y) <= 1 && v.z < 1 && d < 0.85 * fogFar) {
        seen++; dmin = Math.min(dmin, d); sx.push((v.x + 1) / 2); sy.push((1 - v.y) / 2);
      }
    }
    if (!seen) return;
    const fog = world.scene.fog, ff = fog ? Math.min(1, Math.max(0, (dmin - fog.near) / (fog.far - fog.near))) : 0;
    const box2 = [Math.min(...sx), Math.min(...sy), Math.max(...sx), Math.max(...sy)];
    const area = (box2[2] - box2[0]) * 360 * (box2[3] - box2[1]) * 640;    // footprint on a 360x640 phone
    out.push({ caster: name, corners_in_shadow_box: inS, footprint_corners_in_view: seen, distance: +dmin.toFixed(1),
      fog: +ff.toFixed(2), visible_area_px_360: +(area * (1 - ff)).toFixed(0), screen: box2.map(q => +q.toFixed(3)) });
  };
  for (const o of meshes(world.scene)) {
    if (!o.castShadow || !visibleChain(o)) continue;
    if (o.isInstancedMesh) {
      if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
      const n = Math.min(o.count, 4000);
      for (let k = 0; k < n; k++) {
        o.getMatrixAt(k, m4); m4.premultiply(o.matrixWorld);
        b.copy(o.geometry.boundingBox).applyMatrix4(m4);
        if (b.min.y < -5) continue;                           // parked off-stage
        test(b, label(o) + `#${k}`);
        if (out.length > 40) return out;
      }
    } else { b.setFromObject(o); if (!b.isEmpty()) test(b, label(o)); }
  }
  return out;
}

// ---- probes ------------------------------------------------------------------------------------------
function pxSize(world, p, size) {
  const cam = world.camera, d = cam.position.distanceTo(p);
  return size * world.H / (2 * d * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2));
}

function screen(world, p) {
  const v = p.clone().project(world.camera);
  return { x: (v.x + 1) / 2, y: (1 - v.y) / 2, in: Math.abs(v.x) <= 1 && Math.abs(v.y) <= 1 && v.z < 1 };
}

function evalProbes(world, probes) {
  const out = [];
  for (const pr of probes || []) {
    if (pr.kind === 'thickness') {
      const p = new THREE.Vector3(...pr.p), s = screen(world, p), px = pxSize(world, p, pr.size);
      out.push({ entity: pr.entity, part: pr.part, kind: 'thickness', on_screen: s.in, x: +s.x.toFixed(3), y: +s.y.toFixed(3),
        px_1080: +px.toFixed(2), px_360: +(px * PREVIEW.phone).toFixed(2), px_270: +(px * PREVIEW.small).toFixed(2) });
    } else if (pr.kind === 'pieces') {
      // separate fragments: how many are on screen, and do their ends read as separate on a phone?
      const ends = pr.segs.map(([a, b]) => [screen(world, new THREE.Vector3(...a)), screen(world, new THREE.Vector3(...b))]);
      const onScreen = ends.filter(([a, b]) => a.in || b.in).length;
      let minGap = Infinity;
      for (let i = 0; i < ends.length; i++) for (let j = i + 1; j < ends.length; j++)
        for (const p of ends[i]) for (const q of ends[j]) {
          if (!p.in && !q.in) continue;
          const dx = (p.x - q.x) * world.W, dy = (p.y - q.y) * world.H;
          minGap = Math.min(minGap, Math.hypot(dx, dy));
        }
      // clusters: pieces whose ends are closer than 2 px on a 360 px wide phone read as one
      const parent = ends.map((_, i) => i), find = i => parent[i] === i ? i : (parent[i] = find(parent[i]));
      for (let i = 0; i < ends.length; i++) for (let j = i + 1; j < ends.length; j++)
        for (const p of ends[i]) for (const q of ends[j]) {
          const gap = Math.hypot((p.x - q.x) * world.W, (p.y - q.y) * world.H) * PREVIEW.phone;
          if (gap < 2 && (p.in || q.in)) parent[find(i)] = find(j);
        }
      const readable = new Set(ends.map((e, i) => (e[0].in || e[1].in) ? find(i) : null).filter(x => x !== null)).size;
      out.push({ entity: pr.entity, kind: 'pieces', count: pr.segs.length, on_screen: onScreen, readable_at_360: readable,
        ends: ends.map(e => e.map(q => [+q.x.toFixed(3), +q.y.toFixed(3)])),
        min_end_gap_px_1080: Number.isFinite(minGap) ? +minGap.toFixed(1) : null });
    } else if (pr.kind === 'chain') {
      // a bead chain reads as a chain only if, wherever the gaps between beads are visible, a connector
      // bridges them; otherwise it reads as loose floating balls
      const p = new THREE.Vector3(...pr.p), s = screen(world, p), k = pxSize(world, p, 1);
      out.push({ entity: pr.entity, kind: 'chain', on_screen: s.in, bead_px_1080: +(pr.bead * k).toFixed(2),
        gap_px_1080: +(Math.max(0, pr.pitch - pr.bead) * k).toFixed(2), connector_px_1080: +(pr.connector * k).toFixed(2),
        bead_px_360: +(pr.bead * k * PREVIEW.phone).toFixed(2), connector_px_360: +(pr.connector * k * PREVIEW.phone).toFixed(2) });
    } else if (pr.kind === 'point') {
      const s = screen(world, new THREE.Vector3(...pr.p));
      out.push({ entity: pr.entity, part: pr.part, kind: 'point', on_screen: s.in, x: +s.x.toFixed(3), y: +s.y.toFixed(3) });
    } else if (pr.kind === 'missing') {
      out.push({ entity: pr.entity, part: pr.part, kind: 'missing', why: pr.why });
    }
  }
  return out;
}

// ---- one sampled frame -------------------------------------------------------------------------------
export function inspectFrame(world, scene, plan, i, shot) {
  const cam = world.camera, near = cam.near, far = cam.far;
  const nonfinite = [];
  if (!finiteArray(cam.position.toArray()) || !finiteArray(cam.projectionMatrix.elements)) nonfinite.push('camera');
  for (const o of meshes(world.scene))
    if (o.isInstancedMesh && visibleChain(o) && !finiteArray(o.instanceMatrix.array)) nonfinite.push(label(o) + ' instance matrices');
  const focal = scene.focal ? scene.focal(i) : null;
  const dSubject = focal ? cam.position.distanceTo(focal) : null;
  const probes = evalProbes(world, scene.probes ? scene.probes(i) : []);
  return {
    i, t: +(i / plan.fps).toFixed(3), shot: shot.start,
    camera: { near: +near.toFixed(4), far: +far.toFixed(1), fov: cam.fov, pos: cam.position.toArray().map(v => +v.toFixed(3)) },
    depth: { ratio: Math.round(far / near), subject_distance: dSubject && +dSubject.toFixed(3),
      step_at_subject: dSubject && +depthStep(dSubject, near).toExponential(2) },
    holes: holes(world),
    nonfinite,
    coplanar: coplanar(world, near),
    shadow_cutoffs: shadowCutoffs(world, scene.groundY ?? 0),
    probes,
  };
}

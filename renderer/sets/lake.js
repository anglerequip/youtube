// Reusable set (CLAUDE.md "Autopilot efficiency": the outdoors/lake set). A calm lake with a grassy bank along
// z = SHORE (water for z < SHORE), a muddy shore slope, a lakebed that deepens away from the bank, reeds, a small
// wooden jetty, trees and hills, plus props at the section 11 budget: a wooden rowing boat, fishing rod with line,
// trout- and gar-like fish that swim by bending their body, a tackle box and a landing net.
//
//   import { lake, rowboat, fish, rod, tackleBox, net, BANK_Y, SHORE } from '../sets/lake.js';
//   const L = lake(world, { jetty: true });      // per frame: L.update(t, world.camera)
//   const f = fish('trout', 0.35); f.position.set(0, -1, -3); scene.add(f); f.swim(t, 1);
//
// Underwater: the surface is drawn from below by a Snell's-window shader (snellSurface). Every pixel of the
// underside refracts the view ray with Snell's law (n = 1.333) and looks up the world above the water in a cube map
// rendered each frame from the surface point over the camera, so the whole bank and sky really are squeezed into a
// 97-degree circle, people on the bank squashed at its rim. Rays past the critical angle are totally reflected and
// look up a second cube map of the underwater world (the lakebed mirrored). Use lighting 'underlake' below water.
// (opt.snell = false falls back to the older flat "mirror" ring sheet.)
import * as THREE from 'three';
import { PALETTE } from '../world.js';
import { MAT } from '../materials.js';

export const SHORE = 2.0, BANK_Y = 0.3, N_WATER = 1.333;
export const CRIT = Math.asin(1 / N_WATER);           // 48.6 deg
const flat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, flatShading: true, ...x });
const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };
const seeded = s => () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);

// lakebed height below the water at distance from the shore (metres, negative = under water)
export const bedY = z => z > SHORE ? BANK_Y : (z > SHORE - 1.2 ? -0.55 * (SHORE - z) / 1.2 : Math.max(-3.4, -0.55 - (SHORE - 1.2 - z) * 0.32));

export function lake(world, opt = {}) {
  const S = world.scene, R = seeded(opt.seed ?? 17);
  world.camera.far = 600;
  if (opt.hills !== false) world.hills(12, 170);
  // grassy bank (z > SHORE), raised
  const bank = world.ground(700); bank.position.set(0, BANK_Y, SHORE + 350);
  // shore slope: mud strip from the bank edge down under the water
  const slopeG = new THREE.PlaneGeometry(700, 1.6, 140, 4); slopeG.rotateX(-Math.PI / 2);
  const sp = slopeG.attributes.position;
  for (let i = 0; i < sp.count; i++) { const z = sp.getZ(i) + SHORE - 0.8 + 0.01; sp.setZ(i, z); sp.setY(i, Math.min(BANK_Y, bedY(z) + (z > SHORE - 0.02 ? BANK_Y : 0)) + 0.02 * Math.sin(sp.getX(i) * 1.7)); }
  slopeG.computeVertexNormals();
  const mud = new THREE.Mesh(slopeG, flat('#6b5a40', { flatShading: false })); mud.receiveShadow = true; S.add(mud);
  // lakebed with a little relief and pebbles of colour
  const bedG = new THREE.PlaneGeometry(400, 260, 160, 104); bedG.rotateX(-Math.PI / 2);
  const bp = bedG.attributes.position, cols = [];
  const c0 = new THREE.Color('#6d6a4a'), c1 = new THREE.Color('#57583c'), c2 = new THREE.Color('#7f7656'), tmp = new THREE.Color();
  for (let i = 0; i < bp.count; i++) {
    const x = bp.getX(i), z = bp.getZ(i) + SHORE - 1.2 - 130;
    bp.setZ(i, z); bp.setY(i, bedY(z) + 0.08 * Math.sin(x * 0.9 + z * 0.4) + 0.05 * Math.sin(x * 2.3 - z * 1.1));
    const r = R(); tmp.copy(r < 0.6 ? c0 : r < 0.85 ? c1 : c2); cols.push(tmp.r, tmp.g, tmp.b);
  }
  bedG.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3)); bedG.computeVertexNormals();
  const bed = new THREE.Mesh(bedG, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, flatShading: true })); bed.receiveShadow = true; S.add(bed);
  // a few rocks on the bed
  for (let k = 0; k < 26; k++) {
    const x = (R() - 0.5) * 30, z = SHORE - 1.5 - R() * 16, s = 0.12 + R() * 0.35;
    const rk = new THREE.Mesh(new THREE.IcosahedronGeometry(s, 1), flat(R() < 0.5 ? '#77735f' : '#5f5d4c'));
    rk.scale.y = 0.6; rk.position.set(x, bedY(z) + s * 0.2, z); rk.rotation.set(R() * 3, R() * 3, 0); S.add(rk);
  }
  // water surface: gentle faceted swell, see-through
  const wG = new THREE.PlaneGeometry(240, 240, 120, 120); wG.rotateX(-Math.PI / 2); wG.translate(0, 0, SHORE + 0.3 - 120);
  const wBase = Float32Array.from(wG.attributes.position.array);
  const water = new THREE.MeshStandardMaterial({ color: opt.waterColor ?? '#5d7f76', roughness: opt.waterRoughness ?? 0.34, metalness: 0.0, transparent: true,
    opacity: opt.opacity ?? 0.8, side: THREE.DoubleSide, flatShading: true, depthWrite: false, envMapIntensity: 0.25 });
  const surf = new THREE.Mesh(wG, water); surf.receiveShadow = true; surf.renderOrder = 2; S.add(surf);
  const farW = new THREE.Mesh(new THREE.RingGeometry(118, 2500, 64, 1), water); farW.rotation.x = -Math.PI / 2; farW.position.set(0, -0.01, SHORE - 120); farW.renderOrder = 2; S.add(farW);
  // the under-surface mirror (total internal reflection outside Snell's window), coloured like the reflected bed
  const mG = new THREE.RingGeometry(1, 260, 160, 24); const rimC = new THREE.Color('#eef6f2'); const mp = mG.attributes.position, mc = [];
  for (let i = 0; i < mp.count; i++) {           // pack the rings toward the inner edge (fine rim, coarse far away)
    const x = mp.getX(i), y = mp.getY(i), r = Math.hypot(x, y), u = (r - 1) / 259, r2 = 1 + 259 * u ** 4;
    mp.setXY(i, x / r * r2, y / r * r2);
  }
  const near = new THREE.Color('#9db6ae'), mid = new THREE.Color('#4d6a60'), far = new THREE.Color('#2f463f');
  for (let i = 0; i < mp.count; i++) {
    const r = Math.hypot(mp.getX(i), mp.getY(i)); const u = Math.min(1, (r - 1) / 0.6), v = Math.min(1, Math.max(0, (r - 1.6) / 4));
    tmp.copy(near).lerp(mid, u).lerp(far, v); if (r < 1.06) tmp.lerp(rimC, 1 - (r - 1) / 0.06); mc.push(tmp.r, tmp.g, tmp.b);
  }
  mG.setAttribute('color', new THREE.Float32BufferAttribute(mc, 3));
  const mirror = new THREE.Mesh(mG, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, fog: true }));
  mirror.rotation.x = Math.PI / 2; mirror.position.y = -0.02; mirror.visible = false; S.add(mirror);
  const snell = opt.snell !== false ? snellSurface(world, opt) : null;
  // reeds along the shore, in clumps
  const reedM = flat('#7d8040', { flatShading: false }), headM = flat('#5e4630', { flatShading: false });
  const reedG = new THREE.CylinderGeometry(0.008, 0.014, 1, 16); reedG.translate(0, 0.5, 0);
  const headG = new THREE.CapsuleGeometry(0.02, 0.09, 6, 16);
  for (const [cx, n] of (opt.reeds ?? [[-9, 22], [-6.5, 14], [5.5, 18], [9, 26], [14, 16], [-15, 20]])) {
    for (let k = 0; k < n; k++) {
      const x = cx + (R() - 0.5) * 2.4, z = SHORE - 0.2 - R() * 1.1, h = 0.8 + R() * 0.9;
      const r = new THREE.Mesh(reedG, reedM); r.scale.y = h; r.position.set(x, bedY(z), z); r.rotation.set((R() - 0.5) * 0.25, 0, (R() - 0.5) * 0.25); S.add(r);
      if (R() < 0.35) { const hd = new THREE.Mesh(headG, headM); hd.position.set(x, bedY(z) + h * 0.98, z); hd.rotation.copy(r.rotation); S.add(hd); }
    }
  }
  // jetty: planks on posts from the bank out over the water
  if (opt.jetty !== false) {
    const jx = opt.jettyX ?? -4.5, j = new THREE.Group();
    for (let z = SHORE + 1.2; z > SHORE - 5.5; z -= 0.32) { const p = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.06, 0.28), MAT.wood(Math.round(z * 3) % 2 ? '#9a7650' : '#8f6d49')); p.position.set(jx, BANK_Y + 0.22, z); j.add(p); }
    for (let z = SHORE + 0.6; z > SHORE - 5.6; z -= 1.6) for (const s of [-0.62, 0.62]) {
      const post = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 3.6, 16), MAT.wood('#6e5236')); post.position.set(jx + s, BANK_Y + 0.2 - 1.6, z); j.add(post);
    }
    S.add(shadowed(j));
  }
  // trees and bushes on the bank, kept off the action area
  const keep = opt.keepClear ?? [[-3.5, 3.5]];
  for (let k = 0; k < (opt.trees ?? 46); k++) {
    const x = (R() - 0.5) * 90, z = SHORE + 5 + R() * 40;
    if (keep.some(([a, b]) => x > a - 2 && x < b + 2) && z < SHORE + 12) continue;
    const s = 0.9 + R() * 1.1;
    const tr = R() < 0.4 ? world.conifer(x, z, s * 1.2) : world.roundTree(x, z, s);
    tr.position.y = BANK_Y;
  }
  // far shore across the lake: a dark tree line
  for (let k = 0; k < 40; k++) { const x = (R() - 0.5) * 260, z = -95 - R() * 20; const tr = world.conifer(x, z, 3 + R() * 3); tr.traverse(o => { if (o.isMesh) o.castShadow = false; }); }
  const farBank = new THREE.Mesh(new THREE.PlaneGeometry(700, 60), flat(PALETTE.grass[1], { flatShading: false })); farBank.rotation.x = -Math.PI / 2; farBank.position.set(0, 0.25, -120); S.add(farBank);

  const v = new THREE.Vector3();
  return {
    surface: surf, water, mirror, bed, snell,
    update(t, camera) {
      const P = wG.attributes.position;
      for (let i = 0; i < P.count; i++) {
        const x = wBase[i * 3], z = wBase[i * 3 + 2];
        P.setY(i, 0.018 * Math.sin(x * 0.8 + t * 1.1) + 0.012 * Math.sin(z * 1.3 - t * 0.8 + x * 0.3));
      }
      P.needsUpdate = true; wG.computeVertexNormals();
      if (snell) snell.material.uniforms.t.value = t;
    },
    // call after the camera is placed for this frame (scene.afterCamera): Snell's window around the camera
    afterCamera(camera) {
      camera.getWorldPosition(v);
      const under = v.y < -0.02;
      if (snell) {
        mirror.visible = false;
        surf.visible = farW.visible = !under;
        water.opacity = this.opacity ?? (opt.opacity ?? 0.8);
        snell.capture(under, v, [surf, farW, mirror]);
        return;
      }
      mirror.visible = under;
      water.opacity = under ? 0.12 : this.opacity ?? (opt.opacity ?? 0.8);
      if (under) { const r = Math.max(0.05, -v.y * Math.tan(CRIT)); mirror.scale.set(r, r, 1); mirror.position.set(v.x, -0.03, v.z); }
    },
  };
}

// The water surface seen from below (see the header). Two cube maps are rendered each underwater frame: `above`
// from just over the surface point above the camera, with daylight fog (what the refracted rays see), and `below`
// from the camera's mirror image above the surface (what the totally reflected rays see; a flat mirror). Both are linear HDR, like the main render target.
export function snellSurface(world, opt = {}) {
  const S = world.scene, res = opt.snellRes ?? 512;
  const mk = () => { const rt = new THREE.WebGLCubeRenderTarget(res, { type: THREE.HalfFloatType, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter });
                     const c = new THREE.CubeCamera(0.03, 600, rt); S.add(c); return c; };
  const above = mk(), below = mk();
  const mat = new THREE.ShaderMaterial({
    side: THREE.DoubleSide, fog: false, depthWrite: true,
    uniforms: { envA: { value: above.renderTarget.texture }, envB: { value: below.renderTarget.texture }, t: { value: 0 },
                gainA: { value: opt.snellGain ?? 1.15 }, tintB: { value: new THREE.Color(opt.mirrorTint ?? '#cfe6dc') },
                ripple: { value: opt.ripple ?? 0.012 }, nw: { value: N_WATER } },
    vertexShader: `varying vec3 wp; void main(){ vec4 w = modelMatrix * vec4(position, 1.0); wp = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `
      uniform samplerCube envA, envB; uniform float t, gainA, ripple, nw; uniform vec3 tintB; varying vec3 wp;
      void main(){
        vec3 d = normalize(wp - cameraPosition);
        if (d.y <= 0.0) discard;
        // a calm surface with a faint swell: tilt the normal a little (the rim shimmers, the circle stays sharp)
        vec2 q = wp.xz;
        vec2 g = ripple * vec2(cos(q.x * 3.1 + t * 1.3) + 0.6 * cos(q.x * 1.7 - q.y * 2.3 + t * 0.9),
                               cos(q.y * 2.7 - t * 1.1) + 0.6 * cos(q.y * 1.9 + q.x * 1.2 - t * 0.7));
        vec3 n = normalize(vec3(g.x, -1.0, g.y));                    // the underside faces down
        vec3 tr = refract(d, n, nw);                                  // water -> air
        vec3 rf = reflect(d, n);
        float c = clamp(dot(-d, n), 0.0, 1.0);
        vec3 col;
        if (dot(tr, tr) < 1e-6) {
          col = textureCube(envB, rf).rgb * tintB;          // total internal reflection
        } else {
          float R = 0.02 + 0.98 * pow(1.0 - c, 5.0);
          float ct = clamp(dot(tr, -n), 0.0, 1.0);                   // near the rim the transmitted light fades too
          R = max(R, 1.0 - smoothstep(0.0, 0.25, ct));
          vec3 a = textureCube(envA, tr).rgb * gainA;
          vec3 b = textureCube(envB, rf).rgb * tintB;
          col = mix(a, b, R);
        }
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  const disc = new THREE.Mesh(new THREE.CircleGeometry(260, 96), mat);
  disc.rotation.x = Math.PI / 2; disc.position.y = -0.004; disc.renderOrder = 1; disc.visible = false; disc.frustumCulled = false;
  disc.userData.noVariation = true; disc.userData.noAO = true; S.add(disc);
  const dayFog = new THREE.Fog('#c9cbc8', 60, 260), waterline = new THREE.Plane(new THREE.Vector3(0, -1, 0), 0);
  disc.capture = (under, camPos, hide) => {
    disc.visible = under;
    if (!under) return;
    disc.position.x = camPos.x; disc.position.z = camPos.z;
    const was = hide.map(o => o.visible); for (const o of hide) o.visible = false;
    disc.visible = false;
    const fog = S.fog, sky = world.skyDome.material.uniforms, top = sky.top.value.clone(), bot = sky.bottom.value.clone();
    // above: daylight sky and no underwater haze
    S.fog = dayFog; sky.top.value.set(opt.skyTop ?? '#aeb9c4'); sky.bottom.value.set(opt.skyBottom ?? '#cfd1ce');
    above.position.set(camPos.x, 0.06, camPos.z); above.update(world.renderer, S);
    S.fog = fog; sky.top.value.copy(top); sky.bottom.value.copy(bot);
    // a flat mirror: the reflected world is the underwater world seen from the camera's mirror image above the surface
    const clip = world.renderer.clippingPlanes;
    world.renderer.clippingPlanes = [waterline];                    // only what is under the water is mirrored
    sky.top.value.copy(S.fog.color); sky.bottom.value.copy(S.fog.color);   // gaps at the bed's edge read as deep water
    below.position.set(camPos.x, -camPos.y, camPos.z); below.update(world.renderer, S);
    sky.top.value.copy(top); sky.bottom.value.copy(bot);
    world.renderer.clippingPlanes = clip;
    hide.forEach((o, k) => { o.visible = was[k]; });
    disc.visible = true;
  };
  return disc;
}

// Wooden rowing boat ~3.2 m long, bow toward -z, sitting in the water (waterline y = 0). .seats: [y, z] seat tops.
export function rowboat(color = '#2e8f86') {
  const g = new THREE.Group();
  const L = 3.2, B = 1.25, D = 0.62;
  // hull: the lower half of a stretched sphere, open at the top, pointed toward the bow
  const hg = new THREE.SphereGeometry(1, 64, 32, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2);
  const hp = hg.attributes.position;
  for (let i = 0; i < hp.count; i++) {
    let x = hp.getX(i), y = hp.getY(i), z = hp.getZ(i);
    const bow = z < 0 ? 1 - 0.55 * Math.pow(-z, 2.2) : 1 - 0.18 * Math.pow(z, 3);    // narrow toward the bow
    hp.setXYZ(i, x * B / 2 * bow, y * D, z * L / 2);
  }
  hg.computeVertexNormals();
  const outM = std(color, { roughness: 0.55, side: THREE.FrontSide }), inM = MAT.wood('#a27c55');
  inM.side = THREE.BackSide;
  const hull = new THREE.Mesh(hg, outM); g.add(hull);
  const inner = new THREE.Mesh(hg, inM); inner.scale.set(0.97, 0.97, 0.985); g.add(inner);
  // gunwale rim
  const rimPts = []; for (let k = 0; k <= 96; k++) { const a = k / 96 * Math.PI * 2, z = Math.cos(a), bow = z < 0 ? 1 - 0.55 * Math.pow(-z, 2.2) : 1 - 0.18 * Math.pow(z, 3); rimPts.push(new THREE.Vector3(Math.sin(a) * B / 2 * bow, 0.0, z * L / 2)); }
  const rim = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(rimPts, true), 192, 0.035, 12, true), MAT.wood('#7a5a3a')); g.add(rim);
  // keep the lake out of the boat: an invisible lid over the opening writes depth just before the water is drawn
  // (transparent queue, lower renderOrder), so the water plane inside the hull fails the depth test while the floor,
  // seats, people and props already drawn below it stay visible
  const lidShape = new THREE.Shape(rimPts.map(p => new THREE.Vector2(p.x, p.z)));
  const lidG = new THREE.ShapeGeometry(lidShape, 24); lidG.rotateX(Math.PI / 2);
  const lid = new THREE.Mesh(lidG, new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: true, transparent: true, side: THREE.DoubleSide }));
  lid.renderOrder = 1; lid.position.y = 0.0; lid.userData.noAO = true; lid.userData.noVariation = true; lid.castShadow = false; lid.name = 'water_lid'; g.add(lid);
  // seats (thwarts) and a floor board
  const seatM = MAT.wood('#8f6d49'), seats = [];
  for (const z of [-0.55, 0.55]) {
    const w = B * 0.86 * (z < 0 ? 0.92 : 0.98);
    const s = new THREE.Mesh(new THREE.BoxGeometry(w, 0.05, 0.28), seatM); s.position.set(0, -0.12, z); g.add(s); seats.push([-0.12 + 0.025, z]);
  }
  const floor = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.03, 2.2), seatM); floor.position.set(0, -0.5, 0.05); g.add(floor);
  // oars resting along the sides
  for (const s of [-1, 1]) {
    const oar = new THREE.Group();
    const sh = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 2.3, 16), MAT.wood('#b08a5c')); sh.rotation.x = Math.PI / 2; oar.add(sh);
    const bl = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.015, 0.45), MAT.wood('#b08a5c')); bl.position.z = -1.25; oar.add(bl);
    oar.position.set(s * (B / 2 - 0.08), 0.03, 0.1); oar.rotation.y = s * 0.05; g.add(oar);
  }
  g.position.y = 0.12;            // freeboard: the rim sits 12 cm above the water
  g.userData = { seats, floorY: -0.5 + 0.015, L, B };
  shadowed(g); lid.castShadow = lid.receiveShadow = false;
  return g;
}

// Trout- or gar-like fish, `len` metres long, facing +x. fish.swim(t, effort) bends the body (a travelling wave
// that grows toward the tail). Every part's vertices are kept in fish-local coordinates so fins bend with it.
export function fish(kind = 'trout', len = 0.35, opt = {}) {
  const g = new THREE.Group(), parts = [];
  const gar = kind === 'gar';
  const top = new THREE.Color(opt.top ?? (gar ? '#4f5233' : '#4d5a3a')), side = new THREE.Color(opt.side ?? (gar ? '#7a7448' : '#9c9a6a')),
        belly = new THREE.Color(opt.belly ?? (gar ? '#cdbf96' : '#ddd4b6')), stripe = new THREE.Color('#c98a7a'), spot = new THREE.Color('#2a2c1e');
  // body: lathe profile along the length (u = 0 tail end ... 1 nose), radius in body lengths
  const prof = [];
  const N = 40;
  for (let k = 0; k <= N; k++) {
    const u = k / N;
    let r;
    if (gar) {                 // alligator gar: a long round torpedo, a short head, then a long broad flat snout
      const body = 0.068 * THREE.MathUtils.smoothstep(u, 0.0, 0.3) * 0.62 + 0.068 * 0.38;
      r = u < 0.66 ? body * (u < 0.08 ? 0.55 + 5.6 * u : 1) : u < 0.78 ? 0.068 - (u - 0.66) / 0.12 * 0.03 : 0.038 - (u - 0.78) / 0.22 * 0.022;
      if (u > 0.985) r *= Math.sqrt(Math.max(0, (1 - u) / 0.015));
    }
    else r = 0.115 * Math.pow(Math.sin(Math.PI * (0.06 + 0.88 * u)), 0.8) * (u < 0.15 ? 0.5 + 3.3 * u : 1);
    prof.push(new THREE.Vector2(Math.max(0.002, r), u));
  }
  const bodyG = new THREE.LatheGeometry(prof, 48);
  bodyG.rotateZ(-Math.PI / 2);                                   // lathe axis y -> x (nose at +x)
  bodyG.translate(-0.5, 0, 0);
  bodyG.scale(len, len, len * (gar ? 0.85 : 0.62));
  if (gar) {                                                    // the snout is broad and flat, like an alligator's
    const P = bodyG.attributes.position;
    for (let i = 0; i < P.count; i++) {
      const x = P.getX(i) / len, f = THREE.MathUtils.smoothstep(x, 0.22, 0.32);
      if (x > 0.22) { P.setY(i, P.getY(i) * (1 - 0.5 * f)); P.setZ(i, P.getZ(i) * (1 + 0.3 * f)); }
    }
  }
  const R = seeded(gar ? 7 : 3);
  const spots = Array.from({ length: gar ? 70 : 46 }, () => [R() - 0.5, R() * 2 - 0.3, 0.008 + R() * 0.012]);
  const colour = G => {
    const P = G.attributes.position, C = [], c = new THREE.Color();
    for (let i = 0; i < P.count; i++) {
      const x = P.getX(i) / len, y = P.getY(i) / len, z = P.getZ(i) / len;
      const h = y / 0.12;                                        // -1 belly .. +1 back
      c.copy(belly).lerp(side, THREE.MathUtils.smoothstep(h, -0.7, 0.1)).lerp(top, THREE.MathUtils.smoothstep(h, 0.15, 0.8));
      if (!gar && Math.abs(h - 0.05) < 0.16 && x > -0.4 && x < 0.3) c.lerp(stripe, 0.45);
      for (const [sx, sy, sr] of spots) if (h > -0.2 && Math.hypot(x - sx, (h - sy) * 0.08) < sr * (gar ? 1.6 : 1)) c.lerp(spot, 0.75);
      C.push(c.r, c.g, c.b);
    }
    G.setAttribute('color', new THREE.Float32BufferAttribute(C, 3));
  };
  colour(bodyG); bodyG.computeVertexNormals();
  const skin = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.42, metalness: 0.08 });
  const finM = new THREE.MeshStandardMaterial({ color: gar ? '#4f4a2c' : '#5f5c3c', roughness: 0.6, side: THREE.DoubleSide });
  const add = (geo, m) => { const mesh = new THREE.Mesh(geo, m); g.add(mesh); parts.push(mesh); return mesh; };
  add(bodyG, skin);
  // fins: thin shapes in the fish's own frame
  const finShape = (pts) => { const s = new THREE.Shape(); s.moveTo(...pts[0]); for (const p of pts.slice(1)) s.lineTo(...p); return new THREE.ShapeGeometry(s, 12); };
  const tailG = finShape(gar ? [[0, 0], [-0.1, 0.07], [-0.13, 0.05], [-0.1, 0], [-0.13, -0.04], [-0.1, -0.05]] : [[0, 0], [-0.13, 0.11], [-0.11, 0.0], [-0.13, -0.11]]);
  tailG.scale(len, len, 1); tailG.translate(-0.48 * len, 0, 0); add(tailG, finM);
  const dors = finShape(gar ? [[0, 0], [-0.07, 0.06], [-0.1, 0]] : [[0, 0], [-0.04, 0.09], [-0.13, 0.05], [-0.13, 0]]);
  dors.scale(len, len, 1); dors.translate((gar ? -0.3 : 0.05) * len, (gar ? 0.055 : 0.095) * len, 0); add(dors, finM);
  const anal = finShape([[0, 0], [-0.06, -0.05], [-0.09, 0]]); anal.scale(len, len, 1); anal.translate((gar ? -0.3 : -0.22) * len, -(gar ? 0.05 : 0.07) * len, 0); add(anal, finM);
  for (const s of [-1, 1]) {
    const pf = finShape([[0, 0], [-0.09, -0.05], [-0.06, 0.01]]); pf.scale(len, len, 1); pf.rotateX(s * 0.9); pf.translate((gar ? 0.1 : 0.22) * len, -0.045 * len, s * 0.04 * len); add(pf, finM);
  }
  // eyes
  const eyeW = new THREE.MeshStandardMaterial({ color: gar ? '#b8913f' : '#e9dfb8', roughness: 0.25 }), eyeB = new THREE.MeshStandardMaterial({ color: '#0d0d0d', roughness: 0.1, metalness: 0.2 });
  const ex = gar ? 0.2 : 0.36, er = (gar ? 0.011 : 0.02) * len;
  for (const s of [-1, 1]) {
    const e = new THREE.SphereGeometry(er, 48, 36); e.translate(ex * len, 0.025 * len, s * (gar ? 0.045 : 0.05) * len); add(e, eyeW);
    const p = new THREE.SphereGeometry(er * 0.6, 32, 24); p.translate(ex * len + er * 0.25, 0.025 * len, s * ((gar ? 0.045 : 0.05) * len + er * 0.6)); add(p, eyeB);
  }
  if (gar) {                                                    // a row of small teeth along the long snout
    const toothM = std('#eee6cf', { roughness: 0.4 });
    for (let k = 0; k < 14; k++) for (const s of [-1, 1]) {
      const tg = new THREE.ConeGeometry(0.0035 * len, 0.012 * len, 12); tg.rotateX(Math.PI);
      tg.translate((0.26 + k * 0.016) * len, -0.004 * len, s * (0.021 - k * 0.0011) * len); add(tg, toothM);
    }
  }
  for (const m of parts) { m.castShadow = true; m.receiveShadow = true; m.userData.base = Float32Array.from(m.geometry.attributes.position.array); }
  // swim: lateral wave z += A(x) sin(k x - w t), A grows toward the tail; effort 0..1 sets amplitude and speed
  g.swim = (t, effort = 0.5, turn = 0) => {
    const A = len * (0.03 + 0.09 * effort), w = 5 + 9 * effort, k = 2 * Math.PI / (len * 1.1);
    for (const m of parts) {
      const P = m.geometry.attributes.position, B = m.userData.base;
      for (let i = 0; i < P.count; i++) {
        const x = B[i * 3], u = Math.min(1, Math.max(0, (0.32 * len - x) / (0.82 * len)));
        P.setZ(i, B[i * 3 + 2] + A * u * u * Math.sin(k * x - w * t) + turn * len * 0.25 * u * u);
      }
      P.needsUpdate = true;
    }
  };
  g.len = len;
  return g;
}

// Fishing rod: butt at the group origin, pointing along +y in its own frame; .set(bend, lineEnd) bends it toward a
// world point and runs the line from the tip to that point with a little sag. Call after the scene's matrices update.
export function rod(scene, len = 2.4) {
  const g = new THREE.Group();
  const blank = std('#2b3038', { roughness: 0.35, metalness: 0.3 }), cork = std('#b58a5a', { roughness: 0.9 });
  const grip = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.014, 0.34, 24), cork); grip.position.y = 0.17; g.add(grip);
  const reel = new THREE.Group(); reel.position.set(0, 0.36, 0.035); g.add(reel);
  const spool = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.03, 32), std('#b9bdc2', { metalness: 0.6, roughness: 0.35 })); spool.rotation.x = Math.PI / 2; reel.add(spool);
  const side = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.01, 32), std('#c92a2e', { roughness: 0.5 })); side.rotation.x = Math.PI / 2; side.position.z = 0.02; reel.add(side);
  const handle = new THREE.Mesh(new THREE.BoxGeometry(0.008, 0.05, 0.008), std('#2b3038')); handle.position.set(0.025, 0.0, 0.03); reel.add(handle);
  const knob = new THREE.Mesh(new THREE.SphereGeometry(0.009, 24, 16), std('#e6e3dc')); knob.position.set(0.025, 0.026, 0.04); reel.add(knob);
  const foot = new THREE.Mesh(new THREE.BoxGeometry(0.01, 0.06, 0.03), std('#2b3038')); foot.position.set(0, 0.36, 0.015); g.add(foot);
  let blankMesh = null, lineMesh = null;
  const lineM = new THREE.MeshBasicMaterial({ color: '#e8e6df', transparent: true, opacity: 0.85 });
  scene.add(g);
  const tipW = new THREE.Vector3(), tmp = new THREE.Vector3();
  g.userData = { reel, spool };
  g.set = (bend = 0, lineEnd = null, sag = 0.08) => {
    // blank: a curve in the rod's own (x, y) plane, bending toward local -z by `bend` (0 straight .. 1 strong)
    const pts = [];
    for (let k = 0; k <= 24; k++) { const u = k / 24; pts.push(new THREE.Vector3(0, 0.3 + (len - 0.3) * u * (1 - 0.18 * bend * u * u), -bend * 0.9 * u * u * u)); }
    const curve = new THREE.CatmullRomCurve3(pts);
    if (blankMesh) { blankMesh.geometry.dispose(); g.remove(blankMesh); }
    const tube = new THREE.TubeGeometry(curve, 48, 0.008, 16, false);
    // taper: scale ring radius along the tube
    const P = tube.attributes.position, nRing = 17;
    for (let i = 0; i < P.count; i++) {
      const seg = Math.floor(i / nRing) / 48, c = curve.getPointAt(Math.min(1, seg));
      tmp.set(P.getX(i), P.getY(i), P.getZ(i)).sub(c).multiplyScalar(1.3 - 1.05 * seg); P.setXYZ(i, c.x + tmp.x, c.y + tmp.y, c.z + tmp.z);
    }
    blankMesh = new THREE.Mesh(tube, blank); blankMesh.castShadow = true; g.add(blankMesh);
    g.updateMatrixWorld(true);
    tipW.copy(pts[pts.length - 1]).applyMatrix4(g.matrixWorld);
    if (lineMesh) { lineMesh.geometry.dispose(); scene.remove(lineMesh); lineMesh = null; }
    if (lineEnd) {
      const e = new THREE.Vector3(...lineEnd), lp = [];
      for (let k = 0; k <= 32; k++) { const u = k / 32; lp.push(tipW.clone().lerp(e, u).add(new THREE.Vector3(0, -sag * 4 * u * (1 - u), 0))); }
      lineMesh = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(lp), 64, 0.0035, 8, false), lineM); scene.add(lineMesh);
    }
    return tipW.clone();
  };
  return g;
}

// Plastic tackle box with a handle, ~0.36 m long
export function tackleBox(color = '#2e8f86') {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.14, 0.2, 2, 2, 2), std(color, { roughness: 0.45 })); body.position.y = 0.07; g.add(body);
  const lid = new THREE.Mesh(new THREE.BoxGeometry(0.37, 0.04, 0.21), std('#2a6f68', { roughness: 0.45 })); lid.position.y = 0.16; g.add(lid);
  const latch = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.04, 0.012), std('#e2c45a')); latch.position.set(0, 0.13, 0.106); g.add(latch);
  const h = new THREE.Mesh(new THREE.TorusGeometry(0.06, 0.009, 12, 32, Math.PI), std('#1d1d20')); h.position.y = 0.18; g.add(h);
  return shadowed(g);
}

// Landing net: hoop on a short handle, net bag of thin rings; `r` hoop radius
export function net(r = 0.25) {
  const g = new THREE.Group(), frame = std('#2b3038', { metalness: 0.4, roughness: 0.4 });
  const hoop = new THREE.Mesh(new THREE.TorusGeometry(r, 0.008, 12, 48), frame); hoop.rotation.x = Math.PI / 2; g.add(hoop);
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.8, 16), MAT.wood('#8a6342')); handle.rotation.z = Math.PI / 2; handle.position.x = -r - 0.4; g.add(handle);
  const bagM = new THREE.MeshStandardMaterial({ color: '#d9d2b4', roughness: 0.9, transparent: true, opacity: 0.55, side: THREE.DoubleSide, wireframe: true });
  const bag = new THREE.Mesh(new THREE.SphereGeometry(r, 24, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), bagM); bag.scale.y = 1.3; g.add(bag);
  return shadowed(g);
}

// Look v3 (quality overhaul, 2026-11-21): the finishing stack every scene gets for free.
//
// What it adds on top of the blueprint renderer (World in world.js):
//   1. Sky-matched image-based lighting: an environment map built from the current lighting preset's sky,
//      horizon, ground and sun, so materials pick up soft fill and believable reflections outdoors and
//      indoors (the old RoomEnvironment was an indoor studio and was switched off for most presets).
//   2. Ambient occlusion (GTAO, half resolution): objects sit in the world instead of floating on it,
//      contact shadows under feet, props and furniture, darker creases on characters.
//   3. Depth of field with auto-focus on what the camera looks at: the "filmed miniature" depth cue.
//      Strength follows real optics (inverse-distance), so close-ups get soft backgrounds and wide shots stay
//      sharp.
//   4. A display-space grade: gentle filmic contrast, warm highlights / cool shadows, a little saturation,
//      local-contrast sharpening (survives YouTube compression), vignette and a very fine grain that is
//      deterministic per frame.
//
// Plan switches (all optional): plan.look = 'v3' (default) | 'legacy'; plan.dof = false | number (strength,
// default 1); plan.ao = false | number; plan.grade = false | {...}; per shot: shot.dof, shot.focus ([x,y,z]
// or metres). Scene modules can set scene.focus(i, t, shot) -> THREE.Vector3 to pick the focus target.
import * as THREE from 'three';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

// ---------------------------------------------------------------- sky-matched environment
export function skyEnvironment(renderer, L, sunDir) {
  const scene = new THREE.Scene();
  const g = new THREE.SphereGeometry(10, 64, 32);
  const m = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false,
    uniforms: {
      top: { value: new THREE.Color(L.skyTop) }, horizon: { value: new THREE.Color(L.sky) },
      ground: { value: new THREE.Color(L.hemiGround) }, sun: { value: new THREE.Color(L.sun) },
      sunDir: { value: sunDir.clone().normalize() }, sunI: { value: Math.min(6, L.sunI * 1.6) },
    },
    vertexShader: 'varying vec3 vd; void main(){ vd = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
    fragmentShader: `uniform vec3 top, horizon, ground, sun, sunDir; uniform float sunI; varying vec3 vd;
      void main(){
        float h = vd.y;
        vec3 sky = mix(horizon, top, smoothstep(0.0, 0.65, h));
        vec3 gnd = mix(horizon * 0.85, ground, smoothstep(0.0, -0.35, h));
        vec3 c = h > 0.0 ? sky : gnd;
        float s = max(dot(normalize(vd), sunDir), 0.0);
        c += sun * (pow(s, 600.0) * sunI * 8.0 + pow(s, 12.0) * 0.35);   // sun disc + glow, for highlights
        gl_FragColor = vec4(c, 1.0);
      }`,
  });
  scene.add(new THREE.Mesh(g, m));
  const pm = new THREE.PMREMGenerator(renderer);
  const tex = pm.fromScene(scene, 0.0, 0.1, 100).texture;
  pm.dispose(); g.dispose(); m.dispose();
  return tex;
}

// ---------------------------------------------------------------- finish pass (linear HDR): AO + DOF
const FinishShader = {
  uniforms: {
    tDiffuse: { value: null }, tAO: { value: null }, tDepth: { value: null },
    res: { value: new THREE.Vector2(1080, 1920) }, near: { value: 0.05 }, far: { value: 400 },
    aoStrength: { value: 0.85 }, aoFadeNear: { value: 18 }, aoFadeFar: { value: 70 },
    focus: { value: 5 }, cocScale: { value: 0 }, maxCoc: { value: 11 },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
  fragmentShader: `
    uniform sampler2D tDiffuse, tAO, tDepth; uniform vec2 res; uniform float near, far, aoStrength, aoFadeNear, aoFadeFar,
      focus, cocScale, maxCoc; varying vec2 vUv;
    float lin(float z){ return (near * far) / (far - z * (far - near)); }          // perspective depth -> metres
    float depthAt(vec2 uv){ return lin(texture2D(tDepth, uv).x); }
    float coc(float d){ return clamp(cocScale * abs(1.0 / focus - 1.0 / d), 0.0, maxCoc); }
    vec3 shade(vec2 uv, float d){
      float ao = pow(texture2D(tAO, uv).r, 1.7);
      ao = mix(ao, 1.0, smoothstep(aoFadeNear, aoFadeFar, d));                  // no AO in the haze
      return texture2D(tDiffuse, uv).rgb * mix(1.0, ao, aoStrength);
    }
    void main(){
      float d0 = depthAt(vUv);
      vec3 col = shade(vUv, d0);
      float c0 = coc(d0);
      if (cocScale > 0.0) {
        // single-pass scatter-as-gather bokeh (golden-angle spiral); background taps may not bleed over a
        // sharper foreground (clamped to 2x the centre's circle)
        // the gather radius follows this pixel's own blur (+ a small margin), so in-focus pixels cost almost
        // nothing; the trade-off is that a blurred foreground edge bleeds only ~3 px over a sharp subject
        vec3 acc = col; float tot = 1.0; float r = 1.2; float ang = 0.0;
        float rmax = min(maxCoc, max(c0 + 1.0, 3.0));
        for (int k = 0; k < 32; k++) {
          if (r >= rmax) break;
          vec2 tc = vUv + vec2(cos(ang), sin(ang)) * r / res;
          float d = depthAt(tc); float cs = coc(d);
          if (d > d0) cs = min(cs, c0 * 2.0);
          float m = smoothstep(r - 0.5, r + 0.5, cs);
          acc += mix(acc / tot, shade(tc, d), m); tot += 1.0;
          ang += 2.39996; r += 2.2 / r;
        }
        col = acc / tot;
      }
      gl_FragColor = vec4(col, 1.0);
    }`,
};

// ---------------------------------------------------------------- grade pass (display space, after tone mapping)
const GradeShader = {
  uniforms: {
    tDiffuse: { value: null }, res: { value: new THREE.Vector2(1080, 1920) }, frame: { value: 0 },
    contrast: { value: 0.10 }, saturation: { value: 1.06 }, warm: { value: new THREE.Vector3(1.02, 1.0, 0.965) },
    cool: { value: new THREE.Vector3(0.975, 0.995, 1.03) }, vignette: { value: 0.22 }, grain: { value: 0.012 },
    sharpen: { value: 0.32 }, lift: { value: 0.055 },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform vec2 res; uniform float frame, contrast, saturation, vignette, grain, sharpen, lift;
    uniform vec3 warm, cool; varying vec2 vUv;
    float hash(vec2 p){ p = fract(p * vec2(443.897, 441.423)); p += dot(p, p.yx + 19.19); return fract((p.x + p.y) * p.x); }
    void main(){
      vec2 px = 1.0 / res;
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      // local-contrast sharpening (5-tap unsharp mask on luma-ish signal, clamped so edges don't ring)
      vec3 blur = (texture2D(tDiffuse, vUv + vec2(px.x, 0.0)).rgb + texture2D(tDiffuse, vUv - vec2(px.x, 0.0)).rgb +
                   texture2D(tDiffuse, vUv + vec2(0.0, px.y)).rgb + texture2D(tDiffuse, vUv - vec2(0.0, px.y)).rgb) * 0.25;
      c += clamp((c - blur) * sharpen, -0.06, 0.06);
      // gentle filmic S-curve around mid grey
      c = clamp(c, 0.0, 1.0);
      c = mix(c, c * c * (3.0 - 2.0 * c), contrast);
      // split tone: warm highlights, cool shadows
      float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
      c *= mix(cool, warm, smoothstep(0.15, 0.75, l));
      // saturation (never above the blueprint's muted look: gentle)
      l = dot(c, vec3(0.2126, 0.7152, 0.0722));
      c = mix(vec3(l), c, saturation);
      // vignette, elliptical for 9:16
      vec2 q = (vUv - 0.5) * vec2(1.0, 0.75);
      c *= 1.0 - vignette * smoothstep(0.18, 0.62, length(q));
      // fine luminance grain, fixed per frame (deterministic renders), weaker in the highlights
      float n = hash(vUv * res + frame * 17.0) - 0.5;
      c += n * grain * (1.0 - l * 0.6);
      // black lift: the blueprint never shows pure black (and QA blocks solid black regions), so the darkest
      // tone is a deep grey (~14/255) even under vignette, AO and contrast
      c = lift + clamp(c, 0.0, 1.0) * (1.0 - lift);
      gl_FragColor = vec4(c, 1.0);
    }`,
};

export class Look {
  constructor(world, opts = {}) {
    this.world = world; this.opts = opts;
    const { W, H } = world, ss = opts.supersample ?? 1;
    const composer = world.composer;
    // GTAO at half resolution (AO is low-frequency; this keeps the cloud render cost sane)
    const aoScale = 0.5;
    this.gtao = new GTAOPass(world.scene, world.camera, W * ss * aoScale, H * ss * aoScale,
      undefined, { radius: 0.9, distanceExponent: 1.6, thickness: 1.6, scale: 1.0, samples: 12, distanceFallOff: 1.0 },
      { lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 9, rings: 2, samples: 16 });
    const setAO = this.gtao.setSize.bind(this.gtao);
    this.gtao.setSize = (w, h) => setAO(Math.round(w * aoScale), Math.round(h * aoScale));
    this.gtao.output = GTAOPass.OUTPUT.Off; this.gtao.needsSwap = false;
    // the depth/normal pre-pass must only see solid surfaces: transparent water, glass, glows, halos and the
    // sky dome would otherwise put AO rings on water and make the depth of field focus on a see-through sheet
    const g = this.gtao;
    g.overrideVisibility = function () {
      const cache = this._visibilityCache;
      this.scene.traverse(o => {
        cache.set(o, o.visible);
        if (o.isPoints || o.isLine || o.isSprite) { o.visible = false; return; }
        if (o.isMesh) {
          const ms = Array.isArray(o.material) ? o.material : [o.material];
          if (ms.some(m => m && (m.transparent || m.depthWrite === false || m.blending === THREE.AdditiveBlending))) o.visible = false;
        }
      });
    };
    if (opts.aoDebug) { this.gtao.output = GTAOPass.OUTPUT.Denoise; this.gtao.needsSwap = true; }
    this.finish = new ShaderPass(FinishShader);
    this.finish.uniforms.res.value.set(W * ss, H * ss);
    this.finish.uniforms.tAO.value = this.gtao.pdRenderTarget.texture;
    this.finish.uniforms.tDepth.value = this.gtao.depthTexture;
    this.grade = new ShaderPass(GradeShader);
    this.grade.uniforms.res.value.set(W * ss, H * ss);
    // insert after the RenderPass (index 0): [render, gtao, finish, bloom, output, grade]
    composer.insertPass(this.gtao, 1);
    composer.insertPass(this.finish, 2);
    composer.addPass(this.grade);
    this.aoStrength = opts.ao === false ? 0 : (typeof opts.ao === 'number' ? opts.ao : 1.0);
    this.dof = opts.dof === false ? 0 : (typeof opts.dof === 'number' ? opts.dof : 1);
    if (opts.grade && typeof opts.grade === 'object') {
      for (const [k, v] of Object.entries(opts.grade)) if (this.grade.uniforms[k] && typeof v === 'number') this.grade.uniforms[k].value = v;
    }
    if (opts.grade === false) this.grade.enabled = false;
    if (!this.aoStrength) { this.gtao.enabled = false; }
    this.ss = ss;
  }

  // called once per frame before render. focusDist in metres; shotDof scales the strength for this shot.
  update(frame, focusDist, shotDof = 1) {
    const cam = this.world.camera, u = this.finish.uniforms;
    u.near.value = cam.near; u.far.value = cam.far;
    u.aoStrength.value = this.gtao.enabled ? this.aoStrength : 0;
    if (!this.gtao.enabled) u.tAO.value = WHITE;
    const f = this.world.scene.fog;
    if (f) { u.aoFadeNear.value = f.near * 0.6; u.aoFadeFar.value = Math.max(f.near * 0.6 + 1, f.far * 0.5); }
    // circle of confusion in px ~ K * |1/focus - 1/d|. K scales with focal length (narrow fov = longer lens)
    // and frame height; tuned so a 2 m close-up blurs a wall 6 m behind by ~7 px at 1080x1920.
    const lens = 1 / Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2);   // 38 deg -> 2.9
    const strength = this.dof * shotDof;
    u.focus.value = Math.max(0.2, focusDist || 5);
    u.cocScale.value = strength > 0 && this.gtao.enabled ? 7.0 * lens * strength * (this.world.H * this.ss / 1920) : 0;
    u.maxCoc.value = 11 * (this.world.H * this.ss / 1920);
    this.grade.uniforms.frame.value = frame % 997;
  }
}

// Breaks up flat CG fills: large matte surfaces (walls, floors, lawns, road, hills) get a gentle world-space
// colour variation at three scales (about 3 m, 60 cm and 15 cm), and textured ones a weaker version that hides
// tiling. Characters (skinned meshes), small props, emissive and transparent materials are left alone.
// A material can opt out with material.userData.noVariation = true.
export function enrichMaterials(scene) {
  const done = new Set();
  scene.traverse(o => {
    if (!o.isMesh || o.isSkinnedMesh || !o.geometry) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    if (!o.geometry.boundingSphere) o.geometry.computeBoundingSphere();
    const r = o.geometry.boundingSphere.radius * Math.max(o.scale.x, o.scale.y, o.scale.z);
    if (r < 0.9) return;
    for (const m of mats) {
      if (!m || done.has(m) || !m.isMeshStandardMaterial || m.transparent || m.userData.noVariation) continue;
      if (m.emissiveIntensity > 0.2 && m.emissive && m.emissive.getHex() !== 0) continue;
      if ((m.metalness ?? 0) > 0.5) continue;
      done.add(m);
      const amp = m.map ? 0.06 : 0.10;
      const prev = m.onBeforeCompile;
      m.onBeforeCompile = (sh, rr) => {
        if (prev) prev(sh, rr);
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vVarW;')
          .replace('#include <project_vertex>', `#include <project_vertex>
            vec4 vw = vec4(transformed, 1.0);
            #ifdef USE_INSTANCING
              vw = instanceMatrix * vw;
            #endif
            vVarW = (modelMatrix * vw).xyz;`);
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', `#include <common>
          varying vec3 vVarW;
          float vh3(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
          float vn3(vec3 p){ vec3 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
            return mix(mix(mix(vh3(i), vh3(i+vec3(1,0,0)), f.x), mix(vh3(i+vec3(0,1,0)), vh3(i+vec3(1,1,0)), f.x), f.y),
                       mix(mix(vh3(i+vec3(0,0,1)), vh3(i+vec3(1,0,1)), f.x), mix(vh3(i+vec3(0,1,1)), vh3(i+vec3(1,1,1)), f.x), f.y), f.z); }`)
          .replace('#include <map_fragment>', `#include <map_fragment>
            float vv = vn3(vVarW * 0.33) * 0.55 + vn3(vVarW * 1.7) * 0.3 + vn3(vVarW * 6.5) * 0.15;
            diffuseColor.rgb *= 1.0 + ${amp.toFixed(3)} * (vv - 0.5) * 2.0;`);
      };
      m.customProgramCacheKey = () => 'var' + amp + (prev ? prev.toString().length : 0);
      m.needsUpdate = true;
    }
  });
}

const WHITE = (() => { const t = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1); t.needsUpdate = true; return t; })();

// ---------------------------------------------------------------- ground cover
// Outdoor scenes looked like a flat painted floor. groundCover scatters instanced grass tufts, a few wild flowers
// and pebbles on the meshes made by world.ground(), concentrated around where the shots look (plan.shots), so
// the near ground has real texture and parallax and objects stand *in* grass. Tufts sway gently in the wind.
// It never places anything on top of other objects (roads, paths, floors, decks, slabs): any mesh standing
// above the ground at a point blocks that point. Deterministic (seeded). plan.ground_cover = false turns it off,
// or pass an object: { density: 1, radius: 14, height: 1, flowers: true }.
export function groundCover(world, plan, opts = {}) {
  const grounds = world.groundMeshes ?? [];
  if (!grounds.length) return null;
  const S = world.scene, R = seededRng(plan.seed ?? 7);
  const density = opts.density ?? 1, radius = opts.radius ?? 14, hScale = opts.height ?? 1;
  S.updateMatrixWorld(true);
  // centres: where the shots aim (deduplicated), else the origin
  const centres = [];
  for (const s of plan.shots ?? []) {
    const l = s.type === 'keys' ? (s.look?.[Math.floor((s.look.length - 1) / 2)]) : (s.look0 ?? s.center);
    if (!l) continue;
    if (!centres.some(c => Math.hypot(c[0] - l[0], c[2] - l[2]) < 4)) centres.push(l);
  }
  if (!centres.length) centres.push([0, 0, 0]);
  // ground footprints and blockers (anything standing above the ground; giant meshes like the sky are ignored)
  const gBoxes = grounds.map(g => ({ box: new THREE.Box3().setFromObject(g), y: new THREE.Box3().setFromObject(g).max.y }));
  const blockers = [];
  const gset = new Set(grounds);
  S.traverse(o => {
    if (!o.isMesh || gset.has(o) || o === world.skyDome || !o.visible) return;
    const b = new THREE.Box3().setFromObject(o);
    if (b.isEmpty()) return;
    const sx = b.max.x - b.min.x, sz = b.max.z - b.min.z;
    if (sx > 400 || sz > 400) return;
    blockers.push(b);
  });
  const blocked = (x, z, y) => blockers.some(b => b.max.y > y + 0.004 && b.min.y < y + 2.5 && x > b.min.x - 0.02 && x < b.max.x + 0.02 && z > b.min.z - 0.02 && z < b.max.z + 0.02);
  const groundY = (x, z) => { for (const g of gBoxes) if (x > g.box.min.x && x < g.box.max.x && z > g.box.min.z && z < g.box.max.z) return g.y; return null; };

  // one tuft: 7 tapered, bent blades fanned around the centre (14 triangles)
  const blades = 7, pos = [], nor = [];
  for (let b = 0; b < blades; b++) {
    const a = (b / blades) * Math.PI * 2 + 0.4 * Math.sin(b * 3.1), lean = 0.25 + 0.2 * ((b * 7) % 3) / 2;
    const h = 0.75 + 0.5 * ((b * 5) % 4) / 3, w = 0.035;
    const dx = Math.cos(a), dz = Math.sin(a), px = -dz * w, pz = dx * w;
    const base = [dx * 0.03, 0, dz * 0.03], mid = [dx * (0.03 + lean * 0.45 * h), 0.55 * h, dz * (0.03 + lean * 0.45 * h)];
    const tip = [dx * (0.03 + lean * h), h, dz * (0.03 + lean * h)];
    const v = [[base[0] - px, base[1], base[2] - pz], [base[0] + px, base[1], base[2] + pz],
               [mid[0] - px * 0.6, mid[1], mid[2] - pz * 0.6], [mid[0] + px * 0.6, mid[1], mid[2] + pz * 0.6], tip];
    for (const t of [[0, 1, 3], [0, 3, 2], [2, 3, 4]]) for (const k of t) { pos.push(...v[k]); nor.push(dx * 0.3, 0.9, dz * 0.3); }
  }
  const tg = new THREE.BufferGeometry();
  tg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  tg.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  const tm = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.92, side: THREE.DoubleSide });
  tm.userData.noVariation = true;
  const uTime = { value: 0 };
  tm.onBeforeCompile = sh => {
    sh.uniforms.uTime = uTime;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform float uTime;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vec3 ip = vec3(instanceMatrix[3][0], 0.0, instanceMatrix[3][2]);
        float sway = sin(uTime * 1.3 + ip.x * 0.7 + ip.z * 0.5) * 0.5 + sin(uTime * 2.1 + ip.x * 1.9) * 0.25;
        transformed.x += sway * 0.12 * transformed.y * transformed.y;
        transformed.z += sway * 0.05 * transformed.y * transformed.y;`);
  };
  tm.customProgramCacheKey = () => 'tuft-v1';
  const target = Math.round(16000 * density);
  const per = Math.ceil(target / centres.length);
  const mats = [], cols = [];
  const grassCols = ['#6d7a33', '#7c8a3c', '#5f6b2b', '#8b9550', '#717d36', '#9aa05a'].map(c => new THREE.Color(c));
  const flowerCols = ['#efe8d2', '#e9cf63', '#b9a5d6', '#e8e4f0'].map(c => new THREE.Color(c));
  const flowers = [], pebbles = [];
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(), p3 = new THREE.Vector3();
  for (const c of centres) {
    for (let k = 0; k < per * 3 && mats.length < target; k++) {
      const a = R() * Math.PI * 2, r = radius * Math.pow(R(), 0.8);
      const x = c[0] + Math.cos(a) * r, z = c[2] + Math.sin(a) * r;
      const y = groundY(x, z); if (y === null || blocked(x, z, y)) continue;
      const s = (0.07 + R() * 0.09) * hScale;
      e.set((R() - 0.5) * 0.25, R() * 6.28, (R() - 0.5) * 0.25); q.setFromEuler(e);
      sc.set(s * (0.8 + R() * 0.5), s, s * (0.8 + R() * 0.5)); p3.set(x, y - 0.005, z);
      mats.push(m4.compose(p3, q, sc).clone());
      cols.push(grassCols[Math.floor(R() * grassCols.length)].clone().multiplyScalar(0.85 + R() * 0.3));
      if (opts.flowers !== false && R() < 0.035) flowers.push([x + (R() - 0.5) * 0.05, y + s * 0.85, z + (R() - 0.5) * 0.05, R()]);
      else if (R() < 0.02) pebbles.push([x + 0.06, y, z + 0.04, R()]);
    }
  }
  if (!mats.length) return null;
  const im = new THREE.InstancedMesh(tg, tm, mats.length);
  mats.forEach((m, i) => { im.setMatrixAt(i, m); im.setColorAt(i, cols[i]); });
  im.receiveShadow = true; im.castShadow = false; im.frustumCulled = false; im.name = 'ground_cover_tufts';
  S.add(im);
  const out = { tufts: im, uTime };
  if (flowers.length) {
    const fg = new THREE.IcosahedronGeometry(0.018, 1), fm = new THREE.MeshStandardMaterial({ roughness: 0.7 });
    fm.userData.noVariation = true;
    const fi = new THREE.InstancedMesh(fg, fm, flowers.length);
    flowers.forEach(([x, y, z, u], i) => { m4.makeTranslation(x, y, z); fi.setMatrixAt(i, m4); fi.setColorAt(i, flowerCols[Math.floor(u * flowerCols.length)]); });
    fi.receiveShadow = true; fi.name = 'ground_cover_flowers'; S.add(fi); out.flowers = fi;
  }
  if (pebbles.length) {
    const pg = new THREE.IcosahedronGeometry(0.035, 1), pm = new THREE.MeshStandardMaterial({ roughness: 0.9, flatShading: true });
    pm.userData.noVariation = true;
    const pi = new THREE.InstancedMesh(pg, pm, pebbles.length);
    pebbles.forEach(([x, y, z, u], i) => {
      e.set(u * 3, u * 7, 0); q.setFromEuler(e); sc.set(1 + u, 0.55, 0.9 + u * 0.6); p3.set(x, y, z);
      pi.setMatrixAt(i, m4.compose(p3, q, sc)); pi.setColorAt(i, new THREE.Color('#8f8a7c').multiplyScalar(0.8 + u * 0.35));
    });
    pi.receiveShadow = true; pi.castShadow = true; pi.name = 'ground_cover_pebbles'; S.add(pi); out.pebbles = pi;
  }
  return out;
}

function seededRng(seed) { let s = (seed * 2654435761) >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

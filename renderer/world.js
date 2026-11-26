// AnglerMind 3D world kit: the house art style from CLAUDE.md "VISUAL BLUEPRINT".
// Low-poly diorama, warm sun with hard shadows, haze, filmic tone mapping, bloom on emissives only.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { Look, skyEnvironment } from './look.js';

export const PALETTE = {
  grass: ['#5a5725', '#64662d', '#676b32', '#5d6329'], grassDark: '#3a4318', grassLight: '#848a4c',
  asphalt: '#352b22', asphaltDay: '#5a544a', concrete: '#beb7a4', kerb: '#a89684', marking: '#e8e6df',
  sky: '#c7c8c7', skyTop: '#aab3bd', treeLime: '#a7b84a', treeOlive: '#7d8c35', conifer: '#3f5a2a',
  trunk: '#5a4632', wood: '#8a6a48', woodDark: '#5e4630', metal: '#c3c7cc', red: '#c92a2e',
  card: '#e5e2d6', cars: ['#d9c7a0', '#e6e3dc', '#b9bdc2', '#8fa6c8', '#a99bc4', '#e2c45a', '#2e8f86', '#c9a77c'],
};

export const LIGHTING = {
  day: { sun: '#fff1dc', sunI: 3.4, elev: 32, az: 215, hemiSky: '#e4e9ee', hemiGround: '#8a8a66', hemiI: 1.5,
         sky: '#cfd1ce', skyTop: '#aeb9c4', fog: '#c9cbc8', fogNear: 60, fogFar: 260, exposure: 1.05 },
  sunset: { sun: '#ffb46e', sunI: 3.6, elev: 11, az: 250, hemiSky: '#e3b693', hemiGround: '#3a3318', hemiI: 0.8,
            sky: '#e8b98f', skyTop: '#8d8fa8', fog: '#d9a986', fogNear: 50, fogFar: 220, exposure: 1.0 },
  // v2 presets (quality overhaul): key light from the camera side so forms read, a rim light from
  // behind for silhouette separation, environment reflections for metals. Bright, consistent grade.
  key: { sun: '#fff3e2', sunI: 2.3, elev: 34, az: 35, hemiSky: '#e6ebf0', hemiGround: '#8d8a6a', hemiI: 1.1,
         rim: '#dfe9ff', rimI: 1.8, rimElev: 22, rimAz: 200, env: 0.35, bloomT: 3.5,
         sky: '#d3d7d6', skyTop: '#a9b8c8', fog: '#cdd2d2', fogNear: 25, fogFar: 140, exposure: 1.0 },
  golden: { sun: '#ffd2a1', sunI: 2.5, elev: 20, az: 55, hemiSky: '#f1dcc6', hemiGround: '#7d6a4a', hemiI: 1.0,
            rim: '#ffe2c0', rimI: 2.0, rimElev: 16, rimAz: 215, env: 0.32, bloomT: 3.5,
            sky: '#efd8bd', skyTop: '#9fb0c6', fog: '#e3cdb4', fogNear: 25, fogFar: 140, exposure: 1.0 },
  // DUO module (docs/styles/DUO.md): crisp clear day, deeper blue sky overhead, less haze, punchier
  // contrast for close character shots. Opt-in per shot; no existing episode uses it.
  clear: { sun: '#fff4e4', sunI: 2.8, elev: 38, az: 30, hemiSky: '#cfe0f2', hemiGround: '#7f8a5c', hemiI: 1.15,
           rim: '#e6efff', rimI: 1.6, rimElev: 24, rimAz: 200, env: 0.35, bloomT: 3.5,
           sky: '#b9cde0', skyTop: '#3d6aa6', fog: '#c4d3e0', fogNear: 35, fogFar: 200, exposure: 1.02 },
  // BUILD module (docs/styles/BUILD.md): cold overcast snow day. Sky and snow measured from the reference
  // frames (sky #8390a4-#8b98ac, snow #c9d0d4-#d2d1dd): soft light, short pale shadows, cool grade.
  blizzard: { sun: '#eef3ff', sunI: 1.6, elev: 48, az: 30, hemiSky: '#c9d3e2', hemiGround: '#b8c0cc', hemiI: 1.6,
              rim: '#dfe8ff', rimI: 1.2, rimElev: 20, rimAz: 200, env: 0.3, bloomT: 3.5,
              sky: '#b3bccb', skyTop: '#7f8ca2', fog: '#c3cad5', fogNear: 12, fogFar: 90, exposure: 1.0 },
  night: { sun: '#a9bcff', sunI: 0.7, elev: 40, az: 160, hemiSky: '#2a3552', hemiGround: '#141c14', hemiI: 0.9,
           sky: '#111826', skyTop: '#080b16', fog: '#111826', fogNear: 40, fogFar: 170, exposure: 1.25 },
};

// Seeded RNG so every render of an episode is identical.
export function rng(seed = 1) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

const flat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.92, metalness: 0, flatShading: true, ...extra });

// deterministic 0..1 hash of a position (does not touch the world RNG)
function hash2(x, z) { const v = Math.sin(x * 12.9898 + z * 78.233) * 43758.5453; return v - Math.floor(v); }
// faceted ball with gently pushed-out vertices, so tree crowns read as foliage clumps, not perfect spheres
function lumpy(r, detail, seed) {
  const g = new THREE.IcosahedronGeometry(r, detail), p = g.attributes.position, v = new THREE.Vector3();
  const key = new Map();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i); const k = `${v.x.toFixed(4)},${v.y.toFixed(4)},${v.z.toFixed(4)}`;
    if (!key.has(k)) key.set(k, 1 + 0.09 * (hash2(v.x * 9 + seed, v.z * 9 + v.y * 5) - 0.5) * 2);
    v.multiplyScalar(key.get(k)); p.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals(); return g;
}

export class World {
  constructor(canvas, W, H, seed = 7, opts = {}) {
    this.W = W; this.H = H; this.rand = rng(seed);
    const ss = opts.supersample ?? 1;      // internal render scale (anti-aliasing for thin geometry)
    const r = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
    r.setPixelRatio(ss); r.setSize(W, H, false);
    r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
    r.toneMapping = THREE.NeutralToneMapping;  // keeps the muted pastels true; soft highlight roll-off r.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer = r;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, W / H, 0.05, 400);

    this.hemi = new THREE.HemisphereLight('#ffffff', '#444444', 1); this.scene.add(this.hemi);
    this.sun = new THREE.DirectionalLight('#ffffff', 3);
    this.sun.castShadow = true; this.sun.shadow.mapSize.set(4096, 4096);
    const sc = this.sun.shadow.camera; sc.left = -9; sc.right = 9; sc.top = 9; sc.bottom = -9; sc.near = 1; sc.far = 80;
    this.sun.shadow.bias = -0.0004; this.sun.shadow.normalBias = 0.02; this.sun.shadow.radius = 2;
    this.scene.add(this.sun); this.scene.add(this.sun.target);
    this.rim = new THREE.DirectionalLight('#ffffff', 0); this.scene.add(this.rim); this.scene.add(this.rim.target);
    const pm = new THREE.PMREMGenerator(r);
    this.envMap = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    this.scene.environment = this.envMap; this.scene.environmentIntensity = 0.0;

    this.skyDome = this._sky(); this.scene.add(this.skyDome);
    this.scene.fog = new THREE.Fog('#c6c8c5', 18, 95);

    const rt = new THREE.WebGLRenderTarget(W * ss, H * ss, { type: THREE.HalfFloatType, samples: 4 });
    this.composer = new EffectComposer(r, rt); this.composer.setPixelRatio(ss); this.composer.setSize(W, H);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    // High threshold: only emissive lights (brake lights, highlights) bloom.
    this.bloom = new UnrealBloomPass(new THREE.Vector2(W, H), 0.75, 0.55, 0.92);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());
    // Look v3 (renderer/look.js): sky-matched IBL, AO, depth of field, grade. plan.look = 'legacy' opts out.
    this.lookName = opts.look ?? 'v3';
    if (this.lookName !== 'legacy') this.look = new Look(this, opts);
    this._envCache = new Map(); this.lookTarget = new THREE.Vector3(); this.drift = opts.drift ?? 1;
    this.setLighting('day');
  }

  _sky() {
    // gradient dome; Look v3 adds soft procedural clouds (uniform `clouds`, 0 = clear, set per preset)
    const g = new THREE.SphereGeometry(300, 48, 24);
    const m = new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { top: { value: new THREE.Color('#a9b4bf') }, bottom: { value: new THREE.Color('#c9cbc8') },
                  clouds: { value: 0 }, cloudCol: { value: new THREE.Color('#ffffff') }, cloudShade: { value: new THREE.Color('#9aa3ad') } },
      vertexShader: 'varying vec3 vd; void main(){ vd = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
      fragmentShader: `uniform vec3 top, bottom, cloudCol, cloudShade; uniform float clouds; varying vec3 vd;
        float hh(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float vn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
          return mix(mix(hh(i), hh(i+vec2(1,0)), f.x), mix(hh(i+vec2(0,1)), hh(i+vec2(1,1)), f.x), f.y); }
        float fbm(vec2 p){ float a = 0.5, s = 0.0; for (int k = 0; k < 5; k++){ s += a * vn(p); p = p * 2.03 + 7.1; a *= 0.5; } return s; }
        void main(){
          float h = vd.y; float t = smoothstep(-0.05, 0.6, h);
          vec3 c = mix(bottom, top, t);
          if (clouds > 0.0 && h > 0.0) {
            vec2 p = vd.xz / (h + 0.18) * 1.6;                       // flattened cloud layer
            float n = fbm(p + 3.0);
            float cov = smoothstep(0.62 - clouds * 0.22, 0.88 - clouds * 0.15, n);
            float shade = smoothstep(0.55, 0.95, fbm(p * 1.7 + 11.0));
            vec3 cc = mix(cloudShade, cloudCol, shade);
            float fade = smoothstep(0.0, 0.12, h) * (1.0 - smoothstep(0.75, 1.0, h) * 0.5);
            c = mix(c, cc, cov * fade * 0.85);
          }
          gl_FragColor = vec4(c, 1.0);
        }`,
    });
    return new THREE.Mesh(g, m);
  }

  setLighting(name, center = new THREE.Vector3()) {
    const L = LIGHTING[name]; this.lightingName = name;
    this.sun.color.set(L.sun); this.sun.intensity = L.sunI;
    const e = THREE.MathUtils.degToRad(L.elev), a = THREE.MathUtils.degToRad(L.az), d = 30;
    this.sun.position.set(center.x + d * Math.cos(e) * Math.sin(a), center.y + d * Math.sin(e), center.z + d * Math.cos(e) * Math.cos(a));
    this.sun.target.position.copy(center);
    this.hemi.color.set(L.hemiSky); this.hemi.groundColor.set(L.hemiGround); this.hemi.intensity = L.hemiI;
    this.skyDome.material.uniforms.top.value.set(L.skyTop); this.skyDome.material.uniforms.bottom.value.set(L.sky);
    this.scene.fog.color.set(L.fog); this.scene.fog.near = L.fogNear; this.scene.fog.far = L.fogFar;
    this.renderer.toneMappingExposure = L.exposure;
    this.scene.environmentIntensity = L.env ?? 0.0;
    if (this.look) {
      const U = this.skyDome.material.uniforms;
      U.clouds.value = L.clouds ?? (name === 'night' || name === 'moonroom' || name === 'reef' ? 0 : name === 'blizzard' ? 0.2 : 0.55);
      U.cloudCol.value.set(L.sun).lerp(new THREE.Color('#ffffff'), 0.55);
      U.cloudShade.value.set(L.sky).lerp(U.cloudCol.value, 0.25).multiplyScalar(0.94);
      // sky-matched environment (cached per preset); presets without an env value get a soft default and a
      // slightly lower hemisphere light, because the environment now supplies part of the fill
      if (!this._envCache.has(name)) this._envCache.set(name, skyEnvironment(this.renderer, L, this.sun.position.clone().sub(center)));
      this.scene.environment = this._envCache.get(name);
      if (L.env === undefined) { this.scene.environmentIntensity = name === 'night' ? 0.35 : 0.55; this.hemi.intensity = L.hemiI * 0.72; }
      else this.scene.environmentIntensity = L.env * 1.25;
    }
    this.bloom.threshold = L.bloomT ?? 0.92;
    if (L.rim) {
      const re = THREE.MathUtils.degToRad(L.rimElev), ra = THREE.MathUtils.degToRad(L.rimAz);
      this.rim.color.set(L.rim); this.rim.intensity = L.rimI;
      this.rim.position.set(center.x + d * Math.cos(re) * Math.sin(ra), center.y + d * Math.sin(re), center.z + d * Math.cos(re) * Math.cos(ra));
      this.rim.target.position.copy(center);
    } else this.rim.intensity = 0;
  }

  // ---------- environment pieces ----------
  grassTexture() {
    const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
    g.fillStyle = PALETTE.grass[0]; g.fillRect(0, 0, 512, 512);
    const R = rng(3);
    for (let i = 0; i < 2600; i++) {
      const pick = R() < 0.12 ? PALETTE.grassDark : PALETTE.grass[Math.floor(R() * PALETTE.grass.length)];
      g.globalAlpha = 0.18 + R() * 0.25; g.fillStyle = pick;
      g.beginPath(); g.ellipse(R() * 512, R() * 512, 3 + R() * 26, 2 + R() * 14, R() * 3, 0, 7); g.fill();
    }
    g.globalAlpha = 1;
    const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8; return t;
  }

  ground(size = 400) {
    const tex = this.grassTexture(); tex.repeat.set(size / 9, size / 9);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshStandardMaterial({ map: tex, roughness: 1 }));
    m.rotation.x = -Math.PI / 2; m.receiveShadow = true; this.scene.add(m);
    (this.groundMeshes ??= []).push(m);      // Look v3 ground cover grows on these (renderer/look.js groundCover)
    return m;
  }

  roundTree(x, z, s = 1) {
    // section 11 polygon budget: 16-sided trunk, crown = one detail-2 faceted ball plus two smaller lumps
    // (jitter comes from a hash of the position, so the world RNG sequence, and every layout, is unchanged)
    const g = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.07 * s, 0.1 * s, 0.9 * s, 16), flat(PALETTE.trunk));
    trunk.position.y = 0.45 * s;
    const col = this.rand() < 0.5 ? PALETTE.treeLime : PALETTE.treeOlive;
    const crown = new THREE.Mesh(lumpy(0.75 * s, 2, x * 7.1 + z * 3.3), flat(col));
    crown.position.y = 1.35 * s; crown.rotation.set(this.rand() * 3, this.rand() * 3, 0);
    g.add(trunk, crown);
    const h = hash2(x, z);
    for (const [dx, dy, dz, r] of [[0.42, -0.18, 0.12, 0.42], [-0.36, -0.08, -0.2, 0.38]]) {
      const lump = new THREE.Mesh(lumpy(r * s * (0.9 + 0.2 * h), 2, x + z + r), flat(col));
      lump.position.set(dx * s * (h > 0.5 ? 1 : -1), 1.35 * s + dy * s, dz * s); g.add(lump);
    }
    g.position.set(x, 0, z);
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    this.scene.add(g); return g;
  }

  conifer(x, z, s = 1) {
    // three stacked 16-sided tiers instead of one 7-sided cone
    const g = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.06 * s, 0.08 * s, 0.5 * s, 16), flat(PALETTE.trunk));
    trunk.position.y = 0.25 * s; g.add(trunk);
    for (const [r, hgt, y] of [[0.62, 1.2, 0.95], [0.5, 1.05, 1.5], [0.36, 0.9, 2.02]]) {
      const tier = new THREE.Mesh(new THREE.ConeGeometry(r * s, hgt * s, 16, 2), flat(PALETTE.conifer));
      tier.position.y = y * s; g.add(tier);
    }
    g.position.set(x, 0, z); g.rotation.y = this.rand() * 6;
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    this.scene.add(g); return g;
  }

  // A tree outside the scene's shadow box would have its cast shadow cut by the box edge (QA:
  // render.shadow_cutoff). Such trees cast nothing and get a soft contact shadow on the ground instead.
  contactShadow(tree, x, z, s = 1) {
    if (!this._blobM) this._blobM = new THREE.MeshBasicMaterial({ color: '#1c2912', transparent: true, opacity: 0.35,
      depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
    tree.traverse(m => { if (m.isMesh) m.castShadow = false; });
    const blob = new THREE.Mesh(new THREE.CircleGeometry(0.95 * s, 32), this._blobM);
    blob.rotation.x = -Math.PI / 2; blob.position.set(x, 0.005, z); blob.renderOrder = 1; this.scene.add(blob);
    return blob;
  }

  scatterTrees(n, rMin, rMax, center = [0, 0]) {
    for (let i = 0; i < n; i++) {
      const a = this.rand() * Math.PI * 2, r = rMin + (rMax - rMin) * Math.sqrt(this.rand());
      const x = center[0] + r * Math.cos(a), z = center[1] + r * Math.sin(a), s = 0.8 + this.rand() * 0.9;
      (this.rand() < 0.35 ? this.conifer(x, z, s * 1.1) : this.roundTree(x, z, s));
    }
  }

  hills(n = 9, radius = 120) {
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + this.rand() * 0.4, r = radius * (0.85 + this.rand() * 0.3);
      const h = new THREE.Mesh(new THREE.IcosahedronGeometry(18 + this.rand() * 22, 3), flat(PALETTE.grass[i % 4]));
      h.scale.y = 0.28; h.position.set(Math.cos(a) * r, -3, Math.sin(a) * r); h.receiveShadow = true;
      this.scene.add(h);
    }
  }

  slab(w, d, h = 0.12, color = PALETTE.concrete) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), flat(color));
    m.position.y = h / 2; m.receiveShadow = true; m.castShadow = true; this.scene.add(m); return m;
  }

  box(w, h, d, color, x = 0, y = 0, z = 0, extra = {}) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), flat(color, extra));
    m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; this.scene.add(m); return m;
  }

  glowRing(radius, tube, color, intensity = 3) {
    const m = new THREE.Mesh(new THREE.TorusGeometry(radius, tube, 10, 64),
      new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: intensity, roughness: 0.5 }));
    m.rotation.x = Math.PI / 2; this.scene.add(m); return m;
  }

  // ---------- camera ----------
  applyShot(shot, t, i = 0) {
    const u = Math.min(1, Math.max(0, (t - shot.start) / Math.max(1e-3, shot.end - shot.start)));
    const e = u * u * (3 - 2 * u) * 0.6 + u * 0.4;   // gentle ease that never fully stops
    const lerp = (a, b) => a.map((v, i) => v + (b[i] - v) * e);
    let pos, look;
    if (shot.type === 'keys') {            // per-frame camera path computed in Python
      const k = Math.min(Math.max(0, i - shot.i0), shot.pos.length - 1);
      this.camera.fov = shot.fovs ? shot.fovs[k] : (shot.fov ?? 38); this.camera.updateProjectionMatrix();
      this.camera.position.set(...shot.pos[k]); this.lookTarget.set(...shot.look[k]);
      this._drift(shot, t); this.camera.lookAt(this.lookTarget);
      return;
    }
    if (shot.type === 'orbit') {
      const az = THREE.MathUtils.degToRad(shot.az0 + (shot.az1 - shot.az0) * e);
      const rad = shot.r0 + ((shot.r1 ?? shot.r0) - shot.r0) * e, hgt = shot.h0 + ((shot.h1 ?? shot.h0) - shot.h0) * e;
      pos = [shot.center[0] + rad * Math.sin(az), hgt, shot.center[2] + rad * Math.cos(az)];
      look = lerp(shot.look0 ?? shot.center, shot.look1 ?? shot.look0 ?? shot.center);
    } else {
      pos = lerp(shot.pos0, shot.pos1 ?? shot.pos0); look = lerp(shot.look0, shot.look1 ?? shot.look0);
    }
    this.camera.fov = shot.fov ?? 38; this.camera.updateProjectionMatrix();
    this.camera.position.set(...pos); this.lookTarget.set(...look);
    this._drift(shot, t); this.camera.lookAt(this.lookTarget);
  }

  // Look v3: a slow "operated camera" float on every shot (sum of incommensurate sines, seeded by the shot
  // start, so renders stay deterministic). Amplitude scales with the distance to the subject: about 0.35 %
  // of it in position and a little less on the aim point. Never shaky: the fastest component is ~0.4 Hz.
  // plan.drift = 0 turns it off; shot.drift scales it per shot (e.g. 0 for a locked-off map view).
  _drift(shot, t) {
    const a = this.drift * (shot.drift ?? 1); if (!a || this.lookName === 'legacy') return;
    const d = this.camera.position.distanceTo(this.lookTarget), s = (shot.start ?? 0) * 7.13 + 1.7;
    const n = (f1, f2, p) => 0.6 * Math.sin(t * f1 * 6.2832 + s * p) + 0.4 * Math.sin(t * f2 * 6.2832 + s * p * 1.7 + 2.1);
    const k = 0.0035 * d * a;
    this.camera.position.x += k * n(0.11, 0.29, 1.0); this.camera.position.y += k * 0.7 * n(0.13, 0.37, 2.3);
    this.camera.position.z += k * n(0.09, 0.23, 3.1);
    const kl = 0.0025 * d * a;
    this.lookTarget.x += kl * n(0.07, 0.31, 4.2); this.lookTarget.y += kl * 0.6 * n(0.12, 0.27, 5.3);
  }

  prepare() {
    // the sky dome (radius 300) is centred on the camera, and the far plane always reaches past it, so it
    // can never be clipped (a clipped dome showed the black clear colour as a triangle on the horizon)
    this.skyDome.position.copy(this.camera.position);
    if (this.camera.far < 330) { this.camera.far = 330; this.camera.updateProjectionMatrix(); }
  }

  render() { this.prepare(); this.composer.render(); }
}

// ---------- 2D overlay: label cards and wordmark, composited over the 3D frame ----------
export function drawCard(ctx, W, H, card, alpha = 1) {
  const big = card.big, small = card.small || '';
  const bigPx = Math.round(H * 0.034), smallPx = Math.round(H * 0.019);
  ctx.save(); ctx.globalAlpha = alpha;
  ctx.font = `800 ${bigPx}px Poppins`; const wb = ctx.measureText(big).width;
  ctx.font = `700 ${smallPx}px Poppins`; const ws = ctx.measureText(small).width;
  const padX = H * 0.02, padY = H * 0.012, w = Math.max(wb, ws) + padX * 2;
  const h = bigPx * 1.15 + (small ? smallPx * 1.25 : 0) + padY * 2;
  const cx = W * (card.x ?? 0.5), cy = H * (card.y ?? 0.2);
  if (card.scale) { ctx.translate(cx, cy); ctx.scale(card.scale, card.scale); ctx.translate(-cx, -cy); }
  const x = cx - w / 2, y = cy - h / 2;
  ctx.shadowColor = 'rgba(0,0,0,0.28)'; ctx.shadowBlur = H * 0.012; ctx.shadowOffsetY = H * 0.004;
  ctx.fillStyle = PALETTE.card; ctx.beginPath(); ctx.roundRect(x, y, w, h, H * 0.008); ctx.fill();
  ctx.shadowColor = 'transparent';
  ctx.fillStyle = card.color || PALETTE.red; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  ctx.font = `800 ${bigPx}px Poppins`; ctx.fillText(big, x + w / 2, y + padY);
  if (small) { ctx.font = `700 ${smallPx}px Poppins`; ctx.fillText(small, x + w / 2, y + padY + bigPx * 1.18); }
  ctx.restore();
}

export function drawBadge(ctx, W, H, text) {
  // small dark pill with a red dot: one consistent indicator for playback speed
  if (!text) return;
  ctx.save(); const px = Math.round(H * 0.019); ctx.font = `700 ${px}px Poppins`;   // round 7: 0.0135 H was unreadable on a phone
  const tw = ctx.measureText(text).width, padX = px * 0.9, dot = px * 0.36;
  const w = tw + padX * 2 + dot * 2.6, h = px * 2.0, x = W / 2 - w / 2, y = H * 0.088 - h / 2;
  ctx.fillStyle = 'rgba(20,22,26,0.55)'; ctx.beginPath(); ctx.roundRect(x, y, w, h, h / 2); ctx.fill();
  ctx.fillStyle = PALETTE.red; ctx.beginPath(); ctx.arc(x + padX + dot, y + h / 2, dot, 0, 7); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.95)'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.letterSpacing = '1px'; ctx.fillText(text, x + padX + dot * 2.6, y + h / 2 + 1); ctx.restore();
}

export function drawWordmark(ctx, W, H, text) {
  ctx.save(); ctx.font = `700 ${Math.round(H * 0.0105)}px Poppins`; ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(255,255,255,0.72)'; ctx.shadowColor = 'rgba(0,0,0,0.35)'; ctx.shadowBlur = 6;
  ctx.letterSpacing = `${Math.round(H * 0.002)}px`;
  ctx.fillText(text, W / 2, H * 0.045); ctx.restore();
}

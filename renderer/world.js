// Counterphysical 3D world kit: the house art style from CLAUDE.md "VISUAL BLUEPRINT".
// Low-poly diorama, warm sun with hard shadows, haze, filmic tone mapping, bloom on emissives only.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

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
  night: { sun: '#a9bcff', sunI: 0.7, elev: 40, az: 160, hemiSky: '#2a3552', hemiGround: '#141c14', hemiI: 0.9,
           sky: '#111826', skyTop: '#080b16', fog: '#111826', fogNear: 40, fogFar: 170, exposure: 1.25 },
};

// Seeded RNG so every render of an episode is identical.
export function rng(seed = 1) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

const flat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.92, metalness: 0, flatShading: true, ...extra });

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
    this.setLighting('day');
  }

  _sky() {
    const g = new THREE.SphereGeometry(300, 32, 16);
    const m = new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { top: { value: new THREE.Color('#a9b4bf') }, bottom: { value: new THREE.Color('#c9cbc8') } },
      vertexShader: 'varying float h; void main(){ h = normalize(position).y; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
      fragmentShader: 'uniform vec3 top; uniform vec3 bottom; varying float h; void main(){ float t = smoothstep(-0.05, 0.6, h); gl_FragColor = vec4(mix(bottom, top, t), 1.0); }',
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
    m.rotation.x = -Math.PI / 2; m.receiveShadow = true; this.scene.add(m); return m;
  }

  roundTree(x, z, s = 1) {
    const g = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.07 * s, 0.1 * s, 0.9 * s, 6), flat(PALETTE.trunk));
    trunk.position.y = 0.45 * s;
    const col = this.rand() < 0.5 ? PALETTE.treeLime : PALETTE.treeOlive;
    const crown = new THREE.Mesh(new THREE.IcosahedronGeometry(0.75 * s, 1), flat(col));
    crown.position.y = 1.35 * s; crown.rotation.set(this.rand() * 3, this.rand() * 3, 0);
    g.add(trunk, crown); g.position.set(x, 0, z);
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    this.scene.add(g); return g;
  }

  conifer(x, z, s = 1) {
    const g = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.06 * s, 0.08 * s, 0.5 * s, 5), flat(PALETTE.trunk));
    trunk.position.y = 0.25 * s;
    const cone = new THREE.Mesh(new THREE.ConeGeometry(0.6 * s, 2.2 * s, 7), flat(PALETTE.conifer));
    cone.position.y = 1.45 * s;
    g.add(trunk, cone); g.position.set(x, 0, z); g.rotation.y = this.rand() * 6;
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    this.scene.add(g); return g;
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
      const h = new THREE.Mesh(new THREE.IcosahedronGeometry(18 + this.rand() * 22, 1), flat(PALETTE.grass[i % 4]));
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
      this.camera.position.set(...shot.pos[k]); this.camera.lookAt(...shot.look[k]);
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
    this.camera.position.set(...pos); this.camera.lookAt(...look);
  }

  render() {
    // the sky dome (radius 300) is centred on the camera, and the far plane always reaches past it, so it
    // can never be clipped (a clipped dome showed the black clear colour as a triangle on the horizon)
    this.skyDome.position.copy(this.camera.position);
    if (this.camera.far < 330) { this.camera.far = 330; this.camera.updateProjectionMatrix(); }
    this.composer.render();
  }
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
  ctx.save(); const px = Math.round(H * 0.0135); ctx.font = `700 ${px}px Poppins`;
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

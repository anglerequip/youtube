// Reusable material library for Counterphysical scenes (premium-stylised, not photoreal).
// Every material is physically based and picks up the scene environment map for reflections.
import * as THREE from 'three';

function canvasTex(w, h, draw, repeat = [1, 1]) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

function seeded(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

// Soft wood grain: long streaks with gentle colour variation and a few knots.
export function woodTexture(base = '#9a7650', seed = 3) {
  const R = seeded(seed);
  return canvasTex(256, 1024, (g, w, h) => {
    g.fillStyle = base; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 140; i++) {
      const x = R() * w, dark = R() < 0.6;
      g.strokeStyle = dark ? `rgba(60,38,20,${0.05 + R() * 0.12})` : `rgba(255,230,190,${0.04 + R() * 0.08})`;
      g.lineWidth = 1 + R() * 3; g.beginPath(); g.moveTo(x, 0);
      for (let y = 0; y <= h; y += 32) g.lineTo(x + Math.sin(y * 0.01 + i) * 4 + (R() - 0.5) * 2, y);
      g.stroke();
    }
    for (let k = 0; k < 3; k++) {
      const x = R() * w, y = R() * h; g.fillStyle = 'rgba(70,45,25,0.35)';
      g.beginPath(); g.ellipse(x, y, 6 + R() * 6, 14 + R() * 10, 0, 0, 7); g.fill();
    }
  });
}

// Fine speckled concrete / cast stone for platforms.
export function concreteTexture(base = '#c9c2b0', seed = 5) {
  const R = seeded(seed);
  return canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = base; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 9000; i++) {
      const v = R(); g.fillStyle = v < 0.5 ? `rgba(80,70,55,${R() * 0.07})` : `rgba(255,255,245,${R() * 0.08})`;
      g.fillRect(R() * w, R() * h, 1 + R() * 2, 1 + R() * 2);
    }
  }, [2, 2]);
}

export const MAT = {
  // polished spring steel: bright, crisp reflections, a little clearcoat sparkle
  springSteel: () => new THREE.MeshPhysicalMaterial({ color: '#e1e4e8', metalness: 0.65, roughness: 0.32,
    clearcoat: 0.0, envMapIntensity: 1.1 }),
  brushedSteel: () => new THREE.MeshPhysicalMaterial({ color: '#b9bec4', metalness: 0.9, roughness: 0.38, envMapIntensity: 1.0 }),
  darkSteel: () => new THREE.MeshPhysicalMaterial({ color: '#3b3f45', metalness: 0.8, roughness: 0.35, envMapIntensity: 0.9 }),
  anodised: (c = '#2f5d8a') => new THREE.MeshPhysicalMaterial({ color: c, metalness: 0.6, roughness: 0.3, clearcoat: 0.4 }),
  wood: (base) => new THREE.MeshStandardMaterial({ map: woodTexture(base), roughness: 0.62, metalness: 0, envMapIntensity: 0.6 }),
  concrete: (base) => new THREE.MeshStandardMaterial({ map: concreteTexture(base), roughness: 0.88, envMapIntensity: 0.5 }),
  plastic: (c) => new THREE.MeshPhysicalMaterial({ color: c, roughness: 0.4, clearcoat: 0.3, envMapIntensity: 0.7 }),
  rubber: (c = '#2a2b2e') => new THREE.MeshStandardMaterial({ color: c, roughness: 0.95 }),
  glass: () => new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: 0.05, transmission: 0.9, thickness: 0.01,
    transparent: true, opacity: 0.35, envMapIntensity: 1.2 }),
  emissive: (c, i = 2) => new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: i, roughness: 0.5 }),
  ceramic: (c = '#e9e5da') => new THREE.MeshPhysicalMaterial({ color: c, roughness: 0.3, clearcoat: 0.5 }),
};

// Soft additive halo sprite (radial gradient), for restrained glows that hug an object.
export function haloSprite(color = '#ff3b30', size = 0.4, opacity = 0.5) {
  const tex = canvasTex(128, 128, (g, w) => {
    const grd = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    grd.addColorStop(0, 'rgba(255,255,255,1)'); grd.addColorStop(0.35, 'rgba(255,255,255,0.35)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd; g.fillRect(0, 0, w, w);
  });
  const m = new THREE.SpriteMaterial({ map: tex, color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false });
  const s = new THREE.Sprite(m); s.scale.set(size, size, 1); return s;
}

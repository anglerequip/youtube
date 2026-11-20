// We cooked crystals (content/episodes/crystal-caper/plan.py): a comedy caper in one diorama world.
// Sets: the house at night (hook + loop ending), the kitchen (pot of syrup, the jar with the string, the
// finished rock candy), the road at sunset (the chase) and the roadside at night (the reveal and the sparks).
// The presenters come from ../characters.js (man() = the wizard, woman() = Nyx); the police officer is an
// original, simple figure built here. This file only draws what the plan lists.
import * as THREE from 'three';
import { PALETTE } from '../world.js';
import { MAT, haloSprite } from '../materials.js';
import { man, woman } from '../characters.js';
import { car, straightRoad, fence } from '../props.js';

const flat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, flatShading: true, ...x });
const smooth = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.7, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };
const mesh = (geo, m, parent, x = 0, y = 0, z = 0) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; o.receiveShadow = true; parent.add(o); return o; };
const BLUE = '#3b6cff', RED = '#ff3b30';

function labelTexture(text, bg = '#e9e1cf', fg = '#c92a2e', w = 512, h = 256, size = 120) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d');
  g.fillStyle = bg; g.fillRect(0, 0, w, h);
  g.fillStyle = fg; g.font = `800 ${size}px Poppins`; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(text, w / 2, h / 2 + 6);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

// ---------- rock candy: elongated sucrose-like prisms (monoclinic-ish, flat faces) ----------
function crystalGeo(len, r) {
  // a six-sided prism with sloped (wedge) ends, slightly skewed so faces catch the light differently
  const pts = [], k = 6;
  const g = new THREE.CylinderGeometry(r, r, len, k, 1, false);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const y = p.getY(i), x = p.getX(i), z = p.getZ(i);
    if (Math.abs(y) > len / 2 - 1e-6) p.setY(i, y + Math.sign(y) * (x * 0.55 + z * 0.2) * 1.0);
    p.setX(i, x * 1.25);
  }
  g.computeVertexNormals(); return g;
}
function candyStick(color, seed, height = 0.2) {
  let s = seed; const R = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const g = new THREE.Group();
  const stick = mesh(new THREE.CylinderGeometry(0.0035, 0.0035, height + 0.09, 16), MAT.wood('#c9a77c'), g, 0, (height + 0.09) / 2, 0);
  stick.castShadow = true;
  const m = new THREE.MeshPhysicalMaterial({ color, roughness: 0.12, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.08,
    flatShading: true, envMapIntensity: 1.4, emissive: color, emissiveIntensity: 0.06 });
  const cr = new THREE.Group(); g.add(cr);
  for (let q = 0; q < 46; q++) {
    const y = 0.02 + R() * (height - 0.03), a = R() * Math.PI * 2;
    const L = 0.012 + R() * 0.02, r = 0.005 + R() * 0.006;
    const c = new THREE.Mesh(crystalGeo(L, r), m);
    c.position.set(Math.cos(a) * 0.011, y, Math.sin(a) * 0.011);
    c.rotation.set((R() - 0.5) * 1.6, R() * 6, Math.PI / 2 * (R() < 0.5 ? 1 : 0.6) + (R() - 0.5) * 0.8);
    c.lookAt(c.position.clone().multiplyScalar(3).setY(y + (R() - 0.5) * 0.02)); c.rotateX(Math.PI / 2);
    c.castShadow = true; cr.add(c);
  }
  g.crystals = cr; g.material = m; return g;
}

// ---------- the police officer (original, simple, smooth) ----------
function officer() {
  const root = new THREE.Group();
  const navy = smooth('#26324a', { roughness: 0.8 }), skin = smooth('#d9a888', { roughness: 0.6 }), dark = smooth('#15181f'), hi = smooth('#d7c27a', { metalness: 0.6, roughness: 0.35 });
  const lathe = (prof, m, parent, y = 0) => {
    const c = new THREE.SplineCurve(prof.map(([yy, r]) => new THREE.Vector2(r, yy)));
    const o = mesh(new THREE.LatheGeometry(c.getPoints(prof.length * 5), 48), m, parent, 0, y, 0); o.scale.z = 0.72; return o;
  };
  // legs and boots
  for (const s of [-1, 1]) {
    const leg = mesh(new THREE.CylinderGeometry(0.075, 0.06, 0.82, 24), navy, root, s * 0.1, 0.46, 0);
    mesh(new THREE.BoxGeometry(0.12, 0.08, 0.26), dark, root, s * 0.1, 0.04, 0.04);
  }
  // torso (jacket) and belt
  lathe([[0.86, 0.0], [0.88, 0.17], [1.05, 0.2], [1.3, 0.21], [1.42, 0.22], [1.48, 0.15], [1.52, 0.06], [1.53, 0.0]], navy, root);
  mesh(new THREE.CylinderGeometry(0.205, 0.205, 0.06, 40), dark, root, 0, 0.92, 0).scale.z = 0.74;
  mesh(new THREE.CircleGeometry(0.03, 24), hi, root, -0.09, 1.33, 0.16).rotation.x = -0.15;   // badge
  // neck + head
  mesh(new THREE.CylinderGeometry(0.05, 0.055, 0.1, 24), skin, root, 0, 1.56, 0);
  const head = new THREE.Group(); head.position.set(0, 1.6, 0); root.add(head);
  const skull = mesh(new THREE.SphereGeometry(0.11, 72, 54), skin, head, 0, 0.1, 0); skull.scale.set(0.92, 1.12, 1);
  mesh(new THREE.SphereGeometry(0.018, 24, 18), skin, head, 0, 0.09, 0.105);                      // nose
  const eyes = [];
  for (const s of [-1, 1]) {
    const e = mesh(new THREE.SphereGeometry(0.013, 24, 18), smooth('#f2efe8'), head, s * 0.038, 0.125, 0.092); e.scale.z = 0.5;
    const pu = mesh(new THREE.SphereGeometry(0.0075, 16, 12), dark, e, 0, 0, 0.011); eyes.push(e);
    mesh(new THREE.BoxGeometry(0.035, 0.007, 0.01), smooth('#3a2a20'), head, s * 0.038, 0.148, 0.098).rotation.z = s * -0.08;  // brows
  }
  mesh(new THREE.BoxGeometry(0.07, 0.012, 0.012), smooth('#3a2a20'), head, 0, 0.065, 0.101);       // moustache-free lip line
  const mouth = mesh(new THREE.SphereGeometry(0.02, 24, 12), smooth('#5a2a25'), head, 0, 0.045, 0.098); mouth.scale.set(1, 0.15, 0.4);
  // peaked cap
  const cap = new THREE.Group(); cap.position.set(0, 0.2, 0); head.add(cap);
  mesh(new THREE.CylinderGeometry(0.118, 0.112, 0.07, 48), navy, cap, 0, 0, 0);
  mesh(new THREE.CylinderGeometry(0.125, 0.125, 0.012, 48), dark, cap, 0, -0.03, 0);
  const peak = mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.01, 32, 1, false, -Math.PI / 2, Math.PI), dark, cap, 0, -0.03, 0.09); peak.rotation.x = 0.25;
  mesh(new THREE.BoxGeometry(0.05, 0.03, 0.01), hi, cap, 0, 0.0, 0.118);
  // arms: pivots at the shoulders
  const arms = [];
  for (const s of [-1, 1]) {
    const sh = new THREE.Group(); sh.position.set(s * 0.25, 1.45, 0); root.add(sh);
    mesh(new THREE.CylinderGeometry(0.055, 0.048, 0.32, 24), navy, sh, 0, -0.16, 0);
    const el = new THREE.Group(); el.position.set(0, -0.32, 0); sh.add(el);
    mesh(new THREE.CylinderGeometry(0.046, 0.04, 0.28, 24), navy, el, 0, -0.14, 0);
    mesh(new THREE.SphereGeometry(0.045, 32, 24), skin, el, 0, -0.31, 0);
    arms.push({ sh, el });
  }
  // a torch in the left hand
  const torch = mesh(new THREE.CylinderGeometry(0.018, 0.022, 0.16, 24), dark, arms[0].el, 0, -0.33, 0.06); torch.rotation.x = Math.PI / 2;
  const lens = mesh(new THREE.CircleGeometry(0.019, 24), MAT.emissive('#fff4d8', 3), arms[0].el, 0, -0.33, 0.141);
  root.rig = { head, arms, mouth, eyes, torch, lens };
  root.faceY = 1.72;
  root.pose = (p = {}) => {
    mouth.scale.y = 0.15 + 0.75 * (p.talk ?? 0);
    for (const e of eyes) e.scale.y = Math.max(0.08, 1 - (p.blink ?? 0));
    head.rotation.set(p.headPitch ?? 0, p.headYaw ?? 0, p.headTilt ?? 0);
    const [L, Rr] = arms;
    L.sh.rotation.set(-(p.torch ?? 0) * 1.25, 0, 0.08); L.el.rotation.set(-(p.torch ?? 0) * 0.3, 0, 0);
    const up = p.hold ?? 0;          // right hand raised (holding the candy up to the face)
    Rr.sh.rotation.set(-0.35 - up * 1.0, 0, -0.08 - up * 0.25); Rr.el.rotation.set(-0.4 - up * 1.35, 0, 0);
  };
  root.pose();
  return shadowed(root);
}

function police(color = '#e6e3dc') {
  const g = car(color, 'sedan', false);
  const navy = flat('#26324a', { roughness: 0.5 });
  // a dark band along each side (livery), and the light bar on the roof
  for (const s of [-1, 1]) { const b = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.16, 3.2), navy); b.position.set(s * 0.885, 0.62, 0); g.add(b); }
  const bar = new THREE.Group(); bar.position.set(0, 1.47, 0.05); g.add(bar);
  mesh(new THREE.BoxGeometry(1.1, 0.06, 0.26), flat('#2a2b2e'), bar, 0, 0, 0);
  const mR = new THREE.MeshStandardMaterial({ color: '#7a1416', emissive: RED, emissiveIntensity: 0.2, roughness: 0.3 });
  const mB = new THREE.MeshStandardMaterial({ color: '#1a2a6a', emissive: BLUE, emissiveIntensity: 0.2, roughness: 0.3 });
  mesh(new THREE.BoxGeometry(0.48, 0.1, 0.22), mR, bar, -0.27, 0.08, 0);
  mesh(new THREE.BoxGeometry(0.48, 0.1, 0.22), mB, bar, 0.27, 0.08, 0);
  const lR = new THREE.PointLight(RED, 0, 16, 1.6), lB = new THREE.PointLight(BLUE, 0, 16, 1.6);
  lR.position.set(-0.4, 1.7, 0); lB.position.set(0.4, 1.7, 0); g.add(lR, lB);
  const hR = haloSprite(RED, 0.9, 0), hB = haloSprite(BLUE, 0.9, 0);
  hR.position.set(-0.27, 1.56, 0.05); hB.position.set(0.27, 1.56, 0.05); g.add(hR, hB);
  // headlights (front is -Z)
  const hl = [];
  for (const x of [-0.6, 0.6]) {
    const m = mesh(new THREE.BoxGeometry(0.3, 0.13, 0.04), MAT.emissive('#fff2d6', 1.5), g, x, 0.68, -2.06);
    hl.push(m);
  }
  g.setLights = (t, on = 1) => {
    // alternating red / blue, two quick flashes each (a common light-bar pattern)
    // slow, soft alternation (about 0.8 cycles per second, smooth ramps): no strobing, safe for viewers
    const w = Math.sin(t * Math.PI * 2 * 0.8), ramp = x => Math.min(1, Math.max(0, x * 1.6));
    const a = on * (0.06 + 0.94 * ramp(w)), b = on * (0.06 + 0.94 * ramp(-w));
    mR.emissiveIntensity = 0.2 + 5.5 * a; mB.emissiveIntensity = 0.2 + 5.5 * b;
    lR.intensity = 9 * a; lB.intensity = 11 * b;
    hR.material.opacity = 0.75 * a; hB.material.opacity = 0.75 * b;
  };
  g.setLights(0, 0);
  return g;
}

function house(S) {
  const g = new THREE.Group();
  const wall = flat('#e6e3dc'), trim = flat('#8a6a48'), roofM = flat('#7b5a44');
  mesh(new THREE.BoxGeometry(6.2, 2.8, 5), wall, g, 0, 1.4, -4.0);
  const roof = mesh(new THREE.CylinderGeometry(0.01, 3.9, 1.9, 4, 1), roofM, g, 0, 3.75, -4.0); roof.rotation.y = Math.PI / 4; roof.scale.set(1.15, 1, 0.92);
  mesh(new THREE.BoxGeometry(1.0, 2.05, 0.08), trim, g, -1.55, 1.03, -1.48);           // door
  mesh(new THREE.SphereGeometry(0.035, 16, 12), flat('#d7c27a'), g, -1.2, 1.0, -1.42);
  // kitchen window, warm light inside
  const winM = MAT.emissive('#ffcf8a', 1.2);
  for (const x of [0.6, 2.0]) {
    mesh(new THREE.BoxGeometry(1.0, 0.9, 0.06), winM, g, x, 1.6, -1.48);
    mesh(new THREE.BoxGeometry(1.1, 0.08, 0.12), trim, g, x, 1.1, -1.44);
    mesh(new THREE.BoxGeometry(0.05, 0.9, 0.08), trim, g, x, 1.6, -1.45);
  }
  const porch = new THREE.PointLight('#ffc98a', 3, 6, 1.8); porch.position.set(-1.55, 2.4, -1.0); g.add(porch);
  mesh(new THREE.SphereGeometry(0.06, 24, 16), MAT.emissive('#ffd7a0', 1.4), g, -1.55, 2.35, -1.35);
  // a street lamp on the camera side: soft warm key light on the front yard
  const lamp = new THREE.PointLight('#ffd9a8', 9, 12, 1.5); lamp.position.set(1.2, 3.2, 6.2); g.add(lamp);
  mesh(new THREE.CylinderGeometry(0.05, 0.06, 3.4, 16), flat('#3a3c40'), g, 2.6, 1.7, 6.6);
  const win = new THREE.PointLight('#ffc07a', 3.5, 6, 1.8); win.position.set(1.3, 1.6, -0.6); g.add(win);
  // path, driveway, low fence, mailbox
  const path = mesh(new THREE.BoxGeometry(1.1, 0.04, 4.5), MAT.concrete('#bcb4a2'), g, -1.55, 0.02, 0.8); path.castShadow = false;
  const drive = mesh(new THREE.BoxGeometry(3.0, 0.03, 9), MAT.concrete('#a9a293'), g, 1.75, 0.015, 1.5); drive.castShadow = false;
  for (let x = -6; x <= -3.2; x += 0.5) mesh(new THREE.BoxGeometry(0.08, 0.6, 0.08), trim, g, x, 0.3, 4.6);
  mesh(new THREE.BoxGeometry(2.9, 0.06, 0.05), trim, g, -4.6, 0.45, 4.6);
  S.add(shadowed(g)); g.lights = [porch, win]; return g;
}

function kitchen(S, L, T) {
  const g = new THREE.Group(); const [kx, , kz] = L.island;
  const floor = mesh(new THREE.BoxGeometry(6.0, 0.1, 5.0), MAT.wood('#a78058'), g, kx, 0.05, kz - 0.5);
  const wallM = flat('#d9cfbd'), tile = flat('#e9e5da'), cab = flat('#7d8c6a');
  mesh(new THREE.BoxGeometry(6.0, 3.0, 0.12), wallM, g, kx, 1.5, kz - 3.0);
  mesh(new THREE.BoxGeometry(0.12, 3.0, 5.0), wallM, g, kx - 3.0, 1.5, kz - 0.5);
  // back counter + cupboards + window
  mesh(new THREE.BoxGeometry(4.2, 0.9, 0.6), cab, g, kx - 0.4, 0.45, kz - 2.65);
  mesh(new THREE.BoxGeometry(4.25, 0.05, 0.64), tile, g, kx - 0.4, 0.92, kz - 2.65);
  mesh(new THREE.BoxGeometry(2.0, 0.7, 0.35), cab, g, kx - 1.5, 2.15, kz - 2.75);
  mesh(new THREE.BoxGeometry(1.3, 0.9, 0.04), MAT.emissive('#f3f1e6', 0.6), g, kx + 1.1, 1.75, kz - 2.93);
  mesh(new THREE.BoxGeometry(1.4, 0.07, 0.1), flat('#8a6a48'), g, kx + 1.1, 1.28, kz - 2.9);
  // the island with a hob
  mesh(new THREE.BoxGeometry(2.4, T - 0.05, 0.9), cab, g, kx, (T - 0.05) / 2, kz);
  const top = mesh(new THREE.BoxGeometry(2.5, 0.05, 1.0), MAT.concrete('#d8d2c4'), g, kx, T - 0.025, kz);
  const [px, , pz] = L.pot;
  mesh(new THREE.BoxGeometry(0.62, 0.012, 0.52), flat('#1f2023', { roughness: 0.3 }), g, px, T + 0.006, pz);
  const burner = mesh(new THREE.TorusGeometry(0.1, 0.012, 12, 40), MAT.emissive('#ff5a2a', 0.6), g, px, T + 0.014, pz); burner.rotation.x = Math.PI / 2;
  // stools
  for (const x of [kx - 0.6, kx + 0.3]) {
    mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.05, 32), MAT.wood('#8a6a48'), g, x, 0.68, kz + 0.8);
    mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.66, 16), MAT.brushedSteel(), g, x, 0.33, kz + 0.8);
  }
  // a plant on the back counter
  mesh(new THREE.CylinderGeometry(0.08, 0.06, 0.14, 24), MAT.ceramic('#c9a77c'), g, kx - 1.9, 1.01, kz - 2.6);
  mesh(new THREE.IcosahedronGeometry(0.14, 2), flat('#7d8c35'), g, kx - 1.9, 1.17, kz - 2.6);
  S.add(shadowed(g));
  return { burner };
}

function pot(S, L, T) {
  const g = new THREE.Group(); const [px, , pz] = L.pot; g.position.set(px, T + 0.012, pz);
  const copper = new THREE.MeshPhysicalMaterial({ color: '#b8734a', metalness: 0.85, roughness: 0.3, envMapIntensity: 1.2 });
  const prof = [[0, 0], [0.004, 0.15], [0.03, 0.165], [0.17, 0.165], [0.18, 0.172], [0.175, 0.16], [0.03, 0.155], [0.012, 0.0]];
  const shell = new THREE.Mesh(new THREE.LatheGeometry(prof.map(([y, r]) => new THREE.Vector2(r, y)), 48), copper);
  shell.material.side = THREE.DoubleSide; shell.castShadow = true; g.add(shell);
  for (const s of [-1, 1]) { const h = mesh(new THREE.TorusGeometry(0.035, 0.008, 12, 32, Math.PI), MAT.darkSteel(), g, s * 0.18, 0.14, 0); h.rotation.y = s * Math.PI / 2; }
  const syrup = mesh(new THREE.CylinderGeometry(0.152, 0.152, 0.005, 48), new THREE.MeshPhysicalMaterial({ color: '#e9c98e', roughness: 0.65, transmission: 0.1, thickness: 0.05 }), g, 0, 0.13, 0);
  // wooden spoon
  const spoon = new THREE.Group(); spoon.position.set(0.03, 0.13, 0); g.add(spoon);
  const handle = mesh(new THREE.CylinderGeometry(0.008, 0.01, 0.32, 16), MAT.wood('#c9a77c'), spoon, 0, 0.12, 0); handle.rotation.z = -0.5; handle.position.x = 0.06;
  // sugar bag beside the hob
  const bag = new THREE.Group(); bag.position.set(px + 0.42, T, pz + 0.08); S.add(bag);
  const paper = new THREE.MeshStandardMaterial({ color: '#efe9da', roughness: 0.9 });
  mesh(new THREE.BoxGeometry(0.16, 0.24, 0.1), paper, bag, 0, 0.12, 0);
  const fold = mesh(new THREE.BoxGeometry(0.16, 0.04, 0.06), paper, bag, 0, 0.255, 0); fold.rotation.x = 0.3;
  const lab = new THREE.Mesh(new THREE.PlaneGeometry(0.15, 0.075), new THREE.MeshStandardMaterial({ map: labelTexture('SUGAR'), roughness: 0.8 }));
  lab.position.set(0, 0.13, 0.051); bag.add(lab);
  // steam: soft sprites rising
  const steam = Array.from({ length: 10 }, (_, k) => { const s = haloSprite('#ffffff', 0.12, 0); s.material.blending = THREE.NormalBlending; g.add(s); return { s, ph: k / 10 }; });
  S.add(shadowed(g));
  return { g, spoon, steam, bag };
}

function jar(S, L, T) {
  const g = new THREE.Group(); const [jx, , jz] = L.jar; g.position.set(jx, T, jz);
  const glass = new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: 0.04, transmission: 0.95, thickness: 0.004, transparent: true, opacity: 0.4, envMapIntensity: 1.3, side: THREE.DoubleSide });
  const prof = [[0, 0.0], [0.0, 0.055], [0.006, 0.06], [0.14, 0.06], [0.155, 0.05], [0.17, 0.048], [0.175, 0.05]];
  const shell = new THREE.Mesh(new THREE.LatheGeometry(prof.map(([y, r]) => new THREE.Vector2(r, y)), 48), glass); g.add(shell);
  const syrup = mesh(new THREE.CylinderGeometry(0.056, 0.056, 0.12, 48), new THREE.MeshPhysicalMaterial({ color: '#f4e2b0', roughness: 0.03, transmission: 0.9, thickness: 0.1, transparent: true, opacity: 0.32 }), g, 0, 0.065, 0);
  syrup.castShadow = false;
  // a pencil across the mouth, a string hanging into the syrup
  const pencil = mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.16, 16), flat('#e2c45a'), g, 0, 0.18, 0); pencil.rotation.z = Math.PI / 2;
  const str = mesh(new THREE.CylinderGeometry(0.0028, 0.0028, 0.15, 12), flat('#f2ead6'), g, 0, 0.105, 0);
  // crystals along the string: pink faceted prisms that grow with the plan's 'grow' value
  const m = new THREE.MeshPhysicalMaterial({ color: '#e8a3b8', roughness: 0.15, clearcoat: 1, flatShading: true, envMapIntensity: 1.3 });
  const cr = [];
  let s = 77; const R = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  for (let q = 0; q < 40; q++) {
    const y = 0.035 + R() * 0.085, a = R() * Math.PI * 2;
    const c = new THREE.Mesh(crystalGeo(0.014 + R() * 0.012, 0.004 + R() * 0.004), m);
    c.position.set(Math.cos(a) * 0.006, y, Math.sin(a) * 0.006); c.rotation.set(R() * 3, R() * 3, R() * 3);
    c.userData.start = R() * 0.35; g.add(c); cr.push(c);
  }
  S.add(g); return { g, cr };
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout, Tm = plan.timing, T = L.top;
  world.ground(1200);
  const nBefore = S.children.length; world.hills(12, 140);
  // keep the hills off the chase road (x = road_x): a hill straddling it swallows the camera
  for (const h of S.children.slice(nBefore)) {
    const dx = h.position.x - plan.layout.road_x;
    if (Math.abs(dx) < 60) h.position.x = plan.layout.road_x + (dx < 0 ? -60 : 60);
  }
  // ---- house set (night)
  const H = L.house;
  const hs = house(S);
  for (const [x, z, s] of [[-5.5, -2.5, 1.6], [5.6, -3.5, 1.8], [-7, 3, 1.3], [7.5, 2.5, 1.5], [-3.5, -9, 2.0], [3.5, -10, 2.1]]) world.roundTree(x, z, s);
  world.conifer(-8.5, -6, 2.2); world.conifer(9, -7, 2.4);
  const homeRoad = straightRoad(S, { z0: -60, z1: 60, lanes: 2, asphalt: PALETTE.asphalt }); homeRoad.rotation.y = Math.PI / 2; homeRoad.position.set(0, 0, 7.6);
  const cop1 = police(); cop1.position.set(...H.car); S.add(cop1);
  const nyx = woman(); S.add(nyx);
  const wiz = man(); S.add(wiz);
  const cop = officer(); S.add(cop);
  // house style: never pure black. Lift near-black materials (Nyx's outfit and hair, tyres, trims) to a dark
  // charcoal that keeps its hue, so they read as black cloth rather than holes.
  const hsl = {};
  S.traverse(o => {
    if (!o.isMesh) return;
    for (const m of [].concat(o.material)) {
      if (!m || !m.color || m.userData.lifted) continue;
      m.color.getHSL(hsl);
      if (hsl.l < 0.025) m.color.setHSL(hsl.h, hsl.s, 0.025);   // working space is linear: 0.025 is about sRGB 40
      m.userData.lifted = true;
    }
  });
  // presenters use vertex colours, so also give their materials a faint emissive floor (dark cloth stays charcoal)
  for (const ch of [nyx, wiz, cop]) ch.traverse(o => {
    if (!o.isMesh) return;
    for (const m of [].concat(o.material)) if (m && m.emissive && m.emissive.getHex() === 0) m.emissive.setRGB(0.014, 0.014, 0.017);
  });
  // a soft moonlight fill for the night sets, so dark clothes and the roadside keep some detail
  const moon = new THREE.HemisphereLight('#9aaad0', '#2a3028', 0); S.add(moon);

  // ---- kitchen set (day)
  const K = L.kitchen;
  const kit = kitchen(S, K, T);
  const pt = pot(S, K, T);
  const jr = jar(S, K, T);
  const candy = new THREE.Group(); candy.position.set(K.candy[0], T, K.candy[2]); S.add(candy);
  const cols = ['#e8a3b8', '#e2b062', '#e8a3b8', '#efc98a', '#d98aa6'];
  for (let q = 0; q < 5; q++) {
    const cup = new THREE.Group(); cup.position.set(-0.24 + q * 0.12, 0, (q % 2) * 0.07); candy.add(cup);
    const glass = new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: 0.05, transmission: 0.9, thickness: 0.004, transparent: true, opacity: 0.35, side: THREE.DoubleSide });
    mesh(new THREE.CylinderGeometry(0.035, 0.03, 0.09, 40, 1, true), glass, cup, 0, 0.045, 0).castShadow = false;
    const st = candyStick(cols[q], 11 + q * 7, 0.15 + (q % 3) * 0.02); st.position.y = 0.02; st.rotation.z = (q - 2) * 0.06; cup.add(st);
  }
  // the stick the cop holds (roadside), and its sparks
  const held = candyStick('#e8a3b8', 91, 0.13); held.scale.setScalar(1.5); S.add(held);
  const sparks = Array.from({ length: 14 }, () => { const s = haloSprite('#8fb7ff', 0.06, 0); S.add(s); return s; });
  const sparkCore = Array.from({ length: 14 }, () => { const s = haloSprite('#e8f0ff', 0.02, 0); S.add(s); return s; });

  // ---- road set (sunset chase) and the roadside stop (night)
  const RX = L.road_x;
  const road = straightRoad(S, { z0: -520, z1: 80, lanes: 2, asphalt: PALETTE.asphaltDay }); road.position.x = RX;
  fence(S, RX - 6.2, -500, 60, 4); fence(S, RX + 6.2, -500, 60, 4);
  for (let z = -480; z < 60; z += 26) { world.roundTree(RX - 11 - (z % 7), z, 1.6 + (z % 3) * 0.2); world.roundTree(RX + 12 + (z % 5), z + 11, 1.7); }
  for (let z = -470; z < 60; z += 61) { world.conifer(RX - 16, z, 2.2); world.conifer(RX + 17, z + 30, 2.4); }
  const theirs = car('#d9c7a0', 'hatch', true);
  const crate = new THREE.Group(); crate.position.set(0, 1.5, 0.3); theirs.add(crate);
  mesh(new THREE.BoxGeometry(0.9, 0.3, 0.7), MAT.wood('#b08a5c'), crate, 0, 0.15, 0);
  for (let q = 0; q < 6; q++) { const st = candyStick(cols[q % 5], 200 + q, 0.16); st.scale.setScalar(1.6); st.position.set(-0.3 + (q % 3) * 0.3, 0.2, -0.15 + Math.floor(q / 3) * 0.3); crate.add(st); }
  S.add(theirs);
  const cop2 = police(); S.add(cop2);
  for (const ch of [theirs, cop2]) ch.traverse(o => {   // tinted windows and tyres stay dark grey, never pure black
    if (!o.isMesh) return;
    for (const m of [].concat(o.material)) if (m && m.emissive && m.emissive.getHex() === 0) m.emissive.setRGB(0.012, 0.012, 0.014);
  });
  const St = L.stop;
  const D = L.dark;
  const dark = new THREE.Group(); dark.position.set(D[0], 0, D[2]); S.add(dark);
  mesh(new THREE.BoxGeometry(0.9, 0.04, 0.6), smooth('#3a2a22', { roughness: 0.85 }), dark, 0, 0.88, 0);
  for (const [x, z] of [[-0.4, -0.25], [0.4, -0.25], [-0.4, 0.25], [0.4, 0.25]]) mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.86, 16), smooth('#2e221c'), dark, x, 0.43, z);
  const crystM = new THREE.MeshPhysicalMaterial({ color: '#f2c6d2', roughness: 0.1, clearcoat: 1, flatShading: true, envMapIntensity: 1.2, emissive: '#f2c6d2', emissiveIntensity: 0.05 });
  const halves = [-1, 1].map(sd => {
    const h = new THREE.Group(); h.position.y = 0.92; dark.add(h);
    let q = sd > 0 ? 5 : 9; const R = () => ((q = (q * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let n = 0; n < 9; n++) {
      const c = new THREE.Mesh(crystalGeo(0.018 + R() * 0.014, 0.008 + R() * 0.005), crystM);
      c.position.set(sd * (0.004 + R() * 0.022), -0.005 + R() * 0.02, (R() - 0.5) * 0.03); c.rotation.set(R() * 3, R() * 3, R() * 3);
      c.castShadow = true; h.add(c);
    }
    h.side = sd; return h;
  });
  mesh(new THREE.BoxGeometry(2.4, 1.6, 0.05), smooth('#1a2030', { roughness: 0.95, emissive: '#1d2538', emissiveIntensity: 1 }), dark, 0, 0.9, -0.6);
  const darkKey = new THREE.SpotLight('#ffe2c4', 0, 2.0, 0.5, 0.6); darkKey.position.set(D[0] + 0.35, 1.35, D[2] + 0.45); darkKey.target.position.set(D[0], 0.92, D[2]); S.add(darkKey, darkKey.target);
  const arcM = MAT.emissive('#cfe0ff', 6);
  const arc = mesh(new THREE.CylinderGeometry(0.0009, 0.0009, 0.016, 8), arcM, dark, 0, 0.928, 0); arc.rotation.z = Math.PI / 2;
  const arcGlow = haloSprite('#8fb7ff', 0.05, 0); arcGlow.position.set(D[0], 0.928, D[2]); S.add(arcGlow);
  const darkLight = new THREE.PointLight('#9fc0ff', 0, 0.6); darkLight.position.set(D[0], 0.95, D[2] + 0.03); S.add(darkLight);

  // headlight pools at the stop (night): the police car's beams on the road
  const beam = new THREE.SpotLight('#fff1d6', 0, 30, 0.5, 0.6, 1.4); S.add(beam); S.add(beam.target);
  const torchBeam = new THREE.SpotLight('#fff4dc', 0, 8, 0.32, 0.5, 1.2); S.add(torchBeam); S.add(torchBeam.target);
  const fill = new THREE.PointLight('#9fb4ff', 0, 10, 1.6); S.add(fill);

  const S_room = Tm.crack2 + 3.55;
  const fp = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const setOf = i => F.set[Math.min(i, F.set.length - 1)];
  const zCar = t => Tm.z0 - Tm.speed * (t - Tm.t_run);
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(0, 0, 0),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1), set = setOf(i);
      const tw = F.talk_w[k], tn = F.talk_n[k], tc = F.talk_c[k];
      // who is where, per set
      const place = (o, p, ry) => { o.position.set(...p); o.rotation.y = ry; o.visible = true; };
      cop1.setLights(t, set === 'house' ? 1 : 0);
      if (set === 'house') {
        const ending = t >= shot.start && plan.shots.indexOf(shot) === plan.shots.length - 1;
        place(nyx, H.nyx, 0.1);
        place(wiz, H.wizard, 0.35); wiz.visible = ending;
        place(cop, H.cop, 0.55); cop.visible = ending;
        held.visible = ending; if (ending) { cop.updateMatrixWorld(true); held.position.copy(cop.rig.arms[1].el.localToWorld(new THREE.Vector3(0, -0.3, 0.02))); held.rotation.set(0.2, 0, 0.3); }
      } else if (set === 'kitchen') {
        place(wiz, K.wizard, 0.05);
        place(nyx, K.nyx, -0.75); cop.visible = false; held.visible = false;
      } else if (set === 'road') {
        wiz.visible = nyx.visible = cop.visible = false; held.visible = false;
      } else if (set === 'dark') {
        wiz.visible = nyx.visible = cop.visible = false; held.visible = false;
      } else {
        place(wiz, St.wizard, L.yaw.wizard); place(nyx, St.nyx, L.yaw.nyx); place(cop, St.cop, L.yaw.cop);
        held.visible = true;
      }
      if (wiz.rig && wiz.rig.staff) wiz.rig.staff.visible = set !== 'kitchen';
      // kitchen props: pot + steam until the faces beat, then the candy cups; the jar until then too
      const faces = shot.lighting === 'golden';
      pt.g.visible = !faces; pt.bag.visible = !faces; kit.burner.visible = !faces; jr.g.visible = !faces; candy.visible = faces;
      kit.burner.material.emissiveIntensity = 0.6 * F.steam[k];
      pt.spoon.rotation.y = t * 2.2;
      for (const { s, ph } of pt.steam) {
        const u = (ph + t * 0.35) % 1; s.position.set(Math.sin(ph * 17 + t) * 0.05, 0.16 + u * 0.45, Math.cos(ph * 11) * 0.05);
        s.scale.setScalar(0.03 + u * 0.06); s.material.opacity = 0.045 * F.steam[k] * Math.sin(Math.PI * u);
      }
      const gr = F.grow[k];
      for (const c of jr.cr) { const v = Math.max(0, (gr - c.userData.start) / (1 - c.userData.start)); c.visible = v > 0.01; c.scale.setScalar(Math.max(0.01, v)); }
      // characters: lip sync from the recorded lines, blinks, small gestures
      const look = (who, x) => who.pose(x);
      if (set === 'kitchen') {
        look(wiz, { talk: tw, blink: F.blink_w[k], headPitch: 0.12 - 0.12 * Math.min(1, tw * 3), headYaw: tn > 0.05 ? 0.35 : 0.05, point: shot === plan.shots[4] ? 0.4 : 0, t });
        const stare = shot === plan.shots[6];
        look(nyx, { talk: tn, blink: F.blink_n[k], headYaw: stare ? 0.75 : (tw > 0.05 ? -0.35 : 0.2), headTilt: stare ? 0.05 : 0.08, t });
      } else if (set === 'house') {
        look(nyx, { talk: tn, blink: F.blink_n[k], headYaw: -0.1, t });
        look(wiz, { talk: tw, blink: F.blink_w[k], headYaw: 0.3, t });
        cop.pose({ talk: tc, blink: F.blink_c[k], hold: 0.55, headYaw: -0.2 });
      } else if (set === 'stop') {
        look(wiz, { talk: tw, blink: F.blink_w[k], headYaw: tc > 0.05 ? 0.3 : 0.0, wave: shot === plan.shots[13] ? 0.3 : 0, t });
        look(nyx, { talk: tn, blink: F.blink_n[k], headYaw: 0.25, t });
        const bite = F.bite[k];
        const holdUp = shot === plan.shots[11] ? 0.7 : 0.75 + 0.25 * bite;
        cop.pose({ talk: tc, blink: F.blink_c[k], torch: shot === plan.shots[12] ? 0 : 0.85, hold: holdUp, headPitch: shot === plan.shots[11] ? 0.15 : -0.05 });
        cop.updateMatrixWorld(true);
        held.position.copy(cop.rig.arms[1].el.localToWorld(new THREE.Vector3(0, -0.3, 0.02)));
        held.rotation.set(0.25 + 0.4 * bite, cop.rotation.y, 0.25);
      }
      // the chase: both cars along the road, the police car 11 m behind; lights on
      const zc = zCar(t);
      theirs.position.set(RX + 1.8, 0, set === 'road' ? zc : St.car[2]); theirs.rotation.y = 0;
      cop2.position.set(RX + 1.8, 0, set === 'road' ? zc + 11 : St.cop_car[2]);
      if (set === 'stop') { theirs.position.x = St.car[0]; cop2.position.x = St.cop_car[0]; }
      theirs.visible = cop2.visible = (set === 'road' || set === 'stop');
      cop2.setLights(t + 0.37, cop2.visible ? 1 : 0);
      theirs.setBrake(set === 'stop' ? 0.5 : 0.15);
      // the payoff close-up: the crystal splits on "Crack", a spark jumps the gap a few times
      dark.visible = set === 'dark';
      darkKey.intensity = set === 'dark' ? (t < S_room ? 1.6 : 0.7) : 0;   // dimmer for "a really dark room"
      const sp = F.split[k];
      for (const h of halves) { h.position.x = h.side * 0.009 * sp; h.rotation.z = -h.side * 0.12 * sp; }
      let fl = 0;
      if (set === 'dark') for (const te of Tm.tribo_sparks) { const age = t - te; if (age >= 0 && age < 0.12) fl = Math.max(fl, 1 - age / 0.12); }
      arc.visible = fl > 0.02; arc.scale.set(1, 0.4 + 1.1 * sp, 1); arcM.emissiveIntensity = 6 * fl;
      arcGlow.material.opacity = 0.85 * fl; arcGlow.scale.setScalar(0.03 + 0.05 * fl); darkLight.intensity = 0.25 * fl;
      // sparks when the cop bites (a few quick bluish flashes at the crack)
      const mouthP = cop.rig.head.localToWorld(new THREE.Vector3(0, 0.05, 0.12));
      for (let q = 0; q < sparks.length; q++) {
        const te = Tm.sparks[q % Tm.sparks.length] + (q >= Tm.sparks.length ? 0.03 : 0), age = t - te;
        const on = set === 'stop' && age >= 0 && age < 0.14;
        const a = on ? 1 - age / 0.14 : 0;
        const off = new THREE.Vector3(Math.sin(q * 2.3) * 0.02, Math.cos(q * 1.7) * 0.012, 0.01 + (q % 3) * 0.006);
        sparks[q].position.copy(mouthP).add(off); sparks[q].material.opacity = 0.9 * a; sparks[q].scale.setScalar(0.035 + 0.04 * a);
        sparkCore[q].position.copy(sparks[q].position); sparkCore[q].material.opacity = a; sparkCore[q].scale.setScalar(0.012 + 0.01 * a);
      }
      // night lights at the stop: headlight beams, the torch, a soft blue fill from the light bar
      const nightStop = set === 'stop';
      beam.intensity = nightStop ? 40 : 0; beam.position.set(St.cop_car[0], 0.8, St.cop_car[2] - 2.2); beam.target.position.set(St.car[0] + 0.5, 0.3, St.car[2] - 3);
      const torchOn = nightStop && shot !== plan.shots[12] && shot !== plan.shots[11] ? 1 : (shot === plan.shots[11] ? 1 : 0);
      torchBeam.intensity = (shot === plan.shots[11] ? 7 : 18) * torchOn; cop.rig.lens.material.emissiveIntensity = 3 * torchOn;
      cop.updateMatrixWorld(true);
      torchBeam.position.copy(cop.rig.lens.getWorldPosition(new THREE.Vector3()));
      torchBeam.target.position.copy(held.position);
      fill.intensity = nightStop ? (shot === plan.shots[12] ? 0.6 : 2.2) : 0; fill.position.set(St.cop[0] - 1.2, 2.0, St.cop[2] + 1.0);
      if (shot !== lastShot) {
        lastShot = shot;
        const f = fp(i);
        world.setLighting(shot.lighting ?? 'key', new THREE.Vector3(f[0], 0, f[2]));
        moon.intensity = (shot.lighting === 'night') ? (set === 'stop' ? 0.85 : set === 'dark' ? 0.55 : 0.4) : (set === 'road' ? 0.35 : 0);
        if (plan.bloom_threshold) world.bloom.threshold = plan.bloom_threshold;
        const sc = world.sun.shadow.camera, e2 = set === 'road' ? 46 : set === 'house' ? 17 : 7;
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.far = 90; sc.updateProjectionMatrix();
      }
      if (set === 'road') {           // keep the sun's shadow box on the moving cars
        const c = new THREE.Vector3(RX + 1.8, 0, zc + 6);
        world.setLighting('sunset', c);
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...fp(i)));
      world.camera.near = Math.min(0.3, Math.max(0.005, d * 0.02)); world.camera.far = 700; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...fp(i)); },
    probes(i) {
      const f = fp(i), set = setOf(i);
      const entity = set === 'dark' ? 'candy' : set === 'road' ? 'cars' : (f[1] < 1.2 && set === 'kitchen') ? (plan.shots.find(s => i / plan.fps >= s.start && i / plan.fps < s.end)?.lighting === 'golden' ? 'candy' : (Math.abs(f[0] - L.kitchen.jar[0]) < 0.1 ? 'jar' : 'pot')) : 'wizard';
      return [{ entity, part: 'subject', kind: 'thickness', p: f, size: set === 'dark' ? 0.05 : set === 'road' ? 1.5 : (f[1] < 1.2 ? 0.15 : 0.4) }];
    },
    vars() { return {}; },
  };
}

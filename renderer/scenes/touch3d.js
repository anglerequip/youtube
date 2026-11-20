// Your phone can't feel you press it (content/episodes/touchscreen-field/plan.py).
// A 10x-scale diorama: a phone lies face up on a wooden deck. In the cutaway beats its glass turns see-through
// and shows the electrode grid; at one crossing the field lines come straight from the plan (the 2D Laplace
// solution for a ladder of fingertip heights), crossfaded by the plan's fingertip height. A bare fingertip,
// a gloved one and a snack sausage come down onto the glass; the crossing lights red when the model's dip
// passes the touch threshold. This file only draws what the plan computed.
import * as THREE from 'three';
import { PALETTE } from '../world.js';
import { MAT, haloSprite } from '../materials.js';

const flat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, flatShading: true, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

// home screen: muted wallpaper, a grid of rounded app tiles in the house car pastels, a dock
function homeScreen() {
  return canvasTex(512, 1060, (g, w, h) => {
    const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#6f8f8a'); gr.addColorStop(1, '#c9b48e');
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    g.fillStyle = 'rgba(255,255,255,0.85)'; g.font = '700 54px Poppins'; g.textAlign = 'center'; g.fillText('12:30', w / 2, 120);
    const cols = PALETTE.cars;
    for (let r = 0; r < 5; r++) for (let c = 0; c < 4; c++) {
      const x = 40 + c * 118, y = 210 + r * 140;
      g.fillStyle = cols[(r * 4 + c * 3) % cols.length]; g.beginPath(); g.roundRect(x, y, 84, 84, 22); g.fill();
      g.fillStyle = 'rgba(255,255,255,0.55)'; g.beginPath(); g.arc(x + 42, y + 42, 16, 0, 7); g.fill();
    }
    g.fillStyle = 'rgba(255,255,255,0.25)'; g.beginPath(); g.roundRect(24, h - 170, w - 48, 130, 40); g.fill();
    for (let c = 0; c < 4; c++) { g.fillStyle = cols[(c * 2 + 1) % cols.length]; g.beginPath(); g.roundRect(46 + c * 116, h - 148, 84, 84, 22); g.fill(); }
  });
}

function knitTex(base) {
  return canvasTex(256, 256, (g, w, h) => {
    g.fillStyle = base; g.fillRect(0, 0, w, h);
    for (let y = 0; y < h; y += 16) for (let x = 0; x < w; x += 16) {
      g.strokeStyle = 'rgba(40,40,60,0.22)'; g.lineWidth = 3;
      g.beginPath(); g.moveTo(x, y); g.lineTo(x + 8, y + 14); g.lineTo(x + 16, y); g.stroke();
    }
  });
}

// a fingertip pointing down, axis tilted towards -z (the hand is behind the phone); the group origin is the
// lowest point of the tip. The nail faces the camera side (+z). A glove is an opaque knitted shell with a
// wedge cut away on the camera side (a cutaway), so the bare finger inside and the 2 mm of wool both show.
function finger(r, skin = '#e3b89c', gloveCol = null) {
  const g = new THREE.Group(), inner = new THREE.Group(); g.add(inner);
  const len = r * 9;
  let mat, tipG, shaftG;
  if (gloveCol) {
    const map = knitTex(gloveCol); map.wrapS = map.wrapT = THREE.RepeatWrapping; map.repeat.set(3, 3);
    mat = new THREE.MeshStandardMaterial({ map, roughness: 1, side: THREE.DoubleSide });
    const cut = 2.1, face = 0.3;                         // wedge (rad) removed around the camera direction
    const phiC = Math.PI / 2 + face;                     // sphere phi facing roughly +z, a little +x
    tipG = new THREE.SphereGeometry(r, 32, 18, phiC + cut / 2, 2 * Math.PI - cut, Math.PI / 2, Math.PI / 2);
    shaftG = new THREE.CylinderGeometry(r, r, len, 32, 1, true, face + cut / 2, 2 * Math.PI - cut);
  } else {
    mat = MAT.plastic(skin); mat.roughness = 0.55; mat.clearcoat = 0.1;
    tipG = new THREE.SphereGeometry(r, 32, 18, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2);   // lower hemisphere
    shaftG = new THREE.CylinderGeometry(r, r, len, 32, 1, false);
  }
  const tip = new THREE.Mesh(tipG, mat);                 // hemisphere and shaft share radius r: no seam
  const shaft = new THREE.Mesh(shaftG, mat); shaft.position.y = len / 2;
  inner.add(tip, shaft);
  if (!gloveCol) {
    for (const y of [len * 0.36, len * 0.7]) {           // knuckle creases on the back (+z) side only
      const k = new THREE.Mesh(new THREE.TorusGeometry(r * 1.0, r * 0.035, 6, 24, Math.PI * 0.8), flat('#c99a80'));
      k.rotation.x = Math.PI / 2; k.rotation.z = Math.PI * 0.1; k.position.y = y; inner.add(k);
    }
    const nailM = new THREE.MeshStandardMaterial({ color: '#f3d9cf', roughness: 0.25, metalness: 0 });
    const nail = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 14), nailM);
    nail.scale.set(r * 0.56, r * 0.95, r * 0.16); nail.position.set(0, r * 1.3, r * 0.93); inner.add(nail);
  }
  inner.position.y = r;                                  // lowest point of the tip at the group origin
  g.rotation.x = -0.45;
  return shadowed(g);
}

function sausage(r) {
  const g = new THREE.Group(), inner = new THREE.Group(); g.add(inner);
  const m = new THREE.MeshStandardMaterial({ color: '#b5704f', roughness: 0.45, flatShading: false });
  const len = r * 7;
  const body = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 20), m); body.position.y = len / 2 + r;
  const a = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 14), m); a.position.y = r;
  const b = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 14), m); b.position.y = len + r;
  const clip = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.25, r * 0.25, r * 0.6, 8), flat('#e2c45a')); clip.position.y = len + r * 2.1;
  // the gloved fingers holding it
  const gm = new THREE.MeshStandardMaterial({ map: knitTex('#8fa6c8'), roughness: 1 });
  const thumb = new THREE.Mesh(new THREE.CapsuleGeometry(r * 0.75, r * 3, 6, 14), gm); thumb.position.set(r * 1.5, len * 0.82, 0); thumb.rotation.z = 0.4;
  const index = new THREE.Mesh(new THREE.CapsuleGeometry(r * 0.75, r * 3, 6, 14), gm); index.position.set(-r * 1.5, len * 0.85, 0); index.rotation.z = -0.4;
  inner.add(body, a, b, clip, thumb, index);
  g.rotation.x = -0.45;
  return shadowed(g);
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout, sc = L.scale;
  world.ground(600); world.hills(12, 140);
  // wooden deck under the phone: planks with gaps
  const deck = new THREE.Group();
  for (let k = -9; k <= 9; k++) {
    const p = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.06, 7.0), MAT.wood(k % 2 ? '#9a7650' : '#8f6d49'));
    p.position.set(k * 0.45, -0.03, 0); p.receiveShadow = true; deck.add(p);
  }
  deck.position.y = 0.006; S.add(deck);
  const trees = [[-5, -6, 2.2], [4.5, -7, 2.6], [-7.5, -1, 2.0], [7, -2.5, 2.4], [2, -11, 3.0], [-3, -12, 2.8]];
  for (const [x, z, s] of trees) { const t = world.roundTree(x, z, s); world.contactShadow(t, x, z, s); }
  world.conifer(-9, -8, 2.5); world.conifer(9.5, -9, 2.8);

  // ---- the phone: graphite body, glass top with the home screen; under it the display and electrode grid
  const W = L.phone_w, Lz = L.phone_l, T = L.phone_t;
  const phone = new THREE.Group(); phone.position.set(...L.phone); S.add(phone);
  const rr = (w, l, rad) => { const sh = new THREE.Shape(), x = w / 2, z = l / 2;
    sh.moveTo(-x + rad, -z); sh.lineTo(x - rad, -z); sh.quadraticCurveTo(x, -z, x, -z + rad); sh.lineTo(x, z - rad); sh.quadraticCurveTo(x, z, x - rad, z);
    sh.lineTo(-x + rad, z); sh.quadraticCurveTo(-x, z, -x, z - rad); sh.lineTo(-x, -z + rad); sh.quadraticCurveTo(-x, -z, -x + rad, -z); return sh; };
  const bev = 0.008, bodyH = L.elec_y - 0.004 - 2 * bev;
  const bodyG = new THREE.ExtrudeGeometry(rr(W - 2 * bev, Lz - 2 * bev, 0.08), { depth: bodyH, bevelEnabled: true, bevelThickness: bev, bevelSize: bev, bevelSegments: 4, curveSegments: 12 });
  bodyG.rotateX(-Math.PI / 2);                     // extrude upwards (+y), shape in the x-z plane
  const body = new THREE.Mesh(bodyG, new THREE.MeshStandardMaterial({ color: '#4a4f57', roughness: 0.45, metalness: 0.6 }));
  body.position.y = bev; phone.add(body);
  shadowed(phone);
  const display = new THREE.Mesh(new THREE.PlaneGeometry(W * 0.94, Lz * 0.96), new THREE.MeshStandardMaterial({ color: '#121622', roughness: 1.0, envMapIntensity: 0 }));
  display.rotation.x = -Math.PI / 2; display.position.y = L.elev_y ?? (L.elec_y - 0.002); phone.add(display);
  const uiMat = new THREE.MeshStandardMaterial({ map: homeScreen(), roughness: 0.9, envMapIntensity: 0, emissive: '#ffffff', emissiveIntensity: 0.0, transparent: true });
  uiMat.emissiveMap = uiMat.map; uiMat.emissiveIntensity = 0.35;
  const ui = new THREE.Mesh(new THREE.PlaneGeometry(W * 0.94, Lz * 0.96), uiMat); ui.rotation.x = -Math.PI / 2; ui.position.y = L.elec_y - 0.001; phone.add(ui);
  const glassM = new THREE.MeshStandardMaterial({ color: '#dfe8ef', roughness: 0.7, metalness: 0, transparent: true, opacity: 0.1, depthWrite: false, envMapIntensity: 0 });
  const glassG = new THREE.ExtrudeGeometry(rr(W * 0.98, Lz * 0.98, 0.075), { depth: L.glass_top - L.elec_y, bevelEnabled: false, curveSegments: 12 });
  glassG.rotateX(-Math.PI / 2);
  const glass = new THREE.Mesh(glassG, glassM); glass.position.y = L.elec_y; phone.add(glass);
  // electrode grid: drive rows (across x) and sense columns (along z), thin emissive strips
  const rowM = new THREE.MeshStandardMaterial({ envMapIntensity: 0, roughness: 1, color: '#d8d2c2', emissive: '#e8dcc2', emissiveIntensity: 0.0, transparent: true, opacity: 0 });
  const colM = new THREE.MeshStandardMaterial({ envMapIntensity: 0, roughness: 1, color: '#9fc4d8', emissive: '#a9d4ec', emissiveIntensity: 0.0, transparent: true, opacity: 0 });
  const rows = [], cols = [];
  const nRows = 31, nCols = 15;
  for (let r = 0; r < nRows; r++) {
    const z = -Lz * 0.46 + r * (Lz * 0.92 / (nRows - 1));
    const m = new THREE.Mesh(new THREE.BoxGeometry(W * 0.92, 0.0012, 0.006), rowM.clone()); m.position.set(0, L.elec_y - 0.0004, z); phone.add(m); rows.push(m);
  }
  for (let c = 0; c < nCols; c++) {
    const x = -W * 0.44 + c * (W * 0.88 / (nCols - 1));
    const m = new THREE.Mesh(new THREE.BoxGeometry(0.006, 0.0012, Lz * 0.92), colM); m.position.set(x, L.elec_y, 0); phone.add(m); cols.push(m);
  }
  // the watched crossing: a drive pad and a sense pad side by side (the solver's cross-section), and its glow
  const [nx, ny, nz] = L.node, [sw, sg] = L.strip;
  const padD = new THREE.Mesh(new THREE.BoxGeometry(sw, 0.0016, 0.05), new THREE.MeshStandardMaterial({ envMapIntensity: 0, color: '#efe6d0', emissive: '#efe2c4', emissiveIntensity: 0, transparent: true, opacity: 0 }));
  padD.position.set(nx - sg / 2 - sw / 2, L.elec_y, nz);
  const padS = new THREE.Mesh(new THREE.BoxGeometry(sw, 0.0016, 0.05), new THREE.MeshStandardMaterial({ envMapIntensity: 0, color: '#a9d4ec', emissive: '#a9d4ec', emissiveIntensity: 0, transparent: true, opacity: 0 }));
  padS.position.set(nx + sg / 2 + sw / 2, L.elec_y, nz);
  S.add(padD, padS);
  const nodeGlow = haloSprite('#ff3b30', 0.16, 0); nodeGlow.position.set(nx, L.elec_y + 0.004, nz); S.add(nodeGlow);
  const nodeRedM = new THREE.MeshStandardMaterial({ color: '#c92a2e', emissive: '#ff3b30', emissiveIntensity: 0, transparent: true, opacity: 0, depthWrite: false });
  const nodeRed = new THREE.Mesh(new THREE.BoxGeometry(sw * 2 + sg + 0.006, 0.002, 0.056), nodeRedM); nodeRed.position.set(nx, L.elec_y + 0.0002, nz); S.add(nodeRed);

  // ---- field lines: every solved set, three planes along the pads; crossfaded by fingertip height
  const toW = (p, dz) => new THREE.Vector3(nx + p[0] * sc, L.elec_y + p[1] * sc, nz + dz);
  const mkSet = (set) => {
    const g = new THREE.Group(), mats = [], curves = [];
    for (const dz of [-0.016, 0, 0.016]) for (const ln0 of set.lines) {
      const cutAt = ln0.pts.findIndex(p => p[1] > 5.0);           // lines that leave upwards: drawn to 5 mm
      const ln = { ...ln0, pts: cutAt > 0 ? ln0.pts.slice(0, cutAt + 1) : ln0.pts };
      if (ln.pts.length < 3) continue;
      const curve = new THREE.CatmullRomCurve3(ln.pts.map(p => toW(p, dz)));
      const col = ln.end === 'finger' ? '#ffb08a' : '#cfe9ff';
      const m = new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending });
      const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, Math.min(120, ln.pts.length * 2), 0.00035, 6, false), m);
      g.add(tube); mats.push(m); curves.push({ curve, end: ln.end });
    }
    S.add(g); return { gap: set.gap, g, mats, curves };
  };
  const ladder = plan.fields.map(mkSet);               // gaps descending: 99 (no finger), 14 ... skin
  const gloveSet = mkSet(plan.glove_field);
  const beadM = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.9, depthWrite: false });
  const beads = Array.from({ length: 60 }, () => { const b = new THREE.Mesh(new THREE.SphereGeometry(0.0007, 8, 6), beadM); S.add(b); return b; });

  // ---- the three things that come down onto the glass
  const fr = L.finger_r;             // the solver's fingertip radius (5 mm real)
  const fing = finger(fr); S.add(fing);
  const glv = finger(fr + L.glove_mm * sc, '#e3b89c', '#8fa6c8'); S.add(glv);
  const inside = finger(fr); inside.position.y = L.glove_mm * sc; glv.add(inside); inside.rotation.x = 0;   // the bare finger inside the see-through wool
  const saus = sausage(0.055); S.add(saus);
  // touch ring on the glass
  const ringM = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0, depthWrite: false });
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.07, 0.078, 48), ringM); ring.rotation.x = -Math.PI / 2; ring.position.set(nx, L.glass_top + 0.0015, nz); S.add(ring);
  const tapM = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0, depthWrite: false });
  const tapDot = new THREE.Mesh(new THREE.CircleGeometry(0.06, 40), tapM); tapDot.rotation.x = -Math.PI / 2; tapDot.position.set(nx, L.glass_top + 0.001, nz); S.add(tapDot);
  // snow (sausage beat): flakes falling in a box around the phone
  const N = 500, pos = new Float32Array(N * 3), seeds = [];
  for (let k = 0; k < N; k++) seeds.push([world.rand() * 2.4 - 1.2, world.rand(), world.rand() * 2.4 - 1.0, 0.4 + world.rand() * 0.5]);
  const snowG = new THREE.BufferGeometry(); snowG.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const flakeTex = canvasTex(64, 64, (g, w, h) => { const gr = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.55, 'rgba(255,255,255,0.85)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
  const snow = new THREE.Points(snowG, new THREE.PointsMaterial({ color: '#ffffff', size: 0.014, map: flakeTex, transparent: true, opacity: 0.95, depthWrite: false, alphaTest: 0.02 }));
  S.add(snow);

  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  let lastShot = null, touchStart = -1, wasTouched = false;
  return {
    lightCenter: new THREE.Vector3(nx, 0, nz),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.gap.length - 1), cut = F.cut[k], gap = F.gap[k], obj = F.obj[k];
      // cutaway
      uiMat.opacity = 1 - cut; uiMat.emissiveIntensity = 0.35 * (1 - cut); glassM.opacity = 0.1 * (1 - cut) + 0.04; glass.visible = cut < 0.9;
      const gcut = Math.max(0, (cut - 0.45) / 0.55);
      rows.forEach((m, r) => {
        const on = F.scan[k] >= 0 && Math.abs(F.scan[k] - r) < 0.8;
        m.material.opacity = 0.75 * gcut; m.material.emissiveIntensity = gcut * (on ? 2.6 : 0.35);
      });
      colM.opacity = 0.7 * gcut; colM.emissiveIntensity = 0.3 * gcut;
      padD.material.opacity = padS.material.opacity = cut; padD.material.emissiveIntensity = padS.material.emissiveIntensity = 0.9 * cut;
      const node = F.node[k];
      nodeRedM.opacity = 0.9 * node * cut; nodeRedM.emissiveIntensity = 2.2 * node; nodeGlow.material.opacity = 0.75 * node * cut;
      // fingertip, glove, sausage: lowest point at `gap` mm above the glass
      const place = (o, on) => { o.visible = on; if (on) o.position.set(nx, L.glass_top + (obj === 'glove' ? gap - L.glove_mm - L.skin_mm : gap - L.skin_mm) * sc, nz); };
      place(fing, obj === 'finger'); place(glv, obj === 'glove'); place(saus, obj === 'sausage');
      // field: crossfade the two ladder sets that bracket the current height
      const on = F.field[k] ? cut : 0;
      for (const s of ladder) s.mats.forEach(m => { m.opacity = 0; });
      gloveSet.mats.forEach(m => { m.opacity = 0; });
      let dominant = ladder[0];
      if (on > 0) {
        const h = obj ? gap : 99;
        if (F.glove[k] && h <= ladder[5].gap) {                   // gloved: blend the 3 mm set into the solved glove set
          const u = Math.min(1, Math.max(0, (ladder[5].gap - h) / (ladder[5].gap - gloveSet.gap)));
          ladder[5].mats.forEach(m => { m.opacity = 0.85 * on * (1 - u); });
          gloveSet.mats.forEach(m => { m.opacity = 0.85 * on * u; });
          dominant = u > 0.5 ? gloveSet : ladder[5];
        } else {
          let j = ladder.length - 1;
          for (let q = 0; q < ladder.length - 1; q++) if (h >= ladder[q + 1].gap) { j = q; break; }
          const a = ladder[j], b = ladder[Math.min(j + 1, ladder.length - 1)];
          const u = a === b ? 0 : Math.min(1, Math.max(0, (Math.log(a.gap) - Math.log(h)) / (Math.log(a.gap) - Math.log(b.gap))));
          a.mats.forEach(m => { m.opacity = 0.85 * on * (1 - u); }); if (b !== a) b.mats.forEach(m => { m.opacity = 0.85 * on * u; });
          dominant = u > 0.5 ? b : a;
        }
      }
      beads.forEach((b, q) => {
        const c = dominant.curves[q % dominant.curves.length];
        b.visible = on > 0.3 && !!c;
        if (c) b.position.copy(c.curve.getPointAt(((t * 0.55 + q * 0.37) % 1)));
      });
      // touch ring: expands once from each new touch
      const touched = F.ring[k] > 0.5;
      if (touched && !wasTouched) touchStart = t; wasTouched = touched;
      const u = touchStart >= 0 ? (t - touchStart) / 0.6 : 2;
      ring.visible = u < 1; ring.scale.setScalar(1 + 1.4 * Math.max(0, u)); ringM.opacity = 0.9 * (1 - Math.max(0, u));
      tapM.opacity = F.ui_tap[k] ? 0.55 : Math.max(0, tapM.opacity - 0.12);
      // snow
      snow.visible = F.snow[k] > 0;
      if (snow.visible) {
        for (let q = 0; q < N; q++) {
          const [x, y0, z, v] = seeds[q], y = 1.1 - ((y0 + t * v * 0.35) % 1.1);
          pos[q * 3] = nx + x + Math.sin(t * 0.8 + q) * 0.02; pos[q * 3 + 1] = y; pos[q * 3 + 2] = nz + z;
        }
        snowG.attributes.position.needsUpdate = true;
      }
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i), d = world.camera.position.distanceTo(new THREE.Vector3(...fp));
        world.setLighting(shot.lighting ?? 'key', new THREE.Vector3(fp[0], 0, fp[2]));
        world.rim.intensity *= 0.25;     // the rim light's mirror image on the flat glass read as a glare blob
        const s = world.sun.shadow.camera, e = 1.6;
        s.left = -e; s.right = e; s.top = e; s.bottom = -e; s.near = 1; s.far = 80; s.updateProjectionMatrix();
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.05, Math.max(0.003, d * 0.02)); world.camera.far = 500; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const k = Math.min(i, F.gap.length - 1);
      if (F.field[k] && F.cut[k] > 0.5) return [{ entity: 'field', part: 'field line', kind: 'thickness', p: [nx, L.elec_y + 0.01, nz], size: 0.0018 }];
      return [{ entity: 'phone', part: 'phone width', kind: 'thickness', p: [nx, L.glass_top, nz], size: W }];
    },
    vars() { return {}; },
  };
}

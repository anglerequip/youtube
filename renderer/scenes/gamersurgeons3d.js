// Surgeons who game make fewer mistakes (content/episodes/gamer-surgeons/plan.py).
// The shared daylight home set (renderer/sets/home.js). On a coffee table: a keyhole-surgery practice box (grey,
// two small holes in the lid) with two long thin tools that pivot about the holes, a peg board inside with a small
// ring the left tool carries from peg to peg, and a little monitor beside the box showing the inside (drawn from
// the same tool-tip positions). A TV on a low stand against the back wall plays an original abstract game (a small
// ship dodging coloured circles); a game controller lies on the table. This file only draws what the plan lists;
// the tools move only while plan.frames.tools_live is 1 (close shots, hands off frame).
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { home, softBox } from '../sets/home.js';
import { MAT } from '../materials.js';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.8, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };
const sm = x => { const u = Math.min(1, Math.max(0, x)); return u * u * (3 - 2 * u); };

// tool-tip motion inside the box (box-local metres; y up from the board). The left tool carries the ring between two
// pegs on a 3.2 s cycle; the right tool hovers near the target peg, ready to take it. Pure function of time.
export function tips(t, live) {
  const tt = live ? t : 0.0;
  const cyc = (tt % 3.2) / 3.2, go = cyc < 0.5 ? sm(cyc / 0.5) : 1 - sm((cyc - 0.5) / 0.5);
  const A = [-0.07, 0.0, -0.03], B = [0.06, 0.0, 0.04];
  const lift = 0.05 * Math.sin(Math.PI * Math.min(1, Math.max(0, cyc < 0.5 ? cyc / 0.5 : (cyc - 0.5) / 0.5)));
  const L = [A[0] + (B[0] - A[0]) * go, 0.075 + lift, A[2] + (B[2] - A[2]) * go];
  const R = [0.09 + 0.012 * Math.sin(tt * 2.1), 0.09 + 0.01 * Math.sin(tt * 1.3), 0.0 + 0.015 * Math.cos(tt * 1.7)];
  return { L, R, go };
}

function trainer() {
  const g = new THREE.Group();
  const W = 0.44, H = 0.2, D = 0.34, t = 0.012;
  const shell = std('#6f767c', { roughness: 0.55, metalness: 0.1 }), dark = std('#22262b', { roughness: 0.9 });
  // open-front cut view is not needed: the box is closed; its inside is shown on the monitor and in the inner camera shots
  const wall = (w, h, d, x, y, z) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d, 2, 2, 2), shell); m.position.set(x, y, z); g.add(m); return m; };
  wall(W, t, D, 0, t / 2, 0);                                     // floor
  wall(t, H, D, -W / 2 + t / 2, H / 2, 0); wall(t, H, D, W / 2 - t / 2, H / 2, 0);
  wall(W, H, t, 0, H / 2, -D / 2 + t / 2);
  const front = wall(W, H, t, 0, H / 2, D / 2 - t / 2); front.userData.front = true;
  // lid with two holes (ring gaskets) where the tools enter
  const lidM = std('#7c848a', { roughness: 0.5, metalness: 0.15 });
  const shape = new THREE.Shape(); shape.moveTo(-W / 2, -D / 2); shape.lineTo(W / 2, -D / 2); shape.lineTo(W / 2, D / 2); shape.lineTo(-W / 2, D / 2); shape.lineTo(-W / 2, -D / 2);
  const holes = [[-0.11, 0.06], [0.11, 0.06]];
  for (const [x, z] of holes) { const h = new THREE.Path(); h.absarc(x, z, 0.018, 0, Math.PI * 2, true); shape.holes.push(h); }
  const lid = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: t, bevelEnabled: false, curveSegments: 32 }), lidM);
  lid.rotation.x = Math.PI / 2; lid.position.y = H + t; g.add(lid);
  for (const [x, z] of holes) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.02, 0.005, 12, 32), dark); ring.rotation.x = Math.PI / 2; ring.position.set(x, H + t + 0.002, z); g.add(ring);
  }
  // peg board inside
  const board = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.012, 0.18, 2, 1, 2), std('#e5e2d6', { roughness: 0.7 })); board.position.set(0, t + 0.006, 0); g.add(board);
  const pegs = [];
  for (const [x, z] of [[-0.07, -0.03], [0.06, 0.04], [-0.02, 0.05], [0.09, -0.05], [-0.1, 0.05], [0.02, -0.05]]) {
    const p = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.045, 16), std('#c9a77c', { roughness: 0.6 }));
    p.position.set(x, t + 0.012 + 0.022, z); g.add(p); pegs.push([x, z]);
  }
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.011, 0.0035, 12, 32), std('#c92a2e', { roughness: 0.5 }));
  ring.rotation.x = Math.PI / 2; g.add(ring);
  // inner light so the inner camera sees the board
  const lamp = new THREE.PointLight('#fff4e4', 0.05, 0.6, 2); lamp.position.set(0, H - 0.02, 0.05); g.add(lamp);
  // two tools: thin shafts with a jaw at the tip and a ring handle outside
  const steel = std('#b9bdc2', { roughness: 0.5, metalness: 0.5 }), grip = std('#2e8f86', { roughness: 0.6 });
  const tool = () => {
    const tg = new THREE.Group();
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.0035, 0.0035, 1, 24), steel); shaft.position.y = 0.5; tg.add(shaft);   // along +y, scaled to length
    tg.userData.shaft = shaft;
    const jaw1 = new THREE.Mesh(new THREE.ConeGeometry(0.004, 0.018, 16), steel); jaw1.rotation.z = 0.25; jaw1.position.set(0.002, -0.006, 0); tg.add(jaw1);
    const jaw2 = jaw1.clone(); jaw2.rotation.z = -0.25; jaw2.position.x = -0.002; tg.add(jaw2);
    const handle = new THREE.Group(); tg.add(handle); tg.userData.handle = handle;
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.009, 0.011, 0.07, 24), grip); body.position.y = 0.035; handle.add(body);
    for (const s of [-1, 1]) { const loop = new THREE.Mesh(new THREE.TorusGeometry(0.014, 0.004, 12, 32), grip); loop.position.set(s * 0.018, 0.075, 0); loop.rotation.y = Math.PI / 2; handle.add(loop); }
    return tg;
  };
  const tL = tool(), tR = tool(); g.add(tL, tR);
  g.userData = { tL, tR, ring, holes: holes.map(([x, z]) => new THREE.Vector3(x, H + t, z)), front, H, W, D, pegs };
  return shadowed(g);
}

// place a tool so it runs from tip p through hole h and on for `out` metres outside the box
function aimTool(tg, tip, hole, out = 0.3) {
  const dir = new THREE.Vector3().subVectors(hole, tip); const inLen = dir.length(); dir.normalize();
  tg.position.copy(tip);
  tg.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
  const L = inLen + out; tg.userData.shaft.scale.y = L; tg.userData.shaft.position.y = L / 2;
  tg.userData.handle.position.y = L;
}

function gameTexture() {
  const c = document.createElement('canvas'); c.width = 512; c.height = 300;
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const g = c.getContext('2d');
  const cols = ['#e2c45a', '#8fa6c8', '#a99bc4', '#2e8f86', '#e6e3dc'];
  tex.userData.draw = t => {
    g.fillStyle = '#121622'; g.fillRect(0, 0, 512, 300);
    for (let k = 0; k < 40; k++) { const x = (k * 97) % 512, y = ((k * 53) + t * 40 * (1 + (k % 3))) % 300; g.fillStyle = 'rgba(229,226,214,0.35)'; g.fillRect(x, y, 2, 2); }
    for (let k = 0; k < 7; k++) {          // falling coloured circles
      const x = 40 + ((k * 151) % 430), y = ((k * 71 + t * 70) % 340) - 20, r = 12 + (k % 3) * 6;
      g.fillStyle = cols[k % cols.length]; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
    }
    const sx = 256 + 170 * Math.sin(t * 1.3) * Math.cos(t * 0.37);     // the player's little ship
    g.fillStyle = '#e8e6df'; g.beginPath(); g.moveTo(sx, 238); g.lineTo(sx - 18, 272); g.lineTo(sx + 18, 272); g.closePath(); g.fill();
    g.fillStyle = '#c92a2e'; g.fillRect(sx - 4, 272, 8, 8 + 4 * Math.sin(t * 20));
    for (let k = 0; k < 3; k++) { g.fillStyle = '#c92a2e'; g.beginPath(); g.arc(24 + k * 22, 22, 7, 0, Math.PI * 2); g.fill(); }
    tex.needsUpdate = true;
  };
  return tex;
}

function monitorTexture(pegs) {
  const c = document.createElement('canvas'); c.width = 384; c.height = 256;
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const g = c.getContext('2d');
  const X = x => 192 + x * 1100, Z = z => 128 + z * 1100;
  tex.userData.draw = (L, R, ring) => {
    const grd = g.createRadialGradient(192, 128, 20, 192, 128, 230); grd.addColorStop(0, '#d8d2c2'); grd.addColorStop(1, '#5b564c');
    g.fillStyle = grd; g.fillRect(0, 0, 384, 256);
    for (const [x, z] of pegs) { g.fillStyle = 'rgba(0,0,0,0.25)'; g.beginPath(); g.arc(X(x) + 4, Z(z) + 4, 6, 0, Math.PI * 2); g.fill(); g.fillStyle = '#c9a77c'; g.beginPath(); g.arc(X(x), Z(z), 5, 0, Math.PI * 2); g.fill(); }
    g.strokeStyle = '#c92a2e'; g.lineWidth = 5; g.beginPath(); g.arc(X(ring[0]), Z(ring[2]), 12, 0, Math.PI * 2); g.stroke();
    const shaft = (p, hx) => { g.strokeStyle = '#d7dadd'; g.lineWidth = 7; g.beginPath(); g.moveTo(X(p[0]), Z(p[2])); g.lineTo(hx, -20); g.stroke();
                               g.fillStyle = '#9aa0a6'; g.beginPath(); g.arc(X(p[0]), Z(p[2]), 6, 0, Math.PI * 2); g.fill(); };
    shaft(L, 40); shaft(R, 344);
    g.fillStyle = 'rgba(0,0,0,0.0)';
    tex.needsUpdate = true;
  };
  return tex;
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, Lo = plan.layout;
  world.ground(600); world.hills(12, 130);
  const HS = home(world, {});
  // the set's ceiling fill sits right above the wizard here: softer, so his sleeve doesn't flare
  HS.root.traverse(o => { if (o.isPointLight && o.position.y > 2.0) o.position.set(1.4, 2.4, 2.2); });
  // coffee table on the rug
  const table = new THREE.Group(), wood = MAT.wood('#8a6342');
  const top = new THREE.Mesh(softBox(1.05, 0.05, 0.6, 0.25), wood); top.position.y = 0.42; table.add(top);
  for (const [x, z] of [[-0.46, -0.24], [0.46, -0.24], [-0.46, 0.24], [0.46, 0.24]]) {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.02, 0.4, 24), wood); leg.position.set(x, 0.2, z); table.add(leg);
  }
  table.position.set(...Lo.table); S.add(shadowed(table));
  const TY = Lo.table[1] + 0.445;
  const box = trainer(); box.position.set(Lo.table[0] + Lo.box_dx, TY, Lo.table[2]); S.add(box);
  // monitor on a small stand beside the box, facing the camera side (+z) and turned a little toward the box
  const mon = new THREE.Group();
  const bez = new THREE.Mesh(softBox(0.4, 0.27, 0.03, 0.2), std('#22262b', { roughness: 0.6 })); bez.position.y = 0.24; mon.add(bez);
  const mtex = monitorTexture(box.userData.pegs);
  const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.36, 0.235), new THREE.MeshBasicMaterial({ map: mtex, toneMapped: false })); scr.position.set(0, 0.24, 0.017); mon.add(scr);
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.12, 16), std('#3a3640')); neck.position.y = 0.07; mon.add(neck);
  const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.08, 0.012, 32), std('#3a3640')); foot.position.y = 0.006; mon.add(foot);
  mon.position.set(Lo.table[0] + Lo.mon_dx, TY, Lo.table[2] - 0.08); mon.rotation.y = -0.35; S.add(shadowed(mon));
  // game controller on the table (original rounded shape)
  const pad = new THREE.Group();
  const pb = new THREE.Mesh(softBox(0.16, 0.035, 0.09, 0.8), std('#3a3640', { roughness: 0.6 })); pad.add(pb);
  for (const s of [-1, 1]) { const grip = new THREE.Mesh(new THREE.SphereGeometry(0.035, 24, 16), std('#3a3640', { roughness: 0.6 })); grip.scale.set(1, 0.55, 1.2); grip.position.set(s * 0.065, -0.004, 0.03); pad.add(grip); }
  for (const [x, z, c] of [[0.045, -0.01, '#c92a2e'], [0.06, 0.008, '#e2c45a'], [0.03, 0.008, '#8fa6c8']]) { const b = new THREE.Mesh(new THREE.CylinderGeometry(0.007, 0.007, 0.01, 16), std(c)); b.position.set(x, 0.02, z); pad.add(b); }
  const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, 0.012, 16), std('#22262b')); stick.position.set(-0.04, 0.022, -0.005); pad.add(stick);
  pad.position.set(Lo.table[0] - 0.38, TY + 0.018, Lo.table[2] + 0.12); pad.rotation.y = 0.4; S.add(shadowed(pad));
  // TV on a low stand against the back wall
  const tvg = new THREE.Group();
  const stand = new THREE.Mesh(softBox(0.95, 0.4, 0.38, 0.2), MAT.wood('#6e4f36')); stand.position.y = 0.2; tvg.add(stand);
  const tvb = new THREE.Mesh(softBox(0.92, 0.55, 0.05, 0.15), std('#1c1f24', { roughness: 0.5 })); tvb.position.y = 0.72; tvg.add(tvb);
  const gtex = gameTexture();
  const tvs = new THREE.Mesh(new THREE.PlaneGeometry(0.86, 0.5), new THREE.MeshBasicMaterial({ map: gtex, toneMapped: false })); tvs.position.set(0, 0.72, 0.027); tvg.add(tvs);
  tvg.position.set(...Lo.tv); tvg.rotation.y = Lo.tv_yaw; S.add(shadowed(tvg));

  const wiz = man(); wiz.position.set(...Lo.wiz); wiz.rotation.y = Lo.wiz_face; S.add(wiz);
  const wom = woman(); wom.position.set(...Lo.woman); wom.rotation.y = Lo.woman_face; S.add(wom);
  const lift = new THREE.Color('#3a3640').convertSRGBToLinear();
  for (const p of [wiz, wom]) p.traverse(o => {
    if (o.isSprite || o.isPointLight) { o.visible = false; return; }   // the staff crystal's glow sprite
    if (!o.isMesh) return;
    if (/^z_(staff|stone|fork)/.test(o.name)) { o.visible = false; return; }
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    if (mats.some(m => m && m.emissive && m.emissiveIntensity > 0 && (m.emissive.r + m.emissive.g + m.emissive.b) > 0.05)) { o.visible = false; return; }   // the staff crystal blooms; no staff here
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || !m.color || m.isMeshBasicMaterial) continue;
      if (Math.max(m.color.r, m.color.g, m.color.b) < lift.r) { m.color.r = Math.max(m.color.r, lift.r); m.color.g = Math.max(m.color.g, lift.g); m.color.b = Math.max(m.color.b, lift.b); }
    }
  });

  // only the room casts shadows: the garden trees beyond the window would fall off the small indoor shadow box
  S.updateMatrixWorld(true);
  const wp = new THREE.Vector3();
  S.traverse(o => { if (o.isMesh && o.castShadow) { o.getWorldPosition(wp); if (!(wp.x > -2.2 && wp.x < 4 && wp.z > -3 && wp.z < 3)) o.castShadow = false; } });
  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const v = new THREE.Vector3();
  const headLook = (person, target, maxYaw = 0.9, eye = 1.5) => {
    v.set(...target).sub(person.position);
    let yaw = Math.atan2(v.x, v.z) - person.rotation.y; yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    const pitch = -Math.atan2(target[1] - person.position.y - eye, Math.hypot(v.x, v.z));
    return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, yaw)), headPitch: Math.max(-0.45, Math.min(0.5, pitch)) };
  };
  const wizHead = [Lo.wiz[0], 1.65, Lo.wiz[2]], womHead = [Lo.woman[0], 1.55, Lo.woman[2]];
  const boxPt = [box.position.x, TY + 0.2, box.position.z], tvPt = [Lo.tv[0], 0.72, Lo.tv[2]];
  const U = box.userData, tipL = new THREE.Vector3(), tipR = new THREE.Vector3();
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(1.0, 0, 0.0),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      const live = F.tools_live[k] > 0;
      const tp = tips(t, live);
      tipL.set(...tp.L); tipR.set(...tp.R);
      aimTool(U.tL, tipL, U.holes[0]); aimTool(U.tR, tipR, U.holes[1]);
      const ringP = tp.go > 0.02 && tp.go < 0.98 ? [tp.L[0], tp.L[1] - 0.008, tp.L[2]] : (tp.go >= 0.98 ? [0.06, 0.025, 0.04] : [-0.07, 0.025, -0.03]);
      U.ring.position.set(...ringP);
      U.front.visible = F.cutaway[k] < 0.5;          // the inner camera shots look in through the (hidden) front wall
      mtex.userData.draw(tp.L, tp.R, ringP);
      gtex.userData.draw(t);
      const lw = F.look_w[k], lm = F.look_m[k];
      const tw = lw === 'woman' ? womHead : lw === 'tv' ? tvPt : boxPt;
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, ...headLook(wiz, tw, 0.9, 1.6), headTilt: 0.04 * Math.sin(t * 0.7), point: F.wiz_point[k] });
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, ...headLook(wom, lm === 'box' ? boxPt : wizHead, 0.5), headTilt: 0.05 * Math.sin(t * 0.9 + 1), point: F.woman_point[k] });
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i);
        world.setLighting(shot.lighting ?? 'key', new THREE.Vector3(fp[0], 0, fp[2]));
        if (plan.bloom_threshold) world.bloom.threshold = plan.bloom_threshold;   // setLighting resets it
        const sc = world.sun.shadow.camera, e2 = 5;
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.far = 80; sc.updateProjectionMatrix();
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.05, Math.max(0.004, d * 0.02)); world.camera.far = 500; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      return [{ entity: 'trainer', part: 'subject', kind: 'thickness', p: boxPt, size: 0.2 }];
    },
    vars() { return {}; },
  };
}

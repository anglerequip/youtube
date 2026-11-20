// Why your cat stares while you eat (content/episodes/cat-stare/plan.py).
// A small round table on a garden patio: the wizard with a sandwich, an orange tabby on a stool staring at it,
// and the woman across the table. Cutaways in the long grass: a lone cat stalking a mouse, a mother cat with
// a mouse for her kittens, two grown cats passing in silence. This file only draws what the plan lists.
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { cat, mouse } from '../cat.js';
import { MAT, haloSprite } from '../materials.js';

const std = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.8, ...x });
const shadowed = g => { g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return g; };

function table(S, L) {
  const g = new THREE.Group(), metal = std('#3b3f45', { metalness: 0.6, roughness: 0.45 });
  const top = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.36, 0.03, 64), MAT.wood('#a27a52'));
  top.position.y = L.table[1] - 0.015; g.add(top);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(0.36, 0.008, 12, 64), metal); rim.rotation.x = Math.PI / 2; rim.position.y = L.table[1] - 0.02; g.add(rim);
  const post = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.03, L.table[1] - 0.05, 24), metal); post.position.y = (L.table[1] - 0.05) / 2 + 0.02; g.add(post);
  const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.24, 0.03, 48), metal); foot.position.y = 0.035; g.add(foot);
  S.add(shadowed(g));
}

function stool(S, L) {
  const g = new THREE.Group(), wood = MAT.wood('#8a6342');
  const seat = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.16, 0.04, 48), wood); seat.position.y = L.cat[1] - 0.02; g.add(seat);
  for (let k = 0; k < 4; k++) {
    const a = k * Math.PI / 2 + Math.PI / 4;
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.02, L.cat[1] - 0.02, 16), wood);
    leg.position.set(Math.cos(a) * 0.12, (L.cat[1] - 0.02) / 2 + 0.04, Math.sin(a) * 0.12); leg.rotation.set(Math.sin(a) * 0.12, 0, -Math.cos(a) * 0.12); g.add(leg);
  }
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.13, 0.008, 10, 40), wood); ring.rotation.x = Math.PI / 2; ring.position.y = 0.3; g.add(ring);
  g.position.set(L.stool[0], 0.04, L.stool[2]); S.add(shadowed(g));
}

function sandwich() {
  const g = new THREE.Group();
  const bread = std('#e2c48c', { roughness: 0.95 }), crust = std('#b9864b', { roughness: 0.95 });
  const slab = (y, m) => {
    const geo = new THREE.BoxGeometry(0.11, 0.014, 0.11, 6, 2, 6);
    const P = geo.attributes.position;
    for (let i = 0; i < P.count; i++) { const x = P.getX(i), z = P.getZ(i); P.setY(i, P.getY(i) + (Math.abs(x) + Math.abs(z) < 0.02 ? 0 : 0) + 0.002 * Math.cos(x * 30)); }
    geo.computeVertexNormals();
    const o = new THREE.Mesh(geo, m); o.position.y = y; g.add(o); return o;
  };
  slab(0.008, bread); slab(0.046, bread);
  const crustBand = (y) => { const c = new THREE.Mesh(new THREE.BoxGeometry(0.114, 0.016, 0.114), crust); c.position.y = y; c.scale.set(1, 0.9, 1); g.add(c); };
  crustBand(0.008); crustBand(0.046);
  const ham = new THREE.Mesh(new THREE.CylinderGeometry(0.062, 0.062, 0.008, 48), std('#d98f8a', { roughness: 0.6 })); ham.position.y = 0.022; ham.scale.set(1, 1, 0.92); g.add(ham);
  const cheese = new THREE.Mesh(new THREE.BoxGeometry(0.105, 0.005, 0.105), std('#f0c94e', { roughness: 0.5 })); cheese.position.y = 0.029; cheese.rotation.y = 0.5; g.add(cheese);
  const lettuce = new THREE.Mesh(new THREE.CylinderGeometry(0.068, 0.066, 0.006, 24), std('#8fb44a', { roughness: 0.7 })); lettuce.position.y = 0.035; g.add(lettuce);
  const P = lettuce.geometry.attributes.position;
  for (let i = 0; i < P.count; i++) { const a = Math.atan2(P.getZ(i), P.getX(i)); const r = Math.hypot(P.getX(i), P.getZ(i)); if (r > 0.05) P.setY(i, P.getY(i) + 0.004 * Math.sin(a * 11)); }
  lettuce.geometry.computeVertexNormals();
  g.rotation.y = 0.4; return shadowed(g);
}

// long-grass tufts (thin tapered blades) so the cutaways read as a field, not a lawn
function grassPatch(S, cx, cz, r, n, seed) {
  let s = seed; const R = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const geo = new THREE.ConeGeometry(0.012, 1, 5, 1); geo.translate(0, 0.5, 0);
  const mats = ['#6f7a35', '#7d8c3e', '#5d6a2c', '#8c9355'].map(c => std(c, { roughness: 1, flatShading: true }));
  const per = Math.ceil(n / mats.length);
  mats.forEach((m, k) => {
    const im = new THREE.InstancedMesh(geo, m, per), M = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
    for (let i = 0; i < per; i++) {
      const a = R() * Math.PI * 2, d = Math.sqrt(R()) * r, h = 0.1 + R() * 0.16;
      e.set((R() - 0.5) * 0.5, R() * 3, (R() - 0.5) * 0.5); q.setFromEuler(e);
      M.compose(new THREE.Vector3(cx + Math.cos(a) * d, 0, cz + Math.sin(a) * d), q, new THREE.Vector3(1, h, 1)); im.setMatrixAt(i, M);
    }
    im.castShadow = false; im.receiveShadow = true; S.add(im);
  });
}

export function build(world, plan) {
  const S = world.scene, F = plan.frames, L = plan.layout;
  world.ground(600); world.hills(12, 130);
  // patio: pale paving slab under the table
  const patio = new THREE.Mesh(new THREE.CylinderGeometry(2.0, 2.05, 0.04, 64), MAT.concrete('#cbc3b1'));
  patio.position.y = 0.02; patio.receiveShadow = true; S.add(patio);
  table(S, L); stool(S, L);
  const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.085, 0.012, 48), std('#f2efe8', { roughness: 0.3 }));
  plate.position.set(L.plate[0], L.table[1] + 0.006, L.plate[2]); plate.castShadow = plate.receiveShadow = true; S.add(plate);
  const sw = sandwich(); sw.position.set(L.plate[0], L.table[1] + 0.012, L.plate[2]); S.add(sw);
  const glass = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.026, 0.11, 32, 1, true), new THREE.MeshPhysicalMaterial({ color: '#e8f0f2', transparent: true, opacity: 0.35, roughness: 0.05 }));
  glass.position.set(0.2, L.table[1] + 0.055, -0.12); S.add(glass);

  const wiz = man(); wiz.position.set(...L.wiz); wiz.rotation.y = Math.PI / 2; S.add(wiz);
  const wom = woman(); wom.position.set(...L.woman); wom.rotation.y = -Math.PI / 2 + 0.12; S.add(wom);
  // pure black never appears in the house style (and reads as a hole on a phone): lift near-black fabric
  // and hair to a deep charcoal, so the woman's black outfit still reads black but keeps its folds
  const lift = new THREE.Color('#3a3640').convertSRGBToLinear();
  for (const p of [wiz, wom]) p.traverse(o => {
    if (!o.isMesh) return;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || !m.color || m.isMeshBasicMaterial) continue;
      if (Math.max(m.color.r, m.color.g, m.color.b) < lift.r) { m.color.r = Math.max(m.color.r, lift.r); m.color.g = Math.max(m.color.g, lift.g); m.color.b = Math.max(m.color.b, lift.b); }
    }
  });

  const tom = cat(); tom.position.set(...L.cat); tom.rotation.y = L.cat_face; S.add(tom);
  // the crumbs that fall from the sandwich onto the table edge, right under the cat's nose
  const crumbM = std('#d8b47a', { roughness: 0.95 });
  const crumbs = [0, 1].map(k => { const c = new THREE.Mesh(new THREE.IcosahedronGeometry(0.008, 2), crumbM); c.castShadow = true; S.add(c); return c; });
  const crumbFrom = new THREE.Vector3(L.plate[0] + 0.05, L.table[1] + 0.05, L.plate[2] - 0.05);
  const crumbTo = [new THREE.Vector3(L.cat[0] - 0.02, L.table[1] + 0.006, -0.28), new THREE.Vector3(L.cat[0] - 0.06, L.table[1] + 0.006, -0.27)];

  // field cutaways behind the patio
  grassPatch(S, L.hunt[0], L.hunt[2], 1.6, 900, 5); grassPatch(S, L.den[0], L.den[2], 1.4, 700, 9); grassPatch(S, L.pass[0], L.pass[2], 1.6, 800, 13);
  const hunter = cat({ coat: '#8a8178', stripe: '#4e4741', iris: '#c9b24a' }); hunter.position.set(L.hunt[0] + 0.5, 0, L.hunt[2] + 0.35); S.add(hunter);
  const prey = mouse(); prey.position.set(L.hunt[0] - 0.25, 0, L.hunt[2] - 0.1); prey.rotation.y = 0.8; S.add(prey);
  const mum = cat({ coat: '#f0e6d6', stripe: '#c9b8a0', iris: '#8fb0c9' }); mum.position.set(L.den[0] - 0.55, 0, L.den[2] + 0.1); mum.rotation.y = Math.PI / 2; S.add(mum);
  const gift = mouse(); gift.visible = false; S.add(gift);
  const kits = [0, 1].map(k => {
    const c = cat({ coat: k ? '#d58a43' : '#efe6d8', stripe: k ? '#a2561f' : '#d0c2ac', scale: 0.52, iris: '#7fa3c8' });
    c.position.set(L.den[0] + 0.25, 0, L.den[2] - 0.12 + k * 0.24); c.rotation.y = -Math.PI / 2 + (k ? -0.25 : 0.25); S.add(c); return c;
  });
  const passA = cat({ coat: '#3b3734', stripe: '#252220', iris: '#d6c050' });
  const passB = cat({ coat: '#c9a77c', stripe: '#8a6a48', iris: '#9cb56a' });
  S.add(passA, passB);

  // the purr: a ribbon of beads beside the cat's head, a soft wave with a sharp red cry inside it
  const beadN = 90, beads = [];
  const beadGeo = new THREE.SphereGeometry(0.0028, 12, 8);
  const calm = new THREE.MeshBasicMaterial({ color: '#f4f0e6', transparent: true, opacity: 0 });
  const cry = new THREE.MeshBasicMaterial({ color: '#ff3b30', transparent: true, opacity: 0 });
  const ribbon = new THREE.Group(); S.add(ribbon);
  for (let k = 0; k < beadN; k++) { const b = new THREE.Mesh(beadGeo, k >= 52 && k < 66 ? cry : calm); ribbon.add(b); beads.push(b); }
  const cryGlow = haloSprite('#ff3b30', 0.05, 0); ribbon.add(cryGlow);

  // garden: trees, a shed and a hedge, sparse
  for (const [x, z, s] of [[-3.2, -3.5, 1.5], [3.4, -4.2, 1.8], [-5.5, 1.5, 1.4], [5.0, 0.5, 1.6], [1.2, -9.5, 2.1], [-2.5, -11, 2.0], [10, -7, 1.8], [-10, -9, 2.0]]) {
    const t = world.roundTree(x, z, s); world.contactShadow(t, x, z, s);
  }
  for (const [x, z, s] of [[-7.5, -3.5, 2.0], [9.5, -11, 2.3], [4.2, -12, 1.9]]) world.contactShadow(world.conifer(x, z, s), x, z, s * 0.7);
  const shed = new THREE.Group();
  const walls = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.3, 1.2), std('#e6e3dc', { flatShading: true })); walls.position.y = 0.65; shed.add(walls);
  const roof = new THREE.Mesh(new THREE.ConeGeometry(1.25, 0.6, 4), std('#8a6a48', { flatShading: true })); roof.position.y = 1.6; roof.rotation.y = Math.PI / 4; roof.scale.set(1, 1, 0.8); shed.add(roof);
  shed.position.set(-4.8, 0, -1.2); shed.rotation.y = 1.2; S.add(shadowed(shed)); world.contactShadow(shed, -4.8, -1.2, 1.3);

  const focalPt = i => F.focal_pt[Math.min(i, F.focal_pt.length - 1)];
  const v = new THREE.Vector3();
  const headLook = (person, target, maxYaw = 0.9) => {
    v.set(...target).sub(person.position);
    const yaw = Math.atan2(v.x, v.z) - person.rotation.y;
    const w = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    const pitch = -Math.atan2(target[1] - person.position.y - 1.55, Math.hypot(v.x, v.z));
    return { headYaw: Math.max(-maxYaw, Math.min(maxYaw, w)), headPitch: Math.max(-0.3, Math.min(0.45, pitch)) };
  };
  const catHead = [L.cat[0], L.cat[1] + 0.3, L.cat[2]];
  const wizHead = [L.wiz[0], 1.62, L.wiz[2]], womHead = [L.woman[0], 1.52, L.woman[2]];
  let lastShot = null;
  return {
    lightCenter: new THREE.Vector3(0, 0, 0),
    groundY: 0,
    update(i, t, shot) {
      const k = Math.min(i, F.talk_w.length - 1);
      // presenters: mouths follow the voice; heads turn to whoever matters
      const lw = F.look_w[k] === 'cat' ? headLook(wiz, catHead) : headLook(wiz, womHead);
      wiz.pose({ talk: F.talk_w[k], blink: F.wiz_blink[k], t, ...lw, headTilt: 0.04 * Math.sin(t * 0.7) });
      const camPos = world.camera.position.toArray();
      const lm = F.look_m[k] === 'camera' ? headLook(wom, camPos) : headLook(wom, wizHead);
      wom.pose({ talk: F.talk_m[k], blink: F.woman_blink[k], t, ...lm, headTilt: 0.05 * Math.sin(t * 0.9 + 1), point: F.look_m[k] === 'camera' ? 0.0 : 0.0 });
      // the house cat
      tom.pose({ mode: 'sit', t, yaw: F.cat_yaw[k], pitch: F.cat_pitch[k], blink: F.cat_blink[k], mouth: F.cat_mouth[k], tail: 0.2, pupil: 1.6 });
      // crumbs fall in a short arc and are gone once eaten
      for (const [q, key] of [[0, 'crumb1'], [1, 'crumb2']]) {
        const u = F[key][k], c = crumbs[q];
        c.visible = u > 0;
        if (u > 0) { c.position.lerpVectors(crumbFrom, crumbTo[q], u); c.position.y = crumbFrom.y + (crumbTo[q].y - crumbFrom.y) * u * u + 0.04 * Math.sin(Math.PI * u); }
      }
      // lone hunter: a slow creep, then a frozen crouch
      const h = F.hunt[k];
      const creep = Math.min(1, h / 3.0);
      hunter.position.set(L.hunt[0] + 0.5 - 0.42 * creep, 0, L.hunt[2] + 0.35 - 0.3 * creep);
      hunter.rotation.y = Math.atan2(prey.position.x - hunter.position.x, prey.position.z - hunter.position.z);
      hunter.pose({ mode: 'crouch', t, walk: creep < 1 ? h * 3.2 : undefined, pupil: 2.2, tail: creep >= 1 ? 0.7 : 0.1, pitch: 0.12 });
      prey.position.y = 0; prey.rotation.y = 0.8 + 0.2 * Math.sin(t * 2);
      // mother: walks in with a mouse in her mouth, drops it before the kittens
      const d = F.den[k], walk = Math.min(1, d / 1.4);
      mum.position.set(L.den[0] - 0.55 + 0.45 * walk, 0, L.den[2] + 0.02);
      mum.pose({ mode: walk < 1 ? 'stand' : 'sit', t, walk: walk < 1 ? d * 6 : undefined, pitch: walk < 1 ? 0.3 : 0.15, mouth: walk < 1 ? 0.35 : 0.0 });
      gift.visible = d > 0;
      if (d > 0) {
        mum.updateMatrixWorld(true);
        if (walk < 1) { mum.userData.head.getWorldPosition(v); gift.position.set(v.x + 0.06, v.y - 0.05, v.z); gift.rotation.set(0, Math.PI / 2, 0.4); }
        else { gift.position.set(L.den[0] + 0.03, 0, L.den[2] + 0.02); gift.rotation.set(0, 1.9, 0); }
      }
      kits.forEach((c, q) => c.pose({ mode: 'sit', t: t + q, pitch: d > 1.4 ? 0.45 : -0.15, mouth: F.kit_mouth[k] * (q ? 1 : 0.8), yaw: 0.2 * Math.sin(t * 1.5 + q) }));
      // two grown cats pass each other without a sound
      const p = F.pass[k], u = Math.min(1, p / 5.6);
      passA.position.set(L.pass[0] - 0.45 + 0.9 * u, 0, L.pass[2] + 0.12); passA.rotation.y = Math.PI / 2;
      passB.position.set(L.pass[0] + 0.45 - 0.9 * u, 0, L.pass[2] - 0.12); passB.rotation.y = -Math.PI / 2;
      passA.pose({ mode: 'stand', t, walk: p * 6, yaw: Math.abs(u - 0.5) < 0.12 ? 0.35 : 0, pitch: 0.05 });
      passB.pose({ mode: 'stand', t: t + 2, walk: p * 6 + 1, yaw: Math.abs(u - 0.5) < 0.12 ? -0.35 : 0, pitch: 0.05 });
      // purr ribbon
      const pr = F.purr[k];
      const vis = pr > 0;
      ribbon.visible = vis;
      if (vis) {
        const cp = world.camera.position;
        ribbon.position.set(L.cat[0] + 0.13, L.cat[1] + 0.34, L.cat[2] + 0.06);
        ribbon.lookAt(cp.x, ribbon.position.y, cp.z);
        const grow = Math.min(1, pr / 0.8);
        for (let q = 0; q < beadN; q++) {
          const x = (q / (beadN - 1) - 0.5) * 0.17, inCry = q >= 52 && q < 66;
          const amp = inCry ? 0.022 * Math.sin(Math.PI * (q - 52) / 13) : 0.006;
          const y = amp * Math.sin(q * (inCry ? 1.9 : 0.55) - pr * 9);
          beads[q].position.set(x, y, 0);
          beads[q].visible = q / beadN <= grow;
        }
        const op = Math.min(1, pr / 0.3);
        calm.opacity = 0.9 * op; cry.opacity = op;
        cryGlow.position.set((59 / (beadN - 1) - 0.5) * 0.17, 0, 0); cryGlow.material.opacity = 0.5 * op; cryGlow.scale.setScalar(0.07);
      }
      if (shot !== lastShot) {
        lastShot = shot;
        const fp = focalPt(i);
        world.setLighting(shot.lighting ?? 'key', new THREE.Vector3(fp[0], 0, fp[2]));
        if (plan.bloom_threshold) world.bloom.threshold = plan.bloom_threshold;
        const sc = world.sun.shadow.camera, e2 = 13;
        sc.left = -e2; sc.right = e2; sc.top = e2; sc.bottom = -e2; sc.far = 80; sc.updateProjectionMatrix();
      }
    },
    afterCamera(i) {
      const d = world.camera.position.distanceTo(new THREE.Vector3(...focalPt(i)));
      world.camera.near = Math.min(0.05, Math.max(0.005, d * 0.02)); world.camera.far = 500; world.camera.updateProjectionMatrix();
    },
    focal(i) { return new THREE.Vector3(...focalPt(i)); },
    probes(i) {
      const fp = focalPt(i);
      return [{ entity: fp[1] < 0.5 ? 'field' : 'cat', part: 'subject', kind: 'thickness', p: fp, size: 0.25 }];
    },
    vars() { return {}; },
  };
}

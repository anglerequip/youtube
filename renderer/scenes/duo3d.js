// Style test for the optional DUO module (docs/styles/DUO.md): our two presenters play a short
// skeptic-vs-explainer exchange around one real physics moment (two balls of different mass dropped
// together land together). Not an episode. Every asset is procedural and our own.
//
// Plan fields used: lines [{who:'man'|'woman', start, end}], drop {release, slow, h}, and per shot:
// look ('man'|'woman'|'camera'|'balls') for who the woman/man face, react (0..1), bigBall (bool).
import * as THREE from 'three';
import { man, woman } from '../characters.js';
import { PALETTE } from '../world.js';
import { MAT } from '../materials.js';

const flat = (c, x = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.8, metalness: 0, flatShading: true, ...x });

export function build(world, plan) {
  const S = world.scene, G = 9.81;
  world.ground(); world.hills && world.hills();
  const deck = 0.08;
  const patio = new THREE.Mesh(new THREE.BoxGeometry(4.2, deck, 3.4, 8, 1, 8), MAT.concrete('#cbc3b0'));
  patio.position.set(0, deck / 2, -0.2); patio.receiveShadow = true; patio.castShadow = true; S.add(patio);
  // workbench behind them, crate beside the woman (holds the "bigger ball" for the last beat)
  const top = world.box(1.8, 0.06, 0.7, PALETTE.wood, -0.1, deck + 0.9, -1.05);
  for (const [x, z] of [[-0.9, -1.3], [0.7, -1.3], [-0.9, -0.8], [0.7, -0.8]]) world.box(0.06, 0.9, 0.06, PALETTE.woodDark, x, deck + 0.45, z);
  world.box(0.5, 0.42, 0.5, '#9a7650', 1.35, deck + 0.21, -0.5);
  for (const [x, z, s] of [[-6, -7, 1.6], [7, -9, 1.9], [-9, -16, 2.2], [4, -18, 1.7], [11, -4, 1.4], [-3, -12, 1.3]]) world.roundTree(x, z, s);
  for (const [x, z, s] of [[-12, -10, 1.6], [13, -14, 2], [9, -22, 2.3]]) world.conifer(x, z, s);
  void top;

  const M = man(), W = woman();
  M.position.set(-0.42, deck, 0.05); M.rotation.y = 0.75;
  W.position.set(0.42, deck, 0.0); W.rotation.y = -0.6;
  S.add(M, W);

  // the two balls: same material family, clearly different size and mass
  const ballGeo = r => new THREE.SphereGeometry(r, 48, 36);
  const heavy = new THREE.Mesh(ballGeo(0.11), flat(PALETTE.red, { roughness: 0.45, flatShading: false }));
  const light = new THREE.Mesh(ballGeo(0.055), flat('#e6e3dc', { roughness: 0.5, flatShading: false }));
  const giant = new THREE.Mesh(ballGeo(0.24), flat('#c92a2e', { roughness: 0.5, flatShading: false }));
  for (const b of [heavy, light, giant]) { b.castShadow = true; b.receiveShadow = true; S.add(b); }

  const wristOf = elbow => elbow.children.find(c => c.isGroup);
  const wR = wristOf(W.rig.elbowR), wL = wristOf(W.rig.elbowL);
  const hold = new THREE.Vector3();
  const D = plan.drop;
  let start = null;                 // world positions at release (fixed once computed)

  const lineAt = t => plan.lines.find(l => t >= l.start && t < l.end);
  const talkCurve = (t, seed) => Math.max(0, Math.sin(t * 12.5 + seed) * 0.6 + Math.sin(t * 5.3 + seed * 2) * 0.4) * 0.85;

  function holdArms(P, amount, wide = 0) {
    // both forearms forward, palms up, as if presenting something
    P.rig.armR.rotation.set(-0.55 * amount, 0, -0.12 - 0.25 * wide);
    P.rig.armL.rotation.set(-0.55 * amount, 0, 0.12 + 0.25 * wide);
    P.rig.elbowR.rotation.set(-0.95 * amount, 0, 0);
    P.rig.elbowL.rotation.set(-0.95 * amount, 0, 0);
  }
  const yawTo = (P, target) => {   // head yaw (local) that turns P's face toward a world point
    const d = target.clone().sub(P.position); const a = Math.atan2(d.x, d.z) - P.rotation.y;
    return THREE.MathUtils.clamp(Math.atan2(Math.sin(a), Math.cos(a)), -0.55, 0.55);
  };

  return {
    lightCenter: new THREE.Vector3(0, 0, 0),
    update(i, t, shot) {
      const line = lineAt(t);
      const camPos = new THREE.Vector3(...(shot.pos0 ?? [0, 1.4, 3]));
      const faceM = new THREE.Vector3(M.position.x, 1.62, M.position.z), faceW = new THREE.Vector3(W.position.x, 1.5, W.position.z);
      const lookTarget = (who, other) => shot.look === 'camera' ? camPos : shot.look === 'balls' ? new THREE.Vector3(0.45, 0.2, 0.4) : other;
      const blink = k => ((t + k) % 3.4) < 0.11 ? 1 : 0;
      // man: calm explainer. Talks on his lines, otherwise watches her.
      const mTalk = line && line.who === 'man' ? talkCurve(t, 1) : 0;
      M.pose({ t, talk: mTalk, blink: blink(0.7), point: shot.manPoint ?? 0,
        headYaw: yawTo(M, shot.look === 'balls' ? new THREE.Vector3(0.45, 0.2, 0.4) : faceW), headPitch: shot.look === 'balls' ? 0.25 : 0,
        headTilt: line && line.who === 'man' ? 0.05 * Math.sin(t * 1.7) : 0 });
      // woman: confident skeptic. Holds the balls until the drop; deadpan to camera on the reaction.
      const wTalk = line && line.who === 'woman' ? talkCurve(t, 2) : 0;
      W.pose({ t, talk: wTalk, blink: blink(0), headYaw: yawTo(W, lookTarget('woman', faceM)),
        headPitch: shot.look === 'balls' ? 0.3 : 0, headTilt: (shot.react ?? 0) * 0.16 });
      const holding = t < D.release;
      if (holding) holdArms(W, 1);
      else if (shot.bigBall) holdArms(W, 0.85, 0.9);
      else { const u = Math.min(1, (t - D.release) / 0.4); holdArms(W, 1 - u); }

      // balls in hand
      W.updateMatrixWorld(true);
      if (holding) {
        wR.localToWorld(hold.set(0, -0.06, 0.07)); heavy.position.copy(hold).add(new THREE.Vector3(0, 0.1, 0));
        wL.localToWorld(hold.set(0, -0.06, 0.06)); light.position.copy(hold).add(new THREE.Vector3(0, 0.05, 0));
        start = null;
      } else {
        if (!start) {               // deterministic: recompute the release pose at exactly t = release
          holdArms(W, 1); W.updateMatrixWorld(true);
          const a = new THREE.Vector3(), b = new THREE.Vector3();
          wR.localToWorld(a.set(0, -0.06, 0.07)); a.y += 0.1; wL.localToWorld(b.set(0, -0.06, 0.06)); b.y += 0.05;
          start = { heavy: a, light: b };
          if (!shot.bigBall) { const u = Math.min(1, (t - D.release) / 0.4); holdArms(W, 1 - u); }
        }
        const tp = (t - D.release) / D.slow;          // physical time since release (slow motion)
        for (const [b, s, r] of [[heavy, start.heavy, 0.11], [light, start.light, 0.055]]) {
          const y = s.y - 0.5 * G * tp * tp;
          b.position.set(s.x, Math.max(deck + r, y), s.z);
        }
      }
      giant.visible = !!shot.bigBall;
      if (shot.bigBall) { W.updateMatrixWorld(true); const a = new THREE.Vector3(), b = new THREE.Vector3();
        wR.localToWorld(a.set(0, -0.05, 0)); wL.localToWorld(b.set(0, -0.05, 0));
        giant.position.copy(a.add(b).multiplyScalar(0.5)).add(new THREE.Vector3(0, 0.02, 0.24)); }
    },
    focal: () => new THREE.Vector3(0, 1.1, 0),
  };
}

// landing times for the self-check (physical seconds after release)
export function landTimes(h0Heavy, h0Light, deck = 0.08) {
  const G = 9.81;
  return { heavy: Math.sqrt(2 * (h0Heavy - deck - 0.11) / G), light: Math.sqrt(2 * (h0Light - deck - 0.055) / G) };
}

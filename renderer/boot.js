// Loads a scene module, builds it, and exposes renderFrame(i) -> JPEG data URL.
import * as THREE from 'three';
import { enrichMaterials, groundCover } from './look.js';
import { World, drawCard, drawWordmark, drawBadge } from './world.js';
import { inspectFrame, staticChecks } from './inspect.js';
import { drawOverlays } from './overlays.js';

export async function boot(sceneName, plan) {
  await document.fonts.load('800 40px Poppins'); await document.fonts.load('700 40px Poppins');
  const { W, H } = plan;
  const gl = document.createElement('canvas'); gl.width = W; gl.height = H;
  const out = document.createElement('canvas'); out.width = W; out.height = H; document.body.appendChild(out);
  const ctx = out.getContext('2d');
  const world = new World(gl, W, H, plan.seed ?? 7, { supersample: plan.supersample ?? 1, look: plan.look, dof: plan.dof, ao: plan.ao, grade: plan.grade, drift: plan.drift, aoDebug: plan.ao_debug });
  const mod = await import(`/renderer/scenes/${sceneName}.js`);
  const scene = mod.build(world, plan);

  if (world.look && plan.surface_variation !== false) enrichMaterials(world.scene);
  const cover = world.look && plan.ground_cover !== false
    ? groundCover(world, plan, typeof plan.ground_cover === 'object' ? plan.ground_cover : {}) : null;
  window.__meta = {};
  const pose = i => {           // put the world in its state for frame i (shared by render and inspect)
    const t = i / plan.fps;
    const shot = plan.shots.find(s => t >= s.start && t < s.end) ?? plan.shots[plan.shots.length - 1];
    if (shot.lighting && shot.lighting !== world.lightingName) {
      world.setLighting(shot.lighting, scene.lightCenter);
      if (plan.bloom_threshold) world.bloom.threshold = plan.bloom_threshold;   // per-episode override (e.g. no specular bloom)
    }
    scene.update(i, t, shot);
    world.applyShot(shot, t, i);
    if (scene.afterCamera) scene.afterCamera(i, t, shot);
    if (world.look) {           // Look v3: auto-focus on the scene's focus target, the shot's focus, or the aim point
      let f = scene.focus ? scene.focus(i, t, shot) : (shot.focus ?? null);
      if (Array.isArray(f)) f = new THREE.Vector3(...f);
      const dist = typeof f === 'number' ? f : world.camera.position.distanceTo(f ?? world.lookTarget);
      world.look.update(i, dist, shot.dof ?? 1);
      if (cover) cover.uTime.value = t;
    }
    return { t, shot };
  };
  window.inspectStatic = () => staticChecks(world);
  window.inspectFrame = i => {
    const { shot } = pose(i);
    world.prepare();
    world.scene.updateMatrixWorld(true); world.camera.updateMatrixWorld(true);
    return inspectFrame(world, scene, plan, i, shot);
  };
  window.renderFrame = (i, quality = 0.93) => {
    const { t, shot } = pose(i);
    world.render();
    if (scene.focal) {           // render metadata for QC (focal object position on screen)
      const p = scene.focal(i).clone().project(world.camera);
      window.__meta[i] = { y: +(0.5 - p.y / 2).toFixed(4), x: +(0.5 + p.x / 2).toFixed(4), cut: shot.start };
    }
    ctx.imageSmoothingQuality = "high"; ctx.drawImage(gl, 0, 0, W, H);
    for (const card of plan.cards ?? []) {
      if (t < card.start || t >= card.end) continue;
      const a = Math.min(1, (t - card.start) / 0.15, (card.end - t) / 0.15);
      const u = Math.min(1, (t - card.start) / 0.35), c1 = 1.7;   // spring-like scale-in (easeOutBack)
      card.scale = 0.85 + 0.15 * (1 + (c1 + 1) * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2));
      const vars = scene.vars ? scene.vars(i, t) : {};
      const fill = s => (s ?? '').replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
      drawCard(ctx, W, H, { ...card, big: fill(card.big), small: fill(card.small) }, a);
    }
    if (plan.overlays) drawOverlays(ctx, W, H, plan.overlays, t, world);   // opt-in building blocks (renderer/overlays.js)
    if (plan.frames && plan.frames.badge) drawBadge(ctx, W, H, plan.frames.badge[Math.min(i, plan.frames.badge.length - 1)]);
    if (plan.wordmark) drawWordmark(ctx, W, H, plan.wordmark);
    return out.toDataURL('image/jpeg', quality);
  };
  return { frames: plan.n_frames };
}

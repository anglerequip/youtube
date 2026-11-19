// Loads a scene module, builds it, and exposes renderFrame(i) -> JPEG data URL.
import * as THREE from 'three';
import { World, drawCard, drawWordmark, drawBadge } from './world.js';

export async function boot(sceneName, plan) {
  await document.fonts.load('800 40px Poppins'); await document.fonts.load('700 40px Poppins');
  const { W, H } = plan;
  const gl = document.createElement('canvas'); gl.width = W; gl.height = H;
  const out = document.createElement('canvas'); out.width = W; out.height = H; document.body.appendChild(out);
  const ctx = out.getContext('2d');
  const world = new World(gl, W, H, plan.seed ?? 7);
  const mod = await import(`/renderer/scenes/${sceneName}.js`);
  const scene = mod.build(world, plan);

  window.__meta = {};
  window.renderFrame = (i, quality = 0.93) => {
    const t = i / plan.fps;
    const shot = plan.shots.find(s => t >= s.start && t < s.end) ?? plan.shots[plan.shots.length - 1];
    if (shot.lighting && shot.lighting !== world.lightingName) world.setLighting(shot.lighting, scene.lightCenter);
    scene.update(i, t, shot);
    world.applyShot(shot, t, i);
    if (scene.afterCamera) scene.afterCamera(i, t, shot);
    world.render();
    if (scene.focal) {           // render metadata for QC (focal object position on screen)
      const p = scene.focal(i).clone().project(world.camera);
      window.__meta[i] = { y: +(0.5 - p.y / 2).toFixed(4), x: +(0.5 + p.x / 2).toFixed(4), cut: shot.start };
    }
    ctx.drawImage(gl, 0, 0);
    for (const card of plan.cards ?? []) {
      if (t < card.start || t >= card.end) continue;
      const a = Math.min(1, (t - card.start) / 0.15, (card.end - t) / 0.15);
      const vars = scene.vars ? scene.vars(i, t) : {};
      const fill = s => (s ?? '').replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
      drawCard(ctx, W, H, { ...card, big: fill(card.big), small: fill(card.small) }, a);
    }
    if (plan.frames && plan.frames.badge) drawBadge(ctx, W, H, plan.frames.badge[Math.min(i, plan.frames.badge.length - 1)]);
    if (plan.wordmark) drawWordmark(ctx, W, H, plan.wordmark);
    return out.toDataURL('image/jpeg', quality);
  };
  return { frames: plan.n_frames };
}

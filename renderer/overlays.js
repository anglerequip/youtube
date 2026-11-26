// Reusable 2D overlay building blocks drawn on top of the 3D frame (docs/styles/BUILD.md, DUO.md).
// All opt-in: a plan lists them in `overlays: [...]`, each with start/end seconds and a `type`.
// Anything with `at: [x, y, z]` is pinned to a point in the 3D world (projected every frame, so it
// follows the camera); `xy: [0..1, 0..1]` pins it to the screen instead. Every design here is ours.
//
//   callout  leader-line label pointing at a part      {at, text, dx, dy}
//   pill     rounded badge with an icon + bold word    {text, icon: check|clock|snow|lock|warn|drop|none, xy, accent}
//   gauge    thermometer-style meter, level animates  {at|xy, label, from, to, color0, color1}
//   arrows   four arrows around a point, in or out    {at, mode: 'in'|'out', r}
//   dim      dimension bracket between two points     {a, b, text}
//   xmark    red X in a thin ring ("blocked/wrong")   {at, r}
//   ring     thin highlight ring that draws itself    {at, r}
//   flash    full-frame white (or colour) flash        {color, peak}
//   tint     full-frame colour wash (night, cold)      {color, alpha}
//   tension  horizontal line-tension meter, per-frame  {xy, values, fps, max, marks: [{v, text, color}], label, unit, over}
import * as THREE from 'three';

const ACCENT = '#f2c94c';           // our badge outline (warm yellow), never neon
const INK = 'rgba(18,20,24,0.88)';  // badge fill
const RED = '#e5484d';

const ease = u => 1 - Math.pow(1 - Math.min(1, Math.max(0, u)), 3);
const fadeA = (t, o, f = 0.18) => Math.min(1, (t - o.start) / f, (o.end - t) / f);

function project(world, p, W, H) {
  const v = new THREE.Vector3(...p).project(world.camera);
  return { x: (v.x + 1) / 2 * W, y: (1 - v.y) / 2 * H, behind: v.z > 1 };
}
const where = (world, o, W, H, key = 'at') => o[key] ? project(world, o[key], W, H)
  : { x: (o.xy?.[0] ?? 0.5) * W, y: (o.xy?.[1] ?? 0.2) * H, behind: false };

function label(ctx, text, x, y, px, align = 'center') {
  ctx.font = `800 ${px}px Poppins`; ctx.textAlign = align; ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round'; ctx.lineWidth = px * 0.28; ctx.strokeStyle = 'rgba(15,16,20,0.85)';
  ctx.strokeText(text, x, y); ctx.fillStyle = '#ffffff'; ctx.fillText(text, x, y);
}

function arrowHead(ctx, x, y, ang, s) {
  ctx.beginPath(); ctx.moveTo(x, y);
  ctx.lineTo(x - s * Math.cos(ang - 0.45), y - s * Math.sin(ang - 0.45));
  ctx.lineTo(x - s * Math.cos(ang + 0.45), y - s * Math.sin(ang + 0.45)); ctx.closePath(); ctx.fill();
}

function icon(ctx, kind, x, y, r) {
  ctx.save(); ctx.translate(x, y);
  if (kind === 'check') {
    ctx.fillStyle = '#3fb950'; ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = r * 0.3; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(-r * 0.45, 0); ctx.lineTo(-r * 0.1, r * 0.35); ctx.lineTo(r * 0.5, -r * 0.35); ctx.stroke();
  } else if (kind === 'clock') {
    ctx.fillStyle = ACCENT; ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.fill();
    ctx.strokeStyle = '#2a2a2a'; ctx.lineWidth = r * 0.2; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, -r * 0.6); ctx.moveTo(0, 0); ctx.lineTo(r * 0.45, r * 0.2); ctx.stroke();
  } else if (kind === 'snow') {
    ctx.strokeStyle = '#ffffff'; ctx.lineWidth = r * 0.22; ctx.lineCap = 'round';
    for (let k = 0; k < 3; k++) { const a = k * Math.PI / 3; ctx.beginPath(); ctx.moveTo(-r * Math.cos(a), -r * Math.sin(a)); ctx.lineTo(r * Math.cos(a), r * Math.sin(a)); ctx.stroke(); }
  } else if (kind === 'lock') {
    ctx.fillStyle = ACCENT; ctx.fillRect(-r * 0.7, -r * 0.1, r * 1.4, r * 1.1);
    ctx.strokeStyle = ACCENT; ctx.lineWidth = r * 0.25; ctx.beginPath(); ctx.arc(0, -r * 0.15, r * 0.45, Math.PI, 0); ctx.stroke();
  } else if (kind === 'warn') {
    ctx.fillStyle = RED; ctx.beginPath(); ctx.moveTo(0, -r); ctx.lineTo(r, r * 0.8); ctx.lineTo(-r, r * 0.8); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.fillRect(-r * 0.09, -r * 0.35, r * 0.18, r * 0.6); ctx.fillRect(-r * 0.09, r * 0.38, r * 0.18, r * 0.18);
  } else if (kind === 'drop') {
    ctx.fillStyle = '#5aa9e6'; ctx.beginPath(); ctx.moveTo(0, -r); ctx.quadraticCurveTo(r, r * 0.2, 0, r); ctx.quadraticCurveTo(-r, r * 0.2, 0, -r); ctx.fill();
  }
  ctx.restore();
}

const DRAW = {
  callout(ctx, W, H, o, t, world) {
    const p = where(world, o, W, H); if (p.behind) return;
    const u = ease((t - o.start) / 0.35), px = Math.round(H * 0.022);
    const lx = p.x + (o.dx ?? 0.0) * W, ly = p.y + (o.dy ?? -0.09) * H;   // label sits above-left by default
    const ex = lx + (p.x - lx) * u, ey = ly + 10 + (p.y - ly - 10) * u;
    ctx.strokeStyle = '#ffffff'; ctx.fillStyle = '#ffffff'; ctx.lineWidth = Math.max(1.5, H * 0.0015);
    ctx.shadowColor = 'rgba(0,0,0,0.45)'; ctx.shadowBlur = 4;
    ctx.beginPath(); ctx.moveTo(lx, ly + px * 0.8); ctx.lineTo(ex, ey); ctx.stroke();
    if (u > 0.98) arrowHead(ctx, ex, ey, Math.atan2(ey - ly, ex - lx), H * 0.009);
    ctx.shadowColor = 'transparent'; label(ctx, o.text, lx, ly, px);
  },
  pill(ctx, W, H, o, t, world) {
    const p = where(world, o, W, H);
    const px = Math.round(H * 0.024), u = (t - o.start) / 0.3, c1 = 1.7;
    const sc = u >= 1 ? 1 : 0.8 + 0.2 * (1 + (c1 + 1) * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2));
    ctx.font = `800 ${px}px Poppins`; const tw = ctx.measureText(o.text).width;
    const hasIcon = (o.icon ?? 'none') !== 'none', ir = px * 0.42;
    const w = tw + px * 1.1 + (hasIcon ? ir * 2.6 : 0), h = px * 1.7;
    ctx.save(); ctx.translate(p.x, p.y); ctx.scale(sc, sc);
    ctx.fillStyle = INK; ctx.strokeStyle = o.accent ?? ACCENT; ctx.lineWidth = Math.max(2, H * 0.0022);
    ctx.beginPath(); ctx.roundRect(-w / 2, -h / 2, w, h, h * 0.32); ctx.fill(); ctx.stroke();
    let x = -w / 2 + px * 0.55;
    if (hasIcon) { icon(ctx, o.icon, x + ir, 0, ir); x += ir * 2.6; }
    ctx.fillStyle = '#ffffff'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillText(o.text, x, px * 0.04);
    ctx.restore();
  },
  gauge(ctx, W, H, o, t, world) {
    const p = where(world, o, W, H); if (p.behind) return;
    const u = ease((t - o.start) / Math.max(0.3, (o.end - o.start) * 0.7));
    const lvl = (o.from ?? 0.8) + ((o.to ?? 0.2) - (o.from ?? 0.8)) * u;
    const c = new THREE.Color(o.color0 ?? '#e8813a').lerp(new THREE.Color(o.color1 ?? '#4fb3e8'), u).getStyle();
    const tubeH = H * 0.065, tubeW = H * 0.009, bulb = H * 0.013, x = p.x, top = p.y - tubeH / 2;
    ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.beginPath(); ctx.roundRect(x - tubeW, top, tubeW * 2, tubeH, tubeW); ctx.fill();
    ctx.beginPath(); ctx.arc(x, top + tubeH + bulb * 0.6, bulb + tubeW * 0.5, 0, 7); ctx.fill();
    ctx.fillStyle = c; const fillH = (tubeH - tubeW) * lvl;
    ctx.fillRect(x - tubeW * 0.55, top + tubeH - fillH, tubeW * 1.1, fillH + bulb * 0.4);
    ctx.beginPath(); ctx.arc(x, top + tubeH + bulb * 0.6, bulb, 0, 7); ctx.fill();
    ctx.strokeStyle = 'rgba(40,40,40,0.5)'; ctx.lineWidth = 1;
    for (let k = 1; k < 6; k++) { const y = top + tubeH * k / 6; ctx.beginPath(); ctx.moveTo(x - tubeW, y); ctx.lineTo(x - tubeW * 0.3, y); ctx.stroke(); }
    // label with a short leader to the left of the tube top
    ctx.strokeStyle = '#ffffff'; ctx.lineWidth = Math.max(1.5, H * 0.0013);
    ctx.beginPath(); ctx.moveTo(x - tubeW * 1.2, top + 4); ctx.lineTo(x - tubeW * 3.5, top + 4); ctx.stroke();
    label(ctx, o.label ?? '', x - tubeW * 4, top + 4, Math.round(H * 0.018), 'right');
  },
  // a horizontal meter whose level follows a per-frame list from the plan (values[i] at i / fps), with labelled
  // marks (e.g. the reel's drag setting and the line's breaking strength). `subs` (per-frame, optional) is a short note
  // in the top row, between the label and the value. `over` (per-frame, optional) draws an
  // overflow arrow past the end of the scale with its own text, for "this would be far off the chart".
  tension(ctx, W, H, o, t) {
    const i = Math.max(0, Math.min(o.values.length - 1, Math.round(t * (o.fps ?? 30))));
    const v = o.values[i], max = o.max ?? 1, x0 = (o.xy?.[0] ?? 0.5) * W, y0 = (o.xy?.[1] ?? 0.2) * H;
    const bw = W * 0.62, bh = H * 0.016, left = x0 - bw / 2;
    ctx.shadowColor = 'rgba(0,0,0,0.35)'; ctx.shadowBlur = 10;
    ctx.fillStyle = 'rgba(229,226,214,0.94)'; ctx.beginPath(); ctx.roundRect(left - W * 0.035, y0 - H * 0.04, bw + W * 0.07, H * 0.085, H * 0.014); ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = 'rgba(40,44,52,0.25)'; ctx.beginPath(); ctx.roundRect(left, y0, bw, bh, bh / 2); ctx.fill();
    const u = Math.max(0, Math.min(1, v / max));
    const red = (o.marks ?? []).find(m => m.color === 'red');
    ctx.fillStyle = red && v >= red.v ? RED : '#2e8f86';
    if (u > 0) { ctx.beginPath(); ctx.roundRect(left, y0, Math.max(bh, bw * u), bh, bh / 2); ctx.fill(); }
    for (const m of o.marks ?? []) {
      const x = left + bw * Math.min(1, m.v / max);
      ctx.fillStyle = m.color === 'red' ? RED : '#c58a12';
      ctx.fillRect(x - 2.5, y0 - bh * 0.7, 5, bh * 2.4);
      ctx.font = `800 ${Math.round(H * 0.0155)}px Poppins`; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      ctx.fillText(m.text, x, y0 + bh * 1.9);
    }
    ctx.fillStyle = '#3a3a3a'; ctx.font = `700 ${Math.round(H * 0.0145)}px Poppins`; ctx.textAlign = 'left'; ctx.textBaseline = 'bottom';
    ctx.fillText(o.label ?? '', left, y0 - bh * 0.5);
    ctx.textAlign = 'right'; ctx.fillStyle = ctx.fillStyle;
    const sub = o.subs ? o.subs[i] : null;          // optional per-frame note under the scale (e.g. line paying out)
    if (sub) { ctx.fillStyle = '#c58a12'; ctx.font = `800 ${Math.round(H * 0.0145)}px Poppins`; ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
               ctx.fillText(sub, left + bw * 0.55, y0 - bh * 0.5); }
    ctx.fillStyle = '#3a3a3a'; ctx.font = `700 ${Math.round(H * 0.0145)}px Poppins`; ctx.textBaseline = 'bottom';
    const ov = o.over ? o.over[i] : null;
    ctx.fillText(ov ? '' : `${v.toFixed(1)} ${o.unit ?? ''}`, left + bw, y0 - bh * 0.5);
    if (ov) {                                         // pegged: an arrow off the end of the scale
      ctx.fillStyle = RED; const ax = left + bw + W * 0.012;
      ctx.beginPath(); ctx.moveTo(ax, y0 - bh * 0.5); ctx.lineTo(ax + W * 0.03, y0 + bh / 2); ctx.lineTo(ax, y0 + bh * 1.5); ctx.closePath(); ctx.fill();
      ctx.font = `800 ${Math.round(H * 0.017)}px Poppins`; ctx.textAlign = 'right'; ctx.fillText(ov, left + bw, y0 - bh * 0.5);
    }
  },
  arrows(ctx, W, H, o, t, world) {
    const p = where(world, o, W, H); if (p.behind) return;
    const r = (o.r ?? 0.07) * H, s = H * 0.022, pulse = 0.12 * Math.sin((t - o.start) * 9);
    ctx.fillStyle = RED; ctx.strokeStyle = RED; ctx.lineWidth = H * 0.006; ctx.lineCap = 'round';
    for (const a of [-2.36, -0.79, 0.79, 2.36]) {
      const inward = (o.mode ?? 'in') === 'in';
      const r0 = r * (1.35 + pulse), r1 = r * (0.95 + pulse);
      const [ra, rb] = inward ? [r0, r1] : [r1, r0];
      const x0 = p.x + ra * Math.cos(a), y0 = p.y + ra * Math.sin(a), x1 = p.x + rb * Math.cos(a), y1 = p.y + rb * Math.sin(a);
      ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); arrowHead(ctx, x1, y1, Math.atan2(y1 - y0, x1 - x0), s);
    }
  },
  dim(ctx, W, H, o, t, world) {
    const a = project(world, o.a, W, H), b = project(world, o.b, W, H); if (a.behind || b.behind) return;
    const u = ease((t - o.start) / 0.4), bx = a.x + (b.x - a.x) * u, by = a.y + (b.y - a.y) * u;
    const ang = Math.atan2(b.y - a.y, b.x - a.x), nx = -Math.sin(ang) * H * 0.008, ny = Math.cos(ang) * H * 0.008;
    ctx.strokeStyle = '#fff'; ctx.lineWidth = Math.max(1.5, H * 0.0015); ctx.shadowColor = 'rgba(0,0,0,0.45)'; ctx.shadowBlur = 4;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(bx, by);
    ctx.moveTo(a.x - nx, a.y - ny); ctx.lineTo(a.x + nx, a.y + ny); ctx.moveTo(bx - nx, by - ny); ctx.lineTo(bx + nx, by + ny); ctx.stroke();
    ctx.shadowColor = 'transparent';
    if (u > 0.6) label(ctx, o.text, (a.x + b.x) / 2 - nx * 4 - H * 0.02, (a.y + b.y) / 2, Math.round(H * 0.02), 'right');
  },
  xmark(ctx, W, H, o, t, world) {
    const p = where(world, o, W, H); if (p.behind) return;
    const r = (o.r ?? 0.03) * H, u = ease((t - o.start) / 0.25);
    ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = Math.max(1.5, H * 0.0015);
    ctx.beginPath(); ctx.arc(p.x, p.y, r * 1.5, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * u); ctx.stroke();
    ctx.strokeStyle = RED; ctx.lineWidth = r * 0.32; ctx.lineCap = 'round'; const k = r * 0.7 * u;
    ctx.beginPath(); ctx.moveTo(p.x - k, p.y - k); ctx.lineTo(p.x + k, p.y + k); ctx.moveTo(p.x + k, p.y - k); ctx.lineTo(p.x - k, p.y + k); ctx.stroke();
  },
  ring(ctx, W, H, o, t, world) {
    const p = where(world, o, W, H); if (p.behind) return;
    const r = (o.r ?? 0.06) * H, u = ease((t - o.start) / 0.45);
    ctx.strokeStyle = 'rgba(255,255,255,0.92)'; ctx.lineWidth = Math.max(1.5, H * 0.0018);
    ctx.shadowColor = 'rgba(0,0,0,0.4)'; ctx.shadowBlur = 5;
    ctx.beginPath(); ctx.arc(p.x, p.y, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * u); ctx.stroke();
  },
  flash(ctx, W, H, o, t) {
    const d = o.end - o.start, u = (t - o.start) / d, a = (o.peak ?? 0.9) * (u < 0.3 ? u / 0.3 : (1 - u) / 0.7);
    ctx.globalAlpha *= Math.max(0, a); ctx.fillStyle = o.color ?? '#ffffff'; ctx.fillRect(0, 0, W, H);
  },
  tint(ctx, W, H, o) { ctx.globalAlpha *= o.alpha ?? 0.35; ctx.fillStyle = o.color ?? '#0b1530'; ctx.fillRect(0, 0, W, H); },
};

export function drawOverlays(ctx, W, H, overlays, t, world) {
  for (const o of overlays ?? []) {
    if (t < o.start || t >= o.end) continue;
    const fn = DRAW[o.type]; if (!fn) continue;
    ctx.save(); ctx.globalAlpha = o.type === 'flash' ? 1 : Math.max(0, fadeA(t, o)); fn(ctx, W, H, o, t, world); ctx.restore();
  }
}
export const OVERLAY_TYPES = Object.keys(DRAW);

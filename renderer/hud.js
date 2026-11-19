// HUD overlay (factory/retention/hud.py compiles it; this file only draws it).
// House style (CLAUDE.md Blueprint 7): off-white rounded cards with a soft shadow, one strong colour (red)
// for the number that matters, thin white lines and rings on the world. Sparing: QA limits how many show.
import * as THREE from 'three';

const _v = new THREE.Vector3();
function project(camera, p, W, H) {
  _v.set(p[0], p[1], p[2]).project(camera);
  if (_v.z > 1 || _v.z < -1) return null;
  return [(_v.x * 0.5 + 0.5) * W, (0.5 - _v.y * 0.5) * H];
}

function fade(w, i) { return Math.max(0, Math.min(1, (i - w.i0 + 1) / 6, (w.i1 - i) / 6)); }

function pill(ctx, x, y, w, h, st, r) {
  ctx.shadowColor = 'rgba(0,0,0,0.26)'; ctx.shadowBlur = h * 0.35; ctx.shadowOffsetY = h * 0.08;
  ctx.fillStyle = st.card; ctx.beginPath(); ctx.roundRect(x, y, w, h, r ?? h * 0.22); ctx.fill();
  ctx.shadowColor = 'transparent';
}

// label (small, muted) above a big red value, in one card centred at (cx, cy)
function valueCard(ctx, W, H, cx, cy, label, value, st, scale = 1) {
  const bigPx = Math.round(H * 0.034), smallPx = Math.round(H * 0.017);
  ctx.font = `800 ${bigPx}px Poppins`; const wb = ctx.measureText(value).width;
  ctx.font = `700 ${smallPx}px Poppins`; const ws = ctx.measureText(label).width;
  const padX = H * 0.02, padY = H * 0.011, w = Math.max(wb, ws) + padX * 2;
  const h = (label ? smallPx * 1.25 : 0) + bigPx * 1.12 + padY * 2;
  ctx.save(); ctx.translate(cx, cy); ctx.scale(scale, scale); ctx.translate(-cx, -cy);
  const x = cx - w / 2, y = cy - h / 2;
  pill(ctx, x, y, w, h, st, H * 0.008);
  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  if (label) { ctx.fillStyle = st.muted; ctx.font = `700 ${smallPx}px Poppins`; ctx.fillText(label, cx, y + padY); }
  ctx.fillStyle = st.accent; ctx.font = `800 ${bigPx}px Poppins`;
  ctx.fillText(value, cx, y + padY + (label ? smallPx * 1.25 : 0));
  ctx.restore();
  return { x, y, w, h };
}

function textPill(ctx, cx, cy, text, st, H, color, icon) {
  const px = Math.round(H * 0.021); ctx.font = `700 ${px}px Poppins`;
  const tw = ctx.measureText(text).width, ic = icon ? px * 1.35 : 0, padX = px * 0.8, h = px * 2.0;
  const w = tw + padX * 2 + ic, x = cx - w / 2, y = cy - h / 2;
  pill(ctx, x, y, w, h, st, h / 2);
  if (icon) {
    const r = px * 0.52, ix = x + padX + r, iy = cy;
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(ix, iy, r, 0, 7); ctx.fill();
    ctx.strokeStyle = st.card; ctx.fillStyle = st.card; ctx.lineWidth = px * 0.14; ctx.lineCap = 'round';
    if (icon === 'check') { ctx.beginPath(); ctx.moveTo(ix - r * 0.45, iy); ctx.lineTo(ix - r * 0.1, iy + r * 0.38); ctx.lineTo(ix + r * 0.48, iy - r * 0.35); ctx.stroke(); }
    else { ctx.font = `800 ${Math.round(px * 0.85)}px Poppins`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('?', ix, iy + 1); }
  }
  ctx.fillStyle = color; ctx.font = `700 ${px}px Poppins`; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(text, x + padX + ic, cy + 1);
}

function worldLine(ctx, a, b, H, alpha) {
  ctx.save(); ctx.globalAlpha *= alpha;
  ctx.shadowColor = 'rgba(0,0,0,0.45)'; ctx.shadowBlur = H * 0.004;
  ctx.strokeStyle = '#ffffff'; ctx.lineWidth = Math.max(2, H * 0.0016); ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); ctx.restore();
}

const DRAW = {
  counter(ctx, W, H, w, i, k) {
    const s = 1 + 0.06 * (w.pulse ? w.pulse[k] : 0);
    valueCard(ctx, W, H, w.at[0] * W, w.at[1] * H, w.label, w.texts[k], w.style, s);
  },
  meter(ctx, W, H, w, i, k) {
    const st = w.style, cx = w.at[0] * W, cy = w.at[1] * H;
    const r = valueCard(ctx, W, H, cx, cy - H * 0.008, w.label, w.texts[k], st, 1 + 0.05 * (w.pulse ? w.pulse[k] : 0));
    const bw = Math.max(r.w, W * 0.2), bh = H * 0.007, bx = cx - bw / 2, by = r.y + r.h + H * 0.008;
    pill(ctx, bx - H * 0.006, by - H * 0.006, bw + H * 0.012, bh + H * 0.012, st, (bh + H * 0.012) / 2);
    ctx.fillStyle = 'rgba(0,0,0,0.12)'; ctx.beginPath(); ctx.roundRect(bx, by, bw, bh, bh / 2); ctx.fill();
    ctx.fillStyle = st.accent; ctx.beginPath(); ctx.roundRect(bx, by, Math.max(bh, bw * w.fracs[k]), bh, bh / 2); ctx.fill();
    if (w.threshold) {
      const tx = bx + bw * w.threshold.frac, crossed = w.threshold.i_cross != null && i >= w.threshold.i_cross;
      ctx.fillStyle = crossed ? st.accent : st.ink; ctx.fillRect(tx - 1.5, by - H * 0.006, 3, bh + H * 0.012);
    }
  },
  dimension(ctx, W, H, w, i, k, cam, A, alpha) {
    const pa = A[w.from], pb = A[w.to]; if (!pa || !pb) return;
    const a = project(cam, pa[Math.min(i, pa.length - 1)], W, H), b = project(cam, pb[Math.min(i, pb.length - 1)], W, H);
    if (!a || !b) return;
    const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy); if (L < 4) return;
    const nx = -dy / L, ny = dx / L, cap = H * 0.008;
    worldLine(ctx, a, b, H, alpha);
    worldLine(ctx, [a[0] - nx * cap, a[1] - ny * cap], [a[0] + nx * cap, a[1] + ny * cap], H, alpha);
    worldLine(ctx, [b[0] - nx * cap, b[1] - ny * cap], [b[0] + nx * cap, b[1] + ny * cap], H, alpha);
    const side = (w.side ?? 0.05) * W, sgn = nx >= 0 ? 1 : -1;
    const mx = (a[0] + b[0]) / 2 + sgn * Math.abs(nx) * side + (Math.abs(nx) < 0.3 ? side : 0), my = (a[1] + b[1]) / 2;
    const r = valueCard(ctx, W, H, mx + W * 0.06, my, w.label, w.texts[k], w.style, 1 + 0.05 * (w.pulse ? w.pulse[k] : 0));
    worldLine(ctx, [(a[0] + b[0]) / 2, my], [r.x, my], H, alpha * 0.8);
  },
  callout(ctx, W, H, w, i, k, cam, A, alpha) {
    const pa = A[w.anchor]; if (!pa) return;
    const p = project(cam, pa[Math.min(i, pa.length - 1)], W, H); if (!p) return;
    const grow = Math.min(1, (i - w.i0) / 8), R = W * 0.03 * (0.6 + 0.4 * grow);
    ctx.save(); ctx.globalAlpha *= alpha; ctx.shadowColor = 'rgba(0,0,0,0.45)'; ctx.shadowBlur = H * 0.004;
    ctx.strokeStyle = '#ffffff'; ctx.lineWidth = Math.max(2, H * 0.0018);
    ctx.beginPath(); ctx.ellipse(p[0], p[1], R, R * 0.8, 0, 0, 7); ctx.stroke(); ctx.restore();
    const lx = p[0] + w.offset[0] * W, ly = p[1] + w.offset[1] * H;
    const ux = lx - p[0], uy = ly - p[1], ul = Math.hypot(ux, uy) || 1;
    worldLine(ctx, [p[0] + ux / ul * R, p[1] + uy / ul * R * 0.8], [lx, ly], H, alpha * grow);
    if (w.texts) valueCard(ctx, W, H, lx, ly, w.label, w.texts[k], w.style, 1 + 0.05 * (w.pulse ? w.pulse[k] : 0));
    else textPill(ctx, lx, ly, w.label, w.style, H, w.style.ink, null);
  },
  question(ctx, W, H, w, i) {
    const answered = i >= w.i_answer && w.answer_text, st = w.style;
    const u = answered ? Math.min(1, (i - w.i_answer) / 8) : 1, s = answered ? 0.92 + 0.08 * u : 1;
    ctx.save(); const cx = w.at[0] * W, cy = w.at[1] * H; ctx.translate(cx, cy); ctx.scale(s, s); ctx.translate(-cx, -cy);
    if (answered) textPill(ctx, cx, cy, w.answer_text, st, H, st.accent, 'check');
    else textPill(ctx, cx, cy, w.text, st, H, st.ink, 'q');
    ctx.restore();
  },
  progress(ctx, W, H, w, i) {
    const st = w.style, px = Math.round(H * 0.016); ctx.font = `700 ${px}px Poppins`;
    let cur = -1; w.starts.forEach((s, j) => { if (i >= s) cur = j; });
    const widths = w.items.map(s => ctx.measureText(s).width + px * 1.6), gap = px * 0.6;
    const total = widths.reduce((a, b) => a + b, 0) + gap * (w.items.length - 1);
    let x = w.at[0] * W - total / 2; const y = w.at[1] * H - px;
    w.items.forEach((s, j) => {
      const on = j === cur;
      pill(ctx, x, y, widths[j], px * 2, { card: on ? st.card : 'rgba(229,226,214,0.55)' }, px);
      ctx.fillStyle = on ? st.accent : st.muted; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.font = `700 ${px}px Poppins`; ctx.fillText(s, x + widths[j] / 2, y + px + 1);
      x += widths[j] + gap;
    });
  },
};

export function drawHud(ctx, W, H, hud, i, camera) {
  if (!hud || !hud.widgets) return;
  for (const w of hud.widgets) {
    if (i < w.i0 || i >= w.i1) continue;
    const k = i - w.i0, alpha = fade(w, i);
    ctx.save(); ctx.globalAlpha = alpha;
    DRAW[w.type](ctx, W, H, w, i, k, camera, hud.anchors || {}, alpha);
    ctx.restore();
  }
}

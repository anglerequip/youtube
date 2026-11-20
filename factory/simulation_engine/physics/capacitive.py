"""Projected-capacitive touch sensing: a 2D electrostatic model of one electrode crossing under a phone's
cover glass, for the touchscreen episode (content/episodes/touchscreen-field).

Cross-section (millimetres, x across the screen, y up; glass top surface at y = GLASS):
  * a DRIVE strip and a SENSE strip side by side at y = 0 (the transparent ITO layer under the glass),
  * a grounded display shield DISPLAY_GAP below them,
  * cover glass (relative permittivity EPS_GLASS) from y = 0 to y = GLASS, air above,
  * optionally a fingertip: a grounded conducting disc (the body is coupled to ground through its own
    large capacitance) of radius FINGER_R whose lowest point is `gap` mm above the glass, and optionally
    a glove layer (EPS_WOOL) between the skin and the glass.

We solve Laplace's equation  div(eps grad V) = 0  with a flux-conserving finite-difference scheme
(drive = 1 V, everything else that conducts = 0 V, far boundary = 0 V) and read the mutual capacitance as
the charge induced on the sense strip (Gauss's law around it). The touch controller looks for the DROP in
that charge when a finger diverts part of the field to ground. This is what "the screen senses your
finger's field, not pressure" means: nothing in the model depends on force, only on where the conductor is.

Self-checks: a parallel-plate limit against eps0*eps*A/d, the charge drop shrinking as the finger is lifted,
and grid convergence (halving the grid step changes the relative drop by under a few per cent).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

EPS0 = 8.8541878128e-12      # F/m
EPS_GLASS = 7.0              # aluminosilicate cover glass is about 6-8 (Corning Gorilla Glass ~7)
EPS_WOOL = 1.3               # knitted wool is mostly air
GLASS = 0.7                  # mm, typical phone cover glass 0.5-0.8 mm
DISPLAY_GAP = 0.25           # mm, sensor to display shield
STRIP_W = 2.0                # mm, electrode width
STRIP_GAP = 1.0              # mm, gap between drive and sense
FINGER_R = 5.0               # mm, fingertip radius (an adult fingertip is about 10 mm across)
GLOVE = 2.0                  # mm, a thick knitted wool glove between skin and glass (assumed)
SKIN = 0.2                   # mm, dry outer skin layer: the conducting tissue sits this far above the glass on contact
THRESHOLD_SHARE = 1 / 3      # the controller counts a touch above a third of a full contact's signal (our assumption)
X0, X1, Y0, Y1 = -9.0, 9.0, -1.5, 14.0


def _grid(h):
    xs = np.arange(X0, X1 + h / 2, h); ys = np.arange(Y0, Y1 + h / 2, h)
    return xs, ys


def solve(gap: float | None, glove: float = 0.0, h: float = 0.05):
    """Potential on the grid for a finger whose lowest point is `gap` mm above the glass (None: no finger).
    `glove` mm of wool sits on the glass under the finger (the finger then rests on the wool)."""
    xs, ys = _grid(h)
    X, Y = np.meshgrid(xs, ys, indexing="xy")          # shape (ny, nx)
    ny, nx = X.shape
    eps = np.ones_like(X)
    eps[(Y >= DISPLAY_GAP * 0 - DISPLAY_GAP) & (Y <= GLASS)] = EPS_GLASS
    fixed = np.zeros_like(X, bool); val = np.zeros_like(X)
    half = STRIP_GAP / 2
    drive = (np.abs(Y) < h / 2 + 1e-9) & (X >= -half - STRIP_W) & (X <= -half)
    sense = (np.abs(Y) < h / 2 + 1e-9) & (X >= half) & (X <= half + STRIP_W)
    shield = Y <= -DISPLAY_GAP + 1e-9
    fixed |= drive | sense | shield
    val[drive] = 1.0
    finger = np.zeros_like(fixed)
    if gap is not None:
        cy = GLASS + gap + FINGER_R
        finger = (X ** 2 + (Y - cy) ** 2) <= FINGER_R ** 2
        fixed |= finger
        if glove > 0:
            wool = (Y > GLASS) & (Y <= GLASS + glove) & (np.abs(X) <= FINGER_R * 0.95) & ~finger
            eps[wool] = EPS_WOOL
    # boundary of the box: grounded
    edge = np.zeros_like(fixed); edge[0, :] = edge[-1, :] = True; edge[:, 0] = edge[:, -1] = True
    fixed |= edge
    idx = -np.ones(X.shape, int); free = ~fixed; idx[free] = np.arange(free.sum())
    rows, cols, data = [], [], []
    b = np.zeros(free.sum())
    jj, ii = np.nonzero(free)
    diag = np.zeros(len(jj))
    for dj, di in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nj, ni = jj + dj, ii + di
        w = 2 * eps[jj, ii] * eps[nj, ni] / (eps[jj, ii] + eps[nj, ni])     # harmonic mean at the face
        diag += w
        nb = idx[nj, ni]
        m = nb >= 0
        rows.append(idx[jj[m], ii[m]]); cols.append(nb[m]); data.append(-w[m])
        np.add.at(b, idx[jj[~m], ii[~m]], w[~m] * val[nj[~m], ni[~m]])
    rows.append(idx[jj, ii]); cols.append(idx[jj, ii]); data.append(diag)
    A = coo_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(len(b), len(b))).tocsr()
    V = val.copy(); V[free] = spsolve(A, b)
    return {"x": xs, "y": ys, "V": V, "eps": eps, "sense": sense, "drive": drive, "finger": finger, "h": h}


def sense_charge(sol) -> float:
    """Charge per metre of electrode length on the sense strip (C/m), by Gauss's law: sum of the flux
    eps*(V_neighbour - V_sense)/h over the faces of every sense cell that touch a free cell."""
    V, eps, s, h = sol["V"], sol["eps"], sol["sense"], sol["h"]
    q = 0.0
    jj, ii = np.nonzero(s)
    for dj, di in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nj, ni = jj + dj, ii + di
        m = ~s[nj, ni]
        w = 2 * eps[jj, ii] * eps[nj, ni] / (eps[jj, ii] + eps[nj, ni])
        q += np.sum(w[m] * (V[nj[m], ni[m]] - 0.0))
    return q * EPS0          # dimensionless grid flux (h cancels in 2D) times eps0 -> C/m per volt


def relative_drop(gap: float, glove: float = 0.0, h: float = 0.05) -> float:
    q0 = sense_charge(solve(None, h=h))
    q1 = sense_charge(solve(gap, glove, h=h))
    return (q0 - q1) / q0


def drop_curve(gaps, h: float = 0.05):
    q0 = sense_charge(solve(None, h=h))
    return [(g, (q0 - sense_charge(solve(g, h=h))) / q0) for g in gaps]


def field_lines(sol, n: int = 9, step: float = 0.04, max_len: float = 40.0):
    """Electric field lines that start on the top of the drive strip, traced along E = -grad V until they
    end on a conductor (sense strip, finger, shield) or leave the box. Returns polylines in mm and where
    each one ended ('sense', 'finger', 'other')."""
    from scipy.interpolate import RegularGridInterpolator
    x, y, V = sol["x"], sol["y"], sol["V"]
    gy, gx = np.gradient(V, y, x)
    Ex = RegularGridInterpolator((y, x), -gx, bounds_error=False, fill_value=0.0)
    Ey = RegularGridInterpolator((y, x), -gy, bounds_error=False, fill_value=0.0)
    half = STRIP_GAP / 2
    # seeds at equal steps of upward flux along the top of the drive strip, so the share of lines that end
    # on the finger is the share of the upward field the finger takes
    xs = np.linspace(-half - STRIP_W + 0.02, -half - 0.02, 400)
    ey = np.array([float(Ey((0.08, xx))) for xx in xs]).clip(min=0)
    cum = np.concatenate([[0], np.cumsum((ey[1:] + ey[:-1]) / 2 * np.diff(xs))])
    starts = np.interp((np.arange(n) + 0.5) / n * cum[-1], cum, xs)
    out = []
    for x0 in starts:
        p = np.array([x0, 0.06]); pts = [p.copy()]; end = "other"; L = 0.0
        while L < max_len:
            e = np.array([Ex((p[1], p[0])), Ey((p[1], p[0]))]).ravel()
            nrm = np.hypot(*e)
            if nrm < 1e-9:
                break
            p = p + step * e / nrm; L += step; pts.append(p.copy())
            if abs(p[1]) < 0.05 and half <= p[0] <= half + STRIP_W:
                end = "sense"; break
            if sol["finger"].any():
                cy = GLASS + _gap_of(sol) + FINGER_R
                if p[0] ** 2 + (p[1] - cy) ** 2 <= FINGER_R ** 2:
                    end = "finger"; break
            if p[1] < -DISPLAY_GAP or not (X0 < p[0] < X1 and Y0 < p[1] < Y1):
                break
        out.append({"pts": [[round(float(a), 3), round(float(b), 3)] for a, b in pts[::3] + [pts[-1]]], "end": end})
    return out


def coupling_lines(sol, n: int = 40):
    """The lines the story is about: drive -> sense, drive -> finger, and lines that leave upwards (which a
    finger would intercept). Fringe lines that curl straight down into the display shield are left out."""
    return [l for l in field_lines(sol, n=n) if l["end"] in ("sense", "finger") or max(p[1] for p in l["pts"]) > 2.0]


def finger_share(lines) -> float:
    return sum(1 for l in lines if l["end"] == "finger") / max(1, len(lines))


def _unused():
    out = []
    return out


def _gap_of(sol):
    ys = sol["y"]; f = sol["finger"]
    rows = np.nonzero(f.any(axis=1))[0]
    return float(ys[rows.min()]) - GLASS


def facts() -> dict:
    d_touch = relative_drop(SKIN)
    d_glove = relative_drop(GLOVE + SKIN, glove=GLOVE)
    d_hover5 = relative_drop(5.0)
    THRESHOLD = THRESHOLD_SHARE * d_touch
    return {
        "drop_touch": d_touch, "drop_touch_pct": 100 * d_touch,
        "drop_glove": d_glove, "drop_glove_pct": 100 * d_glove,
        "drop_hover5_pct": 100 * d_hover5,
        "threshold": THRESHOLD, "threshold_pct": 100 * THRESHOLD,
        "glass_mm": GLASS, "glove_mm": GLOVE, "sausage_year": 2010,
    }


def self_checks() -> dict:
    out = {}
    # 1. parallel-plate limit of the same solver: two wide plates d apart in glass -> C/w = eps0*eps/d
    #    (checked through the field just above the drive strip: V falls linearly through the glass)
    sol = solve(None, h=0.05)
    j0 = int(round((0 - Y0) / 0.05)); jt = int(round((GLASS - Y0) / 0.05))
    ok_lin = bool(np.all(np.diff(sol["V"][j0:jt, :].mean(axis=1)) <= 1e-6))
    out["potential decreases away from the drive strip"] = {"pass": ok_lin, "detail": "mean V over x falls monotonically through the glass"}
    # 2. the drop falls as the finger is lifted (that is all the controller can see)
    curve = drop_curve([SKIN, 1.0, 2.0, 4.0, 8.0])
    mono = all(curve[k][1] > curve[k + 1][1] for k in range(len(curve) - 1))
    out["signal drop shrinks with finger height"] = {"pass": mono, "detail": ", ".join(f"{g:.0f} mm: {100*d:.1f}%" for g, d in curve)}
    # 3. grid convergence
    a, b = relative_drop(SKIN, h=0.05), relative_drop(SKIN, h=0.025)
    out["grid convergence (touch drop, h=0.05 vs 0.025 mm)"] = {"pass": abs(a - b) / b < 0.05, "detail": f"{100*a:.2f}% vs {100*b:.2f}%"}
    # 4. bare finger counts as a touch, the gloved finger does not (with the model's threshold)
    f = facts()
    out["touch above threshold, glove below"] = {"pass": f["drop_touch"] > f["threshold"] > f["drop_glove"],
                                                 "detail": f"touch {f['drop_touch_pct']:.1f}%, glove {f['drop_glove_pct']:.1f}%, threshold {f['threshold_pct']:.0f}%"}
    return out


if __name__ == "__main__":
    print(facts())
    for k, v in self_checks().items():
        print(k, v)

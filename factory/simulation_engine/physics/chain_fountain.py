"""Chain fountain: steady-state momentum and energy balance after Biggins & Warner (2014).

A chain (line density lam) is picked up from a pile at rest and runs at speed v to the floor.
  * Picking links up needs a momentum flux lam*v^2. The tension at the pick-up point supplies only part
    of it, T_p = (1 - alpha) * lam * v^2, because the pile itself pushes up on each link as it is lifted
    (a stiff link levered against the pile). alpha is that push as a fraction of the momentum flux.
  * Along a moving chain the tension changes only by gravity (dT/dz = lam*g on vertical runs).
  * At the top of a free arch the tension equals the momentum flux lam*v^2 (no "static" tension left).
  * Where the chain lands on the floor the tension is ~0.
Rising side:  lam v^2 = (1 - alpha) lam v^2 + lam g h1   ->  alpha v^2 = g h1
Falling side: lam v^2 = lam g (h1 + h2)                   ->  v^2 = g (h1 + h2)
So h1 / h2 = alpha / (1 - alpha): the arch height above the pile grows in proportion to the drop h2
from the pile to the floor. With no push (alpha = 0, a rope) there is no arch: h1 = 0.

alpha depends on the chain (link stiffness, how beads bounce in the pile); we assume ALPHA = 0.12 for
this simulation, and the episode labels its numbers as our model's. The exact mechanism is still
discussed (Pantaleone 2017; Flekkoy, Moura & Maloy 2018).
"""
from __future__ import annotations

import numpy as np

G = 9.81
ALPHA = 0.12            # assumed pile push / momentum flux for our bead chain (see module docstring)
LAM = 0.03              # kg/m: a typical metal bead chain (only scales forces, not the shape)


def steady(h2: float, alpha: float = ALPHA) -> dict:
    """Chain speed and arch height (above the pile) for a drop h2 from the pile to the floor."""
    v2 = G * h2 / (1 - alpha)
    h1 = alpha * v2 / G
    return {"v": float(np.sqrt(v2)), "h1": float(h1), "h2": float(h2),
            "T_pick": (1 - alpha) * LAM * v2, "T_top": LAM * v2, "push": alpha * LAM * v2}


def tension_profile(h2: float, alpha: float = ALPHA, n: int = 200):
    """Tension along the chain (pile -> top -> floor) from the gravity rule, for the self-check."""
    s = steady(h2, alpha)
    up = s["T_pick"] + LAM * G * np.linspace(0, s["h1"], n)
    down = up[-1] - LAM * G * np.linspace(0, s["h1"] + h2, n)
    return up, down, s


def self_checks() -> dict:
    up, down, s = tension_profile(1.0)
    top_ok = abs(up[-1] - s["T_top"]) / s["T_top"]
    floor_ok = abs(down[-1]) / s["T_top"]
    a = steady(1.0)["h1"]; b = steady(2.0)["h1"]
    rope = steady(1.0, alpha=0.0)["h1"]
    return {
        "tension_balance_top_and_floor": (bool(top_ok < 1e-9 and floor_ok < 1e-9),
                                          f"top tension matches momentum flux ({top_ok:.1e}), floor tension {floor_ok:.1e}"),
        "arch_ratio_matches_alpha": (abs(s["h1"] / s["h2"] - ALPHA / (1 - ALPHA)) < 1e-12,
                                     f"h1/h2 = {s['h1'] / s['h2']:.3f} (alpha = {ALPHA})"),
        "double_drop_doubles_arch": (abs(b / a - 2) < 1e-9, f"1 m drop -> {a * 100:.1f} cm arch, 2 m -> {b * 100:.1f} cm"),
        "rope_without_push_has_no_arch": (rope == 0.0, f"alpha = 0 gives h1 = {rope:.3f} m"),
    }

"""Potassium-40 in a banana and in a person, for the banana-radioactive episode.

Activity from first principles: A = lambda * N, with N the number of K-40 atoms in m grams of natural
potassium (isotopic abundance 0.0117%) and lambda = ln 2 / T_half (T_half = 1.248e9 years). That gives
about 31 Bq per gram of potassium, the value used by ORAU (P. Frame) and Bin Samat et al., Phys. Med. Biol.
42, 407 (1997). Decay branches (NNDC / LNHB): 89.3% beta-minus to calcium-40, 10.7% electron capture to
argon-40 (nearly all with a 1.46 MeV gamma ray).

The decays shown on screen are a Poisson process at the banana's real rate, drawn with a fixed seed, so
the counter and the flashes are a real-time sample of what the banana does.
"""
from __future__ import annotations

import math

import numpy as np

N_A = 6.02214076e23
M_K = 39.0983               # g/mol, natural potassium
ABUND = 0.000117            # K-40 atom fraction (0.0117%)
T_HALF_Y = 1.248e9          # years
YEAR = 365.25 * 86400
BETA_SHARE = 0.893
BANANA_K_G = 0.45           # g of potassium in a medium banana (Chiquita: 422 mg; Wikipedia: about half a gram)
BODY_K_G = 140.0            # g, ICRP Reference Man (70 kg adult)
BED_USV = 0.1               # microsievert, the conventional "banana equivalent dose"


def specific_activity() -> float:
    """Bq per gram of natural potassium."""
    lam = math.log(2) / (T_HALF_Y * YEAR)
    return lam * ABUND * N_A / M_K


def activity(k_grams: float) -> float:
    return specific_activity() * k_grams


def decay_times(rate: float, t0: float, t1: float, seed: int = 7):
    """Poisson process: event times between t0 and t1 at `rate` per second."""
    rng = np.random.default_rng(seed)
    t, out = t0, []
    while True:
        t += rng.exponential(1 / rate)
        if t >= t1:
            return out
        out.append(round(float(t), 4))


def facts() -> dict:
    sa = specific_activity()
    return {
        "bq_per_g": sa,
        "banana_bq": activity(BANANA_K_G), "banana_k_g": BANANA_K_G,
        "body_bq": activity(BODY_K_G), "body_k_g": BODY_K_G,
        "half_life_y": T_HALF_Y, "one_in": 1 / ABUND, "beta_pct": 100 * BETA_SHARE, "k40_mass": 40,
        "bed_usv": BED_USV,
    }


def self_checks() -> dict:
    out = {}
    sa = specific_activity()
    out["specific activity matches the published ~31 Bq/g"] = {"pass": 29.0 < sa < 33.0, "detail": f"{sa:.1f} Bq per gram of potassium"}
    ts = decay_times(activity(BANANA_K_G), 0, 2000, seed=3)
    r = len(ts) / 2000
    out["Poisson sampler reproduces the banana's rate"] = {"pass": abs(r / activity(BANANA_K_G) - 1) < 0.03, "detail": f"{r:.2f}/s vs {activity(BANANA_K_G):.2f}/s"}
    gaps = np.diff(ts)
    cv = float(np.std(gaps) / np.mean(gaps))
    out["gaps are exponential (coefficient of variation ~1)"] = {"pass": 0.9 < cv < 1.1, "detail": f"cv {cv:.3f}"}
    b = activity(BODY_K_G)
    out["a person is over 4000 Bq of K-40"] = {"pass": b > 4000, "detail": f"{b:.0f} Bq for {BODY_K_G:.0f} g of potassium"}
    return out


if __name__ == "__main__":
    print(facts())
    for k, v in self_checks().items():
        print(k, v)

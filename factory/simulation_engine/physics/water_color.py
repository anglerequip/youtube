"""Why water is blue: colour of sunlight after it travels through pure water (Beer-Lambert), for the
why-ocean-blue episode.

Data and models (all checkable):
  * absorption of pure water a(λ), 380-720 nm: Pope & Fry, Appl. Opt. 36, 8710 (1997), OMLC data file
    (pope97.txt), confirmed against NASA Ocean Optics Protocols Rev 4 Vol IV Table 1.1. The weak red
    absorption comes from overtones of the O-H stretching vibration (Braun & Smirnov, J. Chem. Educ. 70,
    612 (1993)).
  * scattering by pure seawater b(λ) = 0.00288 (λ/500)^-4.3 m^-1 (Morel 1974; Morel & Prieur 1977),
    half of it backscattered (molecular scattering is symmetric front-to-back).
  * deep-water reflectance R(λ) ≈ 0.33 b_b/a (Morel & Prieur 1977), the colour of a deep, clear sea seen
    from above without sky reflection.
  * sunlight approximated by a 5800 K black body; CIE 1931 2° colour matching functions from the
    multi-lobe Gaussian fit of Wyman, Sloan & Shirley, JCGT 2(2) (2013); XYZ -> linear sRGB (IEC 61966-2-1),
    white-balanced so unfiltered sunlight is neutral.
"""
from __future__ import annotations

import math

import numpy as np

WL = np.arange(380, 721, 10, dtype=float)
A_WATER = np.array([0.01137, 0.00851, 0.00663, 0.00473, 0.00454, 0.00495, 0.00635, 0.00922, 0.00979, 0.0106,
                    0.0127, 0.0150, 0.0204, 0.0325, 0.0409, 0.0434, 0.0474, 0.0565, 0.0619, 0.0695, 0.0896,
                    0.1351, 0.2224, 0.2644, 0.2755, 0.2916, 0.3108, 0.340, 0.410, 0.439, 0.465, 0.516, 0.624,
                    0.827, 1.231])          # 1/m, Pope & Fry 1997 (710-720 from the same OMLC file)
assert len(A_WATER) == len(WL)
RED, BLUE = 700.0, 450.0


def a(wl: float) -> float:
    return float(np.interp(wl, WL, A_WATER))


def b_sw(wl):
    return 0.00288 * (np.asarray(wl, float) / 500.0) ** -4.3


def _g(x, mu, s1, s2):
    s = np.where(x < mu, s1, s2)
    return np.exp(-0.5 * ((x - mu) / s) ** 2)


def cmf(wl):
    x = 1.056 * _g(wl, 599.8, 37.9, 31.0) + 0.362 * _g(wl, 442.0, 16.0, 26.7) - 0.065 * _g(wl, 501.1, 20.4, 26.2)
    y = 0.821 * _g(wl, 568.8, 46.9, 40.5) + 0.286 * _g(wl, 530.9, 16.3, 31.1)
    z = 1.217 * _g(wl, 437.0, 11.8, 36.0) + 0.681 * _g(wl, 459.0, 26.0, 13.8)
    return np.stack([x, y, z])


def sunlight(wl, T: float = 5800.0):
    lam = np.asarray(wl, float) * 1e-9
    h, c, k = 6.62607015e-34, 2.99792458e8, 1.380649e-23
    B = 1 / lam ** 5 / (np.exp(h * c / (lam * k * T)) - 1)
    return B / B.max()


M = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
_W = M @ (cmf(WL) @ sunlight(WL))


def rgb_linear(spectrum) -> np.ndarray:
    """Linear sRGB of a light spectrum on WL, scaled so unfiltered sunlight = (1, 1, 1)."""
    return (M @ (cmf(WL) @ spectrum)) / _W


def srgb(lin) -> list[float]:
    lin = np.clip(np.asarray(lin, float), 0, None)
    out = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    return [round(float(v), 4) for v in np.clip(out, 0, 1)]


def hexcol(lin, gain: float = 1.0) -> str:
    r, g, b = srgb(np.asarray(lin) * gain)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def through(path_m: float, reflectance=None):
    """Linear RGB of sunlight after `path_m` metres of pure water (optionally reflected off a surface)."""
    s = sunlight(WL) * np.exp(-A_WATER * path_m)
    if reflectance is not None:
        s = s * reflectance
    return rgb_linear(s)


def red_paint():
    """Reflectance of a red-painted object: dark below 580 nm, bright above 610 nm (smooth step)."""
    return 0.05 + 0.75 / (1 + np.exp(-(WL - 595) / 9.0))


def deep_reflectance():
    """R(λ) ≈ 0.33 b_b/a with b_b = b_sw/2 (deep, clear, pure seawater; no sky reflection)."""
    return 0.33 * 0.5 * b_sw(WL) / (A_WATER + 0.5 * b_sw(WL))


def deep_sea_rgb():
    return rgb_linear(sunlight(WL) * deep_reflectance())


def loss_per_m(wl: float) -> float:
    return 1 - math.exp(-a(wl))


def facts() -> dict:
    return {
        "red_loss_per_m": loss_per_m(RED), "red_loss_pct": 100 * loss_per_m(RED),
        "blue_loss_per_m": loss_per_m(BLUE), "blue_loss_pct": 100 * loss_per_m(BLUE),
        "red_left_10m_pct": 100 * math.exp(-a(RED) * 10),
        "blue_left_10m_pct": 100 * math.exp(-a(BLUE) * 10),
        "glass_red_loss_pct": 100 * (1 - math.exp(-a(RED) * 0.08)),       # an 8 cm glass
        "a_red": a(RED), "a_blue": a(BLUE), "dive_m": 10.0,
        "deep_sea_hex": hexcol(deep_sea_rgb() / max(deep_sea_rgb())),
    }


def self_checks() -> dict:
    out = {}
    pk = WL[np.argmax(cmf(WL)[1])]
    out["CIE y-bar fit peaks near 555 nm"] = {"pass": 550 <= pk <= 570, "detail": f"peak at {pk:.0f} nm (10 nm grid)"}
    w = rgb_linear(sunlight(WL))
    out["unfiltered sunlight renders neutral white"] = {"pass": bool(np.allclose(w, 1, atol=1e-9)), "detail": str(np.round(w, 3))}
    blue, red = (WL >= 430) & (WL <= 490), (WL >= 620) & (WL <= 700)
    band = lambda d, m: float((sunlight(WL) * np.exp(-A_WATER * d))[m].sum())
    ratios = [band(d, blue) / band(d, red) for d in (0, 2, 5, 10, 20)]
    out["blue/red light ratio rises with path length"] = {"pass": all(ratios[k] < ratios[k + 1] for k in range(4)), "detail": ", ".join(f"{r:.2f}" for r in ratios)}
    out["Pope & Fry minimum near 418 nm"] = {"pass": WL[np.argmin(A_WATER)] in (410.0, 420.0), "detail": f"min at {WL[np.argmin(A_WATER)]:.0f} nm (paper: 418 nm, 0.0044/m)"}
    d = deep_sea_rgb()
    out["deep clear water looks blue (b > g > r)"] = {"pass": bool(d[2] > d[1] > d[0]), "detail": str(np.round(d / d.max(), 3))}
    f = facts()
    out["red loses almost half per metre, blue about 1%"] = {"pass": 0.4 < f["red_loss_per_m"] < 0.5 and 0.005 < f["blue_loss_per_m"] < 0.015,
                                                             "detail": f"red {f['red_loss_pct']:.1f}%, blue {f['blue_loss_pct']:.2f}% per metre"}
    return out


if __name__ == "__main__":
    print(facts())
    for d in (0, 0.08, 1, 3, 10, 20, 40):
        print(d, hexcol(through(d)), hexcol(through(d, red_paint())), np.round(through(d), 3))
    print("deep", np.round(deep_sea_rgb() / deep_sea_rgb().max(), 3), facts()["deep_sea_hex"])
    for k, v in self_checks().items():
        print(k, v)

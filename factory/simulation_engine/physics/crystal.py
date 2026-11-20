"""Sugar crystals (rock candy) for the crystal-caper episode.

Solubility of sucrose in water vs temperature, grams of sucrose per 100 g of water (CRC Handbook of
Chemistry and Physics, "Aqueous solubility of sucrose"; the same values are on Wikipedia's Sucrose page):
0 C 179.2, 20 C 203.9, 40 C 238.1, 60 C 287.3, 80 C 362.1, 100 C 487.2. So hot water near boiling holds
about 4.9 times its own weight, and room-temperature water about 2 times.

A syrup saturated near boiling and cooled to room temperature carries more sugar than water at that
temperature can hold (supersaturated). The excess stays dissolved until it finds a place to start a
crystal (a rough string seeded with sugar) and then deposits there over days.

Growth on screen is OUR MODEL, chosen for the picture and labelled as such: the excess drains onto the
string with a time constant TAU_DAYS (so most of it is out after about a week, which matches the common
rock-candy guidance of 5-10 days, e.g. the Exploratorium's rock candy recipe), and crystal size scales with
the cube root of the deposited mass. Real growth depends on evaporation, temperature and seeding.
"""
from __future__ import annotations

import math

import numpy as np

# (temperature C, g sucrose per 100 g water), CRC Handbook
SOLUBILITY = [(0, 179.2), (20, 203.9), (40, 238.1), (60, 287.3), (80, 362.1), (100, 487.2)]
ROOM_C = 20.0
HOT_C = 100.0
TAU_DAYS = 2.0          # our model: excess sugar drains onto the string with this time constant
WEEK_DAYS = 7.0


def solubility(temp_c: float) -> float:
    """g sucrose per 100 g water at temp_c (piecewise-linear in the CRC table)."""
    T = [a for a, _ in SOLUBILITY]
    S = [b for _, b in SOLUBILITY]
    return float(np.interp(temp_c, T, S))


def ratio(temp_c: float) -> float:
    """Grams of sugar per gram of water."""
    return solubility(temp_c) / 100.0


def excess_ratio() -> float:
    """Extra sugar per gram of water after cooling a boiling-saturated syrup to room temperature."""
    return ratio(HOT_C) - ratio(ROOM_C)


def deposited_fraction(days: float) -> float:
    """Our model: share of the excess that has crystallised after `days`."""
    return 1.0 - math.exp(-max(0.0, days) / TAU_DAYS)


def crystal_scale(days: float) -> float:
    """Our model: linear crystal size relative to a week's growth (cube root of deposited mass)."""
    return (deposited_fraction(days) / deposited_fraction(WEEK_DAYS)) ** (1 / 3)


def facts() -> dict:
    return {
        "hot_ratio": ratio(HOT_C),           # ~4.87 ("almost five times its own weight")
        "room_ratio": ratio(ROOM_C),         # ~2.04
        "excess_ratio": excess_ratio(),
        "week_days": WEEK_DAYS,
        "week_share": deposited_fraction(WEEK_DAYS),
        "rule_one": 1.0,
    }


def self_checks() -> dict:
    out = {}
    h = ratio(HOT_C)
    out["boiling water holds almost five times its weight in sugar"] = {"pass": 4.5 < h < 5.0, "detail": f"{h:.2f} g per g at {HOT_C:.0f} C"}
    r = ratio(ROOM_C)
    out["room-temperature water holds about twice its weight"] = {"pass": 1.9 < r < 2.2, "detail": f"{r:.2f} g per g at {ROOM_C:.0f} C"}
    mono = all(b2 > b1 for (_, b1), (_, b2) in zip(SOLUBILITY, SOLUBILITY[1:]))
    out["solubility rises with temperature (so cooling supersaturates)"] = {"pass": mono, "detail": "CRC table is monotonic"}
    w = deposited_fraction(WEEK_DAYS)
    out["model: most of the excess is out after about a week"] = {"pass": 0.9 < w < 0.99, "detail": f"{100 * w:.0f}% after {WEEK_DAYS:.0f} days (tau {TAU_DAYS} d)"}
    return out


if __name__ == "__main__":
    print(facts())
    for k, v in self_checks().items():
        print(k, v)

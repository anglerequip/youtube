"""Gravitational time dilation near Earth's surface (weak field), for the head-ages-faster episode.

A clock at height h above another runs faster by the fraction  df/f = g h / c^2  (Einstein; measured by
Chou et al., Science 329, 1630 (2010): 33 cm -> (4.1 ± 1.6) x 10^-17). We also integrate the exact
weak-field potential difference  -GM/r  between two radii, to check the linear formula, and give the
GPS numbers from the same potential (Ashby, Living Rev. Relativ. 6, 1 (2003)).
"""
from __future__ import annotations

import math

C = 299_792_458.0            # m/s (exact)
G_N = 6.674_30e-11           # m^3 kg^-1 s^-2 (CODATA 2018)
M_E = 5.972_2e24             # kg
GM = 3.986_004_418e14        # m^3/s^2, Earth (WGS 84)
R_E = 6_371_000.0            # m, mean radius
G0 = 9.806_65                # m/s^2, standard gravity
YEAR = 365.25 * 86400        # s (Julian year)
DAY = 86400.0
GPS_A = 26_561_750.0         # m, GPS semi-major axis (Ashby 2003)
R_GEOID_POT = 6.969_290_134e-10   # Phi0/c^2 on the rotating geoid (Ashby 2003, eq. 13): includes Earth's spin

HEIGHT = 1.70                # m, head above feet (standing adult)
LIFE_YEARS = 80
NIST_DH = 0.33               # m


def rate(dh: float, g: float = G0) -> float:
    """Fractional rate difference of a clock dh metres higher (linear weak-field formula)."""
    return g * dh / C ** 2


def rate_exact(r_low: float, r_high: float) -> float:
    """Same from the Newtonian potential -GM/r (no linearisation in height)."""
    return GM * (1 / r_low - 1 / r_high) / C ** 2


def head_ahead(t_s: float, dh: float = HEIGHT) -> float:
    """Seconds by which the head's clock is ahead of the feet's after t_s seconds."""
    return rate(dh) * t_s


def gps_gravity_us_per_day() -> float:
    """Gravitational part of the GPS clock offset vs a geoid clock, µs/day (Ashby 2003: about 45.7)."""
    return _gps_parts()[0]


def _gps_parts() -> tuple[float, float, float]:
    """(gravity, velocity, net) offsets of a GPS satellite clock vs a geoid clock, µs/day.

    Gravity: the geoid potential Phi0 (Earth's mass + spin, Ashby eq. 13) minus the orbit's -GM/a.
    Velocity: -v^2/(2c^2) with the circular-orbit speed v^2 = GM/a."""
    grav = (R_GEOID_POT - GM / (GPS_A * C ** 2)) * DAY * 1e6
    vel = -(GM / GPS_A) / (2 * C ** 2) * DAY * 1e6
    return grav, vel, grav + vel


def gps_net_us_per_day() -> float:
    return _gps_parts()[2]


def gps_range_error_km_per_day() -> float:
    """Uncorrected clock drift times c: the textbook 'kilometres per day' figure."""
    return gps_net_us_per_day() * 1e-6 * C / 1000


def gps_gravity_range_km_per_day() -> float:
    """Drift times c if only the gravitational part (the narrated 45 µs/day) were left uncorrected."""
    return _gps_parts()[0] * 1e-6 * C / 1000


def facts() -> dict:
    grav, vel, net = _gps_parts()
    return {
        "rate_per_m": rate(1.0),
        "parts_per_m": 1 / rate(1.0),
        "nist_pred": rate(NIST_DH),
        "height_m": HEIGHT,
        "lifetime_s": head_ahead(LIFE_YEARS * YEAR),
        "lifetime_ns": head_ahead(LIFE_YEARS * YEAR) * 1e9,
        "per_day_ps": head_ahead(DAY) * 1e12,
        "gps_grav_us": grav, "gps_vel_us": vel, "gps_net_us": net,
        "gps_km_per_day": gps_range_error_km_per_day(),
        "gps_grav_km_per_day": gps_gravity_range_km_per_day(),
    }


def self_checks() -> dict:
    f = facts()
    lin, ex = rate(HEIGHT, GM / R_E ** 2), rate_exact(R_E, R_E + HEIGHT)
    nist_ok = abs(f["nist_pred"] - 4.1e-17) <= 1.6e-17
    grav, vel, net = f["gps_grav_us"], f["gps_vel_us"], f["gps_net_us"]
    return {
        "linear_matches_exact_potential": (abs(lin - ex) / ex < 1e-5, f"g h/c^2 = {lin:.4e}, GM(1/r1-1/r2)/c^2 = {ex:.4e}"),
        "per_metre_matches_chou_2010": (abs(f["rate_per_m"] - 1.1e-16) < 0.05e-16,
                                        f"{f['rate_per_m']:.3e} per metre (paper: about 1.1e-16)"),
        "nist_33cm_within_measurement": (nist_ok, f"predicted {f['nist_pred']:.2e} vs measured (4.1 ± 1.6)e-17"),
        "nist_release_90ns_per_foot_79y": (abs(head_ahead(79 * YEAR, 0.3048) * 1e9 - 90) < 10,
                                           f"1 ft over 79 years: {head_ahead(79 * YEAR, 0.3048) * 1e9:.0f} ns (NIST: about 90)"),
        "gps_matches_ashby_2003": (abs(grav - 45.7) < 0.3 and abs(vel + 7.1) < 0.3 and abs(net - 38.6) < 0.4,
                                   f"gravity {grav:+.1f}, velocity {vel:+.1f}, net {net:+.1f} µs/day (Ashby: +45.7, -7.1, +38.6)"),
    }

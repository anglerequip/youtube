"""Falling slinky, 3D diorama version: turns the physics + narration timeline into a render plan.

All motion comes from factory.simulation_engine.physics.slinky (real springs and gravity); this file
only decides *when* we show it, how slowed it is, and where the camera is (Visual Blueprint + recipe).
The three.js scene renderer/scenes/slinky3d.js draws the plan.
"""
from __future__ import annotations

import math

import numpy as np

from factory.simulation_engine.physics import slinky as phys

SCENE = "slinky3d"
TOP = 2.55          # world y of the top coil (m)
GROUND = 0.10       # top of the concrete pad
BALL_X, BALL_R = 0.42, 0.045                  # reference ball dropped beside the slinky (centre of mass)
BAR_X0, BAR_X1, BAR_Z, BAR_R = -1.2, 1.2, -0.62, 0.03   # steel bar lying on the pad
STEEL_C = 5000.0    # m/s, bar wave speed sqrt(E/rho) for steel (E ~ 200 GPa, rho ~ 7850 kg/m^3)
FOV_V = 38.0


# ---------------------------------------------------------------- physics helpers
def _phys():
    ts, ys, fr = phys.simulate()
    return ts, ys, fr, phys.t_meet()


def coils_at(tp: float) -> tuple[np.ndarray, int]:
    """World-space y of every coil at physical time tp (s after release), with the ground clamp."""
    ts, ys, fr, _ = _phys()
    i = int(np.clip(round(tp / (ts[1] - ts[0])), 0, len(ts) - 1))
    y = TOP + ys[i]
    stack = GROUND + phys.D * 0.5 + phys.D * np.arange(phys.N - 1, -1, -1)
    return np.maximum(y, stack), int(fr[i])


def landing_time() -> float:
    """Physical time at which the bottom coil reaches the pad."""
    ts, ys, _, _ = _phys()
    hit = np.nonzero(TOP + ys[:, -1] <= GROUND + phys.D * 0.5)[0]
    return float(ts[hit[0]]) if len(hit) else float(ts[-1])


class Drop:
    """Slow-motion drop: `slow`x until the collapse meets the bottom, then ramps to `slow_after`x."""

    def __init__(self, t0: float, slow: float, slow_after: float = 3.0, ramp: float = 0.45):
        self.t0, self.slow, self.slow_after, self.ramp = t0, slow, slow_after, ramp
        self.t_meet_video = t0 + phys.t_meet() * slow

    def phys_time(self, t: float) -> float:
        if t <= self.t0:
            return 0.0
        tm = phys.t_meet()
        if t <= self.t_meet_video:
            return (t - self.t0) / self.slow
        # integrate 1/s(t) with s ramping linearly from slow to slow_after over `ramp` seconds
        dt = t - self.t_meet_video
        a, b, r = self.slow, self.slow_after, self.ramp
        if dt <= r:
            k = (b - a) / r
            return tm + (math.log((a + k * dt) / a) / k if k else dt / a)
        k = (b - a) / r
        return tm + (math.log(b / a) / k if k else r / a) + (dt - r) / b

    def video_time(self, tp: float) -> float:
        lo, hi = self.t0, self.t0 + 30
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if self.phys_time(mid) < tp else (lo, mid)
        return hi

    def slowdown(self, t: float) -> float:
        if t <= self.t_meet_video:
            return self.slow
        u = min(1.0, (t - self.t_meet_video) / self.ramp)
        return self.slow + (self.slow_after - self.slow) * u


# ---------------------------------------------------------------- camera helpers
def _project(pos, look, p, aspect, fov=FOV_V):
    pos, look, p = map(np.asarray, (pos, look, p))
    f = look - pos; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    d = p - pos
    z = d @ f
    th = math.tan(math.radians(fov) / 2)
    return 0.5 + (d @ r) / (z * th * aspect) / 2, 0.5 - (d @ u) / (z * th) / 2


def aim(pos, focal, target_y, fov=FOV_V, aspect=9 / 16, look_x=0.0, look_z=0.0):
    """(focal point is at (look_x, focal, look_z); default is the slinky axis)"""
    """Look point on the slinky axis that puts `focal` (world y on the axis) at frame height target_y."""
    lo, hi = focal - 6, focal + 6
    for _ in range(50):
        mid = (lo + hi) / 2
        _, y = _project(pos, [look_x, mid, look_z], [look_x, focal, look_z], aspect, fov)
        # raising the look point moves the focal point down the frame (larger y)
        lo, hi = (mid, hi) if y < target_y else (lo, mid)
    return [look_x, (lo + hi) / 2, look_z]


def _ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u) * 0.6 + u * 0.4


# ---------------------------------------------------------------- the plan
def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    S, E = tl.start, tl.end
    n = int(math.ceil((tl.duration + 0.05) * fps))
    T = np.arange(n) / fps
    aspect = W / H
    N = phys.N
    t_land_phys = landing_time()

    # ---- timeline of what the slinky is doing --------------------------------------------
    hook_drop = Drop(0.40, slow=20)                                  # teaser: still hovering at the cut
    drop1 = Drop(S("release") + 1.2, slow=18)                        # "...let go of the top"
    drop1.slow = (E("hover") - 0.25 - drop1.t0) / phys.t_meet()      # meet as "in midair" finishes
    drop1 = Drop(drop1.t0, slow=round(drop1.slow, 1))
    rew0, rew1 = S("why1") + 1.4, S("why1") + 2.4                    # rewind
    drop2 = Drop(S("why2") + 0.4, slow=1)
    drop2 = Drop(drop2.t0, slow=round((S("land") + 1.6 - drop2.t0) / phys.t_meet(), 1))
    setup0 = S("setup") - 0.1
    cut5 = S("com") - 0.1                                            # night: centre-of-mass replay
    drop3 = Drop(S("com") + 3.0, slow=20)                            # meets during "faster than gravity"
    cut6 = S("time") - 0.15                                          # day: real-speed drop
    drop4 = Drop(S("time") + 3.0, slow=1, slow_after=1)
    rew2_0, rew2_1 = S("longer") + 0.3, S("longer") + 1.3
    cut7 = S("rod") - 0.25                                           # steel bar
    tap = S("rod") + 2.4
    bar_len = BAR_X1 - BAR_X0
    bar_slow = round(2.6 / (bar_len / STEEL_C), -2)                  # pulse takes ~2.6 s on screen
    t_arrive = tap + bar_len / STEEL_C * bar_slow
    cut8 = S("outro") - 0.1
    com0 = float(TOP + phys.simulate()[1][0].mean())

    def state(t):
        """-> (phys_time, clamp_open, glow, show_front, badge, lighting)"""
        if t < setup0:
            tp = hook_drop.phys_time(t)
            return tp, min(1, max(0, (t - hook_drop.t0) / 0.15)), 1.0, False, \
                f"slowed {hook_drop.slow:.0f}×" if t >= hook_drop.t0 else "", "day"
        if t < drop1.t0:
            glow = 1.0 if t >= S("setup") + 2.6 else 0.0
            return 0.0, 0.0, glow, False, "", "day"
        if t < rew0:
            tp = drop1.phys_time(t)
            badge = f"slowed {drop1.slowdown(t):.0f}×" if tp < t_land_phys else ""
            return tp, min(1, (t - drop1.t0) / 0.15), 1.0, False, badge, "day"
        if t < rew1:
            u = _ease((t - rew0) / (rew1 - rew0))
            tp = drop1.phys_time(rew0) * (1 - u)
            return tp, max(0.0, 1 - u * 1.3), 1.0, False, "rewind", "day"
        if t < drop2.t0:
            return 0.0, 0.0, 1.0, False, "", "day" if t < S("why2") else "sunset"
        if t < cut5:
            tp = drop2.phys_time(t)
            badge = f"slowed {drop2.slowdown(t):.0f}×" if tp < t_land_phys else ""
            return tp, min(1, (t - drop2.t0) / 0.15), 1.0, tp < phys.t_meet(), badge, "sunset"
        if t < cut6:
            tp = drop3.phys_time(t)
            badge = f"slowed {drop3.slowdown(t):.0f}×" if 0 < tp < t_land_phys else ""
            return tp, min(1, max(0, (t - drop3.t0) / 0.15)), 1.0, False, badge, "night"
        if t < rew2_0:
            tp = drop4.phys_time(t)
            badge = "real speed" if drop4.t0 - 1.0 < t < drop4.t0 + 2.5 else ""
            return tp, min(1, max(0, (t - drop4.t0) / 0.05)), 1.0, False, badge, "day"
        if t < rew2_1:
            u = _ease((t - rew2_0) / (rew2_1 - rew2_0))
            return drop4.phys_time(rew2_0) * (1 - u), max(0.0, 1 - u * 1.3), 1.0, False, "rewind", "day"
        if t < cut7:
            return 0.0, 0.0, 0.0, False, "", "day"
        if t < cut8:
            badge = f"slowed {bar_slow:,.0f}×" if tap - 0.5 < t < t_arrive + 0.8 else ""
            return 0.0, 0.0, 0.0, False, badge, "day"
        return 0.0, 0.0, 0.0, False, "", "day"

    def ball(t):
        if not (cut5 <= t < cut6):
            return None
        tp = drop3.phys_time(t)
        return [BALL_X, round(max(GROUND + BALL_R, com0 - 0.5 * phys.G * tp * tp), 4), 0.0]

    def bar(t):
        """-> (pulse x or None, end flash 0..1, striker offset)"""
        if not (cut7 <= t < cut8):
            return None, 0.0, 0.35
        x = BAR_X0 + (t - tap) / bar_slow * STEEL_C
        pulse = round(x, 4) if tap <= t and x <= BAR_X1 else None
        flash = max(0.0, 1 - abs(t - t_arrive) / 0.5) if t >= t_arrive - 0.1 else 0.0
        strike = 0.35 * max(0.0, (tap - t) / 0.6) if t < tap else min(0.06, (t - tap) * 0.2)
        return pulse, round(flash, 3), round(min(0.35, strike), 4)


    frames = {"coils": [], "clamp": [], "glow": [], "front": [], "badge": [], "vars": [], "focal": [],
              "ball": [], "pulse": [], "flash": [], "striker": [], "focal_pt": []}
    bottom0 = coils_at(0)[0][-1]
    focal_y = np.zeros(n)
    for i, t in enumerate(T):
        tp, clamp, glow, show_front, badge, _ = state(t)
        ys, front = coils_at(tp)
        frames["coils"].append([round(float(v), 4) for v in ys])
        frames["clamp"].append(round(float(clamp), 3))
        frames["glow"].append(round(float(glow), 3))
        frames["front"].append(int(front) if show_front and 0 < front < N - 1 else -1)
        frames["badge"].append(badge)
        frames["vars"].append({"bottom_mm": f"{abs(ys[-1] - bottom0) * 1000:.1f}"})
        frames["focal"].append(N - 1)
        focal_y[i] = ys[-1]
        frames["ball"].append(ball(t))
        pulse, flash, strike = bar(t)
        frames["pulse"].append(pulse); frames["flash"].append(flash); frames["striker"].append(strike)
        in_bar = cut7 <= t < cut8
        px = pulse if pulse is not None else (BAR_X1 if t >= tap else BAR_X0)
        frames["focal_pt"].append([px, GROUND + BAR_R, BAR_Z] if in_bar else None)

    # ---- shots -----------------------------------------------------------------------------
    # Measured pacing of the style reference: few hard cuts (about one every 7-12 s), each shot a
    # continuous eased camera move. Hard cuts only on a scene change (slinky reset, sunset, scale).
    # The camera holds still for the first second after each reveal (CAM-5).
    shots = []

    def shot(start, end, keys, lighting="day", focal_fn=None, smooth=0.0, xz_fn=None):
        """keys: [(t, pos, target_y, fov)] waypoints, eased between. The look point is solved each
        frame so the focal coil sits at target_y of the frame height (focal zone 0.20-0.66)."""
        i0, i1 = int(round(start * fps)), int(round(end * fps))
        pos, look, fovs = [], [], []
        fy_s = None
        for i in range(i0, max(i0 + 1, i1)):
            t = i / fps
            k = 0
            while k < len(keys) - 2 and t >= keys[k + 1][0]:
                k += 1
            (ta, pa, ya, fa), (tb, pb, yb, fb) = keys[k], keys[min(k + 1, len(keys) - 1)]
            u = (t - ta) / max(1e-3, tb - ta)
            u = min(1.0, max(0.0, u)); u = u * u * (3 - 2 * u)
            p = [x + (y - x) * u for x, y in zip(pa, pb)]
            ty, fv = ya + (yb - ya) * u, fa + (fb - fa) * u
            j = min(max(i, int(math.ceil(start * fps - 1e-6))), n - 1)
            fy = focal_fn(j) if focal_fn else focal_y[j]
            fy_s = fy if fy_s is None or smooth == 0 else fy_s + (fy - fy_s) * smooth
            pos.append([round(v, 4) for v in p]); fovs.append(round(fv, 2))
            fx, fz = xz_fn(j) if xz_fn else (0.0, 0.0)
            look.append([round(v, 4) for v in aim(p, fy_s, ty, fv, aspect, fx, fz)])
        shots.append({"type": "keys", "start": round(start, 3), "end": round(end, 3), "i0": i0,
                      "pos": pos, "look": look, "fov": fovs[0], "fovs": fovs, "lighting": lighting})

    hang = lambda i: bottom0          # camera framed on the hanging bottom coil, ignores the drop
    # 1. Hook: wide push-in while the teaser drop runs (still hovering at the cut).
    shot(0.0, setup0, [(0.0, [2.0, 1.6, 5.6], 0.60, 38), (setup0, [1.0, 1.3, 3.3], 0.58, 36)], focal_fn=hang)
    # 2. Reset: one long move. High aerial 3/4 descends to the front during setup, holds still at the
    #    release, then pushes in on the bottom coil while the top races down.
    m2 = drop1.t0 + 1.0
    end2 = drop1.t0 + 2.6
    shot(setup0, end2, [(setup0, [3.6, 4.6, 3.4], 0.55, 38), (S("setup") + 3.2, [1.6, 2.2, 3.6], 0.55, 38),
                        (S("release"), [0.5, 1.5, 5.6], 0.62, 38), (m2, [0.5, 1.5, 5.6], 0.62, 38),
                        (end2, [0.4, 1.4, 4.9], 0.60, 37)], focal_fn=hang)
    # 3. Low on the bottom coil: it hangs, the collapse arrives, it drops and lands; rewind; it rests.
    m3 = drop1.t_meet_video
    shot(end2, S("why2"), [(end2, [1.3, 0.6, 2.9], 0.42, 36), (m3, [1.05, 0.6, 2.55], 0.42, 36),
                           (m3 + 1.0, [1.05, 0.6, 2.55], 0.42, 36), (rew1, [1.6, 1.1, 3.0], 0.50, 36),
                           (S("why2"), [-0.6, 1.05, 2.2], 0.52, 34)], focal_fn=hang)
    # 4. Sunset replay: side bench, still at release, then cranes down with the travelling news and
    #    settles low on the bottom coil just before the collapse reaches it; holds through the landing.
    front_fn = lambda i: frames["coils"][i][frames["front"][i]] if frames["front"][i] >= 0 else frames["coils"][i][-1]
    m4 = drop2.t_meet_video
    end4 = max(drop2.t_meet_video + 2.0, drop2.video_time(t_land_phys) + 1.2)
    shot(S("why2"), cut5, [(S("why2"), [-3.0, 1.7, 4.8], 0.60, 38), (drop2.t0 + 1.0, [-2.8, 1.7, 4.5], 0.60, 38),
                           (m4 - 1.2, [-1.4, 1.0, 2.7], 0.45, 36), (m4, [-1.2, 0.8, 2.6], 0.44, 36),
                           (end4, [-1.3, 0.75, 2.7], 0.44, 36)],
         lighting="sunset", focal_fn=front_fn, smooth=0.12)
    # 5. Night: hanging again with a ball at the centre-of-mass height; both are released together.
    shot(cut5, cut6, [(cut5, [2.6, 1.9, 4.6], 0.58, 38), (drop3.t0, [1.9, 1.7, 4.2], 0.58, 38),
                      (drop3.t0 + 1.0, [1.9, 1.7, 4.2], 0.58, 38), (cut6, [1.7, 1.2, 3.6], 0.56, 38)],
         lighting="night", focal_fn=hang)
    # 6. Day, real speed: the same drop is over in a blink; then rewind and crane along the stretch.
    shot(cut6, cut7, [(cut6, [-1.6, 1.3, 4.6], 0.60, 38), (drop4.t0, [-1.2, 1.3, 4.3], 0.60, 38),
                      (drop4.t0 + 1.0, [-1.2, 1.3, 4.3], 0.60, 38), (rew2_1, [-0.8, 1.5, 3.9], 0.60, 38),
                      (cut7, [0.9, 2.6, 3.4], 0.62, 38)], focal_fn=hang)
    # 7. Steel bar: low along the bar, following the pulse from the tapped end to the far end.
    bar_y = GROUND + BAR_R
    fp = lambda i: frames["focal_pt"][i] or [0.0, bar_y, BAR_Z]
    shot(cut7, cut8, [(cut7, [-2.2, 0.75, 0.9], 0.52, 36), (tap, [-1.9, 0.7, 0.75], 0.52, 36),
                      (tap + 0.8, [-1.9, 0.7, 0.75], 0.52, 36), (t_arrive, [-0.2, 0.55, 0.45], 0.52, 36),
                      (cut8, [0.1, 0.6, 0.6], 0.52, 36)],
         focal_fn=lambda i: fp(i)[1], xz_fn=lambda i: (fp(i)[0], fp(i)[2]), smooth=0.15)
    # 8. Big-picture pull-out over the whole little test site to the end.
    shot(cut8, n / fps + 0.1, [(cut8, [2.4, 2.4, 4.0], 0.58, 38), (n / fps, [6.0, 9.5, 9.0], 0.52, 38)],
         focal_fn=lambda i: focal_y[i])
    c12 = end4

    for k in range(len(shots) - 1):
        shots[k]["end"] = shots[k + 1]["start"]
    # frames where the camera follows the travelling front
    for i in range(int(round(S("why2") * fps)), int(round(m4 * fps))):
        if 0 <= i < n and frames["front"][i] >= 0:
            frames["focal"][i] = frames["front"][i]

    # ---- label cards (one at a time, near the top third) ------------------------------------
    cards = [
        {"start": E("setup") - 2.0, "end": E("setup") + 0.25, "big": "gravity = spring", "small": "on the bottom coil", "y": 0.17},
        {"start": drop1.t0 + 1.2, "end": drop1.t_meet_video - 0.1, "big": "{bottom_mm} mm", "small": "bottom moved", "y": 0.17},
        {"start": E("why1") - 2.2, "end": S("why2"), "big": "no change", "small": "in its forces", "y": 0.17},
        {"start": drop2.t_meet_video + 0.4, "end": cut5, "big": f"{phys.t_meet():.2f} s",
         "small": "bottom hovered", "y": 0.17},
        {"start": drop3.t0 + 0.6, "end": drop3.t_meet_video - 0.2, "big": "centre of mass", "small": "falls like the ball", "y": 0.17},
        {"start": drop4.t0 + 0.6, "end": rew2_0, "big": f"{phys.t_meet():.2f} s", "small": "at real speed", "y": 0.17},
        {"start": rew2_1 + 0.3, "end": cut7, "big": "t = √(2L / 3g)", "small": "L = how far it stretches", "y": 0.17},
        {"start": t_arrive + 0.2, "end": cut8, "big": "≈ 5 km/s", "small": "wave speed in steel", "y": 0.17},
    ]

    timing = {
        "hook_release": hook_drop.t0, "drop1_release": drop1.t0, "drop1_slow": drop1.slow,
        "drop1_meet": drop1.t_meet_video, "drop1_land": drop1.video_time(t_land_phys),
        "rewind": [rew0, rew1], "drop2_release": drop2.t0, "drop2_slow": drop2.slow,
        "drop2_meet": drop2.t_meet_video, "drop2_land": drop2.video_time(t_land_phys),
        "drop3_release": drop3.t0, "drop3_land": drop3.video_time(t_land_phys),
        "drop4_release": drop4.t0, "drop4_land": drop4.video_time(t_land_phys), "rewind2": [rew2_0, rew2_1],
        "tap": tap, "bar_arrive": t_arrive, "bar_slow": bar_slow,
        "reveals": [hook_drop.t0, drop1.t0, drop1.t_meet_video, drop2.t0, drop2.t_meet_video,
                    drop3.t0, drop4.t0, tap],
    }
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 11, "top_y": TOP,
            "bar": {"x0": BAR_X0, "x1": BAR_X1, "z": BAR_Z, "r": BAR_R},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing,
            "wordmark": None}


def sfx_events(plan: dict) -> list[tuple[float, str]]:
    t = plan["timing"]
    return [
        (t["hook_release"], "pop"),
        (t["drop1_release"], "pop"), (t["drop1_land"], "thud"),
        (t["rewind"][0], "whoosh"),
        (t["drop2_release"], "pop"), (t["drop2_release"] + 0.3, "rise"), (t["drop2_land"], "thud"),
        (t["drop3_release"], "pop"), (t["drop3_land"], "thud"),
        (t["drop4_release"], "pop"), (t["drop4_land"], "thud"),
        (t["rewind2"][0], "whoosh"),
        (t["tap"], "tick"), (t["bar_arrive"], "pop"),
    ]


def self_checks() -> dict:
    return phys.self_checks()

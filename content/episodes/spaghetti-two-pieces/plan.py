"""Spaghetti: render plan from the snap-back fracture model (factory/simulation_engine/physics/spaghetti.py).

Every shape on screen is a simulation state at some real time t_real. Each section of the video maps
video time to t_real with an explicit playback rate (real speed, slowed down, rewound), and the badge
says when it is slowed.
"""
from __future__ import annotations

import math

import numpy as np

from factory import camera as cam
from factory.simulation_engine.physics import spaghetti as sp

SCENE = "spaghetti3d"
BENCH = 0.75


def _rate_ramp(u, dur, r0, r1):
    """Playback rate (real s per video s) moving log-linearly from r0 to r1 over `dur` video seconds."""
    f = min(1.0, max(0.0, u / dur))
    return math.exp(math.log(r0) + (math.log(r1) - math.log(r0)) * cam.ease(f))


class Track:
    """Piecewise video->real time map: list of (video_start, real_at_start, rate_fn(u))."""
    def __init__(self, run, v0, r0, rate=lambda u: 1.0):
        self.run, self.keys = run, [(v0, r0, rate)]

    def then(self, v, rate_fn):
        vp, rp, fp = self.keys[-1]
        self.keys.append((v, rp + _integrate(fp, v - vp), rate_fn)); return self

    def hold(self, v):
        return self.then(v, lambda u: 0.0)

    def jump(self, v, real):
        self.keys.append((v, real, lambda u: 0.0)); return self

    def real(self, t):
        k = max(i for i, kk in enumerate(self.keys) if kk[0] <= t + 1e-9) if t >= self.keys[0][0] else 0
        v0, r0, f = self.keys[k]
        return r0 + _integrate(f, t - v0)

    def rate(self, t):
        k = max(i for i, kk in enumerate(self.keys) if kk[0] <= t + 1e-9) if t >= self.keys[0][0] else 0
        return self.keys[k][2](t - self.keys[k][0])


def _integrate(f, du, steps=None):
    if du <= 0:
        return 0.0
    n = steps or max(8, int(du * 200))
    h = du / n
    return sum(f((i + 0.5) * h) for i in range(n)) * h


def _phase_coeffs(run, t, pc):
    """Stripe phase along a piece as a + b*s (radians). Before the break the twist is uniform along the
    stick; after it, each half unwinds towards its own grip (left grip at 0, right grip at full twist)."""
    tw = 2 * np.pi * run.twist_turns
    if tw == 0:
        return 0.0, 0.0
    if t < run.t_break:
        f = cam.ease(t / run.t_twist) if run.t_twist > 0 else 1.0
        return 0.0, tw * f / sp.STICK
    f = math.exp(-(t - run.t_break) / 0.0008)
    mid = 0.5 * (pc["s0"] + pc["s1"])
    if mid < run.s_flaw:                 # left half: phase = tw*f*s/STICK
        return 0.0, tw * f / sp.STICK
    return tw * (1 - f), tw * f / sp.STICK   # right half: tw - tw*f*(1 - s/STICK)


def _grips(run, t):
    k = run.kappa_now(t)
    pts, th = sp.arc_points(k, np.array([0.0, sp.STICK]))
    tw = 2 * np.pi * run.twist_turns
    roll = tw * (cam.ease(t / run.t_twist) if run.t_twist > 0 and t < run.t_twist else 1.0) if tw else 0.0
    return [[round(float(pts[0, 0]), 5), round(float(pts[0, 1]), 5), round(float(th[0]), 4)],
            [round(float(pts[1, 0]), 5), round(float(pts[1, 1]), 5), round(float(th[1] + np.pi), 4)], round(roll, 4)]


def _pieces(run, t, glow_gain=2.5, hl=None):
    out = []
    for p in run.pieces(max(0.0, t)):
        pc = {"x": [round(float(v), 5) for v in p["pts"][:, 0]], "y": [round(float(v), 5) for v in p["pts"][:, 1]],
              "s0": round(float(min(p["s"][0], p["s"][-1])), 5), "s1": round(float(max(p["s"][0], p["s"][-1])), 5)}
        if p["s"][0] > p["s"][-1]:           # keep s increasing along the node order for the stripe
            pc["s0"], pc["s1"] = round(float(p["s"][0]), 5), round(float(p["s"][-1]), 5)
        e = np.minimum(1.0, glow_gain * p["excess"])
        if e.max() > 0.01:
            pc["e"] = [round(float(v), 2) for v in e]
        a, b = _phase_coeffs(run, t, pc)
        if b or a:
            pc["pa"], pc["pb"] = round(a, 4), round(b, 3)
        if hl and p["id"] in hl:
            pc["h"] = hl[p["id"]]
        out.append(pc)
    return out


def _crack_flash(run, t_real, window=0.00004):
    """Flash at a crack for a short real-time window after it forms (scaled by playback in the video)."""
    for (tc, s) in run.cracks:
        if 0 <= t_real - tc < window:
            pts, _ = sp.arc_points(run.kappa_break, np.array([s]))
            return [round(float(pts[0, 0]), 5), round(float(pts[0, 1]), 5), round(1 - (t_real - tc) / window, 2)]
    return None


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    S, E = tl.start, tl.end
    n = int(math.ceil((tl.duration + 0.85) * fps))
    T = np.arange(n) / fps
    plain, extra, twisted = sp.standard_runs()
    tb = plain.t_break

    # ---------------------------------------------------------------- time maps per section
    cut_wrong, cut_slow, cut_rehook, cut_hist = S("wrong") - 0.1, S("slow") - 0.1, S("rehook") - 0.1, S("history") - 0.1
    cut_reveal, cut_why, cut_outro = S("reveal") - 0.1, S("why") + 1.2, S("outro") - 0.1
    hook_break = 0.9
    A = (Track(plain, 0.0, tb - hook_break)
         .then(hook_break, lambda u: 1 / 3000)
         .then(hook_break + 0.9, lambda u: _rate_ramp(u, 1.8, 1 / 3000, 1.0))
         .then(hook_break + 2.7, lambda u: 1.0))
    a_end = A.real(cut_wrong)
    # wrong: rewind to just before the crack, then hold on the bent stick (the "weak spot")
    rew = 1.1
    B = Track(plain, cut_wrong, a_end, lambda u: -(a_end - (tb - 0.06)) / rew).hold(cut_wrong + rew)
    # slow + wave + burst: creep to the crack, then ~64,000x through the snap-back wave
    crack_v = S("slow") + 2.2
    second_v = E("burst") - 1.3
    first_secondary = min(c[0] for c in plain.cracks[1:]) - tb
    slow2 = first_secondary / (second_v - crack_v)
    C = (Track(plain, cut_slow, tb - 0.06, lambda u: 0.06 / (crack_v - cut_slow))
         .then(crack_v, lambda u: slow2)
         .then(second_v, lambda u: _rate_ramp(u, 1.4, slow2, 1.0))
         .then(second_v + 1.4, lambda u: 1.0))
    # rehook montage: three more sticks, each bent and snapped (slowed briefly at the snap)
    mont = []
    span = (cut_hist - cut_rehook) / 3
    for j, r in enumerate(extra[:3]):
        v0 = cut_rehook + j * span
        mont.append((v0, v0 + span, Track(r, v0, r.t_break - 0.7).then(v0 + 0.7, lambda u: 1 / 1500)
                     .then(v0 + 1.1, lambda u: _rate_ramp(u, 0.6, 1 / 1500, 1.0)).then(v0 + 1.7, lambda u: 1.0)))
    # history: the last montage stick's pieces at rest (golden light)
    # reveal / twist / result: a fresh stick, twisted one full turn, then bent slowly
    tw_start = E("reveal") - 1.3
    tw_end = S("twist") + 1.9
    twb = twisted.t_break
    break_v = S("result") + 0.55
    F_ = (Track(twisted, cut_reveal, 0.0, lambda u: 0.0)
          .then(tw_start, lambda u: twisted.t_twist / (tw_end - tw_start))
          .then(tw_end, lambda u: twisted.t_bend / (break_v - tw_end))
          .then(break_v, lambda u: 1 / 2000)
          .then(break_v + 0.5, lambda u: _rate_ramp(u, 0.8, 1 / 2000, 1.0))
          .then(break_v + 1.3, lambda u: 1.0))
    # why: replay the twisted snap at ~5,000x: the stripe unwinds, the leftover wave stays weak
    why_rate = 1 / 5000
    G_ = Track(twisted, cut_why, twb - 1.2 * why_rate, lambda u: why_rate)
    g_end = G_.real(S("catch") - 0.1)
    Hh = Track(twisted, S("catch") - 0.1, max(g_end, twb + 0.4)).then(S("catch"), lambda u: 1.0)
    # outro: a fresh untwisted stick being bent, ending exactly on the opening frame's state (loop)
    out_dur = n / fps - cut_outro
    I_ = Track(plain, cut_outro, tb - hook_break - out_dur)

    def section(t):
        if t < cut_wrong:
            return A, "A"
        if t < cut_slow:
            return B, "B"
        if t < cut_rehook:
            return C, "C"
        if t < cut_hist:
            for v0, v1, tr in mont:
                if t < v1:
                    return tr, "D"
            return mont[-1][2], "D"
        if t < cut_reveal:
            return mont[-1][2], "E"
        if t < cut_why:
            return F_, "F"
        if t < S("catch") - 0.1:
            return G_, "G"
        if t < cut_outro:
            return Hh, "H"
        return I_, "I"

    frames = {"pieces": [], "grips": [], "flash": [], "ring": [], "focal_pt": [], "badge": []}
    count_hl = [S("setup") + 1.6 + 0.55 * j for j in range(4)]
    piece_ids_plain = None
    real_log = []
    for i, t in enumerate(T):
        tr, name = section(t)
        run, tre = tr.run, tr.real(t)
        real_log.append((name, tre))
        rate = tr.rate(t)
        hl = None
        if name == "A" and t > count_hl[0] - 0.1:
            ids = [p["id"] for p in run.pieces(tre)]
            hl = {}
            for j, pid in enumerate(sorted(ids)):
                if j < 4:
                    dt_ = t - count_hl[j]
                    hl[pid] = round(max(0.0, 0.9 * math.exp(-max(0, dt_) / 0.35)) if dt_ >= 0 else 0.0, 2)
        gain = 2.5 if name != "G" else 0.9
        frames["pieces"].append(_pieces(run, tre, gain, hl))
        frames["grips"].append(_grips(run, tre))
        frames["flash"].append(_crack_flash(run, tre, window=max(0.00002, 0.3 * abs(rate))) if name in "ACDFG" else None)
        ring = None
        if name == "B" and t > cut_wrong + rew + 0.4:
            pts, th = sp.arc_points(plain.kappa_now(tre), np.array([plain.s_flaw]))
            ring = [round(float(pts[0, 0]), 5), round(float(pts[0, 1]), 5), round(min(1.0, (t - cut_wrong - rew - 0.4) / 0.25), 2), round(float(th[0]), 4)]
        frames["ring"].append(ring)
        badge = ""
        steady = abs(tr.rate(t + 0.05) - rate) < 1e-9 and abs(tr.rate(t - 0.05) - rate) < 1e-9
        if 0 < rate < 0.5 and name != "B" and not steady:
            badge = "SLOW MOTION"
        elif 0 < rate < 0.5 and name != "B":
            f = 1 / rate
            badge = f"SLOWED {int(round(f, -int(math.floor(math.log10(f))) + 1)):,}×" if f >= 10 else "SLOW MOTION"
        elif rate < 0:
            badge = "REWIND"
        if name == "D":
            j = [k for k, (v0, v1, _) in enumerate(mont) if v0 <= t < v1 + 1e-6]
            j = j[0] if j else 2
            done = tre > mont[j][2].run.t_break + 0.0005
            badge = f"TRY {j + 2} · {mont[j][2].run.n_pieces} PIECES" if done else f"TRY {j + 2}"
        if name == "E":
            badge = "AUDOLY & NEUKIRCH, 2005" if t < S("history") + 2.6 else "IG NOBEL PRIZE, 2006"
        if name == "F" and tw_start <= t < tw_end:
            badge = "TWIST: ≈ 1 TURN"          # narration: "almost a full turn"
        frames["badge"].append(badge)

    # ---------------------------------------------------------------- shots (world coordinates)
    K = lambda *a: list(a)
    TW_POS, TW_POS2, TW_LOOK = K(0.27, 0.865, 0.085), K(0.25, 0.87, 0.10), K(-0.06, 0.82, 0.0)   # behind the turning clamp
    shots = cam.chain([
        cam.shot(0.0, cut_wrong - 5.4, [(0.0, K(0.42, 0.93, 0.56), K(0.0, 0.83, 0.0), 34),
                                        (cut_wrong - 5.4, K(0.38, 0.93, 0.52), K(0.0, 0.83, 0.0), 34)], fps, "key"),
        cam.shot(cut_wrong - 5.4, cut_wrong, [(cut_wrong - 5.4, K(0.34, 1.22, 0.44), K(0.0, 0.76, 0.0), 32),
                                              (cut_wrong, K(0.16, 1.27, 0.50), K(0.0, 0.76, 0.0), 32)], fps, "key"),
        # rewind: start wide enough to see the pieces on the bench fly back together, then push in
        cam.shot(cut_wrong, cut_slow, [(cut_wrong, K(0.06, 0.95, 0.42), K(0.0, 0.80, 0.0), 34),
                                       (cut_wrong + 1.6, K(0.07, 0.88, 0.24), K(-0.005, 0.87, 0.0), 32),
                                       (cut_slow, K(0.035, 0.88, 0.19), K(-0.005, 0.878, 0.0), 32)], fps, "key"),
        cam.shot(cut_slow, crack_v + 5.2, [(cut_slow, K(0.0, 0.88, 0.27), K(-0.01, 0.86, 0.0), 34),
                                           (crack_v + 5.2, K(-0.03, 0.88, 0.25), K(-0.03, 0.86, 0.0), 34)], fps, "key"),
        cam.shot(crack_v + 5.2, S("burst") - 0.1, [(crack_v + 5.2, K(-0.03, 0.9, 0.36), K(-0.05, 0.85, 0.0), 34),
                                                   (S("burst"), K(-0.045, 0.9, 0.345), K(-0.05, 0.85, 0.0), 34)], fps, "key"),
        cam.shot(S("burst") - 0.1, cut_rehook, [(S("burst"), K(0.12, 1.0, 0.4), K(-0.02, 0.84, 0.0), 34),
                                                (cut_rehook, K(0.09, 1.0, 0.38), K(-0.02, 0.84, 0.0), 34)], fps, "key"),
        cam.shot(cut_rehook, cut_hist, [(cut_rehook, K(0.2, 1.18, 0.42), K(0.0, 0.77, 0.0), 34),
                                        (cut_hist, K(0.26, 1.2, 0.36), K(0.0, 0.77, 0.0), 34)], fps, "key"),
        cam.shot(cut_hist, cut_reveal, [(cut_hist, K(0.55, 1.08, 0.78), K(0.0, 0.79, -0.02), 30),
                                        (cut_reveal, K(-0.28, 1.08, 0.86), K(0.0, 0.79, -0.02), 30)], fps, "golden"),
        cam.shot(cut_reveal, tw_start - 0.2, [(cut_reveal, K(0.25, 0.855, 0.2), K(0.075, 0.825, 0.0), 34),
                                              (tw_start, K(0.22, 0.86, 0.21), K(0.075, 0.825, 0.0), 34)], fps, "key"),
        # both clamps in frame while one of them turns the stick (reviewer: the twist must be seen)
        cam.shot(tw_start - 0.2, tw_end, [(tw_start - 0.2, TW_POS, TW_LOOK, 38),
                                          (tw_end, TW_POS2, TW_LOOK, 38)], fps, "key"),
        cam.shot(tw_end, cut_why, [(tw_end, K(0.0, 0.88, 0.42), K(0.0, 0.83, 0.0), 34),
                                   (cut_why, K(0.0, 0.885, 0.38), K(0.0, 0.83, 0.0), 34)], fps, "key"),
        cam.shot(cut_why, S("catch") - 0.1, [(cut_why, K(0.045, 0.868, 0.19), K(0.0, 0.856, 0.0), 34),
                                             (S("catch") - 0.1, K(0.0, 0.87, 0.165), K(0.0, 0.856, 0.0), 34)], fps, "key"),
        cam.shot(S("catch") - 0.1, cut_outro, [(S("catch") - 0.1, K(0.3, 1.04, 0.5), K(0.0, 0.8, 0.0), 32),
                                               (cut_outro, K(0.25, 1.07, 0.45), K(0.0, 0.8, 0.0), 32)], fps, "key"),
        cam.shot(cut_outro, cut_outro + 3.2, [(cut_outro, K(0.5, 1.02, 0.66), K(0.0, 0.81, 0.0), 34),
                                              (cut_outro + 3.2, K(0.47, 0.99, 0.62), K(0.0, 0.815, 0.0), 34)], fps, "key"),
        cam.shot(cut_outro + 3.2, n / fps + 0.05, [(cut_outro + 3.2, K(-0.3, 0.98, 0.6), K(0.0, 0.82, 0.0), 34),
                                                  (n / fps, K(0.42, 0.93, 0.56), K(0.0, 0.83, 0.0), 34)], fps, "key"),
    ])
    frames["focal_pt"] = [None] * n
    for s_ in shots:
        for k, lk in enumerate(s_["look"]):
            i = s_["i0"] + k
            if 0 <= i < n:
                frames["focal_pt"][i] = [lk[0], lk[1] - BENCH, lk[2]]
    for i in range(n):
        if frames["focal_pt"][i] is None:
            frames["focal_pt"][i] = frames["focal_pt"][i - 1] if i else [0, 0.08, 0]

    def badge_clear(t0):
        """First time after t0 with no badge on screen."""
        for j in range(int(t0 * fps), n):
            if not frames["badge"][j]:
                return j / fps + 0.1
        return t0

    cards = [
        {"start": count_hl[3] + 0.3, "end": cut_wrong - 0.1, "big": f"{plain.n_pieces} pieces", "small": "from one snap", "y": 0.2},
        # the halves fly up to y~0.24 after the break: this card sits higher, after the badge clears, so it
        # never covers the gap between the two pieces (factory/qa inspect: recognition.card_covers_hero)
        {"start": max(break_v + 0.6, badge_clear(break_v)), "end": cut_why - 0.1, "big": f"{twisted.n_pieces} pieces",
         "small": "twisted first", "y": 0.125},
        {"start": S("catch") + 0.4, "end": S("catch") + 2.6, "big": "≈ 270°", "small": "model (25 cm stick)", "y": 0.16},
        {"start": S("catch") + 2.8, "end": cut_outro - 0.1, "big": "≈ 360°", "small": "in the lab", "y": 0.16},
    ]
    # sound cues at the moments the simulation produces them
    events = []
    for (name, run_, track, v0, v1) in [("A", plain, A, 0, cut_wrong), ("C", plain, C, cut_slow, cut_rehook),
                                        ("F", twisted, F_, cut_reveal, cut_why), ("G", twisted, G_, cut_why, S("catch") - 0.1)] + \
                                       [("D", tr.run, tr, v0, v1) for v0, v1, tr in mont]:
        for (tc, s) in run_.cracks:
            tv = _video_time(track, tc, v0, v1, fps)
            if tv is not None:
                events.append([round(tv, 3), "latch", {"gain": 0.9 if tc == run_.t_break else 0.7, "pan": (s / sp.STICK - 0.5) * 0.8,
                                                        "seed": len(events) + 11}])   # never the same crack twice
        for fr in (run_.fragments if name != "D" else []):      # montage: cracks only (it was a wall of tinks)
            land = next((tt for (tt, c, a) in fr.track if c[1] < sp.RADIUS + 0.003 and tt > fr.t0 + 0.01), None)
            if land is not None:
                tv = _video_time(track, land, v0, v1, fps)
                if tv is not None:
                    events.append([round(tv, 3), "tink", {"gain": 0.3, "seed": len(events) + 101,
                                                            "pitch": 0.85 + 0.1 * (len(events) % 4), "ring": 0.35}])
    events.append([round(cut_wrong + 0.02, 3), "rewind", {"gain": 0.5}])
    events.append([round(cut_why - 0.3, 3), "rewind", {"gain": 0.35}])
    events += [[round(c, 3), "tick", {"gain": 0.35, "pitch": 1.0 + 0.12 * j, "ring": 0.4, "seed": 40 + j}]
               for j, c in enumerate(count_hl)]        # counting the pieces: one step up per piece
    events.append([round(break_v + 0.05, 3), "ding", {"gain": 0.5}])
    timing = {"crack_v": crack_v, "second_v": second_v, "break_v": break_v, "slow2": slow2,
              "cuts": [s_["start"] for s_ in shots[1:]], "reveals": [break_v], "events": events,
              "mutes": [[second_v - 3.0, second_v - 0.05], [tw_end - 0.2, break_v - 0.05]], "swells": [second_v, break_v]}
    # facts: the simulated values every spoken or shown number is checked against (factory/qa/science.py)
    slowed = sorted({int(b.split()[1].replace(",", "").rstrip("×")) for b in frames["badge"] if b.startswith("SLOWED ")})
    facts = {"plain_pieces": plain.n_pieces, "twisted_pieces": twisted.n_pieces,
             "untwisted_min_pieces": min([plain.n_pieces] + [r.n_pieces for r in extra]),
             "montage_pieces": [r.n_pieces for r in extra[:3]], "twist_turns": 1.0, "slow_factors": slowed,
             "events": {
                 # data-level check: the pieces drawn on screen at these times must equal the simulated count
                 "snap_plain": {"t": count_hl[3] + 0.3, "observe": "pieces", "expect": plain.n_pieces},
                 "snap_twisted": {"t": max(break_v + 0.6, badge_clear(break_v)), "observe": "pieces", "expect": twisted.n_pieces}}}
    for j, (v0, v1, tr) in enumerate(mont):
        facts["events"][f"snap_try{j + 2}"] = {"t": v1 - 0.2, "observe": "pieces", "expect": tr.run.n_pieces}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 9, "supersample": 1.0,
            "stick": sp.STICK, "shots": shots, "cards": cards, "frames": frames, "timing": timing, "wordmark": None,
            "facts": facts}


def observe(plan: dict, i: int, what: str):
    """What the plan draws at frame i (QA data-level check)."""
    if what == "pieces":
        return len(plan["frames"]["pieces"][min(i, len(plan["frames"]["pieces"]) - 1)])
    raise KeyError(what)


def _video_time(track, t_real, v0, v1, fps):
    """First video time in [v0, v1) at which the track reaches real time t_real."""
    prev = track.real(v0)
    for i in range(int(math.ceil(v0 * fps)), int(math.ceil(v1 * fps))):
        r = track.real(i / fps)
        if prev < t_real <= r:
            return i / fps
        prev = r
    return None


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 92, "gain": 0.16}


def self_checks() -> dict:
    return sp.self_checks()

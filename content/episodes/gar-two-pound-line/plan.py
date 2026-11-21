"""A 153-pound fish on 2-pound line: render plan (scene renderer/scenes/garline3d.js).

The shared lake set. The rowing boat out on the lake, the wizard on the bow seat with a rod, the woman behind him on
the stern seat, both facing the bow (-x). A gar-like fish 2.2 m long (the reported catch was 7 ft 3 in) runs out
ahead of the boat on the line.

The fight is a simple, illustrative drag model (CLAUDE.md honesty: the caveats say so):
  * line rated 2 lb; the reel's drag is set to 0.7 lb, about a third of the rating (a common rule of thumb; the
    real catch's setting is not in our source);
  * in the water the fish's weight is almost cancelled by buoyancy (we draw weight and buoyancy as near-equal
    arrows), so the line only feels the fish's pull;
  * when the pull exceeds the drag setting the spool slips: tension stays at the drag setting and line pays out;
    otherwise the angler reels in at a lower tension. Runs get shorter as the fish tires;
  * out of the water the line would have to hold the fish's full 153 lb, about 76 times its rating.
Positions, tension, line paid out and the spool's rotation are all computed here; the scene only draws.
"""
from __future__ import annotations

import math

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "garline3d"
SLUG = "gar-two-pound-line"
LB = 4.448                                       # newtons per pound-force
FISH_LB, LINE_LB = 153.0, 2.0
DRAG_LB = 0.7                                    # illustrative drag setting (~1/3 of the line rating)
REEL_LB = 0.42                                   # tension while reeling in (illustrative)
FISH_LEN = 2.21                                  # 7 ft 3 in
SPOOL_R = 0.035

BOAT = [0.0, 0.0, -3.2]
SEAT_X = 0.47
SIT_ROOT_Y = -0.33
WIZ = [BOAT[0] - SEAT_X, SIT_ROOT_Y, BOAT[2]]
WIZ_FACE = -math.pi / 2                          # both face the bow (-x)
WOMAN = [BOAT[0] + SEAT_X, SIT_ROOT_Y, BOAT[2] + 0.08]
WOMAN_FACE = -math.pi / 2
BOW_X = BOAT[0] - 1.55
ALPHA = 0.32                                     # the fish runs out at this angle off the boat's axis, toward the camera
SPEAKER = {"hook": "woman", "what": "wizard", "float": "woman", "pull": "woman", "drag": "woman", "swims": "wizard",
           "tired": "woman", "lift": "woman", "payoff": "wizard"}
SIDE = [BOAT[0] - 0.75, -0.02, BOAT[2] - 1.0]    # where the tired fish lies alongside the boat at the end


def fight(T, S, E, at):
    """Integrate the fight frame by frame: distance d of the fish's nose from the bow, tension (lb), line paid out
    (m, cumulative for the spool), fish effort. Returns arrays."""
    n = len(T)
    dt = T[1] - T[0]
    d = np.zeros(n); ten = np.zeros(n); out = np.zeros(n); eff = np.zeros(n); mode = [""] * n
    dist, paid = 2.6, 0.0
    t_tired0, t_tired1 = S("tired"), E("tired")
    for i, t in enumerate(T):
        if t < S("float") - 0.1:                                  # hook + what: a run, the drag slipping
            pull, v_reel, m = 1.6, 0.0, "run"
        elif t < S("pull"):                                       # float: hovering, slow reel
            pull, v_reel, m = 0.15, 0.08, "hover"
        elif t < at("drag", "Pull") - 0.1:                        # pull + the brake: pulling, still under the setting
            u = min(1.0, (t - S("pull")) / max(0.5, at("drag", "Pull") - 0.1 - S("pull")))
            pull, v_reel, m = 0.15 + 0.45 * u + 0.05 * math.sin(t * 5), 0.0, "pull"
        elif t < t_tired0:                                        # a hard run: over the setting, line slips
            pull, v_reel, m = 1.9, 0.0, "run"
        elif t < t_tired1:                                        # tiring: reel in, short run, reel in...
            u = (t - t_tired0) / (t_tired1 - t_tired0)
            ph = (u * 3.0) % 1.0
            running = ph > 0.62 and u < 0.85
            pull = (1.3 * (1 - u) + 0.5) if running else 0.2 * (1 - u) + 0.1
            v_reel, m = (0.0 if running else 0.75 - 0.15 * u), ("run" if running else "reel")
        else:                                                     # lift + payoff: beside the boat, spent
            pull, v_reel, m = 0.08, 0.0, "spent"
        if pull > DRAG_LB:                                        # the spool slips: tension capped, line pays out
            tension = DRAG_LB
            v_out = 0.32 * min(1.0, (pull - DRAG_LB) / 0.8 + 0.3)
        elif v_reel > 0:
            tension, v_out = max(pull, REEL_LB if m == "reel" else 0.2), -v_reel
        else:
            tension, v_out = pull, 0.0
        if m == "spent":
            v_out = 0.0
        dist = max(0.6, dist + v_out * dt)
        paid += v_out * dt
        d[i], ten[i], out[i], eff[i], mode[i] = dist, tension, paid, min(1.0, pull / 1.6), m
    return d, ten, out, eff, mode


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    T = np.arange(n) / fps
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)
    tw, tm = duo.talk_tracks(tl, SPEAKER, env, fps)
    d, ten, paid, eff, mode = fight(T, S, E, at)
    t_end0 = E("tired") - 0.2                    # the fish comes alongside
    t_lift0, t_lift1 = at("lift", "lift") - 0.3, at("lift", "Out") + 0.2
    t_net = S("payoff") + 0.1

    def fish_at(i):
        t = T[i]
        dist = d[i]
        depth = -1.0 + 0.55 * duo.ramp(t, E("tired") - 2.5, 2.3)
        cx = BOW_X - dist * math.cos(ALPHA) - 0.35 * FISH_LEN * math.cos(ALPHA)
        cz = BOAT[2] - dist * math.sin(ALPHA) - 0.35 * FISH_LEN * math.sin(ALPHA)
        head = math.pi - ALPHA - (0.9 if mode[i] == "run" else 0.5) + 0.12 * math.sin(t * 0.7)
        u = duo.ramp(t, t_end0, 1.6)
        cx, cz = cx + (SIDE[0] - cx) * u, cz + (SIDE[2] - cz) * u
        depth = depth + (SIDE[1] - depth) * u
        head = head + (math.pi - head) * u
        return [round(cx, 4), round(depth, 4), round(cz, 4), round(head, 4), 0.0]

    fishp = [fish_at(i) for i in range(n)]
    fx_at = lambda t: fishp[min(n - 1, int(t * fps))]
    bx, _, bz = BOAT

    E_ = duo.shot(fps)
    K = lambda *a: list(a)
    UL = "underlake"
    f0 = fx_at(0.3); f1 = fx_at(2.5)
    hook_b, hook_c = 2.5, max(4.6, at("hook", "line") - 0.2)
    mid = lambda t: (bx - 1.6 + fx_at(t)[0]) / 2
    tired_c = (S("tired") + E("tired")) / 2
    fA = lambda t: fx_at(t)
    line_view = lambda t0, t1, fov=48: E_(t0, t1, K(bx + 1.7, 2.5, bz + 1.0), K(bx + 1.5, 2.35, bz + 0.85),
                                           K(fA(t0)[0], -0.7, fA(t0)[2]), fov, "key", K(fA(t1)[0], -0.7, fA(t1)[2]))
    shots_spec = [
        # hook (a): under water ahead of the fish: the huge gar swims hard, the thin line runs up from its jaw
        ("under", E_(0.0, hook_b, K(f0[0] - 2.3, -0.8, f0[2] - 2.2), K(f1[0] - 2.0, -0.85, f1[2] - 2.0), K(f0[0] + 0.2, -1.0, f0[2]), 50, UL, K(f1[0] + 0.2, -1.0, f1[2]))),
        # hook (b): the wizard side-on, the rod bent hard out over the bow
        ("out", E_(hook_b, hook_c, K(bx - 0.7, 1.15, bz - 2.9), K(bx - 0.75, 1.1, bz - 2.65), K(bx - 0.78, 0.95, bz), 46)),
        # hook (c): from behind and above the boat along the line to the fish (water see-through)
        ("xray", line_view(hook_c, S("what") - 0.1)),
        # what: the wizard, close
        ("out", E_(S("what") - 0.1, S("float") - 0.1, K(bx - 0.95, 1.08, bz - 1.45), K(bx - 0.92, 1.05, bz - 1.35), K(bx - 0.5, 0.92, bz), 36)),
        # float: side-on to the fish, water clear: weight down, water pushing up, nearly equal
        ("xray", E_(S("float") - 0.1, S("pull") - 0.1, K(fA(S("float"))[0] + 0.2, -0.5, fA(S("float"))[2] - 3.6),
                    K(fA(S("float"))[0] + 0.1, -0.55, fA(S("float"))[2] - 3.2), K(fA(S("float"))[0], -0.9, fA(S("float"))[2]), 46)),
        # pull: under water off the fish's flank: the line tight from its jaw
        ("under", E_(S("pull") - 0.1, S("drag") - 0.1, K(fA(S("pull"))[0] + 0.6, -1.15, fA(S("pull"))[2] - 3.0),
                     K(fA(S("pull"))[0] + 0.5, -1.1, fA(S("pull"))[2] - 2.7), K(fA(S("pull"))[0], -1.0, fA(S("pull"))[2]), 48, UL)),
        # drag: close on the reel as the line slips out
        ("out", E_(S("drag") - 0.1, S("swims") - 0.1, K(bx - 0.75, 0.7, bz - 1.05), K(bx - 0.73, 0.68, bz - 0.98), K(bx - 0.62, 0.42, bz - 0.25), 30)),
        # swims: the wizard, worried, the woman behind him
        ("out", E_(S("swims") - 0.1, S("tired") - 0.1, K(bx - 1.6, 1.15, bz - 2.1), K(bx - 1.45, 1.1, bz - 1.95), K(bx - 0.1, 0.85, bz), 42)),
        # tired (a): along the line again: run, reel, run
        ("xray", line_view(S("tired") - 0.1, tired_c)),
        # tired (b): high three-quarter view from the side as the fish comes in
        ("xray", E_(tired_c, S("lift") - 0.1, K(bx - 1.9, 3.3, bz - 4.6), K(bx - 1.6, 3.0, bz - 4.1), K(fA(tired_c)[0], -0.5, fA(tired_c)[2]), 48, "key", K(fA(S("lift"))[0], -0.4, fA(S("lift"))[2]))),
        # lift: both in the boat, the fish alongside; he starts to lift, she stops him
        ("out", E_(S("lift") - 0.1, at("lift", "Out") - 0.1, K(bx - 1.2, 1.35, bz - 3.2), K(bx - 1.1, 1.3, bz - 2.9), K(bx - 0.7, 0.35, bz - 0.6), 46)),
        # lift (b): low by the water, the huge fish alongside the boat, the thin line from its jaw up to the rod
        ("out", E_(at("lift", "Out") - 0.1, S("payoff") - 0.1, K(SIDE[0] - 1.9, 0.35, SIDE[2] - 1.5), K(SIDE[0] - 1.7, 0.32, SIDE[2] - 1.35), K(SIDE[0] - 0.2, 0.05, SIDE[2]), 48)),
        # payoff: the tiny net next to the huge fish
        ("out", cam.shot(S("payoff") - 0.1, dur + 0.05, [(S("payoff") - 0.1, K(bx - 1.75, 1.95, bz - 2.75), K(bx - 1.0, 0.3, bz - 0.55), 46),
                                                         (dur + 0.05, K(bx - 1.65, 1.85, bz - 2.5), K(bx - 1.0, 0.3, bz - 0.55), 46)], fps, "key")),
    ]
    shots = cam.chain([s for _, s in shots_spec])
    kinds = [kd for kd, _ in shots_spec]
    for kd, s_ in zip(kinds, shots):
        if kd == "xray":
            s_["dof"] = 0

    def kind_at(t):
        for kd, s_ in zip(kinds, shots):
            if s_["start"] <= t < s_["end"]:
                return kd
        return kinds[-1]

    net_pos = [SIDE[0] - 0.42 * FISH_LEN, 0.1, SIDE[2] + 0.05]
    net_yaw = math.atan2(-(WIZ[2] - net_pos[2]), -(WIZ[0] - net_pos[0]))   # handle (local -x) toward the wizard
    frames = {k: [] for k in ("wiz_blink", "woman_blink", "look_w", "look_m", "woman_point", "xray", "fish", "fish_effort",
                              "fish_turn", "tension", "rod_bend", "rod_tilt", "rod_yaw", "line_sag", "spool", "arrows",
                              "wiz_rod_arm", "wiz_net", "lifted", "water_op")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        frames["xray"].append(1 if kind_at(t) == "xray" else 0)
        frames["fish"].append(fishp[i])
        frames["fish_effort"].append(round(0.15 + 0.85 * eff[i], 3))
        frames["fish_turn"].append(round(0.25 * math.sin(t * 0.9) * eff[i], 3))
        lift = duo.bump(t, t_lift0, 0.5, max(0.1, t_lift1 - t_lift0 - 1.0), 0.5)
        frames["lifted"].append(round(lift, 3))
        frames["water_op"].append(round(0.8 - 0.35 * duo.ramp(t, S("lift") - 0.2, 0.3), 3))
        frames["tension"].append(round(float(ten[i]), 3))
        frames["rod_bend"].append(round(min(1.0, 0.15 + 1.15 * ten[i] / LINE_LB + 0.25 * lift), 3))
        frames["rod_tilt"].append(round(52 - 26 * lift - 8 * duo.ramp(t, t_net, 0.6), 2))
        frames["rod_yaw"].append(round(-0.25, 3))
        frames["line_sag"].append(round(0.02 + 0.2 * (1 - min(1.0, ten[i] / DRAG_LB)), 3))
        frames["spool"].append(round(float(paid[i]) / SPOOL_R, 3))
        frames["arrows"].append(round(duo.ramp(t, at("float", "dense") - 0.2, 0.5) * (1 - duo.ramp(t, S("pull") - 0.3, 0.25)), 3))
        frames["wiz_rod_arm"].append(round(0.4 + 0.25 * lift, 3))
        frames["wiz_net"].append(round(duo.ramp(t, t_net, 0.5), 3))
        frames["woman_point"].append(round(duo.bump(t, at("lift", "never") - 0.3, 0.3, 1.6, 0.5) + 0.6 * duo.bump(t, S("drag") + 0.4, 0.3, 1.2, 0.4), 3))
        frames["look_w"].append("woman" if a in ("swims",) or (a == "lift" and t > at("lift", "never")) else
                                ("net" if a == "payoff" else "fish"))
        frames["look_m"].append("wizard" if a in ("lift", "what", "swims", "payoff") else "fish")
        frames["wiz_blink"].append(1.0 if (t % 3.6) < 0.12 else 0.0)
        frames["woman_blink"].append(1.0 if ((t + 1.2) % 3.2) < 0.12 else 0.0)
    frames["focal_pt"] = duo.focal_track(shots, n)

    over = [("153 lb if lifted" if frames["lifted"][i] > 0.3 else None) for i in range(n)]
    shown = [(round(LINE_LB * 1.25 if over[i] else frames["tension"][i], 3)) for i in range(n)]
    overlays = [{"type": "tension", "start": S("pull") - 0.1, "end": E("lift") + 0.1, "xy": [0.5, 0.115], "values": shown,
                 "over": over, "fps": fps, "max": LINE_LB * 1.25, "label": "pull on the line", "unit": "lb",
                 "marks": [{"v": DRAG_LB, "text": "drag slips", "color": "amber"}, {"v": LINE_LB, "text": "line snaps", "color": "red"}]},
                {"type": "callout", "start": at("float", "dense") + 0.1, "end": S("pull") - 0.3, "at": [fishp[int(at("float", "dense") * fps)][0], -1.6, fishp[int(at("float", "dense") * fps)][2] - 0.25],
                 "text": "its weight", "dx": -0.18, "dy": 0.06},
                {"type": "callout", "start": at("float", "dense") + 0.3, "end": S("pull") - 0.3, "at": [fishp[int(at("float", "dense") * fps)][0], -0.2, fishp[int(at("float", "dense") * fps)][2] - 0.25],
                 "text": "water pushes up", "dx": 0.12, "dy": -0.07}]
    cards = [{"start": at("hook", "two") - 0.1, "end": S("what") - 0.15, "big": "153 lb", "small": "on 2 lb line", "y": 0.16}]
    events = [(round(hook_b, 3), "whoosh", {"gain": 0.07}),
              (round(at("pull", "only") - 0.1, 3), "rise", {"gain": 0.06}),
              (round(t_lift0 + 0.5, 3), "ding", {"gain": 0.08}),
              (round(at("drag", "slips") - 0.1, 3), "tick", {"gain": 0.08}),
              (round(t_net + 0.4, 3), "pop", {"gain": 0.07})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [at("hook", "two"), at("float", "dense"), at("drag", "slips")],
               "events": events, "mutes": [], "swells": [S("payoff")]}
    i_end = n - 1
    facts = {"fish_lb": FISH_LB, "line_lb": LINE_LB, "drag_lb": DRAG_LB, "weight_over_rating": round(FISH_LB / LINE_LB, 1),
             "max_tension_lb": round(float(ten.max()), 3),
             "events": {"line_never_over_drag": {"t": dur / 2, "observe": "max_tension_ok", "expect": 1, "tol": 0},
                        "fish_alongside_at_end": {"t": dur - 0.2, "observe": "fish_alongside", "expect": 1, "tol": 0}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 61, "supersample": 1.0, "bloom_threshold": 3.5,
            "end_hold_s": 1.4,
            "layout": {"boat": BOAT, "clip_y": 0.12 - 0.5 + 0.02, "wiz": WIZ, "wiz_face": WIZ_FACE, "woman": WOMAN, "woman_face": WOMAN_FACE,
                       "fish_len": FISH_LEN, "net": net_pos, "net_yaw": net_yaw},
            "shots": shots, "cards": cards, "overlays": overlays, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    F = plan["frames"]
    if what == "max_tension_ok":
        return 1 if max(F["tension"]) <= DRAG_LB + 1e-6 else 0
    if what == "fish_alongside":
        f = F["fish"][k]
        return 1 if math.hypot(f[0] - SIDE[0], f[2] - SIDE[2]) < 0.05 else 0
    if what in F:
        return F[what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 96, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """The drag model never lets the tension pass the drag setting (so never the line's rating); the fish's weight
    out of water is 76x the rating; the run/reel phases really move the fish."""
    class _TL:
        pass
    ts = np.arange(0, 50, 1 / 30)
    marks = {"hook": 0.3, "what": 7.6, "float": 11.1, "pull": 18.4, "drag": 23.0, "swims": 30.0, "tired": 33.0, "lift": 40.0, "payoff": 47.5}
    ends = {"tired": 39.7}
    S = lambda b: marks[b]
    E = lambda b: ends.get(b, marks[b] + 3)
    at = lambda b, w, o=1: marks[b] + 1.0
    d, ten, paid, eff, mode = fight(ts, S, E, at)
    return {"tension never exceeds the drag setting, far below the 2 lb rating": {"pass": ten.max() <= DRAG_LB + 1e-9 < LINE_LB,
                                                                                    "detail": f"max {ten.max():.2f} lb, drag {DRAG_LB} lb, rating {LINE_LB} lb"},
            "out of the water the fish weighs about 76 times the line's rating": {"pass": abs(FISH_LB / LINE_LB - 76.5) < 0.1, "detail": f"{FISH_LB / LINE_LB:.1f}x"},
            "line slips out on runs and comes back on reels": {"pass": paid.max() > 1.0 and d[-1] < d.max() - 1.0,
                                                               "detail": f"max out {paid.max():.1f} m, nearest {d.min():.1f} m, farthest {d.max():.1f} m"},
            "the model fish is 2.2 m (7 ft 3 in)": {"pass": abs(FISH_LEN - 7.25 * 0.3048) < 0.01, "detail": f"{FISH_LEN} m"}}

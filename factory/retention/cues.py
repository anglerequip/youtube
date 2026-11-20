"""Cues: sound, music and camera accents bound to the story, not to seconds.

`retention.cues` in the storyboard is a list of entries like

    - {at: "reality+0.35", riser: 1.4, music: swell, reveal: true}   # build into the reveal
    - {at: "hud:arch2.settle", sfx: lock, gain: 0.3}                  # the number lands: one soft accent
    - {at: "double@doubles", punch_in: 0.08}                          # slow push-in on the key word
    - {at: "catch@no", music: drop, drop_s: 0.5}                      # music drops out before the payoff line

Keys: at (time expression, see timing.py), sfx (a factory/sound_design.py name) + gain/params,
riser (seconds: a swell that *ends* on `at`), music (swell | drop; drop_s, or until: a time expression), punch_in (fraction of the
field of view, eased over punch_s, held to the end of the shot), reveal (register as a reveal for QA).

Every sound produced here goes into the same event list as the plan's own sfx_events(), so the sound
QA layer (repetition, density, periodicity, masking) checks it like any other cue.
"""
from __future__ import annotations

from . import timing


class CueError(ValueError):
    pass


def _smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def compile_cues(spec: list, plan: dict, tl, events: dict, cfg: dict, features: dict) -> dict:
    fps, n = plan["fps"], plan["n_frames"]
    duration = n / fps
    sfx, mutes, swells, reveals, punches = [], [], [], [], []
    for c in spec or []:
        t = timing.resolve(c.get("at"), tl, events, duration)
        if not 0 <= t <= duration:
            raise CueError(f"cue at {c.get('at')!r} resolves to {t:.2f}s, outside the video (0-{duration:.1f}s)")
        if c.get("sfx"):
            s = c["sfx"]
            name, params = (s, {}) if isinstance(s, str) else (s["name"], {k: v for k, v in s.items() if k != "name"})
            params = {**params, **{k: c[k] for k in ("gain", "pitch", "seed", "ring", "speed") if k in c}}
            params.setdefault("gain", 0.3)
            sfx.append((round(t, 3), name, params))
        if c.get("riser"):
            d = float(c["riser"])
            sfx.append((round(max(0.0, t - d), 3), "rise", {"gain": float(c.get("riser_gain", 0.35)), "dur": d}))
        m = c.get("music")
        if m == "swell":
            swells.append(round(t, 3))
        elif m == "drop":
            if c.get("until") is not None:                    # music out from `at` until `until`
                t2 = timing.resolve(c["until"], tl, events, duration)
                mutes.append([round(t, 3), round(max(t, t2), 3)])
            else:                                             # a short gap of silence right before `at`
                d = float(c.get("drop_s", 0.6))
                mutes.append([round(max(0.0, t - d), 3), round(t, 3)])
        elif m is not None:
            raise CueError(f"cue at {c.get('at')!r}: music must be swell or drop, got {m!r}")
        if c.get("punch_in"):
            punches.append((t, float(c["punch_in"]), float(c.get("punch_s", 0.5))))
        if c.get("reveal"):
            reveals.append(round(t, 3))
    # automatic accents (feature flag), plus widgets that ask for one explicitly
    acc = cfg.get("accents", {})
    hud = plan.get("hud") or {}
    auto = bool(features.get("auto_accents"))
    for w in hud.get("widgets", []):
        want = w.get("accent")
        if want is False or (not auto and not want):
            continue
        a = acc.get("answer" if w["type"] == "question" else "appear", {})
        t = w["t_answer"] if w["type"] == "question" else w["t0"]
        sfx.append((round(t, 3), a.get("sfx", "blip"), {"gain": float(a.get("gain", 0.2)), "seed": 400 + len(sfx)}))
        if w["type"] == "meter" and w.get("threshold", {}).get("i_cross") is not None:
            a = acc.get("threshold", {})
            sfx.append((round(w["threshold"]["i_cross"] / fps, 3), a.get("sfx", "lock"), {"gain": float(a.get("gain", 0.3))}))
    if auto:
        a = acc.get("appear", {})
        for card in plan.get("cards", []):
            sfx.append((round(card["start"], 3), a.get("sfx", "blip"), {"gain": float(a.get("gain", 0.2)), "seed": 500 + len(sfx)}))
    applied = apply_punch_ins(plan, punches)
    return {"events": sorted(sfx, key=lambda e: e[0]), "mutes": mutes, "swells": swells, "reveals": reveals,
            "punch_ins": applied}


def apply_punch_ins(plan: dict, punches: list) -> list:
    """Narrow the field of view of keyed shots from t (eased over dur) to the end of that shot."""
    fps = plan["fps"]
    done = []
    for t, amount, dur in punches:
        if not 0 < amount < 0.5:
            raise CueError(f"punch_in {amount} must be between 0 and 0.5 (fraction of the field of view)")
        shot = next((s for s in plan.get("shots", []) if s["start"] <= t < s["end"]), None)
        if shot is None or shot.get("type") != "keys":
            continue
        if not shot.get("fovs"):
            shot["fovs"] = [shot.get("fov", 38)] * len(shot["pos"])
        k0 = int(round(t * fps)) - shot["i0"]
        for k in range(max(0, k0), len(shot["fovs"])):
            u = _smooth((k - k0) / max(1.0, dur * fps))
            shot["fovs"][k] = round(shot["fovs"][k] * (1 - amount * u), 3)
        done.append({"t": round(t, 3), "amount": amount, "shot_start": shot["start"]})
    return done

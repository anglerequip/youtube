"""HUD widgets: on-screen information that is driven by the simulation, compiled into the render plan.

Every widget is declared in the storyboard (`retention.hud`) and compiled here into per-frame data that
renderer/hud.js only draws. Numbers are never typed into the picture by hand: a value comes from the
simulation (`frames:` a per-frame series in the plan, `fact:` a plan fact) or from authored keys that
must be bound to a claim (factory/qa/hud.py enforces this, like the label cards).

Widget types (see docs/RETENTION.md for when each one is justified):
  counter    a live number with a label, e.g. "drop 1.0 m" rising to "2.0 m" while the stand rises
  meter      a bar between min and max with an optional threshold mark that fires an event when crossed
  dimension  a measuring line between two tracked 3D points, labelled with its live value
  callout    a label pinned to a moving 3D point (ring + leader line), optionally with a live value
  question   the episode's open question, pinned until the beat that answers it, then a short "answered" state
  progress   which step of an experiment sequence we are on (e.g. 1 m, 2 m, no push)

Events produced for cues and QA:  hud:<id>.appear, .hide, .settle (value within 2% of where it ends up),
.cross (meter threshold), .answer (question), .step<k> (progress).
"""
from __future__ import annotations

from . import timing

TYPES = ("counter", "meter", "dimension", "callout", "question", "progress")
NUMERIC = ("counter", "meter", "dimension", "callout")


class HudError(ValueError):
    pass


def _smooth(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def value_fn(w: dict, plan: dict, tl, events: dict, duration: float):
    """Return f(i) -> float for the widget's value source, or None if it shows no number."""
    src = w.get("value")
    if src is None:
        return None
    if isinstance(src, (int, float)):
        src = {"keys": [[0, src]]}
    scale, offset = float(src.get("scale", 1.0)), float(src.get("offset", 0.0))
    if "frames" in src:
        series = (plan.get("frames") or {}).get(src["frames"])
        if series is None:
            raise HudError(f"widget {w['id']}: plan has no frames['{src['frames']}']")
        n = len(series)
        return lambda i: float(series[min(max(i, 0), n - 1)]) * scale + offset
    if "fact" in src:
        v = (plan.get("facts") or {}).get(src["fact"])
        if v is None:
            raise HudError(f"widget {w['id']}: plan has no fact '{src['fact']}'")
        return lambda i: float(v) * scale + offset
    if "keys" in src:
        fps = plan["fps"]
        keys = sorted((timing.resolve(t, tl, events, duration), float(v)) for t, v in src["keys"])

        def f(i):
            t = i / fps
            if t <= keys[0][0]:
                return keys[0][1] * scale + offset
            for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
                if t < t1:
                    return (v0 + (v1 - v0) * _smooth((t - t0) / max(1e-6, t1 - t0))) * scale + offset
            return keys[-1][1] * scale + offset
        return f
    raise HudError(f"widget {w['id']}: value needs frames:, fact: or keys:")


def fmt(w: dict, v: float) -> str:
    try:
        return str(w.get("format", "{v:.0f}")).format(v=v)
    except (ValueError, KeyError) as e:
        raise HudError(f"widget {w['id']}: bad format {w.get('format')!r}: {e}") from e


def _settle(vals: list[float], i0: int, fps: int, tol: float = 0.02) -> float:
    """First time after which the value stays within tol of its final value (and keeps changing before)."""
    final = vals[-1]
    band = max(abs(final) * tol, 1e-9)
    k = len(vals) - 1
    while k > 0 and abs(vals[k - 1] - final) <= band:
        k -= 1
    return (i0 + k) / fps


def compile_hud(spec: list, plan: dict, tl, cfg: dict) -> dict:
    """Compile `retention.hud` into plan['hud'] = {widgets, anchors, events}."""
    fps, n = plan["fps"], plan["n_frames"]
    duration = n / fps
    events: dict[str, float] = {}
    widgets = []
    slots = cfg.get("slots", {})
    style = cfg.get("style", {})
    anchor_src = plan.get("anchors") or {}
    used_anchors: set[str] = set()
    ids = set()
    # questions and progress first: their events can open other widgets' windows
    order = sorted(spec, key=lambda w: 0 if w.get("type") in ("question", "progress") else 1)
    for w in order:
        wid, typ = w.get("id"), w.get("type")
        if not wid or wid in ids:
            raise HudError(f"every HUD widget needs a unique id (got {wid!r})")
        ids.add(wid)
        if typ not in TYPES:
            raise HudError(f"widget {wid}: unknown type {typ!r} (one of {TYPES})")
        out = {"id": wid, "type": typ, "label": w.get("label", ""), "style": {**style, **(w.get("style") or {})}}
        # ---- window
        if typ == "question":
            ask = timing.resolve(w.get("ask"), tl, events, duration)
            ans = timing.resolve(w.get("answer"), tl, events, duration)
            hold = float(w.get("hold_s", 2.5))
            if ans <= ask:
                raise HudError(f"question {wid}: answer ({ans:.1f}s) must come after ask ({ask:.1f}s)")
            t0, t1 = ask, min(duration, ans + hold)
            out.update(text=w.get("text", ""), answer_text=w.get("answer_text", ""), t_answer=round(ans, 3),
                       i_answer=int(round(ans * fps)))
            events[f"hud:{wid}.answer"] = ans
        else:
            t0, t1 = timing.window(w.get("show"), tl, events, duration)
        i0, i1 = max(0, int(round(t0 * fps))), min(n, int(round(t1 * fps)))
        if i1 - i0 < 1:
            raise HudError(f"widget {wid}: empty window")
        out.update(i0=i0, i1=i1, t0=round(t0, 3), t1=round(t1, 3))
        events[f"hud:{wid}.appear"], events[f"hud:{wid}.hide"] = t0, t1
        # ---- placement
        if typ in ("counter", "meter", "question", "progress"):
            at = w.get("at") or slots.get(w.get("slot", "top_left"))
            if at is None:
                raise HudError(f"widget {wid}: unknown slot {w.get('slot')!r} (slots: {sorted(slots)})")
            out["at"] = [float(at[0]), float(at[1])]
        if typ == "callout":
            out["anchor"] = w.get("anchor"); out["offset"] = list(w.get("offset", [0.14, -0.07]))
            used_anchors.add(out["anchor"])
        if typ == "dimension":
            out["from"], out["to"] = w.get("from"), w.get("to")
            out["side"] = float(w.get("side", 0.05))       # label offset from the line (frame widths)
            used_anchors.update([out["from"], out["to"]])
        # ---- values
        f = value_fn(w, plan, tl, events, duration) if typ in NUMERIC else None
        if f is not None:
            vals = [f(i) for i in range(i0, i1)]
            texts = [fmt(w, v) for v in vals]
            out["texts"] = texts
            # a short scale pulse whenever the shown number changes (the eye catches the update)
            pulse, last = [], -99
            for k, s in enumerate(texts):
                if k and s != texts[k - 1]:
                    last = k
                pulse.append(round(max(0.0, 1 - (k - last) / 6), 3) if last >= 0 else 0.0)
            out["pulse"] = pulse
            out["values"] = [round(v, 5) for v in vals]
            events[f"hud:{wid}.settle"] = _settle(vals, i0, fps)
            if typ == "meter":
                lo, hi = float(w.get("min", 0.0)), float(w.get("max", 1.0))
                out["fracs"] = [round(min(1.0, max(0.0, (v - lo) / max(1e-9, hi - lo))), 4) for v in vals]
                th = w.get("threshold")
                if th is not None:
                    tv = float(th["value"] if isinstance(th, dict) else th)
                    out["threshold"] = {"frac": (tv - lo) / max(1e-9, hi - lo),
                                        "label": (th.get("label", "") if isinstance(th, dict) else "")}
                    for k in range(1, len(vals)):
                        if (vals[k - 1] - tv) * (vals[k] - tv) <= 0 and vals[k - 1] != vals[k]:
                            events[f"hud:{wid}.cross"] = (i0 + k) / fps
                            out["threshold"]["i_cross"] = i0 + k
                            break
        elif typ in NUMERIC and typ != "callout":
            raise HudError(f"widget {wid}: a {typ} needs a value")
        if typ == "progress":
            items = w.get("items") or []
            if not items:
                raise HudError(f"progress {wid}: needs items")
            out["items"] = [it.get("label", "") for it in items]
            starts = [timing.resolve(it["at"], tl, events, duration) for it in items]
            out["starts"] = [int(round(s * fps)) for s in starts]
            for k, s in enumerate(starts):
                events[f"hud:{wid}.step{k + 1}"] = s
        if w.get("claims"):
            out["claims"] = [{"claim": c["claim"], "t": round(timing.resolve(c["at"], tl, events, duration), 3)}
                             for c in w["claims"]]
        out["accent"] = w.get("accent")
        out["ticks"] = w.get("ticks")
        widgets.append(out)
    anchors = {}
    for a in sorted(x for x in used_anchors if x):
        if a not in anchor_src:
            raise HudError(f"anchor '{a}' is not exported by the plan (plan['anchors'] or plan.py hud_anchors())")
        anchors[a] = anchor_src[a]
    # keep the declared order for drawing (questions were compiled first only for their events)
    by_id = {w["id"]: w for w in widgets}
    widgets = [by_id[w["id"]] for w in spec]
    return {"widgets": widgets, "anchors": anchors, "events": {k: round(v, 3) for k, v in events.items()}}


def tick_events(hud: dict, cfg: dict, fps: int) -> list:
    """Sound ticks for counters that ask for them: one per change of the shown number, rate-limited,
    pitch following the value, so a counting number is heard as well as seen (never a fixed metronome)."""
    tk = cfg.get("ticks", {})
    out = []
    for w in hud["widgets"]:
        spec = w.get("ticks")
        if not spec or "texts" not in w:
            continue
        spec = spec if isinstance(spec, dict) else {}
        gap = 1.0 / float(spec.get("max_rate_hz", tk.get("max_rate_hz", 5.0)))
        max_n = int(spec.get("max", 8))
        name, gain = spec.get("sfx", tk.get("sfx", "blip")), float(spec.get("gain", tk.get("gain", 0.12)))
        vals = w["values"]
        lo, hi = min(vals), max(vals)
        last, k_n = -1e9, 0
        for k in range(1, len(w["texts"])):
            if w["texts"][k] == w["texts"][k - 1]:
                continue
            t = (w["i0"] + k) / fps
            if t - last < gap or k_n >= max_n:
                continue
            u = (vals[k] - lo) / (hi - lo) if hi > lo else 0.5
            out.append((round(t, 3), name, {"gain": gain, "pitch": round(0.85 + 0.5 * u, 3), "seed": 300 + k_n}))
            last, k_n = t, k_n + 1
    return out


def visible_at(hud: dict, i: int) -> list[dict]:
    return [w for w in hud.get("widgets", []) if w["i0"] <= i < w["i1"]]


def text_at(w: dict, i: int) -> str | None:
    if "texts" not in w or not (w["i0"] <= i < w["i1"]):
        return None
    return w["texts"][i - w["i0"]]


def value_at(w: dict, i: int) -> float | None:
    if "values" not in w:
        return None
    k = min(max(0, i - w["i0"]), len(w["values"]) - 1)
    return w["values"][k]


def approx_rect(w: dict, i: int, W: int = 1080, H: int = 1920) -> tuple[float, float, float, float] | None:
    """Rough screen box (x0, y0, x1, y1 as frame fractions) of a screen-anchored widget, for layout checks.
    Mirrors renderer/hud.js sizes: label 1.9% of H, value 3.4% of H, Poppins ~0.58 em per character."""
    if "at" not in w:
        return None
    cx, cy = w["at"]
    if w["type"] == "question":
        txt = max(len(w.get("text", "")), len(w.get("answer_text", "")) + 2)
        wd = (txt * 0.58 * 0.021 * H + 0.06 * H) / W
        return cx - wd / 2, cy - 0.022, cx + wd / 2, cy + 0.022
    if w["type"] == "progress":
        wd = (sum(len(s) for s in w["items"]) * 0.58 * 0.016 * H + len(w["items"]) * 0.05 * H) / W
        return cx - wd / 2, cy - 0.02, cx + wd / 2, cy + 0.02
    s = text_at(w, min(max(i, w["i0"]), w["i1"] - 1)) or ""
    wd = (max(len(s) * 0.58 * 0.034 * H, len(w.get("label", "")) * 0.58 * 0.017 * H, 0.16 * W if w["type"] == "meter" else 0)
          + 0.04 * H) / W
    hgt = (0.034 + 0.019 + 0.024 + (0.012 if w["type"] == "meter" else 0))
    return cx - wd / 2, cy - hgt / 2, cx + wd / 2, cy + hgt / 2


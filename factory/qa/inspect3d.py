"""Layers 4/5 (assets, geometry): inspect the 3D scene graph at sampled frames (renderer/inspect.js).

Runs before the full render (seconds, not hours), so geometry defects block early with their cause:
missing world (clipped sky / far plane), NaN geometry, z-fighting, shadow-map cut-offs, unreadable
thin parts, fragments that merge on a phone screen, loose chain beads, and popping between frames.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from .findings import Finding

ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "renderer"


def config() -> dict:
    return yaml.safe_load((ROOT / "config" / "quality.yaml").read_text())


def sample_times(plan: dict, every: float = 2.0) -> list[float]:
    dur = plan["n_frames"] / plan["fps"]
    ts = {round(t * every, 2) for t in range(int(dur / every) + 1)}
    for s in plan.get("shots", []):
        ts |= {round(s["start"] + 0.1, 2), round(s["end"] - 0.15, 2)}
    for c in plan.get("cards", []):
        ts.add(round(c["start"] + 0.2, 2))
    for ev in ((plan.get("facts") or {}).get("events") or {}).values():
        ts |= {round(ev["t"] + d, 2) for d in (0.0, 0.2, 0.4, 0.6)}
    return sorted(t for t in ts if 0 <= t < dur - 0.1)


def run(scene: str, plan_path: Path, times: list[float], out: Path, timeout: int = 1800) -> dict:
    cmd = ["node", str(RENDERER / "render.mjs"), "--scene", scene, "--plan", str(plan_path),
           "--inspect", ",".join(f"{t:.2f}" for t in times), "--inspect-out", str(out)]
    subprocess.run(cmd, check=True, timeout=timeout, capture_output=True)
    return json.loads(out.read_text())


def card_rect(card: dict, plan: dict) -> tuple:
    """Approximate screen box (fractions) of a label card as renderer/world.js drawCard lays it out."""
    W, H = plan.get("W", 1080), plan.get("H", 1920)
    big, small = str(card.get("big", "")), str(card.get("small", ""))
    wb, ws = len(big) * 0.62 * 0.034 * H, len(small) * 0.55 * 0.019 * H     # Poppins average advance
    w = max(wb, ws) + 2 * 0.02 * H
    h = 0.034 * H * 1.15 + (0.019 * H * 1.25 if small else 0) + 2 * 0.012 * H
    cx, cy = W * card.get("x", 0.5), H * card.get("y", 0.2)
    return ((cx - w / 2) / W, (cy - h / 2) / H, (cx + w / 2) / W, (cy + h / 2) / H)


def _contracts(sb) -> dict:
    return {e.get("id"): (e.get("visual_contract") or {}) for e in (sb.extra.get("entities") or [])} if sb else {}


def analyse(report: dict, plan: dict, sb=None, cfg: dict | None = None) -> list[Finding]:
    """Turn the raw inspection into findings (grouped, so one defect is one finding with its times)."""
    c = (cfg or config())["inspect"]
    F: list[Finding] = []
    groups: dict[str, dict] = {}

    def add(key, sev, blocks, msg, t, **kw):
        g = groups.setdefault(key, {"sev": sev, "blocks": blocks, "msg": msg, "times": [], "kw": kw})
        g["times"].append(t)
        g["sev"] = min(g["sev"], sev)
        if sev <= g["sev"]:
            g["blocks"] = blocks or g["blocks"]
        if sev < g["sev"] or len(g["times"]) == 1:
            g["msg"] = msg

    st = report.get("static", {})
    for name in st.get("nonfinite", []):
        F.append(Finding(f"geometry.nonfinite.{name}", "geometry", 0, "BLOCKED_GEOMETRY",
                         f"mesh '{name}' has NaN/Infinity vertex positions", repair="fix the generator of that mesh"))
    for d in st.get("degenerate", []):
        F.append(Finding(f"geometry.degenerate.{d['mesh']}", "geometry", 3, None,
                         f"mesh '{d['mesh']}' has {d['fraction']:.0%} zero-area triangles", evidence=d))

    contracts = _contracts(sb)
    events = {round(ev["t"] * plan["fps"]): (name, ev) for name, ev in
              ((plan.get("facts") or {}).get("events") or {}).items() if ev.get("observe") == "pieces"}
    frames = report.get("frames", [])
    for k, f in enumerate(frames):
        t = f["t"]
        if f["holes"]["fraction"] > c["hole_fraction_block"]:
            add("geometry.world_missing", 0, "BLOCKED_GEOMETRY",
                f"{f['holes']['fraction']:.2%} of the frame shows no world (clear colour) in box {f['holes']['bbox']}; "
                f"camera near {f['camera']['near']} far {f['camera']['far']}", t,
                expected="sky, ground or geometry behind every pixel",
                repair="keep the sky dome inside the far plane (World.prepare) and close gaps in the set",
                regression_test="tests/test_qa_regression.py::test_chain_v1_black_triangle")
        for nm in f.get("nonfinite", []):
            add(f"geometry.nonfinite.{nm}", 0, "BLOCKED_GEOMETRY", f"{nm} contains NaN/Infinity", t)
        for cp in f.get("coplanar", []):
            add(f"geometry.coplanar.{cp['a']}|{cp['b']}", 2, None,
                f"surfaces '{cp['a']}' and '{cp['b']}' overlap {cp['gap']:.1e} m apart at {cp['distance']} m from the "
                f"camera; the depth buffer needs {cp['need']:.1e} m: z-fighting risk", t,
                repair="offset one surface (a few mm) or use polygonOffset")
        if f["depth"]["ratio"] > c["depth_ratio_warn"]:
            add("geometry.depth_ratio", 3, None, f"far/near ratio {f['depth']['ratio']:,} (depth precision)", t)
        for s in f.get("shadow_cutoffs", []):
            a = s["visible_area_px_360"]
            if a >= c["shadow_cut_risk_px"]:
                sev = 1 if a >= c["shadow_cut_block_px"] else 2
                caster = s["caster"].split("#")[0]
                add(f"render.shadow_cutoff.{caster}", sev, "BLOCKED_RENDER_ARTIFACT" if sev <= 1 else None,
                    f"shadow of '{caster}' is cut by the shadow-map edge while in view ({s['distance']} m away, "
                    f"fog {s['fog']:.0%}, ~{a} px² on a phone, screen box {s['screen']})", t,
                    expected="every visible shadow complete, or none at all",
                    repair="enlarge/re-centre the shadow box, or stop distant objects casting",
                    regression_test="tests/test_qa_regression.py::test_traffic_v1_shadow_seams")
        nxt = frames[k + 1] if k + 1 < len(frames) and frames[k + 1]["i"] == f["i"] + 1 else None
        for pi, p in enumerate(f.get("probes", [])):
            ent = p.get("entity")
            con = contracts.get(ent, {})
            if p["kind"] == "chain" and p["on_screen"]:
                if p["gap_px_1080"] >= c["chain_gap_px"] and p["connector_px_1080"] < c["chain_connector_px"]:
                    add(f"recognition.chain_loose_beads.{ent}", 1, "BLOCKED_OBJECT_RECOGNITION",
                        f"'{ent}': visible {p['gap_px_1080']:.1f} px gaps between {p['bead_px_1080']:.0f} px beads with "
                        f"{'no' if not p['connector_px_1080'] else 'a too thin'} connector: reads as loose balls, not a chain", t,
                        expected=con.get("must_read_as", "a connected chain"), repair="model the links between beads",
                        regression_test="tests/test_qa_regression.py::test_chain_v1_loose_beads")
            if p["kind"] == "thickness" and p["on_screen"] and con.get("min_px_at_360") and \
                    p["px_360"] < float(con["min_px_at_360"]):
                add(f"readability.thin.{ent}.{p.get('part')}", 2, None,
                    f"'{ent}' {p.get('part')} is {p['px_360']:.1f} px on a 360 px phone (contract {con['min_px_at_360']})", t)
            if p["kind"] == "pieces" and f["i"] in events:
                name, ev = events[f["i"]]
                # the count must read at some point in the event window (pieces need a moment to separate)
                win = [q for g in frames if f["i"] <= g["i"] <= f["i"] + int(0.6 * plan["fps"])
                       for q in g.get("probes", []) if q["kind"] == "pieces"]
                best = max(win, key=lambda q: (q["readable_at_360"] == ev["expect"], q["readable_at_360"]))
                p = best
                if p["readable_at_360"] != ev["expect"] or p["on_screen"] != ev["expect"]:
                    add(f"recognition.piece_count.{name}", 0, "BLOCKED_VISUAL_CONTRADICTION",
                        f"event {name}: {p['on_screen']} pieces on screen, {p['readable_at_360']} distinguishable on a "
                        f"phone, but the simulation (and narration) say {ev['expect']}", t,
                        expected=f"{ev['expect']} separate pieces visible", repair="frame all pieces and keep their gaps visible")
            if nxt and nxt["shot"] == f["shot"] and pi < len(nxt.get("probes", [])) and "x" in p:
                q = nxt["probes"][pi]
                if p.get("on_screen") and q.get("on_screen") and \
                        max(abs(q["x"] - p["x"]), abs(q["y"] - p["y"])) > c["pop_jump"]:
                    add(f"temporal.pop.{ent}", 2, None,
                        f"'{ent}' jumps {max(abs(q['x'] - p['x']), abs(q['y'] - p['y'])):.0%} of the frame in one frame", t)
        # a label card must never cover the thing it describes (hero points: fragment ends, focal point)
        for card in plan.get("cards", []):
            if not (card["start"] <= t < card["end"]):
                continue
            x0, y0, x1, y1 = card_rect(card, plan)
            pts = []
            for p in f.get("probes", []):
                if p["kind"] == "pieces":
                    pts += [q for e in p.get("ends", []) for q in e]
                elif "x" in p and p.get("on_screen"):
                    pts.append([p["x"], p["y"]])
            hit = [q for q in pts if x0 <= q[0] <= x1 and y0 <= q[1] <= y1]
            if hit:
                add(f"recognition.card_covers_hero.{card['big']}", 1, "BLOCKED_OBJECT_RECOGNITION",
                    f"card '{card['big']}' covers the hero at {hit[0]} (card box {[round(v, 3) for v in (x0, y0, x1, y1)]})", t,
                    expected="labels sit beside what they describe, never on top of it",
                    repair="move the card (y) or reframe the shot")
    for key, g in groups.items():
        times = sorted(set(g["times"]))
        F.append(Finding(key, key.split(".")[0], g["sev"], g["blocks"] if g["sev"] <= 1 else None,
                         g["msg"] + (f" (at {len(times)} sampled frames, {times[0]:.1f}-{times[-1]:.1f}s)" if len(times) > 1 else ""),
                         t=times[0], evidence={"times": times[:20]}, **g["kw"]))
    return F


def check(ctx, workdir: Path | None = None) -> tuple[list[Finding], dict]:
    plan = ctx.plan
    if plan is None:
        return [], {"note": "no plan"}
    cfg = config()
    workdir = workdir or (ctx.out / "qa")
    workdir.mkdir(parents=True, exist_ok=True)
    pp = workdir / "plan.inspect.json"
    pp.write_text(json.dumps(plan, separators=(",", ":")))
    times = sample_times(plan, cfg["inspect"]["sample_every_s"])
    scene = ctx.sb.extra.get("scene") or plan["scene"]
    rep = run(scene, pp, times, workdir / "inspect.json")
    pp.unlink(missing_ok=True)
    return analyse(rep, plan, ctx.sb, cfg), {"samples": len(rep.get("frames", [])), "scene": scene}

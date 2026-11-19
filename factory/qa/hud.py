"""HUD and story-structure QA (factory/retention): numbers on screen are true, overlays are readable,
sparing and clear of the platform UI, and open questions are actually answered.

Checks (all pre-render, from the plan alone):
  hud.unbacked_number     a widget shows authored numbers (keys/literal) with no claim behind them
  hud.claim_mismatch      at a bound time, the shown number disagrees with the claim's true value
  hud.claim_unknown       a widget binds a claim id the storyboard does not have
  hud.clutter             more widgets / overlays at once than config/retention.yaml allows
  hud.overlap_card        a screen widget overlaps a label card
  hud.unsafe              a screen widget sits outside the platform-safe area or in the caption band
  hud.offscreen           a tracked callout / dimension points at something that is out of frame too often
  hud.too_small           a dimension line is too short on screen to read
  hud.too_brief           a widget is shown for less than min_dwell_s
  story.loop              a question is answered too soon or too late, or does not end in "?"
"""
from __future__ import annotations

from ..retention import hud as H
from ..retention import project
from .findings import Finding
from .science import _truth, agrees, mentions


def _rect_overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _card_rect(card, W=1080, Hh=1920):
    big, small = str(card.get("big", "")), str(card.get("small", ""))
    w = (max(len(big) * 0.6 * 0.034 * Hh, len(small) * 0.55 * 0.019 * Hh) + 0.04 * Hh) / W
    h = (0.034 * 1.15 + (0.019 * 1.25 if small else 0) + 0.024)
    cx, cy = card.get("x", 0.5), card.get("y", 0.2)
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def _label_rect(w, plan, hud, i, W, Hh):
    """Approximate screen box of a tracked widget's label (mirrors renderer/hud.js placement)."""
    cam = project.camera_at(plan, i)
    if cam is None or w["type"] not in ("callout", "dimension"):
        return None
    A = hud["anchors"]
    names = [w["anchor"]] if w["type"] == "callout" else [w["from"], w["to"]]
    pts = [project.to_screen(A[a][min(i, len(A[a]) - 1)], cam, W, Hh) for a in names]
    if any(p is None for p in pts):
        return None
    txt = H.text_at(w, i) or ""
    wd = (max(len(txt) * 0.6 * 0.034 * Hh, len(w.get("label", "")) * 0.58 * 0.017 * Hh) + 0.04 * Hh) / W
    hh = (0.034 * 1.12 + (0.017 * 1.25 if w.get("label") else 0) + 0.022) if txt else 0.042
    if w["type"] == "callout":
        cx, cy = pts[0][0] + w["offset"][0], pts[0][1] + w["offset"][1]
    else:
        (ax, ay), (bx, by) = pts[0][:2], pts[1][:2]
        cx, cy = (ax + bx) / 2 + (w.get("side", 0.05)) + 0.06, (ay + by) / 2
        if abs(by - ay) < 0.3 * max(1e-6, abs(bx - ax)):     # mostly horizontal line: the label sits beside it
            cx = (ax + bx) / 2 + w.get("side", 0.05) + 0.06
    return cx - wd / 2, cy - hh / 2, cx + wd / 2, cy + hh / 2


def check(ctx, rcfg: dict) -> tuple[list[Finding], dict]:
    plan, sb = ctx.plan, ctx.sb
    F: list[Finding] = []
    if not plan or not plan.get("hud"):
        return F, {"widgets": 0}
    hud = plan["hud"]
    fps, n = plan["fps"], plan["n_frames"]
    W, Hh = plan.get("W", 1080), plan.get("H", 1920)
    lim = rcfg.get("limits", {})
    safe = rcfg.get("safe", {"x": [0.06, 0.84], "y": [0.075, 0.66]})
    band = rcfg.get("caption_band", [0.68, 0.78])
    claims = {c.get("id"): c for c in (sb.extra.get("claims") or [])}
    sbf = [str(sb.path / "storyboard.yaml")]
    spec = {w.get("id"): w for w in ((sb.extra.get("retention") or {}).get("hud") or [])}

    for w in hud["widgets"]:
        wid = w["id"]
        # ---- truth of numbers
        src = (spec.get(wid) or {}).get("value")
        authored = isinstance(src, (int, float)) or (isinstance(src, dict) and "keys" in src)
        if "texts" in w and authored and not w.get("claims"):
            shown = {s for s in w["texts"] if mentions(s)}
            if shown:
                F.append(Finding(f"hud.unbacked_number.{wid}", "hud", 1, "BLOCKED_MISSING_EVIDENCE",
                                 f"widget {wid} shows hand-set numbers ({', '.join(sorted(shown)[:3])}) with no claim",
                                 repair="drive it from the simulation (value: {frames: ...} or {fact: ...}) or bind claims:",
                                 files=sbf))
        for b in w.get("claims", []):
            c = claims.get(b["claim"])
            if c is None:
                F.append(Finding(f"hud.claim_unknown.{wid}.{b['claim']}", "hud", 1, "BLOCKED_SPEC",
                                 f"widget {wid} binds claim '{b['claim']}', which the storyboard does not define", files=sbf))
                continue
            truth = _truth(c, ctx.facts)
            i = min(max(int(round(b["t"] * fps)), w["i0"]), w["i1"] - 1)
            if not (w["i0"] <= int(round(b["t"] * fps)) < w["i1"]):
                F.append(Finding(f"hud.claim_outside.{wid}.{b['claim']}", "hud", 2, None,
                                 f"widget {wid}: claim {b['claim']} is bound at {b['t']:.2f}s, outside the widget's window",
                                 t=b["t"], files=sbf))
            txt = H.text_at(w, i) or ""
            ms = [m for m in mentions(txt)]
            if truth is None or not ms:
                F.append(Finding(f"hud.claim_mismatch.{wid}.{b['claim']}", "hud", 0, "BLOCKED_VISUAL_CONTRADICTION",
                                 f"widget {wid} at {b['t']:.2f}s shows '{txt}', which cannot be checked against claim {b['claim']}",
                                 t=b["t"]))
                continue
            ok, why = agrees(ms[0], truth, float(c.get("tolerance", 0.12)))
            if not ok:
                F.append(Finding(f"hud.claim_mismatch.{wid}.{b['claim']}", "hud", 0, "BLOCKED_VISUAL_CONTRADICTION",
                                 f"widget {wid} at {b['t']:.2f}s shows '{txt}' but claim {b['claim']} is {truth:g} ({why})",
                                 t=b["t"], expected=f"{truth:g} {c.get('unit', '')}",
                                 repair="bind the claim where the value has settled, or fix the value source"))
        # ---- dwell
        if (w["i1"] - w["i0"]) / fps < float(lim.get("min_dwell_s", 1.5)):
            F.append(Finding(f"hud.too_brief.{wid}", "hud", 2, None,
                             f"widget {wid} is on screen only {(w['i1'] - w['i0']) / fps:.2f}s", t=w["t0"]))
        # ---- placement of screen widgets
        if "at" in w:
            r = H.approx_rect(w, w["i0"], W, Hh)
            if r[0] < safe["x"][0] or r[2] > safe["x"][1] or r[1] < safe["y"][0] or r[3] > safe["y"][1]:
                F.append(Finding(f"hud.unsafe.{wid}", "hud", 2, None,
                                 f"widget {wid} box x {r[0]:.2f}-{r[2]:.2f}, y {r[1]:.2f}-{r[3]:.2f} leaves the safe area "
                                 f"x {safe['x']}, y {safe['y']} (app buttons / captions cover it)", t=w["t0"],
                                 repair="use a slot from config/retention.yaml or move it inward"))
            for card in plan.get("cards", []):
                if card["start"] < w["t1"] and w["t0"] < card["end"] and _rect_overlap(r, _card_rect(card, W, Hh)):
                    F.append(Finding(f"hud.overlap_card.{wid}", "hud", 2, None,
                                     f"widget {wid} overlaps the card '{card.get('big')}' at {max(card['start'], w['t0']):.1f}s",
                                     t=max(card["start"], w["t0"]), repair="move the widget to another slot or drop the card"))
                    break
        # ---- tracked overlays: anchors on screen, readable size, out of the caption band
        if w["type"] in ("callout", "dimension"):
            names = [w["anchor"]] if w["type"] == "callout" else [w["from"], w["to"]]
            on, tot, small, in_band, unknown = 0, 0, 0, 0, 0
            for i in range(w["i0"], w["i1"], 3):
                cam = project.camera_at(plan, i)
                if cam is None:
                    unknown += 1
                    continue
                pts = []
                for a in names:
                    tr = hud["anchors"][a]
                    pts.append(project.to_screen(tr[min(i, len(tr) - 1)], cam, W, Hh))
                tot += 1
                if all(p is not None and 0.03 <= p[0] <= 0.97 and 0.03 <= p[1] <= 0.97 for p in pts):
                    on += 1
                    if w["type"] == "dimension" and abs(pts[0][1] - pts[1][1]) + abs(pts[0][0] - pts[1][0]) < 0.04:
                        small += 1
                    lab_y = pts[0][1] + (w.get("offset", [0, -0.07])[1] if w["type"] == "callout" else 0)
                    if w["type"] == "dimension":
                        lab_y = (pts[0][1] + pts[1][1]) / 2
                    if band[0] <= lab_y <= band[1]:
                        in_band += 1
            if tot:
                share = on / tot
                if share < float(lim.get("callout_onscreen_share", 0.85)):
                    F.append(Finding(f"hud.offscreen.{wid}", "hud", 2, None,
                                     f"{w['type']} {wid}: its anchor is in frame only {share:.0%} of the time it is shown",
                                     t=w["t0"], repair="shorten show: to the shots that frame the subject"))
                if on and small / on > 0.25:
                    F.append(Finding(f"hud.too_small.{wid}", "hud", 2, None,
                                     f"dimension {wid} is under 4% of the frame on screen {small / on:.0%} of the time: unreadable",
                                     t=w["t0"], repair="show it only on closer shots"))
                if on and in_band / on > 0.2:
                    F.append(Finding(f"hud.caption_clash.{wid}", "hud", 2, None,
                                     f"{w['type']} {wid}: its label sits in the caption band {in_band / on:.0%} of the time",
                                     t=w["t0"]))
    # ---- overlapping overlays (screen widgets, tracked labels, the playback badge), frame by frame
    badge = rcfg.get("reserved", {}).get("badge")
    badges = (plan.get("frames") or {}).get("badge") or []
    seen = set()
    for i in range(0, n, 3):
        rects = []
        for w in H.visible_at(hud, i):
            r = H.approx_rect(w, i, W, Hh) if "at" in w else _label_rect(w, plan, hud, i, W, Hh)
            if r:
                rects.append((w["id"], r))
        if badge and i < len(badges) and badges[i]:       # width follows the badge text (world.js drawBadge)
            px = 0.0135 * Hh
            bw = (len(badges[i]) * 0.62 * px + 2 * 0.9 * px + 2.6 * 0.36 * px) / W
            rects.append(("badge", (0.5 - bw / 2, badge[0], 0.5 + bw / 2, badge[1])))
        for a in range(len(rects)):
            for b in range(a + 1, len(rects)):
                key = tuple(sorted((rects[a][0], rects[b][0])))
                if key not in seen and _rect_overlap(rects[a][1], rects[b][1]):
                    seen.add(key)
                    F.append(Finding(f"hud.overlap.{key[0]}.{key[1]}", "hud", 2, None,
                                     f"{key[0]} and {key[1]} overlap on screen at {i / fps:.1f}s", t=i / fps,
                                     repair="move one of them (slot / offset) or shorten a window so they hand over"))
    # ---- clutter, frame by frame
    worst_w, worst_o, at = 0, 0, 0.0
    for i in range(0, n, 3):
        vis = H.visible_at(hud, i)
        screen = [w for w in vis if "at" in w]
        cards = [c for c in plan.get("cards", []) if c["start"] <= i / fps < c["end"]]
        o = len(vis) + len(cards)
        if len(screen) > worst_w or o > worst_o:
            at = i / fps
        worst_w, worst_o = max(worst_w, len(screen)), max(worst_o, o)
    if worst_w > int(lim.get("max_widgets", 2)) or worst_o > int(lim.get("max_overlays", 3)):
        F.append(Finding("hud.clutter", "hud", 2, None,
                         f"{worst_w} screen widgets / {worst_o} overlays at once (around {at:.1f}s); house style is sparing",
                         t=at, expected=f"at most {lim.get('max_widgets', 2)} widgets and {lim.get('max_overlays', 3)} overlays",
                         repair="shorten windows so they hand over instead of stacking"))
    # ---- story: question loops
    for w in hud["widgets"]:
        if w["type"] != "question":
            continue
        gap = w["t_answer"] - w["t0"]
        if not str(w.get("text", "")).strip().endswith("?"):
            F.append(Finding(f"story.loop_text.{w['id']}", "story", 3, None, f"question {w['id']} does not end with '?'"))
        if gap < float(lim.get("question_min_gap_s", 4.0)):
            F.append(Finding(f"story.loop_short.{w['id']}", "story", 3, None,
                             f"question {w['id']} is answered {gap:.1f}s after it is asked: too soon to create curiosity",
                             t=w["t0"]))
        if gap > float(lim.get("question_max_gap_s", 45.0)):
            F.append(Finding(f"story.loop_long.{w['id']}", "story", 2, None,
                             f"question {w['id']} stays open {gap:.1f}s: viewers forget it", t=w["t0"]))
    metrics = {"widgets": len(hud["widgets"]), "max_screen_widgets": worst_w, "max_overlays": worst_o,
               "events": len(hud.get("events", {})),
               "cue_sounds": len((plan.get("retention") or {}).get("events", []))}
    return F, metrics

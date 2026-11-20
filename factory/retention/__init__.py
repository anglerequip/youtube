"""Retention toolkit: storyboard-driven HUD, cues and caption emphasis for any episode.

An episode opts in with a `retention:` block in storyboard.yaml:

    retention:
      features: {auto_accents: false}       # optional overrides of config/retention.yaml
      hud:   [ ...widgets, see hud.py ]
      cues:  [ ...cues, see cues.py ]

The production workflow and the QA layers load an episode's plan module through `load_plan_module(sb)`,
which returns the module with build_plan / sfx_events / music wrapped so the retention layer is applied
in exactly one place. With no `retention:` block the wrapped functions return what the episode's own
functions return, unchanged.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from types import SimpleNamespace

import yaml

from . import cues as _cues
from . import hud as _hud
from . import timing  # noqa: F401  (public)


@lru_cache(maxsize=1)
def config() -> dict:
    from ..configuration import settings
    p = settings.root / "config" / "retention.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def spec_of(sb) -> dict | None:
    r = (getattr(sb, "extra", None) or {}).get("retention")
    return r or None


def features(sb) -> dict:
    return {**config().get("features", {}), **((spec_of(sb) or {}).get("features") or {})}


def apply(sb, plan: dict, tl, module=None) -> dict:
    """Compile the storyboard's retention block into the plan (in place) and return the plan."""
    spec = spec_of(sb)
    if not spec:
        return plan
    cfg, feats = config(), features(sb)
    if module is not None and hasattr(module, "hud_anchors"):
        plan["anchors"] = {**(plan.get("anchors") or {}), **module.hud_anchors(plan)}
    plan["hud"] = (_hud.compile_hud(spec.get("hud") or [], plan, tl, cfg) if feats.get("hud", True)
                   else {"widgets": [], "anchors": {}, "events": {}})
    plan.pop("anchors", None)          # only the anchors a widget uses travel to the renderer (in plan.hud)
    out = {"events": [], "mutes": [], "swells": [], "reveals": [], "punch_ins": []}
    if feats.get("cues", True):
        out = _cues.compile_cues(spec.get("cues") or [], plan, tl, plan["hud"]["events"], cfg, feats)
    out["events"] = sorted(out["events"] + _hud.tick_events(plan["hud"], cfg, plan["fps"]), key=lambda e: e[0])
    plan["retention"] = {**out, "features": feats}
    tm = plan.setdefault("timing", {})
    tm["reveals"] = sorted(list(tm.get("reveals", [])) + out["reveals"])
    return plan


def caption_emphasis(sb) -> tuple[dict, str]:
    """({beat id: words to emphasise}, mode) for caption_engine.write_ass. Words come from the narration's
    *stars* and from retention.captions.keywords; mode from the caption_emphasis feature (default none)."""
    import re
    mode = str(features(sb).get("caption_emphasis", "none"))
    kw = {w.lower() for w in (((spec_of(sb) or {}).get("captions") or {}).get("keywords") or [])}
    out = {}
    for b in sb.beats:
        stars = {w.lower() for w in re.findall(r"\*([^*\s]+)\*", b.text)}
        words = set(re.findall(r"[\w%°/.-]+", b.text.replace("*", "").lower()))
        out[b.id] = {w.strip(".") for w in stars} | (kw & words)
    return out, mode


def load_plan_module(sb):
    """The episode's plan.py with build_plan / sfx_events / music wrapped by the retention layer."""
    mod = sb.load_module("plan.py")
    if not spec_of(sb):
        return mod
    ns = SimpleNamespace(**{k: getattr(mod, k) for k in dir(mod) if not k.startswith("__")})
    ns.__name__ = getattr(mod, "__name__", "plan")
    ns.__file__ = getattr(mod, "__file__", None)
    ns._base = mod

    def build_plan(tl, *a, **kw):
        return apply(sb, mod.build_plan(tl, *a, **kw), tl, mod)

    def sfx_events(plan):
        base = list(mod.sfx_events(plan)) if hasattr(mod, "sfx_events") else []
        return sorted(base + [tuple(e) for e in (plan.get("retention") or {}).get("events", [])], key=lambda e: e[0])

    def music(plan):
        m = copy.deepcopy(mod.music(plan)) if hasattr(mod, "music") else None
        r = plan.get("retention") or {}
        if m is None:
            return None if not (r.get("mutes") or r.get("swells")) else {"mutes": r.get("mutes", []),
                                                                           "swells": r.get("swells", [])}
        m["mutes"] = list(m.get("mutes", [])) + list(r.get("mutes", []))
        m["swells"] = list(m.get("swells", [])) + list(r.get("swells", []))
        return m

    ns.build_plan, ns.sfx_events, ns.music = build_plan, sfx_events, music
    return ns

"""Scientific and cross-modal consistency (ResearchVerifier + ScriptConsistencyChecker).

Every number a viewer hears or reads must belong to a claim in the storyboard, and every claim must
agree with its value: a simulated measurement (plan `facts()`), a source, or a stated condition.

    NARRATED EVENT = SIMULATED EVENT = ON-SCREEN EVENT DESCRIPTION

The checker understands qualified wording, so it can tell a contradiction from a correct
generalisation:
    "it breaks into three pieces"            + simulation shows 4  -> contradiction (blocker)
    "it breaks into three pieces or more"    + simulation shows 4  -> consistent
    "every strand always breaks into exactly three" + evidence "3 or more, varies" -> overstated (blocker)

Claim fields (storyboard.yaml `claims:`):
    id, beat            the beat whose narration states it (or `card` for an on-screen label)
    unit                pieces | cm | m | m/s | km/s | s | % | turn | year | x | ...
    value / sim         the true value: a literal, or a key in the plan module's facts()
    scope               specific (one shown event) | typical | model | universal | condition | history
    match               optional word near the number, to pick the right one when a beat has several
    evidence            {quality: 1-5, source: "...", range: [lo, hi]}  (hi null = open-ended)
    tolerance           relative tolerance for "about"/"almost" wording (default 0.12)
"""
from __future__ import annotations

import re

from .findings import Finding

# ----------------------------------------------------------------------------- numbers in text
_ONES = {"zero": 0, "one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
         "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
         "ninety": 90}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000}
_FRACTIONS = {"half": 0.5, "quarter": 0.25, "third": 1 / 3, "three quarters": 0.75}

# unit words -> canonical unit
UNITS = [
    (r"pieces?|fragments?|bits", "pieces"),
    (r"centimet(?:re|er)s?|cm", "cm"),
    (r"millimet(?:re|er)s?|mm", "mm"),
    (r"kilomet(?:re|er)s? per second|km/s", "km/s"),
    (r"met(?:re|er)s? per second|m/s", "m/s"),
    (r"kilomet(?:re|er)s?|km", "km"),
    (r"met(?:re|er)s?(?! per)|m(?![a-z/])", "m"),
    (r"seconds?|s(?![a-z])", "s"),
    (r"percent|per cent|%", "%"),
    (r"degrees?|°", "deg"),
    (r"turns?", "turn"),
    (r"times|×|x(?![a-z])", "x"),
    (r"coils?", "coils"),
    (r"cars?|drivers?", "count"),
]
_UNIT_RE = "|".join(f"(?:{u})" for u, _ in UNITS)

APPROX = ("about", "around", "roughly", "approximately", "≈", "~", "some", "close to", "nearly", "almost")
AT_LEAST = ("or more", "at least", "or even more", "and up", "plus")
MORE_THAN = ("more than", "over", "upwards of")
AT_MOST = ("at most", "up to", "or fewer", "or less", "no more than")

ABSOLUTE = ("always", "never", "exactly", "impossible", "guaranteed", "every", "only", "proves",
            "perfectly", "instantly")


def _words_to_number(tokens: list[str]) -> float | None:
    total, cur, seen = 0.0, 0.0, False
    for w in tokens:
        if w in _ONES:
            cur += _ONES[w]; seen = True
        elif w in _TENS:
            cur += _TENS[w]; seen = True
        elif w == "hundred":
            cur = (cur or 1) * 100; seen = True
        elif w in ("thousand", "million"):
            total += (cur or 1) * _SCALES[w]; cur = 0; seen = True
        elif w == "and":
            continue
        else:
            return None
    return total + cur if seen else None


_NUMWORD = "|".join(sorted(list(_ONES) + list(_TENS) + list(_SCALES) + ["and"], key=len, reverse=True))
_NUM_RE = re.compile(
    rf"(?P<digits>\d[\d,]*(?:\.\d+)?)"
    rf"|(?P<frac>three quarters|half|a quarter|quarter)"
    rf"|(?P<words>(?:\b(?:{_NUMWORD})\b[\s-]*)+(?:point(?:\s+\b(?:{'|'.join(_ONES)})\b)+)?)",
    re.I)


def mentions(text: str) -> list[dict]:
    """Quantities in a sentence: [{value, unit, qualifier, absolute, span, text}].

    A number counts only if a unit word follows it closely ("four pieces", "fourteen centimetres",
    "sixty-two percent", "a quarter of a second"); plain counting words ("one end", "a stick") are ignored.
    """
    t = text.replace("*", "")
    out = []
    for m in _NUM_RE.finditer(t):
        raw = m.group(0).strip(" -")
        if not raw:
            continue
        if m.group("digits"):
            val = float(m.group("digits").replace(",", ""))
        elif m.group("frac"):
            val = _FRACTIONS.get(m.group("frac").lower().replace("a quarter", "quarter"), None)
        else:
            parts = re.split(r"\s+point\s+", raw.lower().replace("-", " "))
            toks = [w for w in parts[0].split() if w]
            if toks and toks[0] in ("a", "an") and len(toks) == 1:
                continue                           # "a stick" is not a quantity
            if toks and toks[0] in ("a", "an") and toks[1:2] and toks[1] not in _SCALES:
                toks = toks[1:]                    # "a one metre" -> "one"
            val = _words_to_number(toks)
            if val is not None and len(parts) > 1:
                dec = "".join(str(_ONES[w]) for w in parts[1].split() if w in _ONES)
                val = float(f"{int(val)}.{dec}") if dec else val
        if val is None:
            continue
        after = t[m.end(): m.end() + 40]
        um = re.match(rf"\s*(?:of a |of an |a |an |full |half )?(?:{_UNIT_RE})\b", after, re.I) or \
            re.match(rf"\s*(?:{_UNIT_RE})", after, re.I)
        if not um:
            if re.match(r"\s*of (?:them|these|those)\b", after, re.I):
                unit = "ref"                       # "four of them": refers back to the claim's unit
            elif 1000 <= val <= 2100 and float(val).is_integer() and (m.group("words") or m.group("digits")):
                unit = "year"
            elif val >= 2 and re.match(r"\s*[a-z]{3,}", after, re.I) and \
                    not re.match(r"\s*(?:and|or|of|to|in|at|is|was|by|than|times)\b", after, re.I):
                unit = "count"                     # "seven tries", "three pieces": any counted noun
            else:
                continue
        else:
            word = um.group(0).strip().lower()
            word = re.sub(r"^(of a |of an |a |an |full |half )", "", word)
            unit = next((c for u, c in UNITS if re.fullmatch(u, word, re.I)), word)
        before = t[max(0, m.start() - 30): m.start()].lower()
        after_l = t[m.end(): m.end() + 60].lower()
        q = _qualifier(before)
        if any(re.search(rf"\b{re.escape(a)}\b", after_l[:45]) for a in AT_LEAST):
            q = "at_least"
        if re.search(r"\b(or|to)\s+(?:\w+\s+){0,2}(more|four|five|six|seven|eight|nine|ten)\b", after_l[:45]):
            q = "at_least" if q == "exact" else q
        sent = _sentence_of(t, m.start())
        out.append({"value": float(val), "unit": unit, "qualifier": q, "text": raw,
                    "absolute": [w for w in ABSOLUTE if re.search(rf"\b{w}\b", sent.lower())],
                    "sentence": sent, "pos": m.start()})
    for m in _FULL.finditer(t):                    # "almost a full turn" = 1 turn
        before = t[max(0, m.start() - 30): m.start()].lower()
        sent = _sentence_of(t, m.start())
        out.append({"value": 1.0, "unit": "turn" if m.group(1).lower() != "one" else "ref",
                    "qualifier": _qualifier(before), "text": m.group(0),
                    "absolute": [w for w in ABSOLUTE if re.search(rf"\b{w}\b", sent.lower())],
                    "sentence": sent, "pos": m.start()})
    for rx, val, unit in _SPECIAL:
        for m in rx.finditer(t):
            if any(abs(o["pos"] - m.start()) < 3 for o in out):
                continue
            before = t[max(0, m.start() - 30): m.start()].lower()
            sent = _sentence_of(t, m.start())
            out.append({"value": val, "unit": unit, "qualifier": _qualifier(before), "text": m.group(0),
                        "absolute": [w for w in ABSOLUTE if re.search(rf"\b{w}\b", sent.lower())],
                        "sentence": sent, "pos": m.start()})
    out.sort(key=lambda d: d["pos"])
    return out


def _has(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(phrase)}(?![\w])", text) is not None


def _qualifier(before: str) -> str:
    near = before[-22:]
    if any(_has(near, a) for a in MORE_THAN):
        return "more_than"
    if any(_has(near, a) for a in AT_MOST):
        return "at_most"
    if _has(near, "almost") or _has(near, "nearly"):
        return "almost"
    if any(_has(near, a) for a in APPROX):
        return "approx"
    return "exact"


_FULL = re.compile(r"\b(?:a|one) full (turn|rotation|one)\b", re.I)
_SPECIAL = [(re.compile(r"\b(?:in|into) (two|half)\b(?!\s+(?:thousand|hundred|million|point))", re.I), 2.0, "pieces"),     # "breaks in two"
            (re.compile(r"\bdoubles?\b", re.I), 2.0, "x"),                       # "the arch doubles"
            (re.compile(r"\btriples?\b", re.I), 3.0, "x")]


def _sentence_of(t: str, pos: int) -> str:
    starts = [m.end() for m in re.finditer(r"[.!?]\s+", t[:pos])]
    s = starts[-1] if starts else 0
    e = re.search(r"[.!?](\s|$)", t[pos:])
    return t[s: pos + (e.end() if e else len(t) - pos)].strip()


def absolutes(text: str) -> list[tuple[str, str]]:
    """(word, sentence) for every absolute term in the text."""
    t = text.replace("*", "")
    hits = []
    for w in ABSOLUTE:
        for m in re.finditer(rf"\b{w}\b", t, re.I):
            if re.search(r"\b(almost|nearly|hardly|virtually)\s+$", t[max(0, m.start() - 12): m.start()], re.I):
                continue                       # "almost never" is already qualified
            if w == "only" and mentions(t[m.end(): m.end() + 30]) and mentions(t[m.end(): m.end() + 30])[0]["pos"] <= 2:
                continue                       # "only forty-two percent" compares numbers; the number has its own claim
            hits.append((w, _sentence_of(t, m.start())))
    return hits


# ----------------------------------------------------------------------------- consistency
def agrees(mention: dict, truth: float, tol: float = 0.12) -> tuple[bool, str]:
    """Does the wording of `mention` correctly describe the true value?"""
    n, q = mention["value"], mention["qualifier"]
    if q == "exact":
        ok = abs(truth - n) <= max(1e-9, 0.02 * abs(n)) if not float(n).is_integer() else round(truth) == n and abs(truth - n) < 0.5
        return ok, f"says exactly {n:g}, true value {truth:g}"
    if q == "at_least":
        return truth >= n - 1e-9, f"says {n:g} or more, true value {truth:g}"
    if q == "more_than":
        return truth > n, f"says more than {n:g}, true value {truth:g}"
    if q == "at_most":
        return truth <= n + 1e-9, f"says at most {n:g}, true value {truth:g}"
    if q == "almost":
        return n * (1 - 2 * tol) <= truth <= n * (1 + 0.02), f"says almost {n:g}, true value {truth:g}"
    return abs(truth - n) <= tol * max(abs(n), 1e-9), f"says about {n:g}, true value {truth:g} (±{tol:.0%})"


def check(sb, facts: dict, cards: list | None = None, badges: list | None = None) -> list[Finding]:
    """Layer 1/3: claims vs narration vs on-screen cards vs simulation facts."""
    F: list[Finding] = []
    claims = sb.extra.get("claims") or []
    beats = {b.id: b for b in sb.beats}
    if not claims:
        F.append(Finding("spec.no_claims", "science", 1, "BLOCKED_MISSING_EVIDENCE",
                         "storyboard has no claims section; no number can be verified",
                         expected="every spoken or shown quantity mapped to a claim",
                         repair="add claims: with value/sim, scope and evidence", files=[str(sb.path / "storyboard.yaml")]))
    used: set[tuple[str, int]] = set()
    allowed = {(a.get("beat"), a.get("word")) for a in (sb.extra.get("absolute_ok") or [])}
    for c in claims:
        cid = c.get("id", "?")
        truth = _truth(c, facts)
        where = c.get("beat")
        if truth is None:
            F.append(Finding(f"science.no_value.{cid}", "science", 1, "BLOCKED_MISSING_EVIDENCE",
                             f"claim {cid} has no value (literal or simulated fact '{c.get('sim')}' missing)",
                             repair="give the claim a value or export it from plan.facts()"))
            continue
        ev = c.get("evidence") or {}
        if c.get("scope") not in ("condition",) and not ev.get("source") and not c.get("sim"):
            F.append(Finding(f"science.no_source.{cid}", "science", 1, "BLOCKED_MISSING_EVIDENCE",
                             f"claim {cid} has neither a simulation value nor a source", repair="cite a source"))
        if ev.get("source") and int(ev.get("quality", 3)) > 3 and c.get("scope") in ("universal", "typical"):
            F.append(Finding(f"science.weak_source.{cid}", "science", 1, "BLOCKED_MISSING_EVIDENCE",
                             f"claim {cid} is {c.get('scope')} but rests on a quality-{ev.get('quality')} source",
                             expected="peer-reviewed research, an institution, or an original experiment (quality 1-3)"))
        if where is None and c.get("card"):
            continue                                   # an on-screen-only fact (checked with the cards below)
        if where not in beats:
            F.append(Finding(f"spec.bad_beat.{cid}", "spec", 1, "BLOCKED_VISUAL_CONTRADICTION",
                             f"claim {cid} points at beat '{where}', which does not exist"))
            continue
        ms = [(i, m) for i, m in enumerate(mentions(beats[where].text)) if _unit_ok(m["unit"], c.get("unit"))]
        if c.get("match"):
            pos = beats[where].text.replace("*", "").lower().find(c["match"].lower())
            # a number usually comes just before the words it describes ("forty-eight percent ... overtaken")
            ms.sort(key=lambda im: (im[1]["pos"] > pos, abs(im[1]["pos"] - pos)) if pos >= 0 else (0, 0))
        ms = [im for im in ms if (where, im[0]) not in used]
        if not ms:
            F.append(Finding(f"science.not_said.{cid}", "science", 2, None,
                             f"claim {cid} ({c.get('unit')}) is not stated in beat '{where}'",
                             repair="remove the stale claim or restore the sentence"))
            continue
        i, m = ms[0]
        used.add((where, i))
        ok, why = agrees(m, truth, float(c.get("tolerance", 0.12)))
        m = dict(m, absolute=sorted({w for w, _ in absolutes(m["sentence"]) if (where, w) not in allowed}))
        rng = ev.get("range")
        if ok and rng and m["qualifier"] == "exact" and c.get("scope") in ("typical", "universal") and \
                (rng[1] is None or rng[0] != rng[1]):
            ok, why = False, f"states a single value ({m['value']:g}) for something that varies ({_rng(rng)})"
        if ok and m["absolute"] and c.get("scope") != "universal":
            ok, why = False, f"uses '{', '.join(m['absolute'])}' for a {c.get('scope', 'specific')} result"
        if ok and m["absolute"] and c.get("scope") == "universal" and int(ev.get("quality", 5)) > 2:
            ok, why = False, f"universal wording ('{', '.join(m['absolute'])}') needs quality 1-2 evidence"
        if not ok:
            event = c.get("event")
            F.append(Finding(f"science.mismatch.{cid}", "science", 0,
                             "BLOCKED_VISUAL_CONTRADICTION" if c.get("sim") else "BLOCKED_FACTUAL_ERROR",
                             f"beat '{where}': \"{m['sentence']}\" {why}",
                             expected=f"{c.get('scope', 'specific')} claim, true value {truth:g} {c.get('unit', '')}",
                             evidence={"claim": cid, "mention": m["text"], "qualifier": m["qualifier"], "truth": truth,
                                       "event": event},
                             repair="correct the narration wording, or the simulation and its graphics",
                             files=[str(sb.path / "storyboard.yaml")], regression_test="tests/test_qa_science.py"))
    # every number the viewer hears must be bound to a claim
    for b in sb.beats:
        for i, m in enumerate(mentions(b.text)):
            if (b.id, i) not in used:
                F.append(Finding(f"science.unverified_number.{b.id}.{i}", "science", 1, "BLOCKED_MISSING_EVIDENCE",
                                 f"beat '{b.id}' says \"{m['text']} {m['unit']}\" but no claim backs it",
                                 evidence={"sentence": m["sentence"]},
                                 repair="add a claim with a source or a simulated value, or drop the number"))
    # absolute language needs a justification on record
    for b in sb.beats:
        for w, sent in absolutes(b.text):
            if (b.id, w) in allowed:
                continue
            claimed = any(c.get("beat") == b.id and c.get("scope") == "universal" for c in claims)
            if not claimed:
                F.append(Finding(f"science.absolute.{b.id}.{w}", "science", 1, "BLOCKED_FACTUAL_ERROR",
                                 f"beat '{b.id}' uses '{w}': \"{sent}\"",
                                 expected="absolute words need strong evidence: a universal claim with a quality 1-2 source, "
                                          "or an absolute_ok entry explaining why the word is literally true",
                                 repair="qualify the wording or record the justification"))
    # on-screen numbers (cards) must match a claim's true value
    for card in cards or []:
        if "{" in f"{card.get('big', '')}{card.get('small', '')}":
            continue                    # filled from live simulation values at render time (checked by events)
        for m in mentions(f"{card.get('big', '')} {card.get('small', '')}"):
            truths = [(c, _truth(c, facts)) for c in claims if _unit_ok(m["unit"], c.get("unit"))]
            hit = [c for c, tv in truths if tv is not None and agrees(m, tv, float(c.get("tolerance", 0.12)))[0]]
            if not hit:
                F.append(Finding(f"science.card_mismatch.{card.get('big')}", "science", 0, "BLOCKED_VISUAL_CONTRADICTION",
                                 f"on-screen card '{card.get('big')} {card.get('small', '')}' matches no claim",
                                 t=card.get("start"), evidence={"card": card},
                                 repair="generate the card from the claim's value"))
    # badges (slow-motion factor, try counters, citations) must show simulated or cited values
    for text in sorted(set(badges or [])):
        for m in mentions(text):
            if m["unit"] == "x":
                ok = any(abs(m["value"] - f) <= 0.5 for f in facts.get("slow_factors", []))
            elif m["unit"] == "pieces" and any(abs(m["value"] - v) < 1e-9 for v in _numbers(facts)):
                ok = True                       # a count produced by the simulation itself
            else:
                truths = [_truth(c, facts) for c in claims if _unit_ok(m["unit"], c.get("unit")) and m["unit"] != "ref"]
                ok = any(tv is not None and agrees(m, tv, float(c.get("tolerance", 0.12)))[0]
                         for c, tv in zip([c for c in claims if _unit_ok(m["unit"], c.get("unit")) and m["unit"] != "ref"], truths))
            if not ok:
                F.append(Finding(f"science.badge_mismatch.{text}", "science", 0, "BLOCKED_VISUAL_CONTRADICTION",
                                 f"on-screen badge '{text}' shows {m['value']:g} {m['unit']}, which no claim or simulated fact supports",
                                 evidence={"badge": text}, repair="derive the badge from the timeline / simulation"))
    return F


def _numbers(x):
    """Every number inside a (nested) facts structure."""
    if isinstance(x, bool):
        return []
    if isinstance(x, (int, float)):
        return [float(x)]
    if isinstance(x, dict):
        return [v for k in x.values() for v in _numbers(k)]
    if isinstance(x, (list, tuple)):
        return [v for k in x for v in _numbers(k)]
    return []


def _truth(c: dict, facts: dict):
    if c.get("sim") is not None:
        v = facts.get(c["sim"])
        return None if v is None else float(v)
    v = c.get("value")
    return None if v is None else float(v)


def _unit_ok(found: str, want: str | None) -> bool:
    if want is None:
        return True
    alias = {"pieces": {"pieces", "count"}}
    return found == want or found == "ref" or found in alias.get(want, set())


def _rng(r):
    return f"{r[0]}+" if r[1] is None else f"{r[0]}-{r[1]}"

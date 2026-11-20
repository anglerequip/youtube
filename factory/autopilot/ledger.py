"""Topic ledger: every topic we have ever touched, so the same video is never made twice.

Caesar (2026-11-20): "unique topics for every video, never accidentally make the same video twice".

The ledger is an append-only JSON-lines file committed to the repo (content/ledger/topics.jsonl), so it
survives every session and machine. Each line is one event; the latest line per id is the topic's
current state. Two checks use it: when an idea enters the topic pool, and again right before scripting.

The automatic duplicate check compares the topic's *core claim* (one line saying what the video shows),
its title and its keywords, after normalising words and folding synonyms ("sea" == "ocean"). It returns
the nearest entries so the writer (Claude) can make the final semantic call and justify any follow-up.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "content" / "ledger" / "topics.jsonl"

STATUSES = ("idea", "in_production", "scheduled", "published", "held_back", "rejected", "dropped")
# statuses that block a new video on the same topic (an "idea" blocks a second identical idea too)
BLOCKING = set(STATUSES)

BLOCK_AT = 0.50     # similarity at or above this is a duplicate
WARN_AT = 0.30      # shown to the writer as "close, check by hand"

STOP = set("""a an the of in on at to for from by with and or but is are was were be been being it its this that
these those your you my our we they them their his her he she i me why how what when where who which does do did
not no can cant could would should will just really actually so very than then into out up down over under
about as if one two only also even more most less much many any some all every each own same s t""".split())

# words that name the same thing; folded to the first word of each group
SYNONYMS = [
    ("ocean", "sea", "seas", "oceans", "seawater"),
    ("water", "h2o"),
    ("blue", "bluish"),
    ("car", "cars", "vehicle", "vehicles", "traffic"),
    ("lane", "lanes"),
    ("time", "clock", "clocks", "ages", "age", "aging", "ageing", "older", "old"),
    ("gravity", "gravitational"),
    ("radioactive", "radioactivity", "radiation", "decay"),
    ("phone", "phones", "touchscreen", "touchscreens", "screen", "screens", "smartphone"),
    ("touch", "touching", "press", "pressing", "presses"),
    ("slinky", "spring"),
    ("chain", "beads", "bead"),
    ("spaghetti", "pasta", "noodle", "noodles"),
    ("snap", "break", "breaks", "breaking", "snaps", "fracture"),
    ("sun", "sunlight", "solar"),
    ("cat", "cats", "kitten"),
    ("crystal", "crystals", "crystallisation", "crystallization"),
    ("drain", "sink", "plughole", "bathtub"),
    ("coriolis", "hemisphere", "hemispheres"),
    ("gps", "satnav", "satellite", "satellites"),
    ("relativity", "einstein"),
    ("electron", "electrons"),
    ("light", "colour", "color", "colours", "colors"),
]
_FOLD = {w: g[0] for g in SYNONYMS for w in g}


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", (text or "").lower().replace("'", "")):
        if w in STOP:
            continue
        w = _FOLD.get(w, w)
        out.add(_FOLD.get(_stem(w), _stem(w)) if w not in _FOLD.values() else w)
    return out


def similarity(a: "Topic", b: "Topic") -> float:
    """0..1. Word overlap of claim+title+keywords (containment, so a short claim inside a long one counts),
    blended with character similarity of the core claims."""
    wa = words(f"{a.core_claim} {a.title} {' '.join(a.keywords)}")
    wb = words(f"{b.core_claim} {b.title} {' '.join(b.keywords)}")
    if not wa or not wb:
        return 0.0
    inter = len(wa & wb)
    contain = inter / min(len(wa), len(wb))
    jacc = inter / len(wa | wb)
    chars = SequenceMatcher(None, a.core_claim.lower(), b.core_claim.lower()).ratio()
    return round(0.55 * contain + 0.25 * jacc + 0.20 * chars, 3)


@dataclass
class Topic:
    id: str
    core_claim: str
    title: str = ""
    area: str = ""
    keywords: list[str] = field(default_factory=list)
    status: str = "idea"
    slug: str = ""
    reason: str = ""
    follows: str = ""          # id of the video this deliberately follows up (allowed only with a new angle)
    sources: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    updated: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


class Ledger:
    def __init__(self, path: Path = LEDGER):
        self.path = Path(path)

    def events(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def topics(self) -> dict[str, Topic]:
        cur: dict[str, Topic] = {}
        for e in self.events():
            base = asdict(cur[e["id"]]) if e["id"] in cur else {}
            base.update(e)
            cur[e["id"]] = Topic(**{k: v for k, v in base.items() if k in Topic.__dataclass_fields__})
        return cur

    def _append(self, rec: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def nearest(self, t: Topic, n: int = 5) -> list[tuple[float, Topic]]:
        scored = [(similarity(t, o), o) for o in self.topics().values() if o.id != t.id]
        return sorted(scored, key=lambda x: -x[0])[:n]

    def check(self, t: Topic) -> dict:
        """{'verdict': 'ok'|'close'|'duplicate', 'nearest': [...]}. A deliberate follow-up (t.follows set to
        an existing id) is downgraded from duplicate to close, so the writer must justify the new angle."""
        near = self.nearest(t)
        top = near[0][0] if near else 0.0
        verdict = "duplicate" if top >= BLOCK_AT else "close" if top >= WARN_AT else "ok"
        if verdict == "duplicate" and t.follows and t.follows in self.topics():
            verdict = "close"
        return {"verdict": verdict, "score": top,
                "nearest": [{"id": o.id, "score": s, "status": o.status, "title": o.title,
                             "core_claim": o.core_claim} for s, o in near]}

    def add(self, t: Topic, *, force: bool = False) -> dict:
        """Add a new topic. Refuses duplicates unless force=True (then it is recorded as rejected)."""
        if t.status not in STATUSES:
            raise ValueError(f"unknown status {t.status!r}")
        if t.id in self.topics():
            raise ValueError(f"topic id {t.id!r} already in the ledger")
        res = self.check(t)
        if res["verdict"] == "duplicate" and not force:
            return res
        t.updated = _now()
        self._append(asdict(t))
        return res

    def set_status(self, topic_id: str, status: str, reason: str = "", **extra) -> Topic:
        if status not in STATUSES:
            raise ValueError(f"unknown status {status!r}")
        if topic_id not in self.topics():
            raise KeyError(topic_id)
        rec = {"id": topic_id, "status": status, "updated": _now(), **extra}
        if reason:
            rec["reason"] = reason
        self._append(rec)
        return self.topics()[topic_id]

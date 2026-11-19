"""Findings, severities and production states shared by every QA layer.

A Finding is one piece of evidence-backed QA output. Severity follows the production brief:
  0 critical blocker   release blocked immediately
  1 major blocker      must repair before release
  2 high priority      repair before approval unless a documented exception is recorded
  3 polish             prioritise by impact and cost
  4 optional
Each finding names the blocked state it maps to (BLOCKED_*), so the gate can send the production back
to the earliest stage that can repair the cause.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

# gated production states, in order
STATES = ("IDEA", "RESEARCHING", "FACT_VERIFIED", "SCRIPT_VALIDATED", "VISUAL_PLAN_APPROVED",
          "ASSETS_VALIDATED", "ANIMATIC_APPROVED", "PREVIEW_RENDERED", "PREVIEW_QA_PASSED",
          "AUDIO_QA_PASSED", "FINAL_RENDERED", "FINAL_QA_PASSED", "READY_FOR_RELEASE")
BLOCKED = ("BLOCKED_FACTUAL_ERROR", "BLOCKED_GEOMETRY", "BLOCKED_RENDER_ARTIFACT", "BLOCKED_PHYSICS",
           "BLOCKED_OBJECT_RECOGNITION", "BLOCKED_VISUAL_CONTRADICTION", "BLOCKED_AUDIO",
           "BLOCKED_PACING", "BLOCKED_MISSING_EVIDENCE", "BLOCKED_SPEC", "BLOCKED_REVIEW_UNAVAILABLE")

# where a blocked production returns to (repair the cause, not the symptom)
RETURN_TO = {
    "BLOCKED_FACTUAL_ERROR": "RESEARCHING",
    "BLOCKED_MISSING_EVIDENCE": "RESEARCHING",
    "BLOCKED_VISUAL_CONTRADICTION": "SCRIPT_VALIDATED",     # script or simulation and its graphics
    "BLOCKED_PHYSICS": "FACT_VERIFIED",                     # simulation
    "BLOCKED_OBJECT_RECOGNITION": "VISUAL_PLAN_APPROVED",   # asset design and camera planning
    "BLOCKED_GEOMETRY": "VISUAL_PLAN_APPROVED",             # geometry implementation
    "BLOCKED_RENDER_ARTIFACT": "ASSETS_VALIDATED",
    "BLOCKED_PACING": "VISUAL_PLAN_APPROVED",               # animatic / shot editing
    "BLOCKED_AUDIO": "PREVIEW_QA_PASSED",                   # audio production
    "BLOCKED_SPEC": "IDEA",                                 # the storyboard itself is incomplete
    "BLOCKED_REVIEW_UNAVAILABLE": "FINAL_RENDERED",
}

SEVERITY_NAMES = {0: "critical", 1: "major", 2: "high", 3: "polish", 4: "optional"}


@dataclass
class Finding:
    id: str                       # stable defect id, e.g. "science.count_mismatch.snap_plain"
    layer: str                    # spec | science | assets | simulation | storyboard | preview | audio | final | review
    severity: int
    blocks: str | None            # BLOCKED_* state when this finding is a blocker
    message: str                  # observed behaviour
    expected: str = ""
    evidence: dict = field(default_factory=dict)
    t: float | None = None        # video time (s) when it applies
    shot: int | None = None
    asset: str | None = None
    repair: str = ""
    files: list = field(default_factory=list)
    regression_test: str = ""
    confidence: float = 1.0
    objective: bool = True
    status: str = "open"          # open | accepted (documented exception) | fixed

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity_name"] = SEVERITY_NAMES.get(self.severity, "?")
        return d

    @property
    def is_blocker(self) -> bool:
        return self.status == "open" and self.severity <= 1


@dataclass
class LayerResult:
    layer: str
    ran: bool
    findings: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    note: str = ""                # e.g. why a layer could not run

    def to_dict(self) -> dict:
        return {"layer": self.layer, "ran": self.ran, "note": self.note, "metrics": self.metrics,
                "findings": [f.to_dict() for f in self.findings]}

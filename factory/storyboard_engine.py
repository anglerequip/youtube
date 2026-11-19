"""Storyboards: the structured description that drives rendering.

An episode lives in content/episodes/<slug>/:
  storyboard.yaml  narration beats, on-screen text, sound cues, metadata, caveats and sources
  sim.py           a `Sim(Scene)` class that animates the beats (see simulation_engine/base.py)

Each narration beat has an `id`; the simulation syncs to beats by id, so editing the words
re-times the visuals automatically.
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .configuration import settings


@dataclass
class Beat:
    id: str
    text: str
    pause_after: float = 0.25        # silence after the line (s)
    on_screen: str | None = None     # optional big text shown during this beat
    sfx: str | None = None           # optional sound cue name, played at beat start
    camera: str | None = None        # optional hint for the sim ("zoom_bottom", ...)
    # Recipe fields (docs/research SCRIPT/MOTION specs). All optional.
    pace: str = "calm"               # brisk | calm | build | reveal | hold
    emphasis: list = field(default_factory=list)
    speed: float | None = None       # per-beat multiplier on the episode speed
    viewer_question: str | None = None
    visual_events: list = field(default_factory=list)
    reveal: bool = False
    shot: str | None = None
    focal: str | None = None
    fidelity: str | None = None
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Beat":
        known = {f for f in cls.__dataclass_fields__ if f != "extra"}
        return cls(**{k: v for k, v in d.items() if k in known},
                   extra={k: v for k, v in d.items() if k not in known})


@dataclass
class Storyboard:
    slug: str
    path: Path
    title: str
    topic: str
    description: str
    tags: list[str]
    beats: list[Beat]
    voice: str | None = None
    speed: float = 1.0
    caveats: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    component: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def lines(self) -> list[Beat]:   # narration helpers use this name
        return self.beats

    @property
    def out_dir(self) -> Path:
        d = settings.out_dir / self.slug
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def final_video(self) -> Path:
        return self.out_dir / "final.mp4"

    def youtube_metadata(self) -> dict:
        """Title, description and tags as they will be sent to YouTube."""
        from .configuration import settings
        desc = self.description
        if self.sources:
            desc += "\n\nSources:\n" + "\n".join(f"- {s}" for s in self.sources)
        desc += f"\n\n{settings.channel_name}: {settings.channel_tagline}"
        return {"title": self.title[:100], "description": desc[:5000], "tags": self.tags,
                "categoryId": "28"}  # 28 = Science & Technology

    def full_text(self) -> str:
        return " ".join(b.text for b in self.beats)

    def load_sim_class(self):
        sim_file = self.path / "sim.py"
        name = f"episode_sim_{self.slug.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(name, sim_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "Sim"):
            raise AttributeError(f"{sim_file} must define a class named Sim")
        return mod.Sim


REQUIRED = ("title", "topic", "beats")


def load(path_or_slug: str | Path) -> Storyboard:
    p = Path(path_or_slug)
    if not (p / "storyboard.yaml").exists():
        p = settings.content_dir / str(path_or_slug)
    p = p.resolve()
    data = yaml.safe_load((p / "storyboard.yaml").read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        raise ValueError(f"{p}/storyboard.yaml is missing {missing}")
    beats = [Beat.from_dict(b) for b in data.pop("beats")]
    ids = [b.id for b in beats]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate beat ids in {p}: {ids}")
    return Storyboard(
        slug=data.pop("slug", p.name),
        path=p,
        title=data.pop("title"),
        topic=data.pop("topic"),
        description=str(data.pop("description", "")).strip(),
        tags=list(data.pop("tags", [])),
        beats=beats,
        voice=data.pop("voice", None),
        speed=float(data.pop("speed", 1.0)),
        caveats=list(data.pop("caveats", [])),
        sources=list(data.pop("sources", [])),
        component=data.pop("component", None),
        extra=data,
    )


def all_storyboards() -> list[Storyboard]:
    d = settings.content_dir
    return [load(p) for p in sorted(d.iterdir()) if (p / "storyboard.yaml").exists()]

"""Sign-off line for the description, chosen by the video's topic (Caesar, 2026-11-20: "it should depend
on the context of the video"). Table copied from factory/publishing/copywriter.py on branch
claude/project-thread-4jcuxd, so the autopilot package builder and the PC publisher agree. Keep them in step.
"""
from __future__ import annotations

import re

TOPIC_TAGLINES = (   # first match wins
    (("cat", "cats", "dog", "dogs", "pet", "pets", "animal", "animals", "bird", "birds", "wildlife"),
     "animal science that breaks your intuition."),
    (("biology", "body", "brain", "health", "human", "sleep", "medicine", "anatomy"),
     "biology that breaks your intuition."),
    (("chemistry", "chemical", "crystal", "crystals", "molecule", "molecules", "reaction"),
     "chemistry that breaks your intuition."),
    (("maths", "math", "probability", "statistics", "geometry"),
     "maths that breaks your intuition."),
    (("physics", "relativity", "gravity", "momentum", "waves", "electricity", "optics"),
     "physics that breaks your intuition."),
)
GENERIC_TAGLINE = "science that breaks your intuition."


def tagline(tags: list[str], title: str, override: str | None = None) -> str:
    """A storyboard's own publish.tagline wins; otherwise the tags and title pick the line."""
    if override:
        return override.strip()
    words = set(re.findall(r"[a-z]+", " ".join([*map(str, tags), str(title)]).lower()))
    for keys, line in TOPIC_TAGLINES:
        if words & set(keys):
            return line
    return GENERIC_TAGLINE

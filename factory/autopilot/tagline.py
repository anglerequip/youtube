"""Sign-off line for the description, chosen by the video's topic (Caesar, 2026-11-20: "it should depend
on the context of the video"; 2026-11-26: the channel is now AnglerMind). The first version was copied from factory/publishing/copywriter.py on branch
claude/project-thread-4jcuxd, so the autopilot package builder and the PC publisher agree. Keep them in step.
"""
from __future__ import annotations

import re

# AnglerMind sign-offs (Caesar, 2026-11-26: the channel becomes AnglerMind; docs/BRAND.md). Each line names
# what the site really does for that topic. First match wins.
TOPIC_TAGLINES = (
    (("lure", "lures", "colour", "colours", "color", "colors", "bait", "spinner", "jig"),
     "the right lure and colour, picked on real data."),
    (("depth", "map", "maps", "spot", "spots", "lake", "lakes", "bathymetry", "structure"),
     "real depth maps and ranked spots."),
    (("solunar", "moon", "sun", "weather", "wind", "rain", "dawn", "dusk", "pressure"),
     "the best fishing hours, scored from sun, moon and weather."),
    (("rod", "rods", "reel", "reels", "line", "gear", "setup", "tackle"),
     "rods, reels and lines that genuinely balance."),
    (("fish", "fishing", "angler", "anglers", "angling", "boat", "pike", "perch", "trout", "bass", "zander",
      "salmon", "carp", "gar", "catch"),
     "the science behind every cast."),
)
GENERIC_TAGLINE = "fish smarter."
CHANNEL = "AnglerMind"
CTA = "Try it free at anglermind.com."


def tagline(tags: list[str], title: str, override: str | None = None) -> str:
    """A storyboard's own publish.tagline wins; otherwise the tags and title pick the line."""
    if override:
        return override.strip()
    words = set(re.findall(r"[a-z]+", " ".join([*map(str, tags), str(title)]).lower()))
    for keys, line in TOPIC_TAGLINES:
        if words & set(keys):
            return line
    return GENERIC_TAGLINE


def sign_off(tags: list[str], title: str, override: str | None = None) -> str:
    """The description's closing line: "AnglerMind: <topic line> Try it free at anglermind.com." """
    return f"{CHANNEL}: {tagline(tags, title, override)} {CTA}"


_OLD_NAME = re.compile(r"counter ?physical", re.I)


def rebrand(text: str) -> str:
    """Copy written in the Counterphysical days, made right for the renamed channel at post time.

    Queued packages were written before the rename (2026-11-26). Rather than edit folders the hourly job
    may be posting, the posters pass every description through this: the old name becomes AnglerMind and
    a sign-off without the site gets the call to action. Idempotent."""
    if not text or not _OLD_NAME.search(text):
        return text or ""
    out = []
    for line in text.split("\n"):
        line = _OLD_NAME.sub(CHANNEL, line)
        line = line.replace("#AnglerMind", "#anglermind")
        if line.startswith(f"{CHANNEL}:") and "anglermind.com" not in line:
            line = f"{line.rstrip()} {CTA}"
        out.append(line)
    return "\n".join(out)


# Series playlists (2026-11-21 YouTube audit): a playlist per topic family keeps a viewer who liked one Short
# watching the next one, and gives the Shorts "related video" link a home. First match wins.
TOPIC_PLAYLISTS = (
    (("game", "games", "gaming", "gamer", "gamers", "videogame", "fps", "frame"), "Video game science"),
    (("anglermind", "demo", "tool", "tools", "app", "website"), "AnglerMind in action"),
    (("fish", "fishing", "angler", "angling", "lure", "boat"), "Fishing science"),
    (("cat", "cats", "dog", "dogs", "pet", "pets", "animal", "animals", "bird", "birds", "wildlife",
      "shrimp", "insect", "insects"), "Animal science"),
    (("biology", "body", "brain", "health", "human", "sleep", "medicine", "anatomy"), "Your body, explained"),
    (("physics", "relativity", "gravity", "momentum", "waves", "electricity", "optics",
      "traffic", "car", "cars", "slinky"), "Physics that breaks your intuition"),
)
GENERIC_PLAYLIST = "Surprising science"


def playlist(tags: list[str], title: str, override: str | None = None) -> str:
    """The package's own playlist wins; otherwise the tags and title pick a series."""
    if override:
        return override.strip()
    words = set(re.findall(r"[a-z]+", " ".join([*map(str, tags), str(title)]).lower()))
    for keys, name in TOPIC_PLAYLISTS:
        if words & set(keys):
            return name
    return GENERIC_PLAYLIST

"""Per-platform post text, written from the storyboard.

A Claude session writing an episode should add a `publish:` block to storyboard.yaml with
hand-written copy (see falling-slinky-3d). Anything it leaves out falls back to defaults built from
the title, the hook beat, the description, sources and tags, so every episode gets a package.

  publish:
    cover_at_s: 16                       # frame used for the cover (and TikTok's cover frame)
    cover_headline: "The bottom doesn't fall"
    cover_label: {big: "0.26 s", small: "of pure hovering"}
    hashtags: [physics, science, slinky]  # topical, 3-5; platform tags like #shorts are added here
    youtube:  {title: "...", description: "..."}
    tiktok:   {caption: "..."}
    facebook: {caption: "..."}

Platform limits used below (checked by package.checks):
  YouTube title <= 100 chars (aim <= 70 so it isn't cut on phones), description <= 5000 bytes,
    over 60 hashtags makes YouTube ignore all of them; the first three show above the title.
  TikTok caption <= 2200 UTF-16 units (Content Posting API `title`).
  Facebook Reels description: no hard limit we rely on; keep it short.
"""
from __future__ import annotations

import re

from ..configuration import settings

YOUTUBE_TITLE_MAX = 100
YOUTUBE_DESC_MAX = 5000
TIKTOK_CAPTION_MAX = 2200

# Wording we must never use (another channel's name/phrasing; see project memory).
BANNED = ("universe disagrees", "disagrees")


def clean(text: str) -> str:
    """Narration markup -> plain text: drop *stress* stars, collapse whitespace, keep paragraph breaks."""
    text = re.sub(r"\*(\S[^*]*?)\*", r"\1", str(text))
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text.strip())]
    return "\n\n".join(p for p in paras if p)


def hashtag(word: str) -> str:
    w = re.sub(r"[^0-9A-Za-z_]", "", str(word).lstrip("#"))
    return f"#{w.lower()}" if w else ""


def _uniq(tags):
    out = []
    for t in tags:
        if t and t not in out:
            out.append(t)
    return out


def _description_body(sb) -> str:
    """Storyboard description without its trailing hashtag-only lines."""
    lines = [ln for ln in sb.description.splitlines() if not re.fullmatch(r"\s*(#\w+\s*)+", ln)]
    return "\n".join(lines).strip()


def _first_sentences(text: str, n: int = 1) -> str:
    parts = re.split(r"(?<=[.!?])\s+", clean(text))
    return " ".join(parts[:n]).strip()


def topical_hashtags(sb, k: int = 4) -> list[str]:
    pub = sb.extra.get("publish") or {}
    src = pub.get("hashtags") or [t for t in sb.tags if t.lower() not in ("shorts", "simulation")]
    return _uniq(hashtag(t) for t in src)[:k]


def ai_disclosure() -> str:
    voice = {"kokoro": "an AI text-to-speech voice", "elevenlabs": "an AI voice (ElevenLabs)"}.get(
        settings.tts_provider, "an AI voice")
    return ("How it's made: the motion comes from a real physics simulation, rendered as a 3D model. "
            f"The narration is {voice}.")


def youtube(sb) -> dict:
    pub = (sb.extra.get("publish") or {})
    yt = pub.get("youtube") or {}
    title = clean(yt.get("title") or sb.title)
    lead = re.sub(r"\*(\S[^*]*?)\*", r"\1", str(yt.get("description") or _description_body(sb))).strip()
    tags_line = " ".join(_uniq(["#shorts"] + topical_hashtags(sb, 4)))
    parts = [lead.strip()]
    if sb.sources:
        parts.append("Sources:\n" + "\n".join(f"- {s}" for s in sb.sources))
    parts.append(ai_disclosure())
    parts.append(f"{settings.channel_name}: {settings.channel_tagline}")
    parts.append(tags_line)
    desc = "\n\n".join(p for p in parts if p)
    tags = _uniq([t.lstrip("#").lower() for t in sb.tags if t.lower() != "shorts"] + [settings.channel_name.lower()])
    return {
        "title": title[:YOUTUBE_TITLE_MAX],
        "description": desc,
        "tags": tags,
        "category_id": str(pub.get("category_id", "28")),   # 28 Science & Technology, 27 Education, 15 Pets & Animals
        "language": str(pub.get("language", "en")),
        "made_for_kids": False,
        "contains_synthetic_media": settings_ai_label(),
    }


def tiktok(sb) -> dict:
    pub = (sb.extra.get("publish") or {})
    tt = pub.get("tiktok") or {}
    if tt.get("caption"):
        body = clean(tt["caption"])
    else:
        body = f"{_first_sentences(sb.beats[0].text, 2)} {_first_sentences(_description_body(sb), 1)}".strip()
    tags = " ".join(_uniq(topical_hashtags(sb, 4) + ["#learnontiktok"]))
    caption = body if all(h in body for h in tags.split()) else f"{body}\n\n{tags}"
    return {
        "caption": caption,
        "is_aigc": settings_ai_label(),
        "disable_comment": False,
        "disable_duet": False,
        "disable_stitch": False,
    }


def facebook(sb) -> dict:
    pub = (sb.extra.get("publish") or {})
    fb = pub.get("facebook") or {}
    if fb.get("caption"):
        body = clean(fb["caption"])
    else:
        body = f"{_first_sentences(sb.beats[0].text, 2)}\n\n{_first_sentences(_description_body(sb), 2)}"
    tags = " ".join(topical_hashtags(sb, 3))
    desc = body if all(h in body for h in tags.split()) else f"{body}\n\n{tags}"
    return {
        "title": clean((fb.get("title") or sb.title))[:255],
        "description": desc,
        "is_ai_generated": settings_ai_label(),
    }


def settings_ai_label() -> bool:
    """AI labels default ON (TikTok and YouTube ask for them on realistic synthetic media; our narration
    is a synthetic voice). Set AI_LABEL=false in .env only if a platform's rules clearly don't apply."""
    import os
    return os.environ.get("AI_LABEL", "true").strip().lower() not in ("0", "false", "no", "off")


def all_platforms(sb) -> dict:
    return {"youtube": youtube(sb), "tiktok": tiktok(sb), "facebook": facebook(sb)}

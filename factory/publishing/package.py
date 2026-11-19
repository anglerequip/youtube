"""Build the publishing package for one video. Needs no credentials and posts nothing.

  python -m factory package <slug> [--video path/to/final.mp4]

Writes out/<slug>/publish/:
  package.json        everything the publisher sends, per platform, with a hash for each platform
  review.md           the same, laid out for a human to read
  cover.jpg           1080x1920 cover in the house style
  cover_safezones.jpg review aid: where app buttons and overlays will sit

Each platform's `hash` covers the video sha256, the cover sha256 and that platform's fields. An
approval is recorded against that hash, so editing a caption or re-rendering the video after approval
voids the approval automatically.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..configuration import settings
from ..storyboard_engine import Storyboard, load
from . import PLATFORMS, copywriter, cover

FB_MAX_S = 90          # Facebook Reels API accepts 3-90 s
MIN_W, MIN_H = 540, 960


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(video: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", str(video)],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    s = d["streams"][0]
    return {"width": int(s["width"]), "height": int(s["height"]), "duration_s": float(d["format"]["duration"])}


def platform_hash(slug: str, platform: str, fields: dict, video_sha: str, cover_sha: str) -> str:
    payload = {k: v for k, v in fields.items() if k != "hash"}
    blob = json.dumps([slug, platform, video_sha, cover_sha, payload], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def _default_cover_time(sb: Storyboard, duration: float) -> float:
    pub = sb.extra.get("publish") or {}
    if pub.get("cover_at_s") is not None:
        return float(pub["cover_at_s"])
    tl = sb.out_dir / "timeline.json"
    beat = pub.get("cover_beat")
    if beat and tl.exists():
        for ln in json.loads(tl.read_text())["lines"]:
            if ln["id"] == beat:
                return (ln["start"] + ln["end"]) / 2
    return round(duration * 0.25, 2)


def checks(pkg: dict) -> list[dict]:
    out = []

    def add(name, ok, detail=""):
        out.append({"name": name, "ok": bool(ok), "detail": detail})

    v = pkg["video"]
    add("video over the minimum length", v["duration_s"] >= settings.min_seconds,
        f"{v['duration_s']:.1f} s (minimum {settings.min_seconds:.0f} s)")
    add("Facebook Reels length limit", v["duration_s"] <= FB_MAX_S, f"{v['duration_s']:.1f} s (max {FB_MAX_S} s)")
    add("vertical 9:16 video", abs(v["width"] / v["height"] - 9 / 16) < 0.01 and v["width"] >= MIN_W,
        f"{v['width']}x{v['height']}")
    yt, tt, fb = (pkg["platforms"][p] for p in PLATFORMS)
    add("YouTube title length", 0 < len(yt["title"]) <= copywriter.YOUTUBE_TITLE_MAX,
        f"{len(yt['title'])} chars{' (over 70: may be cut on phones)' if len(yt['title']) > 70 else ''}")
    add("YouTube description length", len(yt["description"].encode()) <= copywriter.YOUTUBE_DESC_MAX,
        f"{len(yt['description'].encode())} bytes")
    add("YouTube description has #shorts", "#shorts" in yt["description"].lower())
    n_tags = sum(len(f.split("#")) - 1 for f in [yt["description"]])
    add("YouTube hashtag count", n_tags <= 15, f"{n_tags} hashtags")
    add("TikTok caption length", 0 < len(tt["caption"].encode("utf-16-le")) // 2 <= copywriter.TIKTOK_CAPTION_MAX,
        f"{len(tt['caption'])} chars")
    tt_tags = tt["caption"].count("#")
    add("TikTok hashtags 3-6", 3 <= tt_tags <= 6, f"{tt_tags} hashtags")
    add("Facebook caption present", bool(fb["description"].strip()))
    add("AI label on TikTok and YouTube", tt["is_aigc"] and yt["contains_synthetic_media"],
        "set AI_LABEL=true (the default)")
    text = json.dumps(pkg["platforms"]).lower()
    bad = [w for w in copywriter.BANNED if w in text]
    add("no banned wording", not bad, ", ".join(bad))
    add("no narration markup left", "*" not in "".join([yt["title"], tt["caption"], fb["description"]]))
    add("cover image under 2 MB (YouTube limit)", pkg["cover"]["bytes"] <= 2_000_000, f"{pkg['cover']['bytes']} bytes")
    return out


def build(slug_or_sb, video: Path | None = None) -> dict:
    sb = slug_or_sb if isinstance(slug_or_sb, Storyboard) else load(slug_or_sb)
    video = Path(video or sb.final_video)
    if not video.exists():
        raise FileNotFoundError(f"{video} does not exist; render the episode first")
    out = sb.out_dir / "publish"
    out.mkdir(parents=True, exist_ok=True)
    pub = sb.extra.get("publish") or {}

    meta = probe(video)
    at_s = min(_default_cover_time(sb, meta["duration_s"]), meta["duration_s"] - 0.5)
    headline = copywriter.clean(pub.get("cover_headline") or sb.title)
    c = cover.build(video, out, at_s, headline, pub.get("cover_label"), frame_source=sb.out_dir / "visual.mp4")
    video_sha, cover_sha = sha256_file(video), sha256_file(c["path"])

    platforms = copywriter.all_platforms(sb)
    platforms["tiktok"]["cover_timestamp_ms"] = int(at_s * 1000)
    platforms["tiktok"]["privacy_level"] = None        # chosen at post time from TikTok's creator info
    for name, fields in platforms.items():
        fields["hash"] = platform_hash(sb.slug, name, fields, video_sha, cover_sha)

    pkg = {
        "slug": sb.slug,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "video": {"path": str(video.resolve()), "sha256": video_sha, "bytes": video.stat().st_size, **meta},
        "cover": {"path": str(c["path"].resolve()), "sha256": cover_sha, "bytes": c["path"].stat().st_size,
                  "at_s": at_s, "frame_source": c["frame_source"], "headline": headline,
                  "label": pub.get("cover_label")},
        "platforms": platforms,
    }
    pkg["checks"] = checks(pkg)
    pkg["ok"] = all(ch["ok"] for ch in pkg["checks"])
    (out / "package.json").write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "review.md").write_text(review_markdown(pkg), encoding="utf-8")
    return pkg


def load_package(slug: str) -> dict:
    p = settings.out_dir / slug / "publish" / "package.json"
    return json.loads(p.read_text(encoding="utf-8"))


def verify(pkg: dict, platform: str) -> str:
    """Recompute a platform's hash from the files on disk. Raises if anything changed."""
    v, c = Path(pkg["video"]["path"]), Path(pkg["cover"]["path"])
    vs, cs = sha256_file(v), sha256_file(c)
    if vs != pkg["video"]["sha256"]:
        raise ValueError(f"{pkg['slug']}: the video changed after packaging")
    if cs != pkg["cover"]["sha256"]:
        raise ValueError(f"{pkg['slug']}: the cover changed after packaging")
    fields = pkg["platforms"][platform]
    h = platform_hash(pkg["slug"], platform, fields, vs, cs)
    if h != fields["hash"]:
        raise ValueError(f"{pkg['slug']}/{platform}: the post text changed after packaging")
    return h


def review_markdown(pkg: dict) -> str:
    yt, tt, fb = (pkg["platforms"][p] for p in PLATFORMS)
    v = pkg["video"]
    lines = [
        f"# Publishing package: {pkg['slug']}",
        "",
        f"Video: `{Path(v['path']).name}`, {v['duration_s']:.1f} s, {v['width']}x{v['height']}, "
        f"sha256 `{v['sha256'][:12]}`",
        f"Cover: `cover.jpg`, frame at {pkg['cover']['at_s']:.2f} s, headline \"{pkg['cover']['headline']}\"",
        "",
        f"## YouTube Shorts (hash {yt['hash'][:8]})",
        f"**Title:** {yt['title']}",
        "",
        "**Description:**",
        "",
        "```",
        yt["description"],
        "```",
        f"**Tags:** {', '.join(yt['tags'])}",
        f"**Altered or synthetic content label:** {'on' if yt['contains_synthetic_media'] else 'off'} · "
        f"made for kids: {'yes' if yt['made_for_kids'] else 'no'}",
        "",
        f"## TikTok (hash {tt['hash'][:8]})",
        "```",
        tt["caption"],
        "```",
        f"**AI-generated label:** {'on' if tt['is_aigc'] else 'off'} · cover frame at "
        f"{tt['cover_timestamp_ms'] / 1000:.2f} s · comments, duet and stitch allowed",
        "",
        f"## Facebook Reels (hash {fb['hash'][:8]})",
        f"**Title:** {fb['title']}",
        "",
        "```",
        fb["description"],
        "```",
        f"**AI info label:** {'on' if fb['is_ai_generated'] else 'off'}",
        "",
        "## Checks",
        *[f"- {'PASS' if c['ok'] else 'FAIL'} {c['name']}{': ' + c['detail'] if c['detail'] else ''}"
          for c in pkg["checks"]],
        "",
    ]
    return "\n".join(lines)

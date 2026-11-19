"""Cover / thumbnail in the house style (CLAUDE.md, Visual Blueprint sections 6, 7 and 10).

A frame from our own render, with:
  - a small COUNTERPHYSICAL wordmark at the top (outside the caption band),
  - the off-white rounded label card with the one number that matters in red (section 7),
  - a short headline in white with a soft blurred shadow over a gentle dark fade, placed over the
    burned-in caption band so a frame taken from final.mp4 never shows a half caption.

Safe zones: everything important stays inside x 8-92 % and y 5-80 %, clear of the TikTok/Reels
buttons on the right and the caption/username overlay at the bottom, and inside the centre crop the
YouTube Shorts grid uses.
"""
from __future__ import annotations

import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..configuration import settings

W, H = 1080, 1920
CARD = (0xE5, 0xE2, 0xD6)
RED = (0xC9, 0x2A, 0x2E)
FONTS = settings.root / "assets" / "fonts"


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)


def extract_frame(video: Path, at_s: float) -> Image.Image:
    with tempfile.TemporaryDirectory() as d:
        png = Path(d) / "f.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at_s:.3f}", "-i", str(video),
                        "-frames:v", "1", str(png)], check=True)
        im = Image.open(png).convert("RGB")
        im.load()
    return _fit(im)


def _fit(im: Image.Image) -> Image.Image:
    """Cover-crop to 1080x1920."""
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def _shadowed_text(base: Image.Image, xy, text, font, fill=(255, 255, 255), anchor="mm",
                   blur=10, alpha=150, offset=(0, 5), spacing=10, align="center"):
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).multiline_text((xy[0] + offset[0], xy[1] + offset[1]), text, font=font,
                                      fill=(0, 0, 0, alpha), anchor=anchor, spacing=spacing, align=align)
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(base).multiline_text(xy, text, font=font, fill=fill, anchor=anchor, spacing=spacing,
                                        align=align)


def _fade(base: Image.Image, y0: float, y1: float, peak: int = 150):
    """Soft dark band, transparent at y0 and y1, darkest in the middle third."""
    band = Image.new("L", (1, H), 0)
    a, b = int(y0 * H), int(y1 * H)
    for y in range(a, b):
        t = (y - a) / max(1, b - a)
        k = min(1.0, t / 0.3, (1 - t) / 0.3)
        band.putpixel((0, y), int(peak * k))
    mask = band.resize((W, H))
    base.alpha_composite(Image.composite(Image.new("RGBA", (W, H), (8, 10, 16, 255)),
                                         Image.new("RGBA", (W, H), (0, 0, 0, 0)), mask))


def _card(base: Image.Image, cy: int, big: str, small: str | None):
    fb, fs = _font("ExtraBold", 112), _font("SemiBold", 46)
    d = ImageDraw.Draw(base)
    bw = d.textlength(big, font=fb)
    sw = d.textlength(small, font=fs) if small else 0
    w = int(max(bw, sw, 470) + 110)
    h = 270 if small else 190
    x0, y0 = (W - w) // 2, cy - h // 2
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 10, x0 + w, y0 + h + 10), 34, fill=(0, 0, 0, 110))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), 34, fill=CARD + (255,))
    if small:
        d.text((W // 2, y0 + 105), big, font=fb, fill=RED, anchor="mm")
        d.text((W // 2, y0 + 208), small, font=fs, fill=RED, anchor="mm")
    else:
        d.text((W // 2, cy), big, font=fb, fill=RED, anchor="mm")


def _soften(base: Image.Image, y0: float, y1: float, radius: int = 28):
    """Blur a horizontal band (feathered) so burned-in overlays from final.mp4 don't show through."""
    blurred = base.filter(ImageFilter.GaussianBlur(radius))
    mask = Image.new("L", (1, H), 0)
    a, b = int(y0 * H), int(y1 * H)
    for y in range(a, b):
        t = (y - a) / max(1, b - a)
        mask.putpixel((0, y), int(255 * min(1.0, t / 0.2, (1 - t) / 0.2)))
    base.alpha_composite(Image.composite(blurred, Image.new("RGBA", base.size, (0, 0, 0, 0)), mask.resize(base.size)))


def compose(frame: Image.Image, headline: str, label: dict | None = None,
            wordmark: str | None = None, clean_frame: bool = False) -> Image.Image:
    base = frame.convert("RGBA")
    if not clean_frame:            # frame from final.mp4: hide the burned caption and corner badges
        _soften(base, 0.035, 0.125)
        _soften(base, 0.62, 0.84)
    # wordmark
    wm = (wordmark if wordmark is not None else settings.channel_name).upper()
    if wm:
        _fade(base, 0.0, 0.12, peak=70)
        _shadowed_text(base, (W // 2, int(0.055 * H)), " ".join(wm), _font("SemiBold", 34),
                       fill=(245, 243, 236), blur=6, alpha=140, offset=(0, 2))
    if label and label.get("big"):
        _card(base, int(0.175 * H), str(label["big"]), label.get("small"))
    # headline over the caption band
    _fade(base, 0.55, 0.92, peak=175)
    size, wrapped = 104, headline
    for size in (104, 96, 88, 80, 72):
        f = _font("ExtraBold", size)
        width_chars = max(8, int(900 / (size * 0.56)))
        wrapped = "\n".join(textwrap.wrap(headline, width_chars))
        box = ImageDraw.Draw(base).multiline_textbbox((0, 0), wrapped, font=f, spacing=12)
        if box[2] - box[0] <= 900 and wrapped.count("\n") <= 2:
            break
    _shadowed_text(base, (W // 2, int(0.705 * H)), wrapped, _font("ExtraBold", size), spacing=12,
                   blur=14, alpha=170, offset=(0, 6))
    return base.convert("RGB")


def safe_zone_preview(cover: Image.Image) -> Image.Image:
    """Review aid: shade where TikTok/Reels/Shorts buttons and captions sit."""
    im = cover.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle((0, int(0.80 * H), W, H), fill=(255, 0, 0, 70))           # caption / username overlay
    d.rectangle((int(0.86 * W), int(0.45 * H), W, int(0.80 * H)), fill=(255, 0, 0, 70))  # like/comment rail
    d.rectangle((0, 0, W, int(0.045 * H)), fill=(255, 0, 0, 50))          # status bar / tabs
    im.alpha_composite(ov)
    return im.convert("RGB")


def build(video: Path, out: Path, at_s: float, headline: str, label: dict | None = None,
          frame_source: Path | None = None) -> dict:
    """Write cover.jpg (+ cover_safezones.jpg) into `out`. Returns paths and the frame time."""
    src = frame_source if frame_source and frame_source.exists() else video
    img = compose(extract_frame(src, at_s), headline, label, clean_frame=src != video)
    out.mkdir(parents=True, exist_ok=True)
    p = out / "cover.jpg"
    img.save(p, quality=92, optimize=True)
    safe_zone_preview(img).resize((540, 960)).save(out / "cover_safezones.jpg", quality=85)
    return {"path": p, "at_s": at_s, "frame_source": src.name}

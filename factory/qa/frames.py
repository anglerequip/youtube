"""Layers 6/8 (preview and final render QA): inspect the encoded video's pixels.

What the scene-graph inspection cannot see, the pixels can: black holes in the final image,
blown-out exposure, and temporal flicker (z-fighting, shadow shimmer, popping textures) that only shows
up between consecutive frames. Cuts and declared physical events are excluded from flicker detection,
so a hard cut or a crack flash is not reported as an artefact.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from .findings import Finding


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_type",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    num, den = v["r_frame_rate"].split("/")
    return {"duration": float(d["format"]["duration"]), "w": v["width"], "h": v["height"], "fps": float(num) / float(den),
            "audio": any(s["codec_type"] == "audio" for s in d["streams"])}


def frames(path: Path, w: int, h: int, fps: float | None = None, gray: bool = False, start: float = 0, dur: float | None = None):
    """Yield decoded frames (h, w[, 3]) as uint8 arrays, scaled to w x h."""
    vf = f"scale={w}:{h}:flags=area" + (f",fps={fps}" if fps else "")
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)] + (["-t", str(dur)] if dur else []) + \
          ["-i", str(path), "-vf", vf, "-f", "rawvideo", "-pix_fmt", "gray" if gray else "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h * (1 if gray else 3)
    try:
        while True:
            buf = p.stdout.read(n)
            if len(buf) < n:
                break
            a = np.frombuffer(buf, np.uint8)
            yield a.reshape(h, w) if gray else a.reshape(h, w, 3)
    finally:
        p.stdout.close(); p.wait()


def _blobs(mask: np.ndarray):
    from scipy import ndimage
    lab, n = ndimage.label(mask)
    if not n:
        return []
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    out = []
    for k in np.argsort(sizes)[::-1][:3]:
        ys, xs = np.nonzero(lab == k + 1)
        out.append((float(sizes[k]) / mask.size, [float(xs.min() / mask.shape[1]), float(ys.min() / mask.shape[0]),
                                                   float((xs.max() + 1) / mask.shape[1]), float((ys.max() + 1) / mask.shape[0])]))
    return out


def check_pixels(path: Path, cfg: dict, exclude_bands: list | None = None) -> tuple[list[Finding], dict]:
    """Black holes and exposure, sampled at cfg['sample_fps'] on a 360x640 copy.

    exclude_bands: [(y0, y1)] fractions of frame height to ignore (e.g. the caption band, which has
    dark drop shadows by design)."""
    c = cfg["frames"]
    F, metrics = [], {"black_frames": 0}
    holes, over = [], []
    fps = c["sample_fps"]
    for k, fr in enumerate(frames(path, 360, 640, fps=fps)):
        t = k / fps
        dark = (fr.max(axis=2) <= c["black_rgb"])
        for y0, y1 in exclude_bands or []:
            dark[int(y0 * 640): int(y1 * 640)] = False
        if dark.mean() > 0.9:
            metrics["black_frames"] += 1          # a fully black frame is checked by the pacing layer
            continue
        for area, bbox in _blobs(dark):
            if area > c["black_blob_area"]:
                holes.append((t, area, bbox))
        if (fr.min(axis=2) >= 250).mean() > c["overexposed_share"]:
            over.append(t)
    if holes:
        ts = [h[0] for h in holes]
        worst = max(holes, key=lambda h: h[1])
        F.append(Finding("render.black_region", "frames", 0, "BLOCKED_RENDER_ARTIFACT",
                         f"solid black region of {worst[1]:.2%} of the frame at {worst[0]:.1f}s, box "
                         f"{[round(v, 2) for v in worst[2]]} ({len(ts)} sampled frames, {ts[0]:.1f}-{ts[-1]:.1f}s)",
                         t=worst[0], expected="no unlit holes (pure black is never part of the house style)",
                         evidence={"times": ts[:30], "bbox": worst[2]},
                         repair="find the missing geometry: sky/far clipping, open meshes, a camera inside an object",
                         regression_test="tests/test_qa_regression.py::test_chain_v1_black_triangle"))
    if len(over) > 3:
        F.append(Finding("render.overexposed", "frames", 3, None,
                         f"{len(over)} sampled frames have more than {c['overexposed_share']:.0%} blown-out pixels",
                         t=over[0], evidence={"times": over[:20]}))
    metrics["holes"] = len(holes)
    return F, metrics


def check_flicker(path: Path, cfg: dict, cuts: list[float], events: list[float],
                  region: tuple | None = None) -> tuple[list[Finding], dict]:
    """Temporal flicker: a tile whose brightness spikes for single frames, repeatedly, without a cut or
    an event to explain it. Full frame rate on a small grey copy (the artefact lives between frames)."""
    c = cfg["frames"]
    info = probe(path)
    fps = info["fps"]
    W, H, T = 360, 640, c["flicker_tile"] // 2      # tiles of 24 px on the 360-wide copy
    means, moves, prev = [], [], None
    for fr in frames(path, W, H, gray=True):
        a = fr.astype(np.float32)
        hh, ww = (H // T) * T, (W // T) * T
        means.append(a[:hh, :ww].reshape(hh // T, T, ww // T, T).mean(axis=(1, 3)))
        if prev is not None:             # per-tile pixel change: high all the time when things move through it
            moves.append(np.abs(a - prev)[:hh, :ww].reshape(hh // T, T, ww // T, T).mean(axis=(1, 3)))
        prev = a
    if len(means) < 5:
        return [], {}
    M = np.stack(means)                                           # (frames, rows, cols)
    d = M[1:-1] - 0.5 * (M[:-2] + M[2:])                          # single-frame spike
    ramp = np.abs(M[2:] - M[:-2])                                  # genuine motion changes the neighbours too
    mad = np.median(np.abs(d), axis=0) + 0.5
    spike = (np.abs(d) > np.maximum(c["flicker_min_delta"], c["flicker_z"] * mad)) & (ramp < 0.5 * np.abs(d))
    # moving content: a tile whose pixels change a lot in most nearby frames (cars streaming past a fast
    # camera) produces brightness wobble without any defect (PC render, other lane round 4, 38 s: a queue of
    # cars sweeping through the tile). Flicker on static content changes the pixels only on the spike frames.
    Dm = np.stack(moves)                                          # (frames-1, rows, cols); Dm[k] = |f[k+1]-f[k]|
    busy = np.zeros_like(spike)
    for k in range(len(d)):
        lo, hi = max(0, k - 4), min(len(Dm), k + 6)
        busy[k] = np.median(Dm[lo:hi], axis=0) > c.get("flicker_motion_ratio", 0.85) * np.abs(d[k])
    spike &= ~busy
    # ignore frames near cuts and declared events (flashes, cracks, reveals)
    ok = np.ones(len(d), bool)
    for t in list(cuts) + list(events):
        i = int(round(t * fps)) - 1
        ok[max(0, i - 2): i + 3] = False
    spike &= ok[:, None, None]
    if region:                                                    # restrict to the picture area (not captions)
        y0, y1 = int(region[0] * M.shape[1]), int(region[1] * M.shape[1])
        spike[:, :y0] = False; spike[:, y1:] = False
    # a defect is repeated spiking in the same place: >= 3 separate spike episodes within 2 s in one tile.
    # Spikes within 2 frames of each other form one episode: an object edge crossing a tile (a car passing
    # close to the camera) gives one short burst, while shimmer and blinking keep coming back. A long
    # unbroken run (>= 5 spikes, e.g. every-other-frame blinking) counts on its own.
    hits = []
    win = int(2 * fps)
    for r in range(spike.shape[1]):
        for cc in range(spike.shape[2]):
            idx = np.nonzero(spike[:, r, cc])[0]
            if not len(idx):
                continue
            eps = [[idx[0]]]
            for i in idx[1:]:
                (eps[-1].append(i) if i - eps[-1][-1] <= 2 else eps.append([i]))
            starts = [e[0] for e in eps]
            hit = next((e[0] for e in eps if len(e) >= 5), None)
            for j in range(len(starts) - 2):
                if starts[j + 2] - starts[j] <= win:
                    hit = starts[j] if hit is None else min(hit, starts[j])
                    break
            if hit is not None:
                hits.append(((hit + 1) / fps, r, cc))
    F = []
    if hits:
        hits.sort()
        F.append(Finding("temporal.flicker", "frames", 1 if len(hits) >= 3 else 2,
                         "BLOCKED_RENDER_ARTIFACT" if len(hits) >= 3 else None,
                         f"brightness flicker (repeated single-frame spikes) in {len(hits)} screen tiles, first at "
                         f"{hits[0][0]:.1f}s near ({(hits[0][2] + .5) * T / W:.2f}, {(hits[0][1] + .5) * T / H:.2f})",
                         t=hits[0][0], evidence={"tiles": [[round(h[0], 2), round((h[2] + .5) * T / W, 2), round((h[1] + .5) * T / H, 2)]
                                                           for h in hits[:20]]},
                         repair="z-fighting, shadow-map shimmer or texture aliasing: see the geometry findings at these times"))
    return F, {"flicker_tiles": len(hits), "frames": len(M)}

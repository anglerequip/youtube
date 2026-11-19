"""Generate the blind narrator audition pack.

  python tools/voice_audition.py kokoro          # all Kokoro candidates
  python tools/voice_audition.py elevenlabs      # needs ELEVENLABS_API_KEY
  python tools/voice_audition.py import <dir>    # add clips made elsewhere (e.g. Qwen3-TTS on a GPU),
                                                 # named <candidate>__<passage>.wav
  python tools/voice_audition.py pack            # shuffle, anonymise, loudness-match, write mp3s + key

Output: out/audition/raw/<candidate>/<passage>.wav, then out/audition/pack/ (anonymous mp3s,
manifest.json without names) and out/audition/key.json (the answer key; keep it private until
the votes are in).
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from factory.narration.pronounce import normalise  # noqa: E402

OUT = ROOT / "out" / "audition"
RAW = OUT / "raw"
PASSAGES = yaml.safe_load((ROOT / "content" / "voice_audition.yaml").read_text(encoding="utf-8"))["passages"]

# Kokoro candidates: the model card's best-rated English voices, plus speed variants and one blend.
KOKORO = {
    "kokoro_am_michael": {"voice": "am_michael", "speed": 1.0},
    "kokoro_am_fenrir": {"voice": "am_fenrir", "speed": 1.0},
    "kokoro_am_puck": {"voice": "am_puck", "speed": 1.0},
    "kokoro_af_heart": {"voice": "af_heart", "speed": 1.0},
    "kokoro_af_bella": {"voice": "af_bella", "speed": 1.0},
    "kokoro_bf_emma": {"voice": "bf_emma", "speed": 1.0},
    "kokoro_bm_george": {"voice": "bm_george", "speed": 1.0},
    "kokoro_bm_fable": {"voice": "bm_fable", "speed": 1.0},
    "kokoro_blend_michael_fenrir": {"blend": {"am_michael": 0.6, "am_fenrir": 0.4}, "speed": 1.0},
}


def kokoro():
    from kokoro_onnx import Kokoro
    from factory.voice_engine.kokoro import ensure_models
    model, voices = ensure_models()
    k = Kokoro(str(model), str(voices))
    timing = {}
    for name, cfg in KOKORO.items():
        d = RAW / name
        d.mkdir(parents=True, exist_ok=True)
        voice = cfg.get("voice")
        if "blend" in cfg:
            voice = sum(k.get_voice_style(v) * w for v, w in cfg["blend"].items())
        t0 = time.time()
        total = 0.0
        for p in PASSAGES:
            s, sr = k.create(normalise(p["text"]), voice=voice, speed=cfg["speed"], lang="en-us")
            sf.write(d / f"{p['id']}.wav", s, sr)
            total += len(s) / sr
        timing[name] = {"seconds_audio": round(total, 1), "seconds_compute": round(time.time() - t0, 1)}
        print(name, timing[name], flush=True)
    _merge_timing(timing)


def elevenlabs():
    from factory.voice_engine.elevenlabs import ElevenLabsTTS
    tts = ElevenLabsTTS()
    name = f"elevenlabs_{tts.voice[:6]}"
    d = RAW / name
    d.mkdir(parents=True, exist_ok=True)
    t0, total = time.time(), 0.0
    for p in PASSAGES:
        s, sr = tts.synth(normalise(p["text"]))
        sf.write(d / f"{p['id']}.wav", s, sr)
        total += len(s) / sr
    _merge_timing({name: {"seconds_audio": round(total, 1), "seconds_compute": round(time.time() - t0, 1)}})


def import_dir(src: str):
    for f in Path(src).glob("*__*.wav"):
        cand, pid = f.stem.split("__", 1)
        d = RAW / cand
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{pid}.wav").write_bytes(f.read_bytes())
        print("imported", cand, pid)


def _merge_timing(new: dict):
    p = OUT / "timing.json"
    cur = json.loads(p.read_text()) if p.exists() else {}
    cur.update(new)
    p.write_text(json.dumps(cur, indent=2))


def _loudness_match(src: Path, dst: Path):
    # EBU R128 to -16 LUFS so no voice wins by simply being louder.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "1",
                    "-codec:a", "libmp3lame", "-q:a", "2", str(dst)], check=True)


def pack(seed: int = 20261119):
    cands = sorted(p.name for p in RAW.iterdir() if p.is_dir())
    rnd = random.Random(seed)
    order = cands[:]
    rnd.shuffle(order)
    letters = [chr(ord("A") + i) for i in range(len(order))]
    key = dict(zip(letters, order))
    pk = OUT / "pack"
    if pk.exists():
        for f in pk.glob("*"):
            f.unlink()
    pk.mkdir(parents=True, exist_ok=True)
    manifest = {"passages": [{"id": p["id"], "label": p["label"], "text": p["text"]} for p in PASSAGES],
                "voices": []}
    for letter, cand in key.items():
        clips = {}
        for p in PASSAGES:
            src = RAW / cand / f"{p['id']}.wav"
            if src.exists():
                dst = pk / f"voice_{letter}_{p['id']}.mp3"
                _loudness_match(src, dst)
                clips[p["id"]] = dst.name
        manifest["voices"].append({"letter": letter, "clips": clips})
    (pk / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (OUT / "key.json").write_text(json.dumps(key, indent=2))
    print(f"packed {len(key)} voices into {pk}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pack"
    {"kokoro": kokoro, "elevenlabs": elevenlabs, "pack": pack}.get(cmd, lambda: import_dir(sys.argv[2]))()

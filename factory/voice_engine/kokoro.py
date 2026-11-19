"""Kokoro (82M) via kokoro-onnx: free, offline, good quality, fast on CPU."""
from __future__ import annotations

import urllib.request

from ..configuration import settings

MODEL_DIR = settings.models_dir
BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")

DEFAULT_VOICE = settings.kokoro_voice


def ensure_models() -> tuple[Path, Path]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in FILES:
        p = MODEL_DIR / name
        if not p.exists():
            print(f"downloading {name} ...", flush=True)
            tmp = p.with_suffix(p.suffix + ".part")
            urllib.request.urlretrieve(BASE + name, tmp)
            tmp.rename(p)
        paths.append(p)
    return paths[0], paths[1]


class KokoroTTS:
    name = "kokoro"

    def __init__(self):
        from kokoro_onnx import Kokoro
        model, voices = ensure_models()
        self.k = Kokoro(str(model), str(voices))

    def synth(self, text: str, voice: str | None = None, speed: float = 1.0):
        samples, sr = self.k.create(text, voice=voice or DEFAULT_VOICE, speed=speed, lang="en-us")
        return samples, sr

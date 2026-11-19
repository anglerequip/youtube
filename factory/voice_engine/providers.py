"""Pick a TTS backend. Every backend has synth(text, voice, speed) -> (float32 samples, sample_rate)."""
from __future__ import annotations

import numpy as np

from ..configuration import settings


class DummyTTS:
    """Test-only provider: returns silence of a plausible length (about 2.6 words per second)."""
    name = "dummy"

    def synth(self, text: str, voice: str | None = None, speed: float = 1.0):
        sr = 24000
        secs = max(0.6, len(text.split()) / (2.6 * speed))
        t = np.arange(int(secs * sr)) / sr
        # a quiet tone so audio checks see a signal; clearly not speech
        return (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr


def get_tts(provider: str | None = None):
    provider = (provider or settings.tts_provider or "kokoro").lower()
    if provider == "kokoro":
        from .kokoro import KokoroTTS
        return KokoroTTS()
    if provider == "elevenlabs":
        from .elevenlabs import ElevenLabsTTS
        return ElevenLabsTTS()
    if provider == "dummy":
        return DummyTTS()
    raise ValueError(f"unknown TTS_PROVIDER {provider!r} (use kokoro, elevenlabs or dummy)")

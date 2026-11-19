"""ElevenLabs backend (optional, paid). Set TTS_PROVIDER=elevenlabs and ELEVENLABS_API_KEY."""
from __future__ import annotations

import os

import numpy as np
import requests

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}"
# "Adam", a stock ElevenLabs voice. Override with ELEVENLABS_VOICE_ID.
DEFAULT_VOICE = "pNInz6obpgDQGcFmaJgB"


class ElevenLabsTTS:
    name = "elevenlabs"

    def __init__(self):
        self.key = os.environ["ELEVENLABS_API_KEY"]
        self.voice = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE)
        self.model = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")

    def synth(self, text: str, voice: str | None = None, speed: float = 1.0):
        # Episode `voice` values are Kokoro voice names, so ElevenLabs uses its own voice setting.
        r = requests.post(
            API.format(voice=self.voice),
            params={"output_format": "pcm_24000"},
            headers={"xi-api-key": self.key, "Content-Type": "application/json"},
            json={"text": text, "model_id": self.model, "voice_settings": {"speed": speed}},
            timeout=120,
        )
        r.raise_for_status()
        pcm = np.frombuffer(r.content, dtype="<i2").astype(np.float32) / 32768.0
        return pcm, 24000

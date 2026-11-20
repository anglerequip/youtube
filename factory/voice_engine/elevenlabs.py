"""ElevenLabs backend (optional, paid). Set TTS_PROVIDER=elevenlabs and ELEVENLABS_API_KEY.

Delivery settings follow common practice for natural narration with the v2 model: lower stability
(more variation in tone), similarity around 70 %, some style exaggeration, speaker boost on. One request
per beat (credit-light); the neighbouring beats are sent as context so the tone carries across cuts.
*word* emphasis from the storyboard becomes CAPS, which ElevenLabs stresses. Every value can be
overridden with an environment variable (ELEVENLABS_STABILITY, _SIMILARITY, _STYLE).
"""
from __future__ import annotations

import os
import re

import numpy as np
import requests

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}"
# The channel narrator (Caesar, 2026-11-20). Override with ELEVENLABS_VOICE_ID.
DEFAULT_VOICE = "TWutjvRaJqAX89preB4e"


def to_elevenlabs_text(text: str) -> str:
    """Storyboard markup -> ElevenLabs cues: *word* -> WORD (stress); '...' kept (a pause)."""
    return re.sub(r"\*([^*]+)\*", lambda m: m.group(1).upper(), text)


class ElevenLabsTTS:
    name = "elevenlabs"

    def __init__(self):
        self.key = os.environ["ELEVENLABS_API_KEY"]
        self.voice = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE)
        self.model = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
        env = lambda k, d: float(os.environ.get(k, d))
        self.settings = {"stability": env("ELEVENLABS_STABILITY", 0.35),
                         "similarity_boost": env("ELEVENLABS_SIMILARITY", 0.70),
                         "style": env("ELEVENLABS_STYLE", 0.35),
                         "use_speaker_boost": True}

    def synth(self, text: str, voice: str | None = None, speed: float = 1.0,
              previous_text: str | None = None, next_text: str | None = None):
        # Episode `voice` values are Kokoro voice names, so ElevenLabs uses its own voice setting.
        body = {"text": to_elevenlabs_text(text), "model_id": self.model,
                "voice_settings": {**self.settings, "speed": max(0.7, min(1.2, speed))}}
        if previous_text:
            body["previous_text"] = to_elevenlabs_text(previous_text)
        if next_text:
            body["next_text"] = to_elevenlabs_text(next_text)
        r = requests.post(
            API.format(voice=self.voice),
            params={"output_format": "pcm_24000"},
            headers={"xi-api-key": self.key, "Content-Type": "application/json"},
            json=body,
            timeout=120,
        )
        r.raise_for_status()
        pcm = np.frombuffer(r.content, dtype="<i2").astype(np.float32) / 32768.0
        return pcm, 24000

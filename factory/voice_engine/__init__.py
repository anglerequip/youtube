"""Voice engine: pluggable TTS providers plus narration/timing.

Providers (set TTS_PROVIDER):
  kokoro      free, local, default
  elevenlabs  paid API, needs ELEVENLABS_API_KEY
  dummy       silent placeholder audio sized to the text; for tests only, never for real videos
"""
from .providers import get_tts  # noqa: F401

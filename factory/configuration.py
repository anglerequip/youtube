"""Settings, read from environment variables (and an optional .env file in the repo root).

Secrets live only in the environment or in .env, which is git-ignored. See .env.example.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    content_dir: Path = Path(_env("CONTENT_DIR", str(ROOT / "content" / "episodes")))
    out_dir: Path = Path(_env("OUT_DIR", str(ROOT / "out")))
    data_dir: Path = Path(_env("DATA_DIR", str(ROOT / "data")))
    models_dir: Path = Path(_env("MODELS_DIR", str(ROOT / "models")))
    channel_name: str = _env("CHANNEL_NAME", "Counterphysical")
    channel_tagline: str = _env("CHANNEL_TAGLINE", "physics that breaks your intuition.")
    tts_provider: str = _env("TTS_PROVIDER", "kokoro")
    kokoro_voice: str = _env("KOKORO_VOICE", "af_bella")
    fps: int = int(_env("FPS", "30"))
    min_seconds: float = float(_env("MIN_SECONDS", "61"))
    max_seconds: float = float(_env("MAX_SECONDS", "90"))

    @property
    def db_path(self) -> Path:
        return Path(_env("DB_PATH", str(self.data_dir / "factory.db")))


settings = Settings()

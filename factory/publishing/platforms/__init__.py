"""Platform uploaders. Each module exposes `post(pkg) -> (remote_id, url)` and `check() -> str`.

They are only ever called by publisher.py for a row the human approved, after the package hash was
re-verified. Credentials come from .env / environment variables and token files under data/.
"""
from __future__ import annotations

import json
from pathlib import Path

from ...configuration import settings


class NotConfigured(RuntimeError):
    """Credentials for this platform are missing. The message says what to set up."""


def token_path(name: str) -> Path:
    return settings.data_dir / "tokens" / f"{name}.json"


def load_token(name: str) -> dict | None:
    p = token_path(name)
    return json.loads(p.read_text()) if p.exists() else None


def save_token(name: str, data: dict):
    p = token_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))

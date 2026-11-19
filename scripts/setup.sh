#!/usr/bin/env bash
# macOS / Linux setup. Run from the repo root: bash scripts/setup.sh
set -euo pipefail
command -v ffmpeg >/dev/null || { echo "Install ffmpeg first (brew install ffmpeg / sudo apt install ffmpeg)"; exit 1; }
command -v python3 >/dev/null || { echo "Install Python 3.10+ first"; exit 1; }
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt pytest
[ -f .env ] || cp .env.example .env
.venv/bin/python -c "from factory.voice_engine.kokoro import ensure_models; ensure_models()"
.venv/bin/python -m pytest -q
echo
echo "Done. Render the first Short with: .venv/bin/python -m factory produce falling-slinky"

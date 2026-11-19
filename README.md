# Counterphysical: science Shorts factory

Generates original physics and maths YouTube Shorts from code: a real simulation, a free AI voiceover,
synced captions and generated sound effects, checked automatically and sent to you for approval.
Nothing is ever uploaded without your explicit approval.

**Status:** Phases 1-2 done. One finished Short (`falling-slinky`). Telegram approval, YouTube upload
and analytics are next. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design, costs
and roadmap.

## Quick start (Windows)

```powershell
git clone https://github.com/anglerequip/youtube.git
cd youtube
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
.\.venv\Scripts\python.exe -m factory produce falling-slinky
```

The setup script installs Python, FFmpeg and Git with `winget` if they are missing, creates a virtual
environment, downloads the free voice model (about 350 MB, once) and runs the tests.
On macOS/Linux use `bash scripts/setup.sh`.

The finished video is written to `out/falling-slinky/final.mp4`.

## Commands

```
python -m factory produce <slug> [--previews] [--force] [--tts kokoro|elevenlabs]
python -m factory status              # every video and its state
python -m factory history <slug>      # state changes for one video
python -m factory qc <slug>           # re-run quality checks
python -m pytest -q                   # unit + end-to-end tests
```

## Layout

```
factory/
  configuration.py      settings from env / .env
  database.py           SQLite + state machine (approval can't be skipped)
  storyboard_engine.py  storyboard.yaml loader, YouTube metadata
  voice_engine/         Kokoro (free), ElevenLabs (optional), narration timing
  simulation_engine/    Scene base class + frame renderer (reusable components go here)
  caption_engine.py     burned-in captions
  video_editor.py       generated sfx, mixing, final mux
  quality_control.py    automatic checks before review
  production.py         the production workflow
content/episodes/<slug>/  storyboard.yaml + sim.py per video
tests/                    unit tests + end-to-end test
```

## Credentials

Copy `.env.example` to `.env`. Nothing is needed for Phases 1-2. Telegram and YouTube credentials are
only needed from Phase 4/5, and they stay in `.env`, which is git-ignored.

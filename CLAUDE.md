# Counterphysical Shorts factory

Read `docs/ARCHITECTURE.md` first. This file is the guide for a Claude session writing new episodes.

## Writing a new episode

1. Pick a topic that is genuinely counterintuitive *and* simulatable with real physics or maths.
   Check `content/episodes/` so you don't repeat one. Never copy another channel's scripts,
   footage, branding or exact video concepts.
2. Research it. Put real, checkable sources and honest caveats in the storyboard. Never invent data
   or overstate a result to make it more dramatic.
3. Create `content/episodes/<slug>/storyboard.yaml` (copy the structure of `falling-slinky`):
   - 6-9 beats, 25-45 s total narration. Beat 1 is the hook: a surprising claim in under 3 s.
   - Short spoken sentences; spell numbers the way they should be read.
   - `on_screen` for an occasional key phrase or equation, `sfx` (whoosh, thud, pop, tick, rise, ding).
4. Create `sim.py` with `class Sim(Scene)`. Sync to beats with `self.tl.start("<beat id>")`.
   Keep visuals between y=0.25 and y=0.90 of the frame (captions sit at about y=0.30).
   Add `self_checks()` comparing the simulation to theory, and `sfx_events()` for physical moments.
5. Run `python -m factory produce <slug> --previews` and look at `out/<slug>/previews/*.png`.
   Fix anything QC flags. Commit the episode folder only (never `out/`, `data/`, `.env`).

## Rules

- Nothing is ever published without the human's approval in Telegram. Do not add code paths that
  upload from the production workflow.
- Secrets only in `.env` / environment variables.
- Run `python -m pytest -q` before committing.

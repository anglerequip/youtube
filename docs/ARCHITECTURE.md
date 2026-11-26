# AnglerMind video factory: architecture

(Formerly the Counterphysical Shorts factory. Brand rules: `docs/BRAND.md`.)

Status as of 2026-11-19: Phases 1 and 2 are done (structure, first Short, QC, tests).
Phases 3 to 7 are listed at the bottom with what is and isn't built.

## 1. How a video is made

```
 ideas ──► research ──► script ──► storyboard.yaml + sim.py
                                          │
                     ┌────────────────────┴─────────────── production workflow ──┐
                     │ voice_engine     narrate each beat, measure its timing     │
                     │ simulation_engine render frames synced to beat timings     │
                     │ caption_engine   2-3 word captions from the same timings   │
                     │ video_editor     mix generated sfx, burn captions, mux     │
                     │ qa (pre-render)  spec, claims, events, 3D inspection, pacing│
                     │                  (blocks before the full render)           │
                     │ quality_control  24+ checks incl. the sim's physics tests  │
                     │ qa (post-render) pixels, flicker, audio, independent review│
                     │                  -> release gate + out/<slug>/qa/report.md │
                     └───────────────────────────────┬────────────────────────────┘
                                                     ▼
                                   PENDING_APPROVAL ─► Telegram: Approve / Reject / Revise
                                                     │ (only on Approve, and only the exact file approved)
                     ┌───────────────────────────────┴──────────── publishing workflow ─┐
                     │ youtube_publisher  upload + schedule, idempotent, sha256-checked │
                     │ analytics_engine   pull metrics into SQLite, compare formats     │
                     └──────────────────────────────────────────────────────────────────┘
```

The self-checking QA system and its release gate are described in `docs/QA.md`.

Production and publishing are separate commands, and the database refuses any state change that
skips approval (see `factory/database.py`, `ALLOWED`).

### States

`IDEA → RESEARCHED → SCRIPTED → STORYBOARDED → RENDERED → QUALITY_CHECKED → PENDING_APPROVAL → APPROVED → SCHEDULED → PUBLISHED → ANALYZED`

Side states: `QC_FAILED`, `REVISION_REQUESTED`, `REJECTED`, `FAILED`. Every change is logged in the
`transitions` table with a timestamp and note (`python -m factory history <slug>`).

### Storyboard

`content/episodes/<slug>/storyboard.yaml` holds the narration beats (each with an `id`), optional
on-screen text, sound cues and camera hints, plus title, description, tags, caveats and sources.
`sim.py` holds a `Sim(Scene)` class that animates against beat ids, so rewording a line re-times the
visuals automatically. A sim can also declare `self_checks()` (physics tests that QC runs) and
`sfx_events()` (sounds at physical moments, like an impact).

## 2. Technology choices

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | everything below is Python-native |
| Visuals | numpy simulations drawn with Matplotlib, piped to FFmpeg | exact physics, no GPU, renders at about real time on 4 CPU cores; Manim can be added per component later |
| Voice | Kokoro-82M via `kokoro-onnx` | free, offline, natural; ElevenLabs is a drop-in (`TTS_PROVIDER=elevenlabs`) |
| Captions | timed from the narration itself (each beat is synthesised separately) | exact sync with no Whisper pass; Whisper word alignment can be added later for word-level highlighting |
| Sound effects | synthesised in numpy (`video_editor.sfx`) | original, license-free |
| Database | SQLite (WAL) | zero setup, safe for one machine |
| Approval | Telegram Bot API | free, works on your phone |
| Publishing / analytics | YouTube Data API v3 + YouTube Analytics API | free, OAuth |
| Orchestration | Python CLI now; a scheduler loop in Phase 7 | simple, resumable (steps are cached by content hash) |

## 3. What costs money, and what doesn't

| Operation | Paid? |
|---|---|
| Rendering, voice (Kokoro), captions, sfx, QC, database | Free, runs on your PC |
| Telegram bot | Free |
| YouTube upload and analytics APIs | Free within quota. The default quota is 10,000 units/day and an upload is one of the most expensive calls, so the default allows only a handful of uploads a day. Google grants increases for free on request, which we'll need before 10+/day |
| **Writing ideas, scripts and sim code** | **The only part that needs an LLM.** Three options below |

LLM options for the creative step (configurable, `LLM_PROVIDER`):

1. **manual (default, $0 extra):** a Claude Code session (like this one) writes storyboards and sims
   into the repo, either when you ask or as a scheduled task. This uses your Claude plan's normal
   usage limits. It is *not* an API your Python code can call, so it can't run unattended inside the
   factory loop; it works by committing new episodes the factory then renders.
2. **anthropic:** the Claude API, called from Python. Fully automatic, but billed per token on a
   separate API account. A Claude subscription does not include API credits.
3. **ollama:** a free local model. Fully automatic and free, but noticeably weaker at writing correct
   physics and simulation code, so expect more QC failures.

Recommendation: stay on option 1 while we build the component library. Once most videos are
"storyboard + parameters for an existing component" rather than new code, switch to option 2 and
measure the real cost per video before scaling.

## 4. Hardware and measured speed

Measured in the build container (4 CPU cores, no GPU) on the 41.5 s slinky Short:
voice 11 s (including model load), simulation render 38 s, mux 8 s, QC 3 s. About **1 minute per
Short**, so 20 Shorts/day is about 20 CPU-minutes. Storage is about 2-3 MB per final video plus
about 10 MB of intermediates (deletable). The voice model is a one-time 350 MB download.
These numbers will differ on your PC; `python -m factory produce` prints its own timings.

## 5. Implementation sequence

| Phase | Scope | Status |
|---|---|---|
| 1 | Structure, config, database + state machine, setup scripts | done |
| 2 | First original Short end to end, QC, unit + end-to-end tests | done |
| 3 | Reusable components (traffic waves, pendulums/projectiles, probability/maths), three video types, idea scoring, LLM provider interface | next |
| 4 | Telegram approval bot (preview, title, topic, duration, caveats; Approve / Reject / Revise) | not started |
| 5 | YouTube OAuth upload + scheduling, sha256 and idempotency guards | not started |
| 6 | Analytics pull + performance database + format comparisons | not started |
| 7 | Batch generation, job queue, parallel renders, daily scheduler | not started |

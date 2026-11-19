# Self-checking production (factory/qa)

Built 2026-11-19 after Caesar rejected three videos (other lane: sidewalk glitches; spaghetti: said
three pieces, showed four; chain fountain: no visible links and a black hole in the sky). The rule since
then: **nothing reaches Caesar unless the system has checked it against its own specification, and an
independent reviewer has looked at the actual video.** Nothing in this system publishes anything;
release still needs Caesar's approval in Telegram.

## 1. One source of truth

`storyboard.yaml` now holds, next to the narration:

| key | what it says | checked by |
|---|---|---|
| `claims:` | every number the viewer hears or reads: unit, true value (`value:` from a source, or `sim:` from the plan's `facts`), scope (specific / typical / model / universal / condition / history), evidence quality 1-5 and source | science layer |
| `absolute_ok:` | each absolute word ("never", "exactly", "every") with the reason it is literally true | science layer |
| `entities:` | what must be visible: type, risk category A-F, importance, `visual_contract` (`must_read_as`, pixel minimums) | geometry layer, Critical Designer |
| `hero:` | the one thing the viewer must follow | review packet |

`plan.py` returns `facts` (the simulated values, the slow-motion factors, and `events`: moments where
what is drawn must equal what was simulated, read through `observe(plan, i, what)`).

Risk categories (brief Part VI): A faces, B thin connected objects (chains, springs), C mechanically
recognisable objects (cars, jars), D deformable and fracturing objects, E large surfaces, F background.

## 2. Layers

| # | layer | when | file | finds |
|---|---|---|---|---|
| 1 | spec | before render | `qa/spec.py` | missing claims, entities, hero, sources; duration rule (> 60 s); slow hook |
| 2 | science | before render | `qa/science.py` | numbers that disagree with their claim, unbound numbers, overstated or absolute wording, wrong cards and badges. Understands "three or more", "almost a full turn", "four of them", "in two" |
| 3 | events | before render | `qa/spec.py` | drawn state differs from the simulation at a declared event; on/off tracks that blink for one frame |
| 4 | pacing | before render | `qa/pacing.py` | stretches with no attention event (cut, card, badge, sound event, reveal), slow hook, jump cuts, dead air at the end |
| 5a | sound | before render | `qa/sound.py` | the sound team's logic: the identical sample on repeat, too many effects per second, metronome rhythms, effects competing with the voice (measured on the exact stems the mixer sums), startling cues, music too loud under the voice |
| 5 | geometry | before render | `qa/inspect3d.py` + `renderer/inspect.js` | world missing (sentinel render), NaN, z-fighting (gap vs depth precision at the visible distance), shadow-map cut-offs, chain beads without visible links, piece counts that do not read on a 360x640 phone, labels covering the hero, popping |
| 6 | pixels | after render | `qa/frames.py` | solid black regions, blown-out frames |
| 7 | flicker | after render | `qa/frames.py` | repeated single-frame brightness spikes per screen tile (cuts and declared events excluded) |
| 8 | audio | after render | `qa/audio.py` | duration, clipping, true peak, loudness, unvoiced beats, dead air, silent physical events |
| 9 | review | after render | `qa/critic.py` | independent Critical Designer critique of the actual frames |
| 10 | sound review | after render | `qa/sound.py` | independent Sound Reviewer: "would a viewer find anything in this soundtrack annoying?", judged from the cue sheet, a level timeline and a spectrogram of the final mix |

Layers 1-5 run inside `produce` right after the plan is built. A blocker stops the production there,
before the 1.5-2.5 hour full render, and writes the report.

## 3. Severity, states and the gate

Severity 0 critical, 1 major (both block), 2 high (repair before approval unless an exception is
recorded), 3 polish, 4 optional. Every blocker names a `BLOCKED_*` state, and the report says which
stage repairs it (`RETURN_TO` in `qa/findings.py`): a factual error goes back to research, a visual
contradiction to the script/simulation, geometry to the visual plan, a missing review to review.

Rubric (`config/quality.yaml`): eight categories scored 0-5. The automated score starts at 5 and loses
points per finding; the reviewer's score is used when lower. Approve only with a weighted score of at
least 4.0, no primary category (science, cross-modal, clarity, geometry) under 3.5, and no blocker.
`READY_FOR_RELEASE` then moves the database to `QUALITY_CHECKED`, the only state from which a video
can be sent to Caesar for approval.

## 4. The Critical Designer

`critic.build_packet` writes `out/<slug>/qa/review/`: six blind frames, time-stamped contact sheets at
phone size, `intent.md` (narration, claims, contracts, expected events, caveats), the review brief
(brief Part XLII) and `schema.json`. It contains none of the generator's explanations or automated
verdicts. A separate reviewer (a fresh model context with no generator history, or a person) writes
`critique.json` with the video's sha256, and a second fresh reviewer, who never sees the first critique,
writes `critique_2.json`. Caesar asked for two (2026-11-19) after single reviewers swung between rounds on
unchanged shots. The gate averages the two reviewers' scores per category; a rejection blocks only when
both reject, and a severity-1 problem raised by one reviewer while the other approves is kept in the
report at severity 2. Without both valid critiques for the exact file (`review: picture_reviewers` in
`config/quality.yaml`), the gate blocks with `BLOCKED_REVIEW_UNAVAILABLE`. The generator never writes
these files.

## 4b. The sound team

Added after Caesar heard the chain fountain go "ding ding ding" every half second: 203 cues of one
identical bell sample, each quiet enough that loudness checks never noticed. `sound.check` reads the cue
sheet (every cue rendered and hashed, so "the same sample" is exact) and the voice / effects / music stems
from `sound_design.stems`, the same function the mixer uses. Cues within 0.15 s are one event (a crack-crack
burst at a snap is meaning, not clutter). Varying the sample does not make a rhythm acceptable: round 2 of
the chain swapped the bell for 168 varied "coil" clicks, about 3 a second, which the old logic waved through as
"texture" and the Sound Reviewer heard as a ticking clock. Now every cue counts towards density, the
`click_train` check catches one kind of cue going on without a pause (by name, whatever the sample), and a
run of only four evenly spaced cues is already flagged as a metronome. Texture (short, never-identical cues)
is only exempt from the identical-sample count. Thresholds: `config/quality.yaml` `sound:`.

`sound.build_packet` writes `out/<slug>/qa/review_audio/` (cue_sheet.md, timeline.png, stats.json,
intent.md, INSTRUCTIONS.md, schema.json, packet.json). A separate reviewer writes `critique_audio.json`
bound to the video's sha256; without it the gate blocks (`review.audio_unavailable`). The audio score is
the Sound Reviewer's (the Critical Designer's audio score is provisional: it only sees levels). Episode rule: vary every repeated cue
(`seed`, `pitch`, `ring` on tinks), one cue per event the viewer should notice, nothing over the words.

## 5. Commands

```
python -m factory produce <slug> --previews   # pre-render gate, render, post-render QA, report
python -m factory qa <slug> [--video f.mp4] [--no-inspect]   # all layers on an existing render
python -m factory qa-gate <slug>              # after critique.json exists: re-run the gate
```

Reports: `out/<slug>/qa/report.md` and `report.json`. Thresholds: `config/quality.yaml`. Known defect
classes and their tests: `config/defects.yaml`. Regression tests: `tests/test_qa_science.py`,
`tests/test_qa_regression.py` (old scenes in `renderer/scenes/regression/`, clips in
`tests/fixtures/regression/`).

## 6. Limitations (honest)

- The geometry checks see what scenes expose: meshes, the camera, the sun's shadow camera, and the
  `probes()` a scene declares. A defect in something no probe covers (say a texture that looks wrong
  but is technically fine) is left to the pixel layers and the reviewer.
- Shadow cut-off detection uses bounding boxes, so it can flag a caster whose real shadow is only
  barely cut; it weights by on-screen area and haze to keep this to real cases.
- Flicker detection samples 24 px tiles on a 360-wide copy: slow crawling seams (not single-frame
  spikes) are not caught by it; the shadow-cutoff check covers the known cause.
- Number parsing covers how our scripts speak (number words, fractions, "a full turn", "in two",
  "double"). An unusual phrasing can slip through; every unbound number is still reported.
- Perceptual listening (pronunciation, naturalness, music) is not automated and is always reported as
  NOT performed. The sound team judges annoyance from measurable proxies and plots; it does not hear.
  Caesar's own listen stays the final check for sound. Engagement can only be measured on the platform after release.
- The Critical Designer is another model instance: independent of the generator's context, but not of
  the model family. Caesar's own review in Telegram stays the final gate.

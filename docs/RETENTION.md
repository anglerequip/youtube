# Retention toolkit (factory/retention)

Reusable, storyboard-driven tools that make a Short easier to follow and harder to scroll away from,
without breaking the house style (CLAUDE.md Visual Blueprint) or the QA rule that every number on screen
is true. Built 2026-11-19 from the competitor study in `docs/research/competitor-shorts-2026-11.md`.

Everything is **opt-in per episode**: a storyboard without a `retention:` block renders exactly as before
(tested: `tests/test_retention.py::test_episodes_without_retention_are_unchanged`).

## How it fits the pipeline

```
storyboard.yaml ──► plan.py build_plan()  ──► retention.apply()  ──► plan.json ──► renderer (boot.js → hud.js)
   retention:                                   │ hud.compile_hud    plan.hud     (2D overlay over the 3D frame)
     hud:  widgets                              │ cues.compile_cues  plan.retention.events ─► sfx_events() ─► sound_design mix
     cues: sound/music/camera                   │ tick_events        plan.retention.mutes/swells ─► music()
     features: overrides                        └ punch-ins edit the keyed shots' field of view
                                                         │
                                 factory/qa: hud layer (truth, layout, clutter, loops), pacing counts HUD events,
                                             sound layer checks every generated cue (repetition, density, masking)
```

`retention.load_plan_module(sb)` is the single place the layer is applied; production and QA both use it.

## Time expressions (factory/retention/timing.py)

| Form | Meaning |
|---|---|
| `12.5` | seconds |
| `payoff`, `payoff.end` | start / end of a beat |
| `payoff+0.4`, `catch.end-0.2` | offsets |
| `double@doubles` | when the word "doubles" is spoken in beat `double` (same estimate the captions use; `word#2` for the 2nd match) |
| `hud:<id>.appear / .hide / .settle / .cross / .answer / .zero / .step<k>` | HUD events |
| `end` | end of the video |

`show:` takes a beat id (whole beat) or `[from, to]`; a bare beat id as `to` means "until that beat ends".

## HUD widgets (`retention.hud`)

All numbers come from the simulation: `value: {frames: <plan frames key>, scale, offset}` or
`{fact: <plan fact>}`. Authored `keys: [[time, value], ...]` are allowed only with `claims:` bound
(QA blocks otherwise). `claims: [{claim: <id>, at: <time>}]` makes QA compare the shown value with the
claim at that moment.

| type | Use it for | Required | Notes |
|---|---|---|---|
| `counter` | experiment state that changes (drop height, speed, count) | value, format, slot/at | `ticks: {max, max_rate_hz, sfx, gain}` adds a soft blip per change, pitch rising with the value |
| `meter` | a quantity approaching a meaningful threshold | value, min, max | `threshold: {value}` fires `hud:<id>.cross` |
| `dimension` | measuring something in the world (an arch height, a gap) | from, to (anchors), value | white measuring line with end caps, label card beside it |
| `callout` | pointing at where the physics happens | anchor, label | ring + leader line, tracks the 3D point |
| `question` | the episode's open loop | text, ask, answer, answer_text | "?" chip until the answer, then a ✓ answer chip for `hold_s` |
| `progress` | a sequence of experiments (1 m, 2 m, no push) | items: [{label, at}] | current step highlighted |
| `timer` | counting down to a real physical moment, or a slowed clock | `mode: down` + `target` (time expression), or `mode: up` + `rate` | fires `hud:<id>.zero`; format `m:ss.ss` or `x.xx s`. Only for a moment the physics really has |
| `arrow` | the force at the moment the narration names it | anchor, `dir` [x,y,z], `length_m`, label | red (Blueprint accent), tracks the 3D anchor, projected QA like callouts |

Anchors: plan.py exports `hud_anchors(plan) -> {name: [[x, y, z] per frame]}` in world metres.
Placement slots, the platform-safe area, the caption band, limits and colours are in `config/retention.yaml`.

### What the HUD QA layer checks (factory/qa/hud.py)

- `hud.unbacked_number` (blocker): a widget shows hand-set numbers without a claim.
- `hud.claim_mismatch` (critical): the shown number disagrees with the bound claim.
- `hud.unsafe`: outside the safe area (TikTok / Shorts right rail, top bar, captions).
- `hud.overlap.*`, `hud.overlap_card.*`: two overlays (or a widget and the speed badge / a card) collide.
- `hud.offscreen`, `hud.too_small`, `hud.caption_clash`: a tracked overlay points off frame, is too small to
  read, or its label lands in the caption band (computed with the plan's own camera, before rendering).
- `hud.clutter`: more than `max_widgets` screen widgets / `max_overlays` overlays at once.
- `story.loop_*`: a question that is answered too soon (< 4 s), too late (> 45 s), or has no "?".

## Cues (`retention.cues`)

```yaml
cues:
  - {at: "hud:drop.settle", sfx: lock, gain: 0.28}          # a number lands: one accent
  - {at: "double@doubles", punch_in: 0.07, punch_s: 0.9}     # slow push-in on the key word
  - {at: "catch@no", music: drop, until: outro}              # music out during the experiment
  - {at: "outro", music: swell}                              # music returns with the payoff
  - {at: "reality", riser: 1.4, reveal: true}                # a riser that ENDS on the reveal
```

Sounds available (all synthesised, license-free): the existing set plus `blip` (soft HUD update) and
`lock` (value lands / answer). Every generated sound passes through `sfx_events()`, so the sound QA layer
(repetition, density, periodicity, masking) judges it like any other cue.

## Feature flags (`config/retention.yaml` → `features`, override per episode under `retention.features`)

| flag | default | effect |
|---|---|---|
| `hud` | true | compile widgets (only if the episode declares some) |
| `cues` | true | compile cues |
| `auto_accents` | **false** | a soft blip when every card / widget appears, a lock when a meter crosses its threshold. Off until an A/B test says it helps |
| `caption_emphasis` | **none** | `weight`: narration `*stars*` and `retention.captions.keywords` are drawn bolder. Colour highlighting stays forbidden (Blueprint 6) |

## Writing guide: when each tool earns its place

1. **One live number per experiment.** If the narration says a number, show where it comes from
   (a counter or a measuring line driven by the simulation) instead of a static card.
2. **Measure in the world, not in a corner.** Prefer `dimension` / `callout` attached to the object over a
   screen-corner counter when the object is big enough on screen (QA tells you when it is not).
3. **One open question at a time,** asked in words by the narration and pinned as a chip until answered.
4. **Show the counterfactual.** If the script says "without X, no Y", switch X off in the model on screen
   (a meter going to zero) and let the picture prove it (see `chain-fountain-hud`, catch beat).
5. **Hook frame = the impossible thing, big, already moving.** Override the first shot so the phenomenon
   fills the middle third at frame 0 and the camera is moving.
6. **Accents mark arrivals, not decoration.** A sound when a value *lands* or a question is *answered*;
   never a metronome (the sound QA blocks those).

## Demo

`content/episodes/chain-fountain-hud` = the chain-fountain episode (same narration) + drop counter, live arch
measuring line, the open question chip, a tracked "pile pushes up" callout in the macro, and a no-push
experiment (meter 12 % → 0 % → 12 %) where the arch collapses into a rope-like drape and comes back for the
loop. Its plan.py reuses `../chain-fountain/plan.py` and adds only anchors, the push series and a tighter
opening shot.

## A/B tests worth running

The toolkit's flags make one-variable comparisons cheap: hook framing, live HUD vs static cards,
the on-screen counterfactual, the question chip, `auto_accents`, `caption_emphasis`. The test table,
metrics and how to record results are in `docs/research/competitor-shorts-2026-11.md` section F.2.
No technique here is promised to raise views by any amount; the research shows correlations in 25
videos, not causes.

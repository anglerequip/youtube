# Motion design system

Counterphysical research lab, v1, 2026-11-19. Rules for camera, cuts, visual events and attention
cues, built on top of the Visual Blueprint in `CLAUDE.md` (which owns the look: palette, objects,
lighting, camera types). Evidence lives in `VISUAL_STORYTELLING_RESEARCH.md` (VS-Q#) and R2.

## 1. Storyboard annotations

Every beat lists its visual events. These are what the renderer schedules and what QC checks.

```yaml
beats:
  - id: chain
    shot: highway_centreline        # Blueprint camera key, or side_bench / macro (proposed)
    pace: build                     # brisk | calm | build | reveal | hold
    focal: car_01                   # id of the focal object in the scene
    visual_events:
      - {t: 0.00, type: cut, on_event: brake_onset}           # type 1
      - {t: 0.10, type: camera, move: dolly_in, dur: 2.5, ease: in_out_sine}   # type 2
      - {t: 0.40, type: state_change, what: car_01 brakes}     # type 3
      - {t: 1.20, type: info_reveal, what: label "small tap"}  # type 4
      - {t: 1.50, type: object_motion, what: brake glow propagates to car_08}  # type 5
    fidelity: simulated             # simulated | diagrammatic | exaggerated | illustrative
```

`t` is relative to the beat start, so rewording a line re-times everything (the factory already syncs
to beat ids).

## 2. Event density rules

| ID | Rule | Default | Level | Basis |
|---|---|---|---|---|
| MD-1 | Max gap between meaningful visual events (any type) | 3.0 s | warn | VS-Q1, R2-F10 (B/E) |
| MD-2 | Max gap between meaningful events in a `why`/explanation beat | 2.5 s | warn | R2-F21 (D) |
| MD-3 | Max length of a shot with no type 3-5 events (camera drift only) | 4.0 s | warn | VS-Q2 (E) |
| MD-4 | Max shot length with continuous type 3-5 events | 13 s | warn | VS-Q2 (E) |
| MD-5 | Hard-cut interval between camera angles | 7-12 s typical, cut on a change of scene, scale or time of day (measured on the reference Short: 5 cuts in 60.5 s, R1 section 5); min 1.2 s between any two cuts | min is fail, typical is guidance | R1 (D); VS-Q4. Conflicts with Blueprint "2.5-4 s", see note below |
| MD-6 | Hard cut lands within ±2 frames of a physical event on the focal object when one exists in the window ±0.5 s | prefer | guidance | R2-F12 (C) |
| MD-7 | After a cut, the focal object is visible within 0.3 s, and its screen position moves < 25% of frame height, or it carries the highlight ring | required | warn | VS-Q4/Q7 |
| MD-8 | No hard cut during the reveal window (`reveal: true` beat, first 1.5 s) | required | fail | VS-Q3 |
| MD-9 | Opening frame in motion, no title card or logo sting | required | fail | Blueprint section 8, HK-1 |

**Blueprint conflict (MD-5).** CLAUDE.md says cuts every 2.5-4 s. Frame analysis of the reference
Short (R1 section 5) found shots of 7-12 s with continuous eased camera moves and frequent on-screen
events inside each shot. MD-1/MD-2 keep the viewer's visual events frequent; MD-5 no longer asks for
frequent cuts. Caesar decides whether to update the Blueprint text. Experiment V1 tests both.

"Meaningful" excludes idle motion: tree sway, ambient traffic not involved in the explanation,
camera drift under 2% of frame per second.

## 3. Camera

The Blueprint defines five shots (chase, overhead 3/4, top-down map, highway centreline,
big-picture pull-out). Proposed additions for non-traffic topics, in the same world and lighting:

- `side_bench`: orthographic-feeling side view at the object's height (falling, springs, pendulums, projectiles).
- `macro`: close view of one part of a mechanism (the bottom coil, a single tyre).

Movement rules:

| ID | Rule | Default |
|---|---|---|
| CAM-1 | All moves eased (sine or cubic in-out); no linear starts or stops | required |
| CAM-2 | Drift speed | 1-3% of frame width per second |
| CAM-3 | Deliberate move (dolly/zoom to a detail) | 0.8-2.5 s, ≤ 1 per beat |
| CAM-4 | Rotation/orbit | ≤ 8°/s |
| CAM-5 | No camera move during the first 1.0 s of a reveal; hold still while the result happens | required (R2-F9, F11) |
| CAM-6 | Camera may track the focal object; tracking lag ≤ 0.2 s, no overshoot | required |
| CAM-7 | Time scale changes (slow motion) are labelled on screen ("slowed 10×") | required (fidelity) |

## 4. Attention cues

| Cue | Use | Rule |
|---|---|---|
| Ground ring (Blueprint: thin white ellipse) | Marks the focal object | One at a time; appears 0.2 s before the object's key moment |
| Red (brake/alert `#c92a2e`) | The phenomenon itself | Reserved: nothing decorative may be red or saturated |
| Ghost overlay (semi-transparent copy) | "What you'd expect" vs reality (misconception beats, SC-17) | 35-50% opacity, labelled "expected" or similar |
| Force/velocity arrows | Only when the quantity matters to the explanation | Length proportional to magnitude (fidelity: diagrammatic), max 3 arrows on screen |
| Pulse travelling along a structure | Showing propagation (a wave, news travelling down a slinky) | Speed equals the simulated propagation speed, or labelled as diagrammatic |
| Dim the rest | During the reveal | Non-focal elements may desaturate up to 30% |

**MD-10** At the reveal, motion energy outside the focal region (mean absolute frame difference outside
the focal bounding box, expanded 20%) must be below 25% of its episode median. (R2-F9, F11; Tier C/E.)

**MD-11** Focal object size at its key moment: ≥ 6% of frame height or ≥ 10% of frame width; key signal
(brake light, coil, impact flash) ≥ 1% of frame width with bloom. (VS-Q9; Tier E. Addresses the
reference Short's tiny brake lights.)

**MD-12** Complexity budget: ≤ 3 objects that matter on screen; ≥ 40% of the frame low-detail. QC proxy:
fraction of pixels with Sobel edge magnitude above threshold, per second; warn if above the 90th
percentile of our own catalogue for > 2 s. (R2-F10.)

## 5. Scientific fidelity

Each visual element carries a fidelity tag:

| Tag | Meaning | Obligation |
|---|---|---|
| `simulated` | Motion computed from the physics model | `self_checks()` must cover the quantity shown |
| `diagrammatic` | Arrows, pulses, ghosts that represent a quantity | Proportional where a magnitude is implied |
| `exaggerated` | Real behaviour scaled for readability (bigger brake glow, slowed time, enlarged gaps) | If it could change the interpretation (time, distance, speed comparisons), label it on screen |
| `illustrative` | Not physics (scenery, decorative props) | Must not move in a way that suggests physics |

QC fails an episode where an `exaggerated` element affecting time, distance or speed has no label,
and where any number in a card is not traceable to `self_checks()` or `sources` (SC-13).

## 6. Pacing by beat type

| `pace` | Visual event target gap | Camera | Cuts |
|---|---|---|---|
| `brisk` (hook) | ≤ 1.5 s | in motion from frame 0 | 0-1 |
| `calm` (setup, explanation) | ≤ 2.5-3 s | slow drift or tracking | on beat change |
| `build` (escalation) | shrinking gaps, 3 s → 1.5 s | may accelerate drift | cut on events |
| `reveal` | one big event, then hold | still for ≥ 1 s (CAM-5) | none for 1.5 s (MD-8) |
| `hold` (takeaway or prediction window) | none required, ≤ 2 s | still or very slow drift | none |

## 7. Loop endings

Use a visual loop only when the system genuinely returns to its starting state (reverse-explanation
hooks, cyclic systems like a ring road returning to free flow) or the final frame restates the hook.
Do not force a loop by cutting back to frame 0 when the topic has moved on. (R2 "not automated" item
2; Blueprint section 8 says "ending loops visually", proposed refinement: "when it explains".)

## 8. QC checklist (renderer must emit the metadata)

Per frame: focal object id + bounding box; camera pose; text boxes and roles; cut flag. Per episode:
visual events list with types. From these, QC computes MD-1 to MD-12, CAM-5, CAM-7, TX-6, TX-7 and
reports distributions (min, median, 90th percentile, max) of event gaps per beat type.

## 9. Experiments

| Exp | Comparison | Primary metric |
|---|---|---|
| V1 | Continuous tracked simulation vs cut between 3 perspectives (brief Exp. 4) | APV |
| V2 | Minimal scene vs richer scenery (brief Exp. 7) | APV, quiz |
| V3 | Highlight ring + ghost overlay vs no cues | Quiz on mechanism; mechanism comments |
| V4 | MD-1 gap 2 s vs 3.5 s target (different topics) | Retention curve shape where available |

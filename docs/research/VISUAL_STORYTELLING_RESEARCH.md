# Visual storytelling research

Counterphysical research lab, v1, 2026-11-19. Evidence base for `MOTION_DESIGN_SYSTEM.md`.
Cites R2 (`RESEARCH_REPORT_02_ATTENTION_AND_COGNITION.md`) findings as R2-F#. A second revision will
add distributions measured from the competitor micro-analysis (Report 01); this version uses the
literature and the reference Short.

## 1. Five kinds of visual change

The brief's key distinction, adopted as the annotation scheme for both our research and our renders:

| Type | Name | Example in our videos | Detected automatically by |
|---|---|---|---|
| 1 | Hard cut | Ring top-down → highway centreline | Scene detection (PySceneDetect content detector) |
| 2 | Camera movement | Ease in on the slinky's bottom coil | Our renderer's camera track (known exactly); for competitors, optical-flow global motion |
| 3 | Simulation-state change | Release, a car starts braking, a parameter changes | Our `sfx_events()` / beat markers; for competitors, manual annotation |
| 4 | Information reveal | Label card, force arrow, ghost overlay | Our text/overlay events; for competitors, manual or OCR |
| 5 | Object-level movement | Brake glow travelling back through the queue | Our sim; for competitors, manual |

Automatic cut counts only see type 1. A continuous simulation shot with no cuts can still be dense in
types 2-5, and a heavily cut video can be empty of types 3-4. Every analysis below reports the types
separately.

## 2. The research questions, answered as far as evidence allows

### Q1. How often should the visual change?

- **Evidence.** In 25-30 s adverts, each extra second of scene length lowered attentional synchrony
  by ~5%; median scene 2.1 s (IQR 1.5-3 s); cuts helped most where scenes were long, with diminishing
  returns (Wals et al. 2026, R2-F10, Tier B). Measured frame by frame, the reference Short has only 5 hard
  cuts in 60.5 s (shots 7-12 s) and keeps attention with continuous camera moves and on-screen events
  inside each shot (R1 section 5, Tier D); the Blueprint's "2.5-4 s" overstates its cut rate.
- **Uncertainty.** Wals measured cuts, not the other four types, and found no scenes under 1 s.
  Synchrony is not comprehension.
- **Working answer.** Something meaningful (any of types 1-5) about every 1.5-3 s; a hard cut is not
  required if the shot keeps delivering type 3-5 events. Treat > 3 s without any meaningful event as
  a warning, > 5 s as a likely retention dip to check in analytics (hypothesis H4).

### Q2. How long can a single shot stay effective?

- **Evidence.** Wals: the effect of a cut was strongest after long scenes. Film-editing research shows
  shot lengths in popular films have shortened over decades to around a few seconds on average
  (Cutting, DeLong & Nothelfer 2010, *Psychological Science*; prior knowledge, Tier C/D).
- **Working answer.** A shot can run 6-10 s if it contains a continuous process the viewer is
  following and events keep arriving (the slinky collapse, a wave travelling). A static or
  slowly-drifting shot with only narration should not exceed ~4 s.

### Q3. When is a cut better than a camera move?

- **Evidence.** Edit blindness: cuts during continuing motion go unnoticed and preserve tracking
  (Smith & Henderson 2008; R2-F12, Tier C). Cuts boost synchrony (R2-F10). Camera moves keep spatial
  continuity, which matters when the viewer must track one object.
- **Working answer.** *Cut* for a change of scale, perspective or scene, timed on a physical event
  (brake onset, impact). *Move* when the viewer must keep tracking the same object (ease in on the
  bottom coil). Never cut away during the reveal itself; cut after it.

### Q4. When does rapid editing hurt comprehension?

- **Evidence.** Faster pacing raises arousal and memory for calm content but reduces memory for already
  arousing content (Lang et al. 1999; R2-F11, Tier C). Complexity harms attention with a ~0.66 s
  lag (R2-F10). Multimedia segmenting and coherence research: learners need time to build a model of a
  process (Mayer; Tier C).
- **Working answer.** When each cut forces the viewer to re-find the focal object in a new layout.
  Rule: after a hard cut the focal object must appear within 0.3 s near the same screen region, or be
  highlighted; no two hard cuts within 1.2 s.

### Q5. Can continuous motion outperform frequent cuts?

- **Evidence.** None directly for science Shorts. Representational animation helps learning when the
  motion *is* the content (Höffler & Leutner 2007, d = 0.40; R2-F13, Tier C).
- **Working answer.** Plausibly yes for process topics (waves, falling, orbits), if the camera and
  overlays keep producing type 2-4 events. This is Experiment 4 in the brief (continuous tracked
  simulation vs multiple perspectives).

### Q6. How should simulations direct attention?

- **Evidence.** Surprising change attracts gaze (Itti & Baldi 2009; R2-F9). Signalling helps (R2-F14).
  Visual complexity scatters gaze (R2-F10).
- **Working answer.** One focal object at a time, marked with a reserved cue (Blueprint white ground
  ring; brake-light red is the only saturated colour). Everything else calm at the moment of change.

### Q7. What makes a viewer lose track?

Synthesis (Tier C/E): (a) a cut that moves the focal object to an unexpected screen position; (b)
several things moving with no cue which matters; (c) the key signal too small on a phone (reference
Short: brake lights a few pixels big, R2-F21); (d) narration describing something not on screen yet,
or already gone; (e) captions covering the focal object.

### Q8. What information density is appropriate?

- **Evidence.** Working-memory limits (Cowan 2001, *Behavioral and Brain Sciences*: roughly 3-5 chunks;
  prior knowledge, Tier C). Signalling and segmenting research.
- **Working answer.** At most one new idea per beat; at most 3 objects that matter on screen at once;
  one measurement card at a time (text spec TX-3).

### Q9. How much screen should one object take? How much empty space?

- **Evidence.** No direct study for Shorts. Phone-viewing legibility is the constraint: a 1080×1920
  frame shown ~7 cm wide makes 1% of width ≈ 0.7 mm.
- **Working answer (Tier E).** Focal object ≥ 6% of frame height or ≥ 10% of frame width at its key
  moment; its key signal (brake light, coil) ≥ 1% of frame width (≈ 11 px) with bloom. Keep
  ≥ 40% of the frame low-detail (sky, asphalt, grass) so the focal object stands out (figure-ground).

### Q10. How should complexity evolve?

- **Evidence.** Complexity hurts synchrony with a delay (R2-F10); busy setups can be followed by calm
  reveals (R2-F11).
- **Working answer.** Start simple (one system, one focal object), add elements only as the
  explanation needs them, peak complexity in the "why" section, and strip back for the reveal and
  takeaway. Pull-outs to show scale (Blueprint shot 5) belong after the mechanism is understood.

## 3. Pacing patterns by structure

| Script structure | Recommended pacing | Why |
|---|---|---|
| B result-first | Fast opening (anomaly), slower explanation, calm landing | The anomaly needs no setup; the explanation needs room |
| D prediction | Held setup (prediction window), fast test, held reveal, calm why | Suspense then surprise (R2-F7, F19) |
| E escalation | Accelerating | Matches the physics: consequences grow |
| G variable sweep | Alternating: change → hold → change | Each new value needs a moment to read |
| C hidden mechanism | Constant moderate with a slowdown at the mechanism | Even progress, emphasis where the insight is |
| H story | Slower setup with a rapid final demonstration | Story context first, experiment as climax |

## 4. Candidate visual styles

| Style | Readability on phone | Render cost (our stack) | Storytelling fit | Status |
|---|---|---|---|---|
| Low-poly 3D diorama (Blueprint) | High if focal signals are large and bloomed | Medium-high (3D renderer in progress) | Excellent for traffic, vehicles, everyday scenes | **House style**, chosen by Caesar |
| Minimal 2D diagram (current Matplotlib) | Very high | Low (≈ real time on 4 cores) | Good for maths, waves, abstract systems | Keep as fallback and for maths topics, styled with Blueprint palette |
| Animated graph | High for one curve | Low | Good as a short inset for a measured quantity | Use as level-4 card, not over the 3D world (Blueprint section 7) |
| Split-screen comparison | Halves object size on 9:16 | Low | Good for one-variable comparisons | Prefer stacked (top/bottom) or same-scene comparison |
| Top-down system view | High for patterns (jams, flows) | Medium | Good for "the whole system" beats | Blueprint shot 3 |
| Side-view mechanism | High for vertical motion | Low-medium | Good for falling, pendulums, springs | Add as a Blueprint camera for non-traffic topics |

The Blueprint is written around traffic. Non-traffic topics (slinky, projectiles, probability) need
the same world and palette with additional shot types: a side-view "bench" shot and a close-up macro
shot. Proposed for the pipeline thread; not a change to the house style.

## 5. Open items for revision 2

- Measure type 1-5 event intervals (distributions, not means) on 40-60 competitor Shorts (Report 01).
- Compare high- vs median-performing Shorts within the same channels on event gaps and opening frames.
- Phone-screenshot check of Shorts UI overlays to replace the Tier D safe-area numbers.

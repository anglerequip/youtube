# Script engine specification

Counterphysical research lab, v1, 2026-11-19. Builds on `RESEARCH_REPORT_02_ATTENTION_AND_COGNITION.md`
(R2-F#), `HOOK_ENGINE_SPECIFICATION.md` (HK-#) and the Visual Blueprint in `CLAUDE.md`.

A script here is not text that reads well. It is a timed sequence of claims, each tied to something
that changes on screen. The engine's job is to produce narration, delivery direction and a visual
plan that can be checked against each other.

## 1. Principles and their evidence

| # | Principle | Tier | Evidence | What the engine does |
|---|---|---|---|---|
| P1 | One question per Short, answered | C/E | R2-F18 (short videos, one idea), R2-F6 (curiosity must be resolved) | Script has exactly one `thesis`; QA fails if the hook's promise isn't paid off |
| P2 | Name the wrong intuition, then break it | **B** | R2-F8 (Muller et al. 2008, physics videos) | `misconception` field required for counterintuitive topics; it must be spoken or shown before the reveal |
| P3 | Let the simulation show; narration adds meaning | C | R2-F13 (representational animation helps), Mayer coherence | Lint flags beats whose narration only describes motion already visible ("the ball moves left") without a reason or consequence |
| P4 | Coherent causal chain | C | Mental-model research; R2-F8 | `causal_chain` field: 2-4 links, each mapped to a beat and a visual event |
| P5 | Real progress every few seconds | B/E | R2-F10 (long unchanging scenes lose attention), R2-F21 | Every beat answers a `viewer_question` and contains ≥ 1 meaningful visual event |
| P6 | No unnecessary setup | E | Creator practice (D) | Context beats allowed only if a later beat depends on them (`depends_on`) |
| P7 | Keep the qualifications that matter | brief rule | Honesty; R2-F20 (stories reduce scrutiny, so our duty is higher) | Caveats tagged `material: true` must appear in narration or on screen, not just the description |
| P8 | No false suspense | E | R2 conflicts table | Withhold only the final mechanism; QA flags beats with no new information |
| P9 | Hold still at the payoff | C | R2-F9, F11 | Reveal beat has `pace: reveal` (low background motion, pause after) |

## 2. Structures

Eight structures from the brief, with the topic types they fit. Choosing one is a creative decision
recorded in the script; no structure is mandatory.

| Key | Structure | Best for | Weak for | Pairs with hook families |
|---|---|---|---|---|
| A | Question → experiment → explanation → answer | Clear yes/no or which-one questions | Topics without a single answer | 2, 3, 16 |
| B | Surprising result → backwards explanation | Visually striking anomalies (slinky) | Results that need setup to look strange | 1, 12 |
| C | Familiar problem → hidden mechanism → demonstration | Everyday mysteries (traffic, kettles) | Abstract maths | 3, 8 |
| D | Prediction → test → unexpected result → explanation | Misconception topics (falling objects, Monty Hall) | Results most people predict correctly | 2, 7 |
| E | Small cause → escalating consequence → insight | Chain reactions, instabilities, traffic waves | Equilibrium phenomena | 11, 6 |
| F | Two explanations → experiment → resolution | Topics with a popular wrong explanation (lift, tides) | Topics where one explanation is obviously silly | 7, 15 |
| G | Progressive simulation with changing variables | Thresholds, phase changes, optimisation | Single-moment phenomena | 6, 13 |
| H | Story of a discovery → experiment → principle | Historical experiments (Sugiyama 2008, Galileo's ramps) | Topics without a real, sourced story | 3, 4 |

Selection rule (default, Tier E): the topic record lists a `key_visual_moment` and a `misconception`.
If the key moment is striking alone → B. If a documented misconception exists and the result is
binary → D. If the phenomenon grows from a small cause → E. If a variable has a visible threshold
→ G. Otherwise A or C. The generator drafts the chosen structure plus one alternative.

## 3. Duration

Duration follows information load, not a fixed target. Platform limit is 3 minutes (R2-F3); no
evidence picks a number (R2 "not automated"). Bands below are starting hypotheses (Tier E) and the
QC warns, never fails, outside them.

| Topic type | Typical links in causal chain | Band (s) |
|---|---|---|
| Single visual demonstration | 1 | 20-35 |
| Simple physical explanation | 2 | 30-45 |
| Multistep simulation / escalation | 3 | 40-60 |
| Engineering comparison | 2-3 | 40-60 |
| Concept needing context | 3-4 | 45-75 |
| Discovery story | 3-4 | 45-90 |

Rule of thumb for the generator: target ≈ 12 s per causal link + 6 s for hook + 5 s for takeaway.

## 4. Machine-checkable rules

All thresholds live in `config/script_rules.yaml`. "Warn" means QC reports it for review; "fail"
means the episode can't reach PENDING_APPROVAL until fixed or the rule is overridden with a reason.

| ID | Rule | Default | Level | Tier |
|---|---|---|---|---|
| SC-1 | Beats per episode | 6-10 | warn | house rule |
| SC-2 | Overall speech rate (words ÷ narrated seconds, excluding pauses) | 150-185 wpm target; warn outside 140-200 | warn | C (R2-F17) |
| SC-3 | Per-beat speech rate | ≤ 210 wpm | warn | C |
| SC-4 | Sentence length | ≤ 18 words each; mean 7-13 | warn | E (short sentences help TTS prosody and captioning; long ones allowed when they carry a causal "because") |
| SC-5 | Beat narration length | ≤ 30 words (≈ 10 s) | warn | B/E (R2-F10: each beat should get a visual event; long beats invite static stretches) |
| SC-6 | Hook rules | HK-1 to HK-11 | per hook spec | — |
| SC-7 | First substantive claim (a sentence that states a fact about the system) | by 3.0 s | fail | E, = HK-3 |
| SC-8 | First partial payoff (something explained or shown that answers part of the hook) | by 12 s or 30% of duration, whichever is later | warn | E (P8) |
| SC-9 | Reveal beat (main answer) starts | 40-85% of duration | warn | E |
| SC-10 | Takeaway beat duration | ≥ 2.5 s narrated, and the final frame holds ≥ 0.8 s after the last word | fail | E (the final insight needs time, brief Part XII) |
| SC-11 | New technical terms (words not in the 5,000 most common English words and not in an allow-list) | ≤ 2, each defined in the same or next sentence | warn | C (cognitive load) |
| SC-12 | Independent claims | ≤ 5 | warn | E |
| SC-13 | Every number in narration or on-screen text is backed by `sources`, a `self_checks()` result, or marked `illustrative` | required | fail | brief rule |
| SC-14 | Absolute words ("always", "never", "every", "impossible", "all", "no one", "instantly", "at all", "not even a little") | flagged for review with the matching caveat | warn | brief rule |
| SC-15 | Filler words ("basically", "actually", "literally", "really", "so yeah", "kind of", "you know") | ≤ 1 per episode | warn | E |
| SC-16 | Each beat declares `viewer_question` and ≥ 1 `visual_events` entry (type 1-5, see visual spec) | required | fail | B/E (P5) |
| SC-17 | `misconception` spoken or shown before the reveal beat | required when `topic.counterintuitive: true` | fail | B (P2) |
| SC-18 | Hook `promise` matched by `payoff_beat`, which must contain the visual evidence | required | fail | C (HK-7) |
| SC-19 | Material caveats in narration or on-screen text | required | fail | P7 |
| SC-20 | Originality: no 8-word sequence shared with any transcript in `research/transcripts/` or any of our earlier scripts; flag cosine similarity > 0.85 of sentence embeddings | flag | warn | brief rule |
| SC-21 | Narration describes motion with no added meaning (lint heuristic: beat text matches only motion verbs + the focal noun) | flag | warn | C (P3) |
| SC-22 | Ending call-to-action ("follow", "subscribe", "like") | flagged; allowed by config `script.allow_cta` | warn | E (R2 "not automated" item 6) |

The current house rule in `CLAUDE.md` (6-9 beats, 25-45 s) remains the default band for single-step
topics; SC-1 and section 3 widen it only when the topic needs more links.

## 5. Script generator output

The brief's fields A-K map onto an extended `storyboard.yaml`. New fields are optional for the
renderer (it only needs `beats`), so existing episodes keep working.

```yaml
slug: horizontal-vs-dropped
thesis: "A ball fired sideways hits the ground at the same time as one dropped from the same height,
  because sideways speed doesn't change how fast it falls."                 # A
sources:                                                                  # B
  - "Any introductory mechanics text: independence of horizontal and vertical motion, e.g. OpenStax University Physics Vol. 1, section 4.3 (Projectile Motion)"
audience: "No physics background. Knows things fall. No algebra."         # C
hook_ref: hooks.yaml#H3                                                   # D
structure: D                                                              # D/E
misconception: "A ball fired fast sideways stays in the air longer."
causal_chain:                                                             # E
  - "Gravity pulls both balls down equally hard."
  - "Sideways speed adds no upward push."
  - "So both drop the same distance in the same time."
caveats:                                                                  # K
  - text: "Air resistance is ignored; with real air, a very fast ball can behave slightly differently."
    material: true
  - text: "At extreme speeds, Earth's curvature matters (that's how orbits work)."
    material: false
duration_band: [30, 45]
beats:
  - id: hook
    text: "One ball is dropped. One is fired sideways. Which lands first?"  # G
    viewer_question: "Which ball lands first?"
    visual_events:                                                        # F
      - {t: 0.0, type: object_motion, what: "both balls on the ledge, launcher arm drawn back"}
    delivery: {pace: brisk, emphasis: ["dropped", "sideways"]}            # H
    prediction_window_s: 1.2
  - id: reveal
    text: "They land at exactly the same moment."
    viewer_question: "What happens?"
    visual_events:
      - {t: 0.0, type: state_change, what: "both released"}
      - {t: 0.5, type: info_reveal, what: "impact flash on both, same frame"}
    delivery: {pace: reveal, pause_after: 0.6}
    reveal: true                                                          # I
  # ...
final_insight: "Falling doesn't care how fast you're going sideways."     # J
```

### 5.1 Delivery direction (H)

Delivery is written as structured fields, not inline symbols, so every voice provider can use what it
supports:

- `pace`: `brisk` (hook), `calm` (setup/explanation), `build` (escalation), `reveal` (slower, pause after), `hold` (no narration, visual only).
- `emphasis`: words to stress. Providers that support SSML/emphasis use it; Kokoro can approximate with a comma before the word or splitting the sentence.
- `pause_after`: seconds (already supported by the factory).
- `speed`: per-beat multiplier (0.9-1.1) on the episode speed.

Defaults per pace (Tier E, refine after the voice audition): brisk 1.05×, calm 1.0×, build 1.03×,
reveal 0.95× + 0.5 s pause after, hold = 1.0-2.0 s of silence with sound design only.

Punctuation affects TTS performance: full stops produce the clearest prosody; commas give short
pauses; em dashes and semicolons are read inconsistently by TTS, so the lint converts them to full
stops or commas.

## 6. Script QA

Two layers.

**Automatic (QC, before human review):** all SC rules above, plus the hook rules. Output is a QA
section in the QC report with pass/warn/fail per rule and the offending text.

**Fact pass (by the writing session, recorded in the storyboard):** for every claim in `causal_chain`
and every number, list the source or self-check. A claim that can't be traced is removed or marked
as the model's own result ("in this simulation...").

**Reject** (from the brief) when any of these hold, mapped to rules:

| Brief reject reason | Rule(s) |
|---|---|
| Unsupported scientific claims | fact pass, SC-13 |
| Misleading absolutes | SC-14 + human review |
| Depends on an unverified number | SC-13 |
| Unintelligible without prior knowledge | SC-11, audience field |
| Substantial filler | SC-15, P8 check (beats with no new `viewer_question` answered) |
| No meaningful visual progression | SC-16, visual-event gap check |
| Fails to resolve the opening premise | SC-18 |
| Copies another creator's wording | SC-20 |
| Needs visuals the system can't render faithfully | feasibility gate in the hook spec, component check |

**Quality score** (advisory, 0-5 each, weights in `config/script_rules.yaml`): clarity of thesis,
strength of causal chain, visual-narration fit, pacing (no stagnant beats), payoff strength,
accuracy and honesty of caveats, originality, takeaway memorability. A model-generated score never
replaces watching the render (brief Part XXI).

## 7. Representative scripts

These follow the rules above. They are drafts for the pipeline thread to render, not final copy.
Word counts and durations assume ~170 wpm.

### 7.1 Falling slinky, revised (structure B, hook family 1)

Changes from the current storyboard: the hook shows the anomaly in frame 0 (HK-1), drops "not even a
little" (HK-11/SC-14), names the intuition (SC-17), removes the follow CTA (SC-22, test), and adds an
explicit takeaway hold.

| Beat | Narration | Viewer question | Visual events | Delivery |
|---|---|---|---|---|
| hook | "The top of this slinky is falling. The bottom isn't." | Why isn't the bottom falling? | t=0 mid-collapse, bottom hovering, white ring on bottom coil | brisk; emphasis "isn't" |
| rewind | "Let's go back to just before I let go." | What was the setup? | rewind to hanging state (state change) | calm |
| setup | "Gravity pulls every coil down. The spring pulls each one up. They balance." | Why is it still? | force arrows appear on bottom coil (info reveal) | calm |
| intuition | "So when you let go, you'd expect the whole thing to drop at once." | What should happen? | ghost overlay of a rigid drop, labelled "what you'd expect" (info reveal) | calm |
| release | "Watch the bottom." | — | release (state change), camera eases in on bottom (camera) | reveal; pause 0.3 |
| hover | "The top races down. The bottom hangs there for about a quarter of a second." | How long does it hover? | timer label counting (info reveal) | calm |
| why | "Nothing has changed for the bottom coil yet. Its forces are still balanced. The news of the release travels down the spring, coil by coil." | Why does it wait? | pulse highlight travels down coils (object motion) | calm; emphasis "coil by coil" |
| land | "Only when the collapse arrives does the bottom start to fall." | When does it move? | collapse front reaches bottom; thud (state change) | reveal; pause 0.4 |
| takeaway | "Even in a toy, it takes time for the news to travel." | — | hold on landed slinky, 1 s | calm; hold 1.0 |

≈ 95 words, ≈ 36 s + pauses ≈ 40 s. Caveat on screen in small text at the hover beat or in the
description: "Ideal spring model; a real bottom coil moves about a millimetre." (material: decide in
review; the hook no longer claims zero movement, so it can be non-material).

### 7.2 Traffic waves (structure E, hook family 11)

Sources: Sugiyama et al. 2008, *New Journal of Physics* 10, 033001 (22 cars on a 230 m circuit form a
jam without a bottleneck); Bando et al. 1995, *Physical Review E* 51, 1035 (optimal velocity model);
Stern et al. 2018, *Transportation Research Part C* 89, 205-221 (one automated car dampened stop-and-go
waves on a ring). The wave speed quoted must be measured from our own simulation (self-check), and
presented as "in this model", with the real-world range attributed to its source.

| Beat | Narration | Viewer question | Visual events |
|---|---|---|---|
| hook | "One driver taps the brakes. Watch the car thirty places behind." | What happens back there? | chase cam behind highlighted car, brake glow (object motion); white ring on car 30 in distance |
| intuition | "You'd think a small tap fades out as it passes back." | Does it fade? | label "small tap" on car 1 (info reveal) |
| chain | "But each driver reacts a little late, and brakes a little harder than the one in front." | Why would it grow? | cut on brake to highway centreline shot (hard cut); brake glows propagate backward (object motion) |
| grow | "By car thirty, the tap has become a full stop." | How big does it get? | car 30 stops, ring highlight (state change) |
| wave | "The jam itself moves backward, even though every car drives forward." | Which way does the jam move? | top-down: jam region shaded, label "jam moving backward" with measured speed (info reveal) |
| source | "In this model, the jam forms with no accident and no obstacle. Just reaction and spacing." | So where's the cause? | pull-out to whole road (camera) |
| fix | "Leave a bigger gap, brake gently, and the wave dies out." | Can it be stopped? | same road, one car with large gap; wave damps (state change) |
| takeaway | "The car that causes your jam might be minutes ahead of you." | — | hold on flowing traffic 1 s |

≈ 105 words, ≈ 45 s. Material caveat (voiced in "source" beat): waves form only above a critical
density; at low density the tap does fade out. Add to "intuition" or "fix" if it doesn't fit.

### 7.3 Horizontal vs dropped (structure D, hook family 2)

| Beat | Narration | Visual events |
|---|---|---|
| hook | "One ball is dropped. One is fired sideways. Which lands first?" | side view, both balls on the ledge (object motion: launcher cocks); 1.2 s prediction window |
| intuition | "Most people say the dropped one. The fast one should stay up longer." | label "the fast one stays up?" (info reveal) |
| test | "Let's fire." | release (state change) |
| reveal | "They land at exactly the same moment." | impact flash both, same frame; slow-motion replay (state change + camera) |
| why1 | "Gravity pulls both down just as hard." | equal down arrows on both (info reveal) |
| why2 | "Going sideways doesn't add any upward push. So both fall the same height in the same time." | strobe trail: both balls at equal heights at each tick (info reveal) |
| caveat | "That's without air. Real air slows the fast one slightly." | small label "no air resistance" (info reveal) |
| takeaway | "Falling doesn't care how fast you're going sideways." | hold on the two strobe trails 1 s |

≈ 80 words, ≈ 30-35 s.

## 8. Experiments that test this spec

| Exp | Variable | Arms | Primary metric | Note |
|---|---|---|---|---|
| S1 | Misconception stated vs not (P2) | refutation vs direct | APV + mechanism comments | Matched, different topics; offline quiz first |
| S2 | Structure B (result-first) vs D (prediction-first) | B vs D | APV | = brief Experiment 6 |
| S3 | Duration | band low vs band high for comparable topics | watch time per engaged view | = brief Experiment 5 |
| S4 | CTA ending vs none (SC-22) | with vs without | subs per 1k engaged views, APV | cheap; alternate over 10+ episodes |
| S5 | Speech rate | 160 vs 180 wpm | APV | only after voice is fixed |

Each experiment follows the analysis rules in the hook spec section 8 (≥ 8 episodes per arm,
intervals, confounders recorded, no near-duplicate uploads).
